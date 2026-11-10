"""
اسکریپت خط فرمان اجرای فاز ۲: پردازش، نرمال‌سازی و چانکینگ حقوقی اسناد (Legal Pre-processor)

نمونه‌های کاربرد:
  1. پردازش و چانکینگ تمام اسناد خام دانلودشده:
     python run_preprocessor.py

  2. پردازش یک سند مشخص:
     python run_preprocessor.py --rule-id 71485

  3. مشاهده آمار اسناد و چانک‌های تولیدشده:
     python run_preprocessor.py --stats
"""

import argparse
import json
from pathlib import Path
from preprocessor.pipeline import DocumentProcessor


def print_stats():
    docs_dir = Path("data/processed/documents")
    chunks_dir = Path("data/processed/chunks")

    doc_files = list(docs_dir.glob("*.json")) if docs_dir.exists() else []
    chunk_files = list(chunks_dir.glob("*.json")) if chunks_dir.exists() else []

    total_chunks = 0
    total_tokens = 0
    for cf in chunk_files:
        try:
            chunks_data = json.loads(cf.read_text(encoding="utf-8"))
            total_chunks += len(chunks_data)
            total_tokens += sum(c.get("token_count", 0) for c in chunks_data)
        except Exception:
            pass

    print("==================================================")
    print("📊 آمار اسناد و چانک‌های پردازش‌شده حقوقی:")
    print(f"  - کل اسناد پردازش‌شده: {len(doc_files)}")
    print(f"  - کل چانک‌های استاندارد تولیدشده: {total_chunks}")
    if total_chunks > 0:
        print(f"  - میانگین توکن در هر چانک: {total_tokens // total_chunks}")
        print(f"  - کل تخمین توکن‌ها: {total_tokens:,}")
    print(f"  - مسیر اسناد پردازش‌شده: {docs_dir}")
    print(f"  - مسیر چانک‌های آماده Embedding: {chunks_dir}")
    print("==================================================")


def main():
    parser = argparse.ArgumentParser(
        description="خط پردازش، نرمال‌سازی متن فارسی و چانکینگ تخصصی حقوقی (فاز ۲)"
    )
    parser.add_argument(
        "--rule-id",
        type=int,
        default=None,
        help="پردازش یک سند مشخص بر اساس شناسه (مثلاً 71485)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="نمایش آمار و ارقام چانک‌ها و اسناد پردازش‌شده"
    )

    args = parser.parse_args()

    processor = DocumentProcessor()

    if args.stats:
        print_stats()
        return

    if args.rule_id:
        raw_file = Path(f"data/raw/rules/{args.rule_id}.json")
        if not raw_file.exists() and args.rule_id == 71485:
            raw_file = Path("data/raw/sample_71485.json")

        if not raw_file.exists():
            print(f"❌ فایل خام سند {args.rule_id} در پوشه data/raw/rules/ یافت نشد.")
            return

        print(f"در حال پردازش سند {args.rule_id}...")
        raw_data = json.loads(raw_file.read_text(encoding="utf-8"))
        doc = processor.process_document(raw_data)
        print(f"✅ سند با موفقیت پردازش شد: {doc.total_sections} بخش/ماده ⬅️ {doc.total_chunks} چانک حقوقی.")
    else:
        print("شروع پردازش دسته‌ای اسناد خام موجود...")
        docs = processor.process_all_raw_rules()
        print(f"✅ پردازش به پایان رسید: مجموعاً {len(docs)} سند پردازش شد.")

    print_stats()


if __name__ == "__main__":
    main()
