"""
ماژول تکه‌بندی تخصصی حقوقی (Contextual Legal Chunker)
مطابق با الزامات بخش ۱۰ سند طراحی فنی معماری regulatory_rag_design_roadmap.md
"""

from typing import List, Dict, Optional, Any
from .models import NormalizedSection, LegalChunk
from .normalizer import normalize_persian_text


def estimate_persian_tokens(text: str) -> int:
    """
    تخمین دقیق تعداد توکن‌ها برای مدل‌های چندزبانه (مانند Gemma / Qwen).
    در متون فارسی هر کلمه به طور میانگین ۱.۳ تا ۱.۵ ساب‌توکن دارد.
    """
    if not text:
        return 0
    words = text.split()
    return int(len(words) * 1.35)


class LegalChunker:
    """تکه‌بندی هوشمند متون قانونی بر مبنای مرزهای معنایی مواد و بندها"""

    def __init__(self, max_tokens_per_chunk: int = 800):
        self.max_tokens_per_chunk = max_tokens_per_chunk

    def create_chunks(
        self,
        document_id: int,
        document_title: str,
        document_type: Optional[str],
        source_url: str,
        version_id: Optional[str],
        authority: Optional[str],
        status: Optional[str],
        sections: List[NormalizedSection]
    ) -> List[LegalChunk]:
        """
        ایجاد چانک‌های مستقل برای هر ماده و اتصال تبصره‌ها و بندهای مربوطه
        همراه با تزریق هدر غنی کانتکست (Contextual Header) به هر چانک
        """
        sections_by_id = {s.id: s for s in sections}
        chunks: List[LegalChunk] = []

        # شناسایی موادی که قبلاً به عنوان فرزند یک ماده پردازش شده‌اند تا تکرار نشوند
        processed_as_child = set()

        for sec in sections:
            sec_type = sec.section_type

            # الف) اگر ماده باشد: واحد اصلی چانک
            if sec_type == "ماده":
                # پیدا کردن فرزندان مستقیم (تبصره‌ها و بندها)
                children = [sections_by_id[cid] for cid in sec.children_ids if cid in sections_by_id]
                
                # استخراج عنوان فصل/بخش بالاتر
                chapter_title = None
                if len(sec.section_path) > 1:
                    chapter_title = sec.section_path[0]

                # ساخت متن تجمیعی ماده به همراه تبصره‌ها و بندها
                article_blocks = [f"{sec.title}:\n{sec.normalized_text}"] if sec.normalized_text else [sec.title]

                for child in children:
                    processed_as_child.add(child.id)
                    child_text = child.normalized_text
                    if child.title and child.title not in child_text:
                        article_blocks.append(f"\n{child.title}:\n{child_text}")
                    else:
                        article_blocks.append(f"\n{child_text}")

                combined_content = "\n".join(article_blocks).strip()
                tokens = estimate_persian_tokens(combined_content)

                # مسیر متنی سلسله‌مراتب
                path_str = " > ".join(sec.section_path)

                # ساخت هدر کانتکست مطابق بند ۱۰.۱ نقشه راه
                header_parts = [f"سند: {document_title}"]
                if authority:
                    header_parts.append(f"مرجع: {authority}")
                if status:
                    header_parts.append(f"وضعیت: {status}")
                if path_str:
                    header_parts.append(f"موقعیت: {path_str}")

                context_header = " | ".join(header_parts)
                contextual_content = f"[{context_header}]\nمتن ماده:\n{combined_content}"

                chunk = LegalChunk(
                    document_source_id=str(document_id),
                    document_title=document_title,
                    document_type=document_type,
                    version_id=str(version_id) if version_id else None,
                    chapter=chapter_title,
                    article_number=sec.section_number,
                    section_path=sec.section_path,
                    content=combined_content,
                    contextual_content=contextual_content,
                    token_count=tokens,
                    status=status or sec.tanghih_status,
                    source_url=source_url
                )
                chunks.append(chunk)

            # ب) بخش‌ها یا فصولی که خودشان متن مستقل مقدماتی/کلیات دارند (و ماده زیرمجموعه ندارند)
            elif sec_type in ["بخش", "فصل", "مقدمه"]:
                if sec.normalized_text and len(sec.normalized_text.split()) > 5:
                    # اگر فرزندان ماده ندارد، خود بخش به عنوان یک چانک تعاریف/کلیات ذخیره شود
                    has_article_children = any(
                        sections_by_id.get(cid) and sections_by_id[cid].section_type == "ماده"
                        for cid in sec.children_ids
                    )
                    if not has_article_children:
                        path_str = " > ".join(sec.section_path)
                        context_header = f"سند: {document_title} | موقعیت: {path_str}"
                        contextual_content = f"[{context_header}]\nمتن:\n{sec.normalized_text}"
                        tokens = estimate_persian_tokens(sec.normalized_text)

                        chunk = LegalChunk(
                            document_source_id=str(document_id),
                            document_title=document_title,
                            document_type=document_type,
                            version_id=str(version_id) if version_id else None,
                            chapter=sec.title,
                            article_number=None,
                            section_path=sec.section_path,
                            content=sec.normalized_text,
                            contextual_content=contextual_content,
                            token_count=tokens,
                            status=status or sec.tanghih_status,
                            source_url=source_url
                        )
                        chunks.append(chunk)

            # ج) تبصره یا بندی که به ماده والد متصل نشده و به تنهایی در سطح ریشه است
            elif sec.id not in processed_as_child and sec.normalized_text:
                path_str = " > ".join(sec.section_path)
                context_header = f"سند: {document_title} | موقعیت: {path_str}"
                contextual_content = f"[{context_header}]\nمتن:\n{sec.normalized_text}"
                tokens = estimate_persian_tokens(sec.normalized_text)

                chunk = LegalChunk(
                    document_source_id=str(document_id),
                    document_title=document_title,
                    document_type=document_type,
                    version_id=str(version_id) if version_id else None,
                    chapter=sec.section_path[0] if sec.section_path else None,
                    article_number=sec.section_number,
                    section_path=sec.section_path,
                    content=sec.normalized_text,
                    contextual_content=contextual_content,
                    token_count=tokens,
                    status=status or sec.tanghih_status,
                    source_url=source_url
                )
                chunks.append(chunk)

        return chunks
