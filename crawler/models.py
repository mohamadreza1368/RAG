"""
مدل‌های داده‌ای Pydantic برای اعتبارسنجی و ذخیره‌سازی اطلاعات استخراج‌شده
منطبق با مشخصات بخش ۴ و بخش ۷ سند regulatory_rag_design_roadmap.md
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field


class RuleCategory(BaseModel):
    """مدل دسته‌بندی موضوعی قوانین"""
    id: int
    title: str
    parentId: Optional[int] = None
    order: Optional[int] = 0


class RuleSummary(BaseModel):
    """خلاصه اطلاعات یک قانون در نتایج جستجو یا فهرست"""
    id: int
    ruleId: int
    ruleTypeTitle: Optional[str] = None
    version: Optional[str] = None
    title: str
    description: Optional[str] = None
    approvalNo: Optional[str] = None
    approvalDate: Optional[str] = None
    approvalInstitution: Optional[str] = None
    publishLetterNo: Optional[str] = None
    publishDate: Optional[str] = None
    tanghihStatus: Optional[str] = None
    executeDate: Optional[str] = None
    executeNo: Optional[str] = None
    executeAuthority: Optional[str] = None
    notificationNo: Optional[str] = None
    notificationDate: Optional[str] = None
    notificationAuthority: Optional[str] = None
    categoryTitle: Optional[str] = None


class RuleAttachment(BaseModel):
    """فایل پیوست سند"""
    id: int
    fileGuid: Optional[str] = None
    name: str
    fileType: Optional[str] = None
    local_path: Optional[str] = None
    file_size_bytes: Optional[int] = None


class RulePart(BaseModel):
    """ساختار درختی محتوای حقوقی: بخش، فصل، ماده، بند، تبصره"""
    id: int
    parentId: Optional[int] = None
    title: Optional[str] = None
    tanghihStatusTitle: Optional[str] = None
    tanghihStatusId: Optional[int] = None
    orderNo: Optional[int] = None
    rulePartTypeId: Optional[int] = None
    rulePartType: Optional[str] = None  # ماده، بند، تبصره، فصل، بخش
    description: Optional[str] = None
    body: Optional[str] = None  # متن اصلی به همراه ساختار HTML
    approvalNo: Optional[str] = None
    approvalDate: Optional[str] = None


class RuleDependency(BaseModel):
    """روابط بین اسناد یا نسخه‌ها (نوع پیوند)"""
    id: int
    dependentVersion: Optional[dict] = None
    linkType: Optional[int] = None
    linkTypeTitle: Optional[str] = None


class RuleVersionDetail(BaseModel):
    """جزییات نسخه مشخص یک قانون"""
    id: int
    ruleId: int
    version: Optional[str] = None
    title: str
    description: Optional[str] = None
    approvalNo: Optional[str] = None
    approvalDate: Optional[str] = None
    approvalInstitution: Optional[Any] = None  # می‌تواند رشته یا آبجکت {'id': ..., 'title': ...} باشد
    approvalDescription: Optional[str] = None
    publishLetterNo: Optional[str] = None
    publishDate: Optional[str] = None
    tanghihStatus: Optional[Any] = None  # می‌تواند رشته یا آبجکت باشد
    executeDate: Optional[str] = None
    executeNo: Optional[str] = None
    executeAuthority: Optional[Any] = None
    notificationNo: Optional[str] = None
    notificationDate: Optional[str] = None
    notificationAuthority: Optional[Any] = None
    isReleased: Optional[bool] = None
    expireDate: Optional[str] = None
    files: List[RuleAttachment] = Field(default_factory=list)



class CompleteDocumentPackage(BaseModel):
    """
    پکیج یکپارچه استخراج یک سند رسمی شامل تمام ابعاد ساختاری و رابطه‌ای
    منطبق بر طراحی بخش ۷ سند معماری
    """
    rule_id: int
    source_url: str
    category_id: Optional[int] = None
    category_title: Optional[str] = None
    rule_info: Optional[dict] = None
    active_version: Optional[RuleVersionDetail] = None
    all_versions: List[dict] = Field(default_factory=list)
    parts: List[RulePart] = Field(default_factory=list)
    dependencies: List[RuleDependency] = Field(default_factory=list)
    attachments: List[RuleAttachment] = Field(default_factory=list)
