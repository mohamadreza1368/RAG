import logging
from typing import Dict, Any, Optional
from ..base import BaseRAGEngine

logger = logging.getLogger(__name__)

class SampleCustomRAGEngine(BaseRAGEngine):
    """
    Template / Blueprint for connecting any new RAG engine into the ecosystem.
    Examples of future RAGs:
      - Financial Statements RAG (صورت‌های مالی کدال)
      - Corporate Governance & Circulars RAG (بخشنامه‌های داخلی)
      - Commercial Code & Tax Laws RAG (قوانین تجارت و مالیاتی)
    """

    engine_id: str = "custom_sample"
    display_name: str = "نمونه ماژول RAG سفارشی (Template)"
    description: str = "الگوی آماده جهت اتصال هر پایگاه دانش یا وکتوراستور جدید به اکوسیستم یکپارچه"
    icon: str = "sparkles"
    version: str = "1.0.0"
    enabled: False  # Set to True when implemented

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        mode: Optional[str] = None,
        alpha: Optional[float] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        # Connect to your vector store, elasticsearch, or graph here
        return {
            "engine_id": self.engine_id,
            "engine_name": self.display_name,
            "rag_context": f"محتوای استخراج‌شده نمونه برای پرسش: {query}",
            "warnings": [],
            "sources": [
                {
                    "rule_title": "مستند نمونه",
                    "article": "ماده آزمایشی",
                    "status": "معتبر",
                    "score": 0.95,
                    "snippet": f"این یک خروجی نمونه از موتور {self.display_name} است."
                }
            ],
            "mode": mode or "custom",
            "alpha": alpha
        }

    def health_check(self) -> Dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "status": "template_only",
            "enabled": self.enabled
        }
