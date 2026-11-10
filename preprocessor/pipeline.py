"""
خط پردازش و تبدیل جامع اسناد خام به ساختار حقوقی و چانک‌های استاندارد
(Pre-processing & Legal Transformation Pipeline)
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import ParsedDocument, NormalizedSection, LegalChunk
from .normalizer import normalize_persian_text
from .parser import LegalTreeParser
from .chunker import LegalChunker

logger = logging.getLogger("regulatory_crawler")


class DocumentProcessor:
    """موتور پردازش، نرمال‌سازی و ساختاردهی اسناد حقوقی"""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("data/processed")
        self.docs_dir = self.output_dir / "documents"
        self.chunks_dir = self.output_dir / "chunks"

        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)

        self.tree_parser = LegalTreeParser()
        self.chunker = LegalChunker()

    def process_document(self, raw_doc: dict) -> ParsedDocument:
        """پردازش یک سند خام و تولید بخش‌ها و چانک‌های استاندارد"""
        rule_id = raw_doc["rule_id"]
        source_url = raw_doc.get("source_url") or f"https://cmr.seo.ir/ShowRules?Id={rule_id}"

        # استخراج متادیتا از نسخه فعال یا اطلاعات پایه
        active_version = raw_doc.get("active_version") or {}
        rule_info = raw_doc.get("rule_info") or {}

        title = active_version.get("title") or rule_info.get("title") or f"سند {rule_id}"
        normalized_title = normalize_persian_text(title)

        doc_type = None
        if rule_info.get("ruleType"):
            doc_type = rule_info["ruleType"].get("title")

        # مرجع تصویب
        authority = None
        app_inst = active_version.get("approvalInstitution")
        if isinstance(app_inst, dict):
            authority = app_inst.get("title")
        elif isinstance(app_inst, str):
            authority = app_inst

        # وضعیت تنقیحی
        status = None
        t_stat = active_version.get("tanghihStatus")
        if isinstance(t_stat, dict):
            status = t_stat.get("title")
        elif isinstance(t_stat, str):
            status = t_stat

        approval_date = active_version.get("approvalDate")
        version_id = active_version.get("id")

        # ۱. ساختاردهی بخش‌ها، فصول و مواد
        raw_parts = raw_doc.get("parts") or []
        sections = self.tree_parser.parse_parts(raw_parts)

        # ۲. ایجاد چانک‌های متنی غنی‌شده با کانتکست حقوقی
        chunks = self.chunker.create_chunks(
            document_id=rule_id,
            document_title=normalized_title,
            document_type=doc_type,
            source_url=source_url,
            version_id=str(version_id) if version_id else None,
            authority=authority,
            status=status,
            sections=sections
        )

        parsed_doc = ParsedDocument(
            rule_id=rule_id,
            source_url=source_url,
            title=normalized_title,
            document_type=doc_type,
            issuing_authority=authority,
            approval_date=approval_date,
            tanghih_status=status,
            sections=sections,
            chunks=chunks,
            total_sections=len(sections),
            total_chunks=len(chunks)
        )

        # ۳. ذخیره‌سازی خروجی‌ها بر روی دیسک
        doc_file = self.docs_dir / f"{rule_id}.json"
        doc_file.write_text(
            json.dumps(parsed_doc.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        chunk_dicts = [c.model_dump() for c in chunks]
        chunks_file = self.chunks_dir / f"{rule_id}_chunks.json"
        chunks_file.write_text(
            json.dumps(chunk_dicts, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        logger.info(
            f"سند {rule_id} پردازش شد: "
            f"{len(sections)} بخش/ماده ⬅️ {len(chunks)} چانک کانتکست‌دار حقوقی."
        )

        return parsed_doc

    def process_all_raw_rules(self, raw_rules_dir: Optional[Path] = None) -> List[ParsedDocument]:
        """پردازش کلیه اسناد موجود در پوشه raw/rules"""
        raw_dir = raw_rules_dir or Path("data/raw/rules")
        raw_files = list(raw_dir.glob("*.json"))

        # همچنین اضافه کردن sample_71485 در صورت وجود
        sample_file = Path("data/raw/sample_71485.json")
        if sample_file.exists() and sample_file not in raw_files:
            raw_files.append(sample_file)

        logger.info(f"شروع پردازش دسته‌ای {len(raw_files)} سند خام...")
        processed_docs = []

        for fpath in raw_files:
            try:
                raw_data = json.loads(fpath.read_text(encoding="utf-8"))
                doc = self.process_document(raw_data)
                processed_docs.append(doc)
            except Exception as exc:
                logger.error(f"خطا در پردازش فایل {fpath.name}: {exc}")

        logger.info(f"پایان پردازش دسته‌ای: {len(processed_docs)} سند با موفقیت آماده‌سازی شد.")
        return processed_docs
