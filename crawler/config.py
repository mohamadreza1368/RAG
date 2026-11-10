"""
تنظیمات پایه و پیکربندی ماژول استخراج اطلاعات پایگاه قوانین و مقررات بازار سرمایه (cmr.seo.ir)
مطابق با اهداف سند طراحی معماری regulatory_rag_design_roadmap.md
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field


class CrawlerConfig(BaseModel):
    # نشانی‌های پایه وب‌سرویس
    base_url: str = "https://cmr.seo.ir/api/api/v1"
    site_origin: str = "https://cmr.seo.ir"

    # پارامترهای شبکه
    timeout: int = 20
    max_retries: int = 3
    retry_backoff_factor: float = 1.5
    rate_limit_delay: float = 0.5  # تأخیر بر حسب ثانیه بین درخواست‌ها جهت حفظ رفتار مؤدبانه

    # الزام آی‌پی اتصال برای سرورهای اینترانت ایران (جلوگیری از قطع ارتباط از طریق VPN)
    bind_physical_ip: bool = True
    manual_source_ip: str | None = None

    # هدرهای درخواست
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    # مسیرهای ذخیره‌سازی داده‌های استخراج‌شده
    base_data_dir: Path = Field(default_factory=lambda: Path("data"))
    raw_data_dir: Path = Field(default_factory=lambda: Path("data/raw"))
    attachments_dir: Path = Field(default_factory=lambda: Path("data/attachments"))

    def model_post_init(self, __context) -> None:
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.attachments_dir.mkdir(parents=True, exist_ok=True)


config = CrawlerConfig()
