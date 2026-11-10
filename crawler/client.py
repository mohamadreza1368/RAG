"""
کلاینت ارتباطی مقاوم با پایگاه قوانین و مقررات بازار سرمایه (cmr.seo.ir)
دارای قابلیت اتصال مستقیم از کارت شبکه فیزیکی، کنترل نرخ درخواست (Rate Limit) و تلاش مجدد (Retry)
"""

import time
import base64
import hashlib
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
import urllib3

from .config import config, CrawlerConfig
from .utils import detect_physical_active_ip
from .models import (
    RuleCategory,
    RuleSummary,
    RuleVersionDetail,
    RulePart,
    RuleDependency,
    RuleAttachment,
    CompleteDocumentPackage,
)

# غیرفعال‌سازی هشدارهای مربوط به گواهی SSL داخلی
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("regulatory_crawler")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class SourceAddressAdapter(HTTPAdapter):
    """
    آداپتور شبکه اختصاصی برای مقید کردن سوکت‌های TCP به یک آی‌پی کارت شبکه مشخص.
    جهت اطمینان از خروج ترافیک از شبکه ملی و عدم رد درخواست توسط فایروال بورس.
    """
    def __init__(self, source_address: tuple[str, int], **kwargs):
        self.source_address = source_address
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["source_address"] = self.source_address
        return super().init_poolmanager(*args, **kwargs)


