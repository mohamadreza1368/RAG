"""
ماژول اجرای فرآیند استخراج جامع (Bulk Ingestion Pipeline)
دارای قابلیت ذخیره‌سازی ترتیبی (Checkpointing / Resume)، رعایت سقف نرخ درخواست (Rate Limit)
و تفکیک خطاهای گذرا جهت استخراج امن و کامل تمام ۱۲۸۲ قانون بازار سرمایه.
"""

import sys
import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional
from datetime import datetime

from .client import SeoRuleClient
from .config import config, CrawlerConfig
from .models import CompleteDocumentPackage

logger = logging.getLogger("regulatory_crawler")


class BulkExtractor:
    """مدیریت و اجرای استخراج انبوه و امن داده‌های سامانه قوانین"""

    def __init__(self, client: Optional[SeoRuleClient] = None):
        self.client = client or SeoRuleClient()
        self.cfg = self.client.cfg

        # پوشه‌ها
        self.raw_dir = self.cfg.raw_data_dir
        self.rules_dir = self.raw_dir / "rules"
        self.rules_dir.mkdir(parents=True, exist_ok=True)

        # فایل‌های وضعیت و ایندکس
        self.checkpoint_file = self.raw_dir / "ingestion_checkpoint.json"
        self.index_file = self.raw_dir / "rules_index.json"
        self.categories_file = self.raw_dir / "categories.json"

        # بارگذاری وضعیت ذخیره‌شده قبلی (جهت Resume)
        self.completed_rule_ids: Set[int] = self._load_checkpoint()

    def _load_checkpoint(self) -> Set[int]:
        """بارگذاری شناسه‌های قوانینی که قبلاً با موفقیت استخراج شده‌اند"""
        if self.checkpoint_file.exists():
            try:
                data = json.loads(self.checkpoint_file.read_text(encoding="utf-8"))
                completed = set(data.get("completed_ids", []))
                logger.info(f"سابقه استخراج قبلی بارگذاری شد: {len(completed)} سند از قبل تکمیل شده است.")
                return completed
            except Exception as e:
                logger.warning(f"خطا در خواندن فایل چک‌پوینت: {e}")
        return set()

    def _save_checkpoint(self, rule_id: int) -> None:
        """ثبت آنی شناسه سند موفق در فایل چک‌پوینت"""
        self.completed_rule_ids.add(rule_id)
        data = {
            "last_updated": datetime.now().isoformat(),
            "total_completed": len(self.completed_rule_ids),
            "completed_ids": sorted(list(self.completed_rule_ids)),
        }
        self.checkpoint_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def fetch_and_save_categories(self) -> List[dict]:
        """استخراج و ذخیره کامل درختواره دسته‌بندی‌ها"""
        logger.info("در حال استخراج درختواره دسته‌بندی‌های موضوعی...")
        categories = self.client.get_all_categories()
        cat_dicts = [c.model_dump() for c in categories]
        self.categories_file.write_text(
            json.dumps(cat_dicts, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"{len(categories)} دسته‌بندی استخراج و در {self.categories_file.name} ذخیره شد.")
        return cat_dicts

    def build_rules_index(self, force_refresh: bool = False) -> List[dict]:
        """
        دریافت فهرست تمام اسناد سامانه (۱۲۸۲ سند) از طریق پیجینیشن اندپوینت جستجو
        و ذخیره خلاصه فراداده‌ها در rules_index.json
        """
        if self.index_file.exists() and not force_refresh:
            logger.info(f"فایل ایندکس اسناد از قبل موجود است: {self.index_file.name}")
            try:
                return json.loads(self.index_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        logger.info("شروع فهرست‌برداری کامل اسناد از سامانه (Indexing)...")
        all_rules: List[dict] = []
        seen_ids = set()
        page = 1
        page_size = 50
        total_pages = None

        while True:
            logger.info(f"در حال دریافت فهرست اسناد - صفحه {page}" + (f" از {total_pages}" if total_pages else "") + "...")
            rules, pagination = self.client.search_rules_with_pagination(page_number=page, page_size=page_size)
            if not rules:
                break

            if pagination and "TotalPages" in pagination:
                total_pages = pagination["TotalPages"]

            new_in_page = 0
            for r in rules:
                if r.ruleId not in seen_ids:
                    seen_ids.add(r.ruleId)
                    all_rules.append(r.model_dump())
                    new_in_page += 1

            logger.info(f"تعداد اسناد شناسایی‌شده تا این لحظه: {len(all_rules)}")

            # توقف در صورت رسیدن به صفحه آخر یا نبود داده جدید
            if total_pages and page >= total_pages:
                break
            if new_in_page == 0:
                break

            page += 1


        self.index_file.write_text(
            json.dumps(all_rules, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"فهرست‌برداری پایان یافت: مجموعاً {len(all_rules)} سند در {self.index_file.name} ذخیره شد.")
        return all_rules

    def run(
        self,
        limit: Optional[int] = None,
        category_id: Optional[int] = None,
        force_reingest: bool = False,
    ) -> None:
        """
        اجرای خط استخراج کامل اسناد با رعایت Rate Limit و ثبت پیشرفت
        """
        # ۱. استخراج دسته‌بندی‌ها
        self.fetch_and_save_categories()

        # ۲. ایجاد/بروزرسانی ایندکس قوانین
        all_rules = self.build_rules_index()

        # فیلتر بر اساس دسته‌بندی در صورت درخواست
        if category_id:
            all_rules = [r for r in all_rules if r.get("categoryId") == category_id]
            logger.info(f"فیلتر بر اساس دسته {category_id}: {len(all_rules)} سند انتخاب شد.")

        total_rules = len(all_rules)
        logger.info(f"تعداد کل اسناد برای پردازش: {total_rules}")

        start_time = time.time()
        processed_count = 0
        success_count = 0
        skipped_count = 0
        error_count = 0

        for idx, rule_meta in enumerate(all_rules, start=1):
            rule_id = rule_meta["ruleId"]
            title = rule_meta.get("title", f"Rule_{rule_id}")

            # بررسی وضعیت چک‌پوینت
            rule_file = self.rules_dir / f"{rule_id}.json"
            if not force_reingest and rule_id in self.completed_rule_ids and rule_file.exists():
                skipped_count += 1
                continue

            if limit and processed_count >= limit:
                logger.info(f"محدودیت تعداد ({limit} سند) به پایان رسید.")
                break

            processed_count += 1
            progress_pct = (idx / total_rules) * 100
            elapsed = time.time() - start_time
            logger.info(
                f"[{idx}/{total_rules}] ({progress_pct:.1f}%) استخراج سند {rule_id}: "
                f"{title[:50]}..."
            )

            try:
                package = self.client.fetch_complete_rule(rule_id)
                if package:
                    # ذخیره پکیج سند در فایل اختصاصی
                    rule_file.write_text(
                        json.dumps(package.model_dump(), ensure_ascii=False, indent=2),
                        encoding="utf-8"
                    )
                    self._save_checkpoint(rule_id)
                    success_count += 1
                else:
                    logger.warning(f"پکیج سند {rule_id} خالی بازگردانده شد.")
                    error_count += 1
            except Exception as exc:
                logger.error(f"خطای غیرمنتظره در استخراج سند {rule_id}: {exc}")
                error_count += 1

        total_time = time.time() - start_time
        logger.info("==================================================")
        logger.info("پایان عملیات استخراج اسناد:")
        logger.info(f"  - کل اسناد فهرست: {total_rules}")
        logger.info(f"  - قبلاً استخراج‌شده (رد شده): {skipped_count}")
        logger.info(f"  - با موفقیت استخراج‌شده در این اجرا: {success_count}")
        logger.info(f"  - خطاها: {error_count}")
        logger.info(f"  - زمان کل: {total_time / 60:.1f} دقیقه")
        logger.info(f"  - پوشه خروجی اسناد: {self.rules_dir}")
        logger.info(f"  - پوشه فایل‌های پیوست: {self.cfg.attachments_dir}")
        logger.info("==================================================")
