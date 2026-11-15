"""
هستی‌شناسی و تعاریف پایه‌ای گراف دانش قوانین و مقررات (Knowledge Graph Ontology)
شامل انواع گره‌ها (Entities)، انواع یال‌ها (Relationships) و نگاشت نوع پیوندهای حقوقی
منطبق بر بخش ۴ و ۱۲ سند regulatory_rag_design_roadmap.md
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """انواع گره‌ها (موجودیت‌ها) در گراف دانش"""
    CATEGORY = "Category"            # دسته‌بندی موضوعی
    DOCUMENT = "Document"            # سند رسمی (قانون، دستورالعمل، آیین‌نامه و...)
    VERSION = "Version"              # نسخه تاریخی سند
    SECTION = "Section"              # بخش / فصل
    ARTICLE = "Article"              # ماده قانونی
    NOTE = "Note"                    # تبصره
    CLAUSE = "Clause"                # بند قانونی
    AUTHORITY = "Authority"          # مرجع تصویب یا ابلاغ (هیأت مدیره سازمان، شورا و...)
    ATTACHMENT = "Attachment"        # فایل پیوست رسمی (PDF، DOCX، فرم)


class RelationType(str, Enum):
    """انواع یال‌ها (روابط) در گراف دانش"""
    # ۱. روابط ساختاری و سلسله‌مراتبی (Structural Hierarchy)
    PARENT_CATEGORY_OF = "PARENT_CATEGORY_OF"    # دسته والد به فرزند
    BELONGS_TO_CATEGORY = "BELONGS_TO_CATEGORY"  # سند به دسته موضوعی
    HAS_VERSION = "HAS_VERSION"                  # سند به نسخه
    HAS_SECTION = "HAS_SECTION"                  # نسخه یا بخش به بخش/فصل
    HAS_ARTICLE = "HAS_ARTICLE"                  # بخش/فصل به ماده
    HAS_NOTE = "HAS_NOTE"                        # ماده به تبصره
    HAS_CLAUSE = "HAS_CLAUSE"                    # ماده به بند
    HAS_ATTACHMENT = "HAS_ATTACHMENT"            # نسخه به فایل پیوست
    ISSUED_BY = "ISSUED_BY"                      # نسخه به مرجع تصویب/ابلاغ

    # ۲. روابط حقوقی و تنقیحی بین‌اسناد (Inter-document Legal Relations)
    REPEALS = "REPEALS"                          # نسخ‌کننده (سند مبدأ سند مقصد را نسخ کرده است)
    REPEALED_BY = "REPEALED_BY"                  # منسوخ‌شده توسط (معکوس)
    AMENDS = "AMENDS"                            # اصلاح‌کننده (سند مبدأ سند مقصد را اصلاح کرده است)
    AMENDED_BY = "AMENDED_BY"                    # اصلاح‌شده توسط (معکوس)
    REPLACES = "REPLACES"                        # جایگزین‌کننده
    REPLACED_BY = "REPLACED_BY"                  # جایگزین‌شده توسط (معکوس)
    REFERENCES = "REFERENCES"                    # ارجاع‌دهنده در متن
    REFERENCED_BY = "REFERENCED_BY"              # ارجاع‌شده توسط (معکوس)
    RELATED_TO = "RELATED_TO"                    # مرتبط با (پیوند کلی)


# نگاشت کدهای نوع پیوند وب‌سرویس سازمان بورس به روابط استاندارد گراف
LINK_TYPE_MAPPING: Dict[int, tuple[RelationType, str]] = {
    1: (RelationType.REPEALS, "نسخ"),
    2: (RelationType.AMENDS, "اصلاح"),
    3: (RelationType.AMENDS, "الحاق"),
    4: (RelationType.RELATED_TO, "مرتبط با"),
    5: (RelationType.REFERENCES, "استناد / ارجاع"),
}


class GraphNode(BaseModel):
    """مدل استاندارد یک گره در گراف دانش"""
    id: str                                  # شناسه یکتای گره در کل گراف
    label: NodeType                          # برچسب موجودیت
    name: str                                # نام نمایشی یا عنوان
    properties: Dict[str, Any] = Field(default_factory=dict)  # فراداده‌ها، متن، وضعیت و...


class GraphEdge(BaseModel):
    """مدل استاندارد یک یال (رابطه جهت‌دار) در گراف دانش"""
    source_id: str                           # شناسه گره مبدأ
    target_id: str                           # شناسه گره مقصد
    relation_type: RelationType              # نوع رابطه
    label_fa: Optional[str] = None           # عنوان فارسی رابطه (مثلا 'نسخ می‌کند')
    properties: Dict[str, Any] = Field(default_factory=dict)  # شواهد رابطه، متن، درصد اطمینان
