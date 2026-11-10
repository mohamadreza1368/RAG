"""
ماژول نرمال‌سازی تخصصی متون حقوقی و قوانین به زبان فارسی
مطابق با الزامات بخش ۹.۲ سند طراحی فنی معماری regulatory_rag_design_roadmap.md
"""

import re
import html
from typing import Optional


# نگاشت کاراکترهای عربی به معادل‌های استاندارد فارسی
ARABIC_TO_PERSIAN_MAP = {
    # کاف و یاء
    "ك": "ک",
    "ي": "ی",
    "ى": "ی",
    "ئ": "ئ",
    # هاء
    "ھ": "ه",
    "ة": "ه",
    # الف‌ها
    "إ": "ا",
    "أ": "ا",
    "آ": "آ",
    "ٱ": "ا",
    # ارقام عربی به فارسی
    "٠": "۰",
    "١": "۱",
    "٢": "۲",
    "٣": "۳",
    "٤": "۴",
    "٥": "۵",
    "٦": "۶",
    "٧": "۷",
    "٨": "۸",
    "٩": "۹",
}

# نگاشت ارقام لاتین/انگلیسی به ارقام استاندارد فارسی
LATIN_TO_PERSIAN_DIGITS = {
    "0": "۰",
    "1": "۱",
    "2": "۲",
    "3": "۳",
    "4": "۴",
    "5": "۵",
    "6": "۶",
    "7": "۷",
    "8": "۸",
    "9": "۹",
}

# نگاشت معکوس (ارقام فارسی به لاتین برای پردازش‌های مقایسه‌ای)
PERSIAN_TO_LATIN_DIGITS = {v: k for k, v in LATIN_TO_PERSIAN_DIGITS.items()}
PERSIAN_TO_LATIN_DIGITS.update({
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9"
})

# علائم حرکت و اعراب عربی
HARAKAT_PATTERN = re.compile(r"[\u064B-\u0652\u0656-\u065F\u0670]")

# کاراکتر نیم‌فاصله (Zero Width Non-Joiner)
ZWNJ = "\u200c"


def clean_html(html_content: Optional[str]) -> str:
    """
    تبدیل هوشمند کدهای HTML به متن خام تمیز با حفظ ساختار خطوط و پاراگراف‌ها
    """
    if not html_content:
        return ""

    text = html_content

    # تبدیل تگ‌های شکست خط و پاراگراف به سطر جدید
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</?(p|div|tr|li|h[1-6])\b[^>]*>", "\n", text)

    # حذف تگ‌های اسکریپت و استایل به همراه محتوای درون آن‌ها
    text = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", "", text)

    # حذف سایر تگ‌های HTML باقی‌مانده
    text = re.sub(r"<[^>]+>", "", text)

    # تبدیل Entityهای HTML مانند &nbsp; و &zwnj;
    text = html.unescape(text)

    # تبدیل فاصله‌های نشکن به فاصله معمولی
    text = text.replace("\xa0", " ").replace("\u200b", "")

    return text.strip()


def normalize_persian_text(
    text: str,
    to_persian_digits: bool = True,
    remove_harakat: bool = True
) -> str:
    """
    نرمال‌سازی پیشرفته متن فارسی با حفظ دقیق شماره مواد، علائم حقوقی و نیم‌فاصله‌ها.
    """
    if not text:
        return ""

    # ۱. ابتدا استخراج متن در صورت وجود تگ‌های HTML
    if "<" in text and ">" in text:
        text = clean_html(text)

    # ۲. استانداردسازی کاراکترهای عربی به فارسی
    chars = []
    for ch in text:
        chars.append(ARABIC_TO_PERSIAN_MAP.get(ch, ch))
    text = "".join(chars)

    # ۳. حذف یا حفظ حرکات اعراب
    if remove_harakat:
        text = HARAKAT_PATTERN.sub("", text)

    # ۴. استانداردسازی ارقام در صورت درخواست
    if to_persian_digits:
        for en_d, fa_d in LATIN_TO_PERSIAN_DIGITS.items():
            text = text.replace(en_d, fa_d)

    # ۵. مدیریت دقیق نیم‌فاصله (ZWNJ)
    # الف) حذف فاصله‌های متوالی ZWNJ
    text = re.sub(rf"{ZWNJ}+", ZWNJ, text)
    # ب) حذف ZWNJ قبل یا بعد از فاصله یا سطر جدید
    text = re.sub(rf"\s*{ZWNJ}\s*", ZWNJ, text)
    text = re.sub(rf"(\n|^){ZWNJ}|{ZWNJ}(\n|$)", r"\1\2", text)
    # ج) حذف ZWNJ بعد از نشانه‌گذاری‌های پایان جمله یا پرانتزها
    text = re.sub(rf"([«»\(\)\[\]\.\,\:\;\-\–]){ZWNJ}", r"\1", text)
    text = re.sub(rf"{ZWNJ}([«»\(\)\[\]\.\,\:\;\-\–])", r"\1", text)

    # ۶. استانداردسازی نشانه‌گذاری‌ها و فاصله‌ها
    # یکدست‌سازی گیومه‌های باز و بسته
    text = text.replace('"', '«').replace('"', '»')
    # یکپارچه‌سازی فاصله‌ها (فاصله اضافه بین کلمات)
    text = re.sub(r"[ \t]+", " ", text)
    # استانداردسازی خطوط خالی (حداکثر یک سطر خالی بین پاراگراف‌ها)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()


def extract_numeric_article(title: str) -> Optional[str]:
    """
    استخراج شماره ترتیبی ماده، بخش یا تبصره از عنوان آن (مانند 'ماده 12' -> '12')
    """
    if not title:
        return None

    # ارقام فارسی یا لاتین
    match = re.search(r"(\d+|[\u06F0-\u06F9]+)", title)
    if match:
        raw_num = match.group(1)
        # تبدیل به عدد لاتین استاندارد برای ایندکس و تطبیق
        latin_num = "".join(PERSIAN_TO_LATIN_DIGITS.get(c, c) for c in raw_num)
        return latin_num

    return None
