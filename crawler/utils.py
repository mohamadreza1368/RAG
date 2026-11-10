"""
توابع کمکی شبکه، تشخیص کارت شبکه فعال و نرمال‌سازی اولیه داده‌ها
"""

import socket
import logging
from typing import Optional
import psutil

logger = logging.getLogger("regulatory_crawler")


def detect_physical_active_ip() -> Optional[str]:
    """
    شناسایی خودکار آی‌پی کارت شبکه فیزیکی فعال در سیستم.
    این تابع آداپتورهای مجازی (مانند VPN ،WSL ،Hyper-V و TUN) را فیلتر می‌کند
    تا درخواست‌ها مستقیماً از شبکه ملی بدون مسدود شدن از سمت سرور سازمان بورس ارسال شوند.
    """
    excluded_keywords = [
        "tun", "tap", "vpn", "fortinet", "vethernet",
        "wsl", "loopback", "pseudo", "virtual", "direct"
    ]
    
    candidates = []
    for iface_name, addrs in psutil.net_if_addrs().items():
        stats = psutil.net_if_stats().get(iface_name)
        if not stats or not stats.isup:
            continue
            
        lower_name = iface_name.lower()
        if any(keyword in lower_name for keyword in excluded_keywords):
            continue
            
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip = addr.address
                # نادیده گرفتن IPهای لوکال‌هاست و رنج خوداختصاصی APIPA
                if not ip.startswith(("127.", "169.254.")):
                    candidates.append((iface_name, ip))
                    
    if candidates:
        selected_iface, selected_ip = candidates[0]
        logger.info(f"کارت شبکه فیزیکی انتخاب شد: {selected_iface} با نشانی {selected_ip}")
        return selected_ip
        
    logger.warning("کارت شبکه فیزیکی مجزا یافت نشد؛ از مسیریابی پیش‌فرض سیستم استفاده می‌شود.")
    return None
