"""
پکیج ماژول استخراج قوانین و مقررات بازار سرمایه (cmr.seo.ir)
"""

from .config import config, CrawlerConfig
from .client import SeoRuleClient
from .models import (
    RuleCategory,
    RuleSummary,
    RuleVersionDetail,
    RulePart,
    RuleDependency,
    RuleAttachment,
    CompleteDocumentPackage,
)

__all__ = [
    "config",
    "CrawlerConfig",
    "SeoRuleClient",
    "RuleCategory",
    "RuleSummary",
    "RuleVersionDetail",
    "RulePart",
    "RuleDependency",
    "RuleAttachment",
    "CompleteDocumentPackage",
]
