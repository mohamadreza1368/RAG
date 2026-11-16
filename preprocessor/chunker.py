"""
ماژول تکه‌بندی تخصصی حقوقی (Contextual Legal Chunker)
پشتیبانی از پنجره لغزان، هم‌پوشانی (Overlap) کانتکست بین مواد مجاور و ابعاد استاندارد چانک
"""

import re
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
    """تکه‌بندی هوشمند متون قانونی بر مبنای مرزهای معنایی مواد، فصول و هم‌پوشانی مجاورتی"""

    def __init__(self, max_tokens_per_chunk: int = 900, overlap_tokens: int = 200):
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.overlap_tokens = overlap_tokens

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
        همراه با تزریق کانتکست ماده قبلی/بعدی جهت هم‌پوشانی (Contextual Overlap)
        """
        sections_by_id = {s.id: s for s in sections}
        chunks: List[LegalChunk] = []

        # ۱. استخراج مواد و تجمیع تبصره‌ها و بندهای هر ماده
        article_items = []
        processed_as_child = set()

        for sec in sections:
            if sec.section_type == "ماده":
                children = [sections_by_id[cid] for cid in sec.children_ids if cid in sections_by_id]
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

                article_items.append({
                    "sec": sec,
                    "content": combined_content,
                    "tokens": tokens,
                    "title": sec.title,
                    "art_no": sec.section_number,
                    "path": sec.section_path
                })

        # ۲. تولید چانک‌های مواد با هم‌پوشانی کانتکست مجاور (Contextual Overlap Window)
        total_arts = len(article_items)
        for idx, item in enumerate(article_items):
            sec = item["sec"]
            main_content = item["content"]
            tokens = item["tokens"]
            path_str = " > ".join(sec.section_path)

            # استخراج کانتکست ماده قبلی برای هم‌پوشانی (Preceding Context)
            preceding_context = ""
            if idx > 0:
                prev_item = article_items[idx - 1]
                prev_lines = prev_item["content"].splitlines()
                # چند خط پایانی ماده قبلی به عنوان هم‌پوشانی
                tail_lines = prev_lines[-3:] if len(prev_lines) >= 3 else prev_lines
                preceding_context = f"[کانتکست مرتبط از {prev_item['title']}]: {' '.join(tail_lines)}"

            # استخراج کانتکست ماده بعدی در صورت کوتاه بودن ماده فعلی
            following_context = ""
            if tokens < 200 and idx + 1 < total_arts:
                next_item = article_items[idx + 1]
                next_lines = next_item["content"].splitlines()
                head_lines = next_lines[:3] if len(next_lines) >= 3 else next_lines
                following_context = f"\n[ادامه مرتبط در {next_item['title']}]: {' '.join(head_lines)}"

            # ساخت هدر کانتکست
            header_parts = [f"سند: {document_title}"]
            if authority:
                header_parts.append(f"مرجع: {authority}")
            if status:
                header_parts.append(f"وضعیت: {status}")
            if path_str:
                header_parts.append(f"موقعیت: {path_str}")

            context_header = " | ".join(header_parts)
            contextual_content = f"[{context_header}]\n"
            if preceding_context:
                contextual_content += f"{preceding_context}\n\n"
            contextual_content += f"متن حکم:\n{main_content}"
            if following_context:
                contextual_content += f"\n{following_context}"

            chunk_tokens = estimate_persian_tokens(contextual_content)

            chunk = LegalChunk(
                document_source_id=str(document_id),
                document_title=document_title,
                document_type=document_type,
                version_id=str(version_id) if version_id else None,
                chapter=sec.section_path[0] if sec.section_path else None,
                article_number=sec.section_number,
                paragraph_number=f"ماده {sec.section_number}" if sec.section_number else None,
                section_path=sec.section_path,
                content=main_content,
                contextual_content=contextual_content,
                token_count=chunk_tokens,
                status=status or sec.tanghih_status,
                is_toc=False,
                source_url=source_url
            )
            chunks.append(chunk)

        # ۳. بخش‌ها یا فصول مقدماتی که ماده مستقل ندارند
        for sec in sections:
            sec_type = sec.section_type
            if sec_type in ["بخش", "فصل", "مقدمه"]:
                if sec.normalized_text and len(sec.normalized_text.split()) > 5:
                    has_article_children = any(
                        sections_by_id.get(cid) and sections_by_id[cid].section_type == "ماده"
                        for cid in sec.children_ids
                    )
                    if not has_article_children:
                        path_str = " > ".join(sec.section_path)
                        context_header = f"سند: {document_title} | موقعیت: {path_str}"
                        contextual_content = f"[{context_header}]\nمتن کلیات:\n{sec.normalized_text}"
                        tokens = estimate_persian_tokens(contextual_content)

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
                            is_toc=False,
                            source_url=source_url
                        )
                        chunks.append(chunk)

        return chunks
