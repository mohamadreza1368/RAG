"""
تست جامع عملکرد ماژول نرمال‌سازی فارسی، پارسر حقوقی و چانکر کانتکست‌دار (فاز ۲)
"""

import sys
from pathlib import Path
import json

# افزودن ریشه پروژه به sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from preprocessor.normalizer import clean_html, normalize_persian_text, extract_numeric_article
from preprocessor.pipeline import DocumentProcessor


def test_normalization():
    print("\n--- ۱. تست نرمال‌سازی متن فارسی و پاکسازی HTML ---")

    # تست کاراکترهای عربی و نیم‌فاصله‌ها
    sample_raw = "<p>شركت‌هاي مالي و اداري&nbsp;ماده ۱۲</p>"
    cleaned = normalize_persian_text(sample_raw)
    print(f"خام: {sample_raw}")
    print(f"نرمال‌شده: {cleaned}")
    assert "شرکت" in cleaned, "باید ك عربی به ک تبدیل شده باشد"
    assert "های" in cleaned or "‌های" in cleaned, "باید ي عربی به ی تبدیل شده باشد"

    # تست استخراج شماره ماده
    art_num = extract_numeric_article("ماده 24 مکرر")
    assert art_num == "24", f"شماره ماده باید 24 باشد ولی {art_num} است"
    print(f"شماره استخراج‌شده از 'ماده 24 مکرر': {art_num}")

    print("✅ تست نرمال‌سازی با موفقیت انجام شد.")


def test_pipeline_on_sample_document():
    print("\n--- ۲. تست خط پردازش و چانکینگ روی سند نمونه ۷۱۴۸۵ ---")
    sample_file = Path("data/raw/sample_71485.json")
    assert sample_file.exists(), f"فایل {sample_file} باید موجود باشد"

    processor = DocumentProcessor()
    raw_data = json.loads(sample_file.read_text(encoding="utf-8"))
    parsed_doc = processor.process_document(raw_data)

    print(f"عنوان سند: {parsed_doc.title}")
    print(f"تعداد کل بخش‌ها/مواد (Sections): {parsed_doc.total_sections}")
    print(f"تعداد چانک‌های حقوقی تولیدشده: {parsed_doc.total_chunks}")

    assert parsed_doc.total_sections > 0, "بخش‌های استخراج‌شده نباید صفر باشد"
    assert parsed_doc.total_chunks > 0, "چانک‌ها نباید صفر باشد"

    # بررسی یک چانک نمونه (مثلاً ماده ۲ که تبصره دارد)
    sample_chunk = None
    for c in parsed_doc.chunks:
        if c.article_number == "2":
            sample_chunk = c
            break

    if not sample_chunk:
        sample_chunk = parsed_doc.chunks[0]

    print("\nنمونه چانک تولیدشده:")
    print(f"  - شناسه چانک: {sample_chunk.chunk_id}")
    print(f"  - شماره ماده: {sample_chunk.article_number}")
    print(f"  - مسیر ساختار (Section Path): {' > '.join(sample_chunk.section_path)}")
    print(f"  - تخمین توکن: {sample_chunk.token_count}")
    print(f"  - متن کانتکست‌دار (Contextual Content):\n{sample_chunk.contextual_content[:350]}...\n")

    # اعتبارسنجی اتصال تبصره به ماده
    if sample_chunk.article_number == "2":
        assert "تبصره" in sample_chunk.content, "تبصره ماده ۲ باید درون چانک ماده ۲ قرار گرفته باشد"

    print("✅ تست پردازش سند نمونه ۷۱۴۸۵ با موفقیت پاس شد.")


def test_batch_processing():
    print("\n--- ۳. تست پردازش دسته‌ای کلیه اسناد خام موجود ---")
    processor = DocumentProcessor()
    docs = processor.process_all_raw_rules()
    print(f"تعداد کل اسناد پردازش‌شده در این تست: {len(docs)}")
    assert len(docs) >= 3, "حداقل ۳ سند باید پردازش شده باشند"

    out_docs = list(Path("data/processed/documents").glob("*.json"))
    out_chunks = list(Path("data/processed/chunks").glob("*.json"))
    print(f"فایل‌های ذخیره‌شده در data/processed/documents/: {len(out_docs)}")
    print(f"فایل‌های ذخیره‌شده در data/processed/chunks/: {len(out_chunks)}")

    print("✅ تست پردازش دسته‌ای با موفقیت انجام شد.")


if __name__ == "__main__":
    print("====================================================")
    print("تست ماژول فاز ۲ (نرمال‌سازی، پارسر حقوقی و Legal Chunker)")
    print("====================================================")
    test_normalization()
    test_pipeline_on_sample_document()
    test_batch_processing()
    print("\n🎉 کلیه آزمون‌های فاز ۲ با موفقیت ۱۰۰٪ سپری شدند.")
