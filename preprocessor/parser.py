"""
پارس‌کننده ساختار حقوقی اسناد (Legal Structure Parser)
تبدیل ساختار درختی فصول، مواد و تبصره‌ها به مدل‌های سلسله‌مراتبی و محاسبه مسیر موقعیت منبع (Section Path)
"""

from typing import List, Dict, Optional, Any
from .models import NormalizedSection
from .normalizer import clean_html, normalize_persian_text, extract_numeric_article


class LegalTreeParser:
    """سازنده و اعتبارسنج درخت سلسله‌مراتب حقوقی سند"""

    def parse_parts(self, raw_parts: List[dict]) -> List[NormalizedSection]:
        """
        دریافت لیست قطعات خام و تبدیل آن به درخت ساخت‌یافته NormalizedSection
        همراه با استخراج شماره مواد و محاسبه مسیر سلسله‌مراتبی کامل (Breadcrumbs)
        """
        if not raw_parts:
            return []

        # ۱. ساخت نمونه‌های اولیه با متن نرمال‌شده
        sections_by_id: Dict[int, NormalizedSection] = {}
        for p in raw_parts:
            p_id = p["id"]
            title = p.get("title") or ""
            raw_body = p.get("body") or ""
            normalized_title = normalize_persian_text(title)
            normalized_body = normalize_persian_text(raw_body)

            # ترکیب عنوان و بدنه در صورتی که بخش یا فصل باشد و عنوان نیاز به بدنه داشته باشد
            full_title = normalized_title
            if p.get("rulePartType") in ["بخش", "فصل"] and normalized_body and normalized_body != normalized_title:
                full_title = f"{normalized_title} - {normalized_body}"

            sec_number = extract_numeric_article(title)

            section = NormalizedSection(
                id=p_id,
                parent_id=p.get("parentId"),
                section_type=p.get("rulePartType") or "سایر",
                section_number=sec_number,
                title=full_title,
                raw_body=raw_body,
                normalized_text=normalized_body,
                order_no=p.get("orderNo") or 0,
                tanghih_status=p.get("tanghihStatusTitle"),
                section_path=[],
                children_ids=[]
            )
            sections_by_id[p_id] = section

        # ۲. ایجاد پیوندهای والد و فرزندی
        for p_id, section in sections_by_id.items():
            parent_id = section.parent_id
            if parent_id and parent_id in sections_by_id:
                sections_by_id[parent_id].children_ids.append(p_id)

        # ۳. محاسبه مسیر موقعیت منبع (section_path) به صورت بازگشتی
        def get_path(current_id: int) -> List[str]:
            sec = sections_by_id.get(current_id)
            if not sec:
                return []
            if sec.parent_id and sec.parent_id in sections_by_id:
                return get_path(sec.parent_id) + [sec.title]
            return [sec.title]

        for p_id, section in sections_by_id.items():
            section.section_path = get_path(p_id)

        # ۴. مرتب‌سازی نهایی بر اساس ترتیب قرارگیری
        return list(sections_by_id.values())
