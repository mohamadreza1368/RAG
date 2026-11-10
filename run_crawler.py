"""
اسکریپت خط فرمان جهت اجرای استخراج اطلاعات از پایگاه قوانین سازمان بورس (cmr.seo.ir)

نمونه‌های کاربرد:
  1. استخراج تمام اطلاعات و اسناد (کل ۱۲۸۲ سند به همراه پیوست‌ها):
     python run_crawler.py --all

  2. استخراج آزمایشی ۱۰ سند اول:
     python run_crawler.py --limit 10

  3. استخراج اسناد یک دسته‌بندی خاص (مثلاً دسته ۳۵):
     python run_crawler.py --category 35

  4. ادامه فرآیند متوقف‌شده (Resume خودکار فعال است):
     python run_crawler.py --all
"""

import argparse
from crawler.config import config
from crawler.client import SeoRuleClient
from crawler.extractor import BulkExtractor


def main():
    parser = argparse.ArgumentParser(
        description="سامانه استخراج اسناد حقوقی و مقررات بازار سرمایه (Regulatory RAG Crawler)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="استخراج تمام اسناد موجود در پایگاه قوانین (۱۲۸۲ سند)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="محدودیت تعداد اسناد برای استخراج در این اجرا (مثلاً 10 یا 50)"
    )
    parser.add_argument(
        "--category",
        type=int,
        default=None,
        help="شناسه دسته‌بندی خاص برای استخراج اسناد مربوط به آن"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.2,
        help="فاصله زمانی بر حسب ثانیه بین درخواست‌ها جهت رعایت سقف مجاز سرور (پیش‌فرض: 1.2 ثانیه)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="استخراج مجدد حتی برای اسنادی که قبلاً دانلود شده‌اند"
    )

    args = parser.parse_args()

    # اعمال تنظیمات فاصله زمانی
    config.rate_limit_delay = args.delay

    print("==================================================================")
    print("🚀 سامانه استخراج جامع اسناد حقوقی بازار سرمایه (Regulatory RAG)")
    print(f"⏱️ فاصله زمانی بین درخواست‌ها: {config.rate_limit_delay} ثانیه")
    if args.limit:
        print(f"🎯 سقف تعداد پردازش در این اجرا: {args.limit} سند")
    if args.category:
        print(f"📂 دسته‌بندی هدف: شناسه {args.category}")
    print("==================================================================")

    client = SeoRuleClient(config)
    extractor = BulkExtractor(client)

    extractor.run(
        limit=args.limit,
        category_id=args.category,
        force_reingest=args.force
    )


if __name__ == "__main__":
    main()
