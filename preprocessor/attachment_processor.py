"""
ماژول استخراج، پردازش و چانکینگ تخصصی پیوست‌های حقوقی (PDF و DOCX)
(Legal Attachment Processor)
استخراج متن اسناد رسمی ابلاغ‌شده و تبدیل به چانک‌های ساختاریافته RAG
"""

import os
import uuid
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import LegalChunk
from .normalizer import normalize_persian_text, extract_numeric_article
from .chunker import estimate_persian_tokens

logger = logging.getLogger("regulatory_crawler")


class AttachmentProcessor:
    """پردازشگر اسناد و فایل‌های پیوست (PDF و Word) و تبدیل آن‌ها به چانک‌های استاندارد"""

    def __init__(self, max_tokens_per_chunk: int = 700):
        self.max_tokens_per_chunk = max_tokens_per_chunk

    def extract_text_from_pdf(self, file_path: Path) -> List[Dict[str, Any]]:
        """استخراج صفحه به صفحه متن از فایل PDF"""
        pages_data = []
        if not file_path.exists():
            logger.warning("فایل PDF یافت نشد: %s", file_path)
            return pages_data

        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            for page_idx, page in enumerate(reader.pages):
                raw_text = page.extract_text() or ""
                cleaned = normalize_persian_text(raw_text).strip()
                if len(cleaned) > 20:
                    pages_data.append({
                        "page_number": page_idx + 1,
                        "text": cleaned,
                        "raw_length": len(raw_text)
                    })
        except Exception as e:
            logger.error("خطا در خواندن فایل PDF %s: %s", file_path.name, e)

        return pages_data

    def extract_text_from_docx(self, file_path: Path) -> List[Dict[str, Any]]:
        """استخراج پاراگراف‌ها و جدول‌ها از فایل Word (DOCX)"""
        sections_data = []
        if not file_path.exists():
            logger.warning("فایل DOCX یافت نشد: %s", file_path)
            return sections_data

        try:
            import docx
            doc = docx.Document(str(file_path))
            current_block = []
            block_idx = 1
            current_tokens = 0

            for para in doc.paragraphs:
                p_text = para.text.strip()
                if not p_text:
                    continue
                norm_p = normalize_persian_text(p_text)
                t_count = estimate_persian_tokens(norm_p)

                if current_tokens + t_count > self.max_tokens_per_chunk and current_block:
                    sections_data.append({
                        "section_number": block_idx,
                        "text": "\n".join(current_block),
                        "token_count": current_tokens
                    })
                    block_idx += 1
                    current_block = [norm_p]
                    current_tokens = t_count
                else:
                    current_block.append(norm_p)
                    current_tokens += t_count

            if current_block:
                sections_data.append({
                    "section_number": block_idx,
                    "text": "\n".join(current_block),
                    "token_count": current_tokens
                })

        except Exception as e:
            logger.error("خطا در خواندن فایل Word %s: %s", file_path.name, e)

        return sections_data

    def process_attachment_file(
        self,
        file_path: Path,
        attachment_name: str,
        attachment_id: Any,
        doc_metadata: Dict[str, Any]
    ) -> List[LegalChunk]:
        """تبدیل یک فایل پیوست به لیست چانک‌های حقوقی RAG"""
        chunks: List[LegalChunk] = []
        rule_id = str(doc_metadata.get("rule_id", "unknown"))
        doc_title = doc_metadata.get("title", f"سند {rule_id}")
        source_url = doc_metadata.get("source_url") or f"https://cmr.seo.ir/ShowRules?Id={rule_id}"
        version_id = str(doc_metadata.get("version_id", ""))
        status = doc_metadata.get("status", "معتبر")

        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            pages = self.extract_text_from_pdf(file_path)
            for p in pages:
                page_no = p["page_number"]
                p_text = p["text"]
                tokens = estimate_persian_tokens(p_text)

                # استخراج شماره ماده در صورت وجود در صفحه
                article_no = extract_numeric_article(p_text)

                contextual_header = (
                    f"سند: {doc_title}\n"
                    f"پیوست رسمی: {attachment_name} (شناسه {attachment_id})\n"
                    f"موقعیت: صفحه {page_no} فایل رسمی PDF\n"
                )
                if article_no:
                    contextual_header += f"حاوی احکام: ماده {article_no}\n"

                contextual_content = f"{contextual_header}\nمتن پیوست:\n{p_text}"

                chunk = LegalChunk(
                    chunk_id=str(uuid.uuid4()),
                    document_source_id=rule_id,
                    document_title=doc_title,
                    document_type="پیوست رسمی (PDF)",
                    version_id=version_id if version_id else None,
                    chapter=f"پیوست: {attachment_name}",
                    article_number=article_no,
                    paragraph_number=f"صفحه {page_no}",
                    section_path=[doc_title, "پیوست‌های ابلاغ‌شده", attachment_name, f"صفحه {page_no}"],
                    content=p_text,
                    contextual_content=contextual_content,
                    token_count=tokens,
                    status=status,
                    source_url=source_url
                )
                chunks.append(chunk)

        elif suffix == ".docx":
            blocks = self.extract_text_from_docx(file_path)
            for b in blocks:
                sec_no = b["section_number"]
                b_text = b["text"]
                tokens = b.get("token_count") or estimate_persian_tokens(b_text)
                article_no = extract_numeric_article(b_text)

                contextual_header = (
                    f"سند: {doc_title}\n"
                    f"پیوست رسمی: {attachment_name} (شناسه {attachment_id})\n"
                    f"موقعیت: بخش {sec_no} فایل رسمی Word\n"
                )
                if article_no:
                    contextual_header += f"حاوی احکام: ماده {article_no}\n"

                contextual_content = f"{contextual_header}\nمتن پیوست:\n{b_text}"

                chunk = LegalChunk(
                    chunk_id=str(uuid.uuid4()),
                    document_source_id=rule_id,
                    document_title=doc_title,
                    document_type="پیوست رسمی (Word)",
                    version_id=version_id if version_id else None,
                    chapter=f"پیوست: {attachment_name}",
                    article_number=article_no,
                    paragraph_number=f"بخش {sec_no}",
                    section_path=[doc_title, "پیوست‌های ابلاغ‌شده", attachment_name, f"بخش {sec_no}"],
                    content=b_text,
                    contextual_content=contextual_content,
                    token_count=tokens,
                    status=status,
                    source_url=source_url
                )
                chunks.append(chunk)

        return chunks

    def process_attachments_for_document(
        self,
        raw_doc: Dict[str, Any],
        attachments_base_dir: Path = Path("data/attachments")
    ) -> List[LegalChunk]:
        """پردازش تمام پیوست‌های یک سند خام"""
        all_chunks: List[LegalChunk] = []
        attachments = raw_doc.get("attachments") or []
        if not attachments:
            return all_chunks

        rule_id = raw_doc.get("rule_id")
        active_version = raw_doc.get("active_version") or {}
        rule_info = raw_doc.get("rule_info") or {}

        title = active_version.get("title") or rule_info.get("title") or f"سند {rule_id}"
        norm_title = normalize_persian_text(title)

        doc_meta = {
            "rule_id": rule_id,
            "title": norm_title,
            "source_url": raw_doc.get("source_url"),
            "version_id": active_version.get("id"),
            "status": active_version.get("tanghihStatus", {}).get("title") if isinstance(active_version.get("tanghihStatus"), dict) else active_version.get("tanghihStatus")
        }

        # برای جلوگیری از تکرار متن وقتی هم PDF و هم DOCX موجود است:
        # ترجیحاً PDF را به خاطر استناد دقیق شماره صفحه انتخاب می‌کنیم
        has_pdf = any((att.get("name") or "").lower().endswith(".pdf") for att in attachments)

        for att in attachments:
            att_name = att.get("name") or f"پیوست {att.get('id')}"
            is_pdf = att_name.lower().endswith(".pdf")
            is_docx = att_name.lower().endswith(".docx")

            # اگر هر دو موجود باشد، جهت جلوگیری از افزونگی داده‌ها، نسخه دقیق‌تر PDF را پردازش می‌کنیم
            if has_pdf and is_docx:
                logger.info("پیوست Word %s به دلیل وجود نسخه PDF معادل نادیده گرفته شد.", att_name)
                continue

            # پیدا کردن مسیر محلی فایل
            local_path = None
            if att.get("local_path"):
                cand = Path(att["local_path"])
                if cand.exists():
                    local_path = cand
                elif (attachments_base_dir / cand.name).exists():
                    local_path = attachments_base_dir / cand.name

            if not local_path:
                # جستجو بر اساس شناسه یا نام فایل در پوشه attachments
                for f in attachments_base_dir.glob(f"{att.get('id')}*"):
                    local_path = f
                    break

            if not local_path or not local_path.exists():
                logger.warning("فایل فیزیکی پیوست %s یافت نشد.", att_name)
                continue

            att_chunks = self.process_attachment_file(
                file_path=local_path,
                attachment_name=att_name,
                attachment_id=att.get("id"),
                doc_metadata=doc_meta
            )
            all_chunks.extend(att_chunks)

        return all_chunks
