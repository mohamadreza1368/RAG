"""
مدل‌های داده‌ای Pydantic برای ساختار حقوقی پارس‌شده و چانک‌های استاندارد RAG
مطابق با بخش ۶، بخش ۹ و بخش ۱۰ سند regulatory_rag_design_roadmap.md
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class NormalizedSection(BaseModel):
    """مدل ساختار سلسله‌مراتبی بخش‌ها، فصول، مواد، بندها و تبصره‌ها"""
    id: int
    parent_id: Optional[int] = None
    section_type: str  # بخش، فصل، ماده، بند، تبصره، پیوست و...
    section_number: Optional[str] = None  # شماره ماده یا بند
    title: str
    raw_body: str
    normalized_text: str
    order_no: int = 0
    tanghih_status: Optional[str] = None
    section_path: List[str] = Field(default_factory=list)  # مسیر کامل مثلا: ['بخش یک', 'ماده ۱']
    children_ids: List[int] = Field(default_factory=list)


class LegalChunk(BaseModel):
    """
    مدل استاندارد چانک حقوقی برای بازیابی معنایی و واژگانی
    مطابق با تعریف بخش ۱۰.۲ سند معماری
    """
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_source_id: str
    document_title: str
    document_type: Optional[str] = None
    version_id: Optional[str] = None
    chapter: Optional[str] = None  # عنوان بخش یا فصل
    article_number: Optional[str] = None  # شماره ماده (برای فیلترهای دقیق)
    paragraph_number: Optional[str] = None  # شماره بند یا تبصره
    section_path: List[str] = Field(default_factory=list)
    content: str  # متن خالص استانداردشده ماده و تبصره‌های زیرمجموعه
    contextual_content: str  # متن غنی‌شده با متادیتا و هدر کانتکست
    token_count: int = 0
    status: Optional[str] = None  # وضعیت تنقیحی: معتبر، منسوخ و...
    source_url: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ParsedDocument(BaseModel):
    """خروجی نهایی خط پردازش فاز ۲ برای یک سند رسمی"""
    rule_id: int
    source_url: str
    title: str
    document_type: Optional[str] = None
    issuing_authority: Optional[str] = None
    approval_date: Optional[str] = None
    tanghih_status: Optional[str] = None
    sections: List[NormalizedSection] = Field(default_factory=list)
    chunks: List[LegalChunk] = Field(default_factory=list)
    total_sections: int = 0
    total_chunks: int = 0
