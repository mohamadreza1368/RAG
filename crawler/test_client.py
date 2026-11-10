"""
تست صحت عملکرد کلاینت استخراج و اتصال به وب‌سرویس قوانین بازار سرمایه
"""

import sys
from pathlib import Path
import json

# افزودن ریشه پروژه به sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler.client import SeoRuleClient


def main():
    print("====================================================")
    print("تست ماژول استخراج قوانین و مقررات (SeoRuleClient)")
    print("====================================================")

    client = SeoRuleClient()

    # ۱. تست دریافت دسته‌بندی‌ها
    print("\n[۱] دریافت درختواره دسته‌بندی‌ها...")
    categories = client.get_all_categories()
    print(f"تعداد دسته‌بندی‌های دریافت شده: {len(categories)}")
    assert len(categories) > 0, "لیست دسته‌بندی‌ها نباید خالی باشد!"
    for c in categories[:5]:
        print(f"  - شناسه: {c.id} | والد: {c.parentId} | عنوان: {c.title}")

    # ۲. تست جستجو و دریافت نمونه‌ای از قوانین
    print("\n[۲] تست جستجو و دریافت خلاصه قوانین...")
    rules = client.search_rules(page_number=1, page_size=3)
    print(f"تعداد اسناد دریافت شده: {len(rules)}")
    assert len(rules) > 0, "لیست قوانین نباید خالی باشد!"
    for r in rules:
        print(f"  - شناسه: {r.ruleId} | عنوان: {r.title[:60]}... | مرجع: {r.approvalInstitution}")

    # ۳. تست استخراج کامل سند نمونه نقشه راه (شناسه 71485)
    test_id = 71485
    print(f"\n[۳] استخراج جامع سند نمونه شناسه {test_id} (مطابق سند معماری)...")
    package = client.fetch_complete_rule(test_id)
    assert package is not None, "پکیج سند نمونه نباید خالی باشد!"
    assert package.active_version is not None, "نسخه فعال سند باید موجود باشد!"

    print("\nاطلاعات پکیج استخراج شده:")
    print(f"  - عنوان: {package.active_version.title}")
    print(f"  - تاریخ تصویب: {package.active_version.approvalDate}")
    print(f"  - مرجع تصویب: {package.active_version.approvalInstitution}")
    print(f"  - وضعیت تنقیحی: {package.active_version.tanghihStatus}")
    print(f"  - تعداد مواد/بخش‌های استخراج شده: {len(package.parts)}")
    print(f"  - تعداد روابط سندی (نوع پیوند): {len(package.dependencies)}")
    print(f"  - تعداد فایل‌های پیوست دانلود شده: {len(package.attachments)}")

    if package.parts:
        print("\nنمونه ماده ۱:")
        p1 = package.parts[1] if len(package.parts) > 1 else package.parts[0]
        print(f"  نوع: {p1.rulePartType} | عنوان: {p1.title}")
        print(f"  متن: {p1.body[:150]}...")

    if package.attachments:
        print("\nفایل پیوست:")
        att = package.attachments[0]
        print(f"  نام فایل: {att.name}")
        print(f"  مسیر ذخیره‌شده: {att.local_path}")
        print(f"  حجم: {att.file_size_bytes:,} بایت")

    # ذخیره نمونه JSON پکیج در مسیر data/raw جهت بررسی
    output_sample = Path("data/raw/sample_71485.json")
    output_sample.parent.mkdir(parents=True, exist_ok=True)
    with open(output_sample, "w", encoding="utf-8") as f:
        json.dump(package.model_dump(), f, ensure_ascii=False, indent=2)
    print(f"\nنمونه کامل داده ساخت‌یافته در {output_sample} ذخیره شد.")

    print("\n✅ تمام تست‌های مرحله اول با موفقیت پاس شدند.")


if __name__ == "__main__":
    main()
