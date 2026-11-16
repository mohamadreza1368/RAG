"""
ماژول استخراج، پردازش و تکه‌بندی پیشرفته پیوست‌های حقوقی (PDF، Word و Text)
(Advanced Legal Attachment Processor with Sliding Window & Overlap)
دارای قابلیت تشخیص و تفکیک فهرست مطالب (TOC)، هم‌پوشانی لغوی/معنایی و تنظیم ابعاد چانک‌ها
"""

import re
import os
import uuid
import logging
import unicodedata
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from .models import LegalChunk
from .normalizer import normalize_persian_text, extract_numeric_article
from .chunker import estimate_persian_tokens

logger = logging.getLogger("regulatory_crawler")


def is_table_of_contents(text: str) -> bool:
    """
    تشخیص هوشمند صفحات یا بخش‌های مربوط به فهرست مطالب و عناوین
    جهت جلوگیری از سوگیری نتایج سرچ و نمایش فهرست به جای متن احکام قانونی
    """
    if not text:
        return False

    # ۱. وجود صریح واژه فهرست مطالب در آغاز متن
    first_lines = "\n".join(text.splitlines()[:5])
    if "فهرست مطالب" in first_lines or "فهرست عناوین" in first_lines:
        return True

    # ۲. تراکم نشانه‌گذاری‌های نقطه‌چین (Leader Dots) یا خط‌چین
    dots_patterns = re.findall(r"\.{3,}|…{2,}|_{3,}", text)
    dotted_pages = re.findall(r"\.{2,}\s*\d+", text)
    if len(dots_patterns) >= 4 or len(dotted_pages) >= 3:
        return True

    # ۳. وجود ساختار فهرستی (ردیف‌های متوالی شامل عنوان فصل/ماده + شماره صفحه در انتهای خط)
    toc_line_count = 0
    for line in text.splitlines():
        line_clean = line.strip()
        if re.search(r"^(?:ماده|فصل|بخش|گفتار|پیوست)\s+[\w\d\s]+[\.\s…_]+\d+$", line_clean):
            toc_line_count += 1
    if toc_line_count >= 3:
        return True

    return False


def extract_all_articles_in_text(text: str) -> List[str]:
    """استخراج کلیه شماره موادی که در یک بلوک متنی به آنها پرداخته شده است"""
    matches = re.findall(r"ماده\s*([۰-۹\d]+)", text)
    unique_articles = []
    for m in matches:
        if m not in unique_articles:
            unique_articles.append(m)
    return unique_articles