class SeoRuleClient:
    """کلاینت تعامل با وب‌سرویس‌های پایگاه قوانین سازمان بورس"""

    def __init__(self, cfg: Optional[CrawlerConfig] = None):
        self.cfg = cfg or config
        self.session = requests.Session()
        self.session.verify = False

        # تنظیم هدرهای استاندارد مرورگر
        self.session.headers.update({
            "User-Agent": self.cfg.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "fa,en-US;q=0.9,en;q=0.8",
            "Origin": self.cfg.site_origin,
            "Referer": f"{self.cfg.site_origin}/",
        })

        # تنظیم اتصال از طریق کارت شبکه فیزیکی در صورت فعال بودن
        self._configure_source_ip()

        self._last_request_time = 0.0

    def _configure_source_ip(self) -> None:
        source_ip = self.cfg.manual_source_ip
        if not source_ip and self.cfg.bind_physical_ip:
            source_ip = detect_physical_active_ip()

        if source_ip:
            adapter = SourceAddressAdapter((source_ip, 0), max_retries=self.cfg.max_retries)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)
            logger.info(f"سوکت‌های ارتباطی به آی‌پی محلی {source_ip} متصل شدند.")
        else:
            logger.info("از مسیریابی استاندارد سیستم‌عامل استفاده می‌شود.")

    def _rate_limit(self) -> None:
        """اعمال فاصله زمانی بین درخواست‌ها جهت رعایت اخلاق وب‌کاوی"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.cfg.rate_limit_delay:
            time.sleep(self.cfg.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        url = f"{self.cfg.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        self._rate_limit()

        for attempt in range(1, self.cfg.max_retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.cfg.timeout,
                    **kwargs
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"منبع یافت نشد (404): {url}")
                    return None
                else:
                    logger.warning(f"خطای HTTP {response.status_code} در درخواست به {url} (تلاش {attempt})")
            except (requests.RequestException, Exception) as exc:
                logger.warning(f"خطای ارتباطی در {url}: {exc} (تلاش {attempt} از {self.cfg.max_retries})")

            if attempt < self.cfg.max_retries:
                time.sleep(self.cfg.retry_backoff_factor * attempt)

        raise RuntimeError(f"ارتباط با اندپوینت {url} پس از {self.cfg.max_retries} تلاش ناموفق بود.")

    # -------------------------------------------------------------
    # ۱. دسته‌بندی‌ها (Rule Categories)
    # -------------------------------------------------------------
    def get_all_categories(self) -> List[RuleCategory]:
        """دریافت کل درختواره دسته‌بندی‌های موضوعی"""
        data = self._request("GET", "RuleCategories/getall")
        if not data:
            return []
        return [RuleCategory(**item) for item in data]

    def get_category_recursive(self, category_id: int) -> Optional[dict]:
        """دریافت سلسله‌مراتب درختی یک دسته‌بندی"""
        return self._request("GET", f"RuleCategories/getrecurseive/{category_id}")

    # -------------------------------------------------------------
    # ۲. جستجو و فهرست قوانین (Search & Rule Listings)
    # -------------------------------------------------------------
    def search_rules(
        self,
        category_id: Optional[int] = None,
        page_number: int = 1,
        page_size: int = 50,
        sort: Optional[List[dict]] = None
    ) -> List[RuleSummary]:
        """
        جستجو و بازیابی فهرست قوانین در یک دسته‌بندی یا به صورت عمومی
        """
        payload: Dict[str, Any] = {
            "PageNumber": page_number,
            "PageSize": page_size,
            "IsPartSearch": False,
            "Sort": sort or [{"id": "Title", "desc": True}],
        }
        if category_id and category_id > 0:
            payload["CategoryId"] = category_id

        data = self._request("POST", "Search/searchrule", json=payload)
        if not data or not isinstance(data, list):
            return []
        return [RuleSummary(**item) for item in data]

    # -------------------------------------------------------------
    # ۳. جزییات قانون و نسخه‌ها (Rule Details & Versions)
    # -------------------------------------------------------------
    def get_rule_base_info(self, rule_id: int) -> Optional[dict]:
        """دریافت اطلاعات پایه قانون"""
        return self._request("GET", f"Rules/{rule_id}")

    def get_rule_versions(self, rule_id: int) -> List[dict]:
        """دریافت تاریخچه نسخه‌های یک قانون"""
        payload = {
            "RuleId": rule_id,
            "Filter": "",
            "Sort": "Id asc",
            "PageNumber": 1,
            "PageSize": 100,
        }
        data = self._request("POST", "RuleVersions/search", json=payload)
        return data if isinstance(data, list) else []

    def get_version_detail(self, version_id: int) -> Optional[dict]:
        """دریافت اطلاعات تفصیلی یک نسخه مشخص"""
        return self._request("GET", f"RuleVersions/{version_id}")

    # -------------------------------------------------------------
    # ۴. ساختار درونی مواد و بندها (Rule Parts / Articles)
    # -------------------------------------------------------------
    def get_rule_parts(self, version_id: int) -> List[RulePart]:
        """دریافت ساختار کامل فصول، مواد، بندها و تبصره‌های نسخه"""
        data = self._request("GET", f"RuleParts/getwithrelated/{version_id}")
        if not data or not isinstance(data, list):
            return []
        return [RulePart(**item) for item in data]

    # -------------------------------------------------------------
    # ۵. روابط سندی و پیوندها (Dependencies & Relations)
    # -------------------------------------------------------------
    def get_version_dependencies(self, version_id: int) -> List[RuleDependency]:
        """دریافت روابط سندی و پیوندهای نسخه قانون با سایر مقررات"""
        data = self._request("GET", f"VersionDependencies/alldependencies/{version_id}")
        if not data or not isinstance(data, list):
            return []
        return [RuleDependency(**item) for item in data]

    def get_part_dependencies(self, part_id: int) -> List[dict]:
        """دریافت روابط و ارجاعات در سطح یک ماده یا بند خاص"""
        data = self._request("GET", f"PartDependencies/alldependencies/{part_id}")
        return data if isinstance(data, list) else []

    # -------------------------------------------------------------
    # ۶. دانلود و ذخیره‌سازی فایل‌های پیوست (Attachments)
    # -------------------------------------------------------------
    def save_attachment(self, file_info: dict, target_dir: Optional[Path] = None) -> Optional[RuleAttachment]:
        """
        ذخیره فایل پیوست (PDF یا DOCX) از محتوای Base64 موجود در وب‌سرویس بر روی دیسک
        همراه با محاسبه هش SHA-256 جهت تطبیق با بند ۸ و ۹ سند معماری
        """
        target_dir = target_dir or self.cfg.attachments_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        file_id = file_info.get("id")
        file_name = file_info.get("name") or f"file_{file_id}.pdf"
        file_guid = file_info.get("fileGuid")
        file_type = file_info.get("fileType")
        b64_content = file_info.get("dataFiles")

        if not b64_content:
            logger.warning(f"محتوای فایلی برای پیوست {file_id} وجود ندارد.")
            return None

        # پاکسازی نام فایل از کاراکترهای غیرمجاز در سیستم‌عامل
        safe_filename = "".join(c for c in file_name if c not in r'\/:*?"<>|')
        file_path = target_dir / f"{file_id}_{safe_filename}"

        try:
            binary_data = base64.b64decode(b64_content)
            file_path.write_bytes(binary_data)
            sha256_hash = hashlib.sha256(binary_data).hexdigest()

            logger.info(f"فایل پیوست با موفقیت ذخیره شد: {file_path.name} ({len(binary_data):,} بایت، هش: {sha256_hash[:8]}...)")

            return RuleAttachment(
                id=file_id,
                fileGuid=file_guid,
                name=file_name,
                fileType=file_type,
                local_path=str(file_path),
                file_size_bytes=len(binary_data)
            )
        except Exception as exc:
            logger.error(f"خطا در دیکود یا ذخیره فایل {file_name}: {exc}")
            return None

    # -------------------------------------------------------------
    # ۷. پکیج جامع یک سند (Complete Document Ingestion)
    # -------------------------------------------------------------
    def fetch_complete_rule(self, rule_id: int) -> Optional[CompleteDocumentPackage]:
        """
        دریافت تمام و کمال یک سند شامل مشخصات پایه، آخرین نسخه معتبر،
        تمام مواد و بندها، روابط با سایر اسناد و ذخیره پیوست‌های رسمی.
        """
        logger.info(f"شروع دریافت کامل سند با شناسه {rule_id}...")
        rule_info = self.get_rule_base_info(rule_id)
        if not rule_info:
            logger.error(f"اطلاعات پایه سند {rule_id} یافت نشد.")
            return None

        versions = self.get_rule_versions(rule_id)
        if not versions:
            logger.warning(f"هیچ نسخه‌ای برای سند {rule_id} یافت نشد.")
            return None

        # معمولاً نسخه اول یا نسخه دارای Id بالاتر نسخه جاری است
        active_version_meta = versions[0]
        version_id = active_version_meta["id"]

        version_detail_raw = self.get_version_detail(version_id)
        parts = self.get_rule_parts(version_id)
        dependencies = self.get_version_dependencies(version_id)

        # استخراج و ذخیره فایل‌های پیوست
        attachments: List[RuleAttachment] = []
        if version_detail_raw and version_detail_raw.get("files"):
            for f in version_detail_raw["files"]:
                saved_att = self.save_attachment(f)
                if saved_att:
                    attachments.append(saved_att)

        active_version_obj = None
        if version_detail_raw:
            version_detail_copy = dict(version_detail_raw)
            version_detail_copy["files"] = attachments
            active_version_obj = RuleVersionDetail(**version_detail_copy)

        package = CompleteDocumentPackage(
            rule_id=rule_id,
            source_url=f"{self.cfg.site_origin}/ShowRules?Id={rule_id}",
            category_id=rule_info.get("categoryId"),
            rule_info=rule_info,
            active_version=active_version_obj,
            all_versions=versions,
            parts=parts,
            dependencies=dependencies,
            attachments=attachments
        )

        logger.info(
            f"سند {rule_id} با موفقیت استخراج شد: "
            f"{len(parts)} بخش/ماده، {len(dependencies)} پیوند، {len(attachments)} پیوست."
        )
        return package