class AttachmentProcessor:
    """
    پردازشگر پیشرفته اسناد پیوست با تکه‌بندی پنجره لغزان و هم‌پوشانی (Sliding Window & Overlap)
    """

    def __init__(self, target_tokens: int = 900, overlap_tokens: int = 200):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens

    def extract_text_from_pdf(self, file_path: Path) -> List[Dict[str, Any]]:
        """استخراج صفحه به صفحه با تبدیل کدهای یونیکد به UTF-8 استاندارد و تشخیص فهرست"""
        pages_data = []
        if not file_path.exists():
            logger.warning("فایل PDF یافت نشد: %s", file_path)
            return pages_data

        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            for page_idx, page in enumerate(reader.pages):
                raw_text = page.extract_text() or ""
                # نرمال‌سازی کدهای یونیکد به فرم استاندارد NFKC و پاکسازی متن فارسی
                nfkc_text = unicodedata.normalize("NFKC", raw_text)
                cleaned = normalize_persian_text(nfkc_text).strip()
                if len(cleaned) > 20:
                    is_toc = is_table_of_contents(cleaned)
                    pages_data.append({
                        "page_number": page_idx + 1,
                        "text": cleaned,
                        "is_toc": is_toc,
                        "token_count": estimate_persian_tokens(cleaned)
                    })
        except Exception as e:
            logger.error("خطا در خواندن فایل PDF %s: %s", file_path.name, e)

        return pages_data

    def extract_text_from_docx(self, file_path: Path) -> List[Dict[str, Any]]:
        """استخراج پاراگراف‌ها و جداول سند Word به همراه برچسب‌های متنی"""
        blocks = []
        if not file_path.exists():
            logger.warning("فایل DOCX یافت نشد: %s", file_path)
            return blocks

        try:
            import docx
            doc = docx.Document(str(file_path))

            for para in doc.paragraphs:
                p_text = para.text.strip()
                if not p_text:
                    continue
                nfkc_p = unicodedata.normalize("NFKC", p_text)
                norm_p = normalize_persian_text(nfkc_p)
                blocks.append(norm_p)

            # استخراج محتوای جداول
            for table in doc.tables:
                for row in table.rows:
                    cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if cells:
                        row_line = " | ".join(cells)
                        norm_row = normalize_persian_text(unicodedata.normalize("NFKC", row_line))
                        blocks.append(norm_row)

        except Exception as e:
            logger.error("خطا در خواندن فایل Word %s: %s", file_path.name, e)

        return [{"page_number": 1, "text": b, "is_toc": is_table_of_contents(b), "token_count": estimate_persian_tokens(b)} for b in blocks]

    def create_sliding_window_chunks(
        self,
        sections_data: List[Dict[str, Any]],
        target_tokens: int,
        overlap_tokens: int
    ) -> List[Dict[str, Any]]:
        """
        تکه‌بندی پیوسته متن با حفظ پنجره لغزان و هم‌پوشانی (Sliding Window):
        چانک‌ها دیگر در مرز یک صفحه یا پاراگراف کوتاه قطع نمی‌شوند، بلکه تا سقف target_tokens
        تکمیل شده و با بخش پایانی چانک قبلی هم‌پوشانی (Overlap) دارند.
        """
        # ۱. جداسازی صفحات فهرست مطالب
        toc_sections = [s for s in sections_data if s.get("is_toc")]
        substantive_sections = [s for s in sections_data if not s.get("is_toc")]

        generated_chunks = []

        # چانک‌های جداگانه برای فهرست مطالب (جهت ارجاع بدون تداخل در محتوای اصلی)
        for s in toc_sections:
            generated_chunks.append({
                "text": s["text"],
                "token_count": s["token_count"],
                "page_range": f"صفحه {s['page_number']}",
                "is_toc": True,
                "articles": []
            })

        if not substantive_sections:
            return generated_chunks

        # ساخت واحدهای پاراگرافی به همراه شماره صفحه مبدا
        paragraphs_with_page = []
        for s in substantive_sections:
            page_no = s["page_number"]
            # تقسیم بر اساس خطوط خالی یا سطرها
            lines = [l.strip() for l in s["text"].split("\n") if l.strip()]
            for l in lines:
                paragraphs_with_page.append({"text": l, "page": page_no, "tokens": estimate_persian_tokens(l)})

        # ۲. الگوریتم پنجره لغزان با هم‌پوشانی
        current_paras = []
        current_tokens = 0
        min_page = None
        max_page = None

        for p in paragraphs_with_page:
            p_tokens = p["tokens"]

            if current_tokens + p_tokens > target_tokens and current_paras:
                # بستن چانک فعلی
                chunk_text = "\n".join(item["text"] for item in current_paras)
                articles = extract_all_articles_in_text(chunk_text)
                page_str = f"صفحه {min_page}" if min_page == max_page else f"صفحات {min_page} تا {max_page}"

                generated_chunks.append({
                    "text": chunk_text,
                    "token_count": current_tokens,
                    "page_range": page_str,
                    "is_toc": False,
                    "articles": articles
                })

                # ساخت بخش هم‌پوشانی (Overlap) از انتهای چانک جاری
                overlap_paras = []
                overlap_count = 0
                for prev_item in reversed(current_paras):
                    if overlap_count + prev_item["tokens"] <= overlap_tokens:
                        overlap_paras.insert(0, prev_item)
                        overlap_count += prev_item["tokens"]
                    else:
                        break

                current_paras = overlap_paras + [p]
                current_tokens = overlap_count + p_tokens
                pages_in_window = [item["page"] for item in current_paras]
                min_page = min(pages_in_window)
                max_page = max(pages_in_window)
            else:
                current_paras.append(p)
                current_tokens += p_tokens
                min_page = p["page"] if min_page is None else min(min_page, p["page"])
                max_page = p["page"] if max_page is None else max(max_page, p["page"])

        if current_paras:
            chunk_text = "\n".join(item["text"] for item in current_paras)
            articles = extract_all_articles_in_text(chunk_text)
            page_str = f"صفحه {min_page}" if min_page == max_page else f"صفحات {min_page} تا {max_page}"
            generated_chunks.append({
                "text": chunk_text,
                "token_count": current_tokens,
                "page_range": page_str,
                "is_toc": False,
                "articles": articles
            })

        return generated_chunks

    def process_attachment_file(
        self,
        file_path: Path,
        attachment_name: str,
        attachment_id: Any,
        doc_metadata: Dict[str, Any]
    ) -> List[LegalChunk]:
        """تبدیل یک فایل پیوست به چانک‌های استاندارد با متادیتای حقوقی کامل"""
        chunks: List[LegalChunk] = []
        rule_id = str(doc_metadata.get("rule_id", "unknown"))
        doc_title = doc_metadata.get("title", f"سند {rule_id}")
        source_url = doc_metadata.get("source_url") or f"https://cmr.seo.ir/ShowRules?Id={rule_id}"
        version_id = str(doc_metadata.get("version_id", ""))
        status = doc_metadata.get("status", "معتبر")

        suffix = file_path.suffix.lower()

        raw_sections = []
        doc_type_label = "پیوست رسمی"

        if suffix == ".pdf":
            raw_sections = self.extract_text_from_pdf(file_path)
            doc_type_label = "پیوست رسمی (PDF)"
        elif suffix == ".docx":
            raw_sections = self.extract_text_from_docx(file_path)
            doc_type_label = "پیوست رسمی (Word)"
        elif suffix in [".txt", ".text"]:
            try:
                txt = file_path.read_text(encoding="utf-8", errors="replace")
                cleaned = normalize_persian_text(unicodedata.normalize("NFKC", txt))
                raw_sections = [{"page_number": 1, "text": cleaned, "is_toc": is_table_of_contents(cleaned), "token_count": estimate_persian_tokens(cleaned)}]
                doc_type_label = "پیوست متنی (TXT)"
            except Exception as e:
                logger.error("خطا در خواندن فایل متنی %s: %s", file_path.name, e)

        if not raw_sections:
            return chunks

        # تکه‌بندی با پنجره لغزان و هم‌پوشانی
        windowed_chunks = self.create_sliding_window_chunks(
            sections_data=raw_sections,
            target_tokens=self.target_tokens,
            overlap_tokens=self.overlap_tokens
        )

        for idx, wc in enumerate(windowed_chunks, start=1):
            is_toc = wc["is_toc"]
            page_range = wc["page_range"]
            text_body = wc["text"]
            tokens = wc["token_count"]
            articles = wc["articles"]

            articles_str = f"مواد: {', '.join(articles)}" if articles else ""
            toc_tag = "[فهرست مطالب و عناوین] " if is_toc else ""

            contextual_header = (
                f"سند: {doc_title}\n"
                f"پیوست: {attachment_name} (شناسه {attachment_id})\n"
                f"موقعیت: {page_range} {toc_tag}\n"
            )
            if articles_str:
                contextual_header += f"احکام مندرج: {articles_str}\n"

            contextual_content = f"{contextual_header}\nمتن احکام:\n{text_body}"

            main_article_no = articles[0] if articles else None

            chunk = LegalChunk(
                chunk_id=str(uuid.uuid4()),
                document_source_id=rule_id,
                document_title=doc_title,
                document_type="فهرست مطالب" if is_toc else doc_type_label,
                version_id=version_id if version_id else None,
                chapter=f"پیوست: {attachment_name}",
                article_number=main_article_no,
                paragraph_number=page_range,
                section_path=[doc_title, "پیوست‌ها", attachment_name, page_range],
                content=text_body,
                contextual_content=contextual_content,
                token_count=tokens,
                status=status,
                is_toc=is_toc,
                source_url=source_url
            )
            chunks.append(chunk)

        return chunks

    def process_attachments_for_document(
        self,
        raw_doc: Dict[str, Any],
        attachments_base_dir: Path = Path("data/attachments")
    ) -> List[LegalChunk]:
        """پردازش کلیه پیوست‌های یک سند خام با انطباق هوشمند شناسه عددی"""
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

        has_pdf = any((att.get("name") or "").lower().endswith(".pdf") for att in attachments)

        # کش کردن شناسه‌های عددی موجود در پوشه
        existing_attachments_by_id = {}
        if attachments_base_dir.exists():
            try:
                for entry in attachments_base_dir.iterdir():
                    try:
                        if entry.is_file():
                            prefix = entry.name.split("_")[0]
                            if prefix.isdigit():
                                existing_attachments_by_id[int(prefix)] = entry
                    except OSError:
                        pass
            except OSError as err:
                logger.warning("خطا در پیمایش دایرکتوری پیوست‌ها: %s", err)

        for att in attachments:
            try:
                att_id = att.get("id")
                att_name = att.get("name") or f"پیوست {att_id}"
                is_pdf = att_name.lower().endswith(".pdf")
                is_docx = att_name.lower().endswith(".docx")

                if has_pdf and is_docx:
                    logger.info("پیوست Word %s به دلیل وجود نسخه معادل PDF نادیده گرفته شد.", att_name)
                    continue

                local_path = None
                if att_id is not None and int(att_id) in existing_attachments_by_id:
                    local_path = existing_attachments_by_id[int(att_id)]

                if not local_path and att.get("local_path"):
                    norm_path_str = str(att["local_path"]).replace("\\", "/")
                    cand = Path(norm_path_str)
                    try:
                        if len(cand.name.encode("utf-8")) < 240 and cand.is_file():
                            local_path = cand
                        elif attachments_base_dir.exists():
                            sub_cand = attachments_base_dir / cand.name
                            if len(sub_cand.name.encode("utf-8")) < 240 and sub_cand.is_file():
                                local_path = sub_cand
                    except OSError:
                        pass

                if not local_path:
                    logger.warning("فایل فیزیکی پیوست %s (شناسه %s) یافت نشد.", att_name, att_id)
                    continue

                att_chunks = self.process_attachment_file(
                    file_path=local_path,
                    attachment_name=att_name,
                    attachment_id=att_id,
                    doc_metadata=doc_meta
                )
                all_chunks.extend(att_chunks)
            except Exception as err:
                logger.error("خطا در پردازش پیوست %s از سند %s: %s", att.get("name"), rule_id, err)

        return all_chunks
