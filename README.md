# RAG - Regulatory Knowledge Graph & Hybrid RAG System

سامانه هوشمند جست‌وجو و پاسخ‌گویی تخصصی بر پایه **گراف دانش حقوقی (Knowledge Graph)** و بازیابی ترکیبی (Hybrid Vector + Graph Retrieval) برای قوانین، مقررات، دستورالعمل‌ها، مواد، بندها و پیوست‌های بازار سرمایه و سازمان بورس و اوراق بهادار ([cmr.seo.ir](https://cmr.seo.ir)).

---

## 🏛️ معماری سیستم و هستی‌شناسی گراف دانش (Ontology)

برخلاف RAGهای سنتی که متن را به قطعات ایزوله تبدیل می‌کنند، این سامانه متن را به صورت یک **گراف چندلایه‌ای از موجودیت‌ها و پیوندهای حقوقی** مدل‌سازی می‌کند:

```mermaid
flowchart TD
    Cat["Category (دسته‌بندی موضوعی)"] -->|BELONGS_TO| Doc["Document (سند اصلی قانون)"]
    Doc -->|HAS_VERSION| Ver["Version (نسخه سند)"]
    Doc -->|ISSUED_BY| Auth["Authority (مرجع تصویب)"]
    Ver -->|HAS_ATTACHMENT| Att["Attachment (فایل رسمی PDF/DOCX)"]
    Ver -->|HAS_SECTION| Sec["Section (فصل / بخش)"]
    Sec -->|HAS_ARTICLE| Art["Article (ماده قانونی)"]
    Art -->|HAS_NOTE| Note["Note (تبصره)"]
    Art -->|HAS_CLAUSE| Clause["Clause (بند)"]
    
    Doc -.->|REPEALS (نسخ)| DocOther["Document دیگر (منسوخ‌شده)"]
    Doc -.->|AMENDS (اصلاح)| DocOther2["Document دیگر (اصلاح‌شده)"]
    Doc -.->|REFERENCES (استناد)| DocOther3["Document دیگر (مورد ارجاع)"]
```

---

## 📋 ساختار ماژول‌های پروژه

* **`regulatory_rag_design_roadmap.md`**: سند جامع طراحی فنی، مدل داده، هستی‌شناسی گراف و نقشه راه پیاده‌سازی.
* **`crawler/` (فاز ۱ - Ingestion و خزش)**:
  * `config.py` & `client.py`: کلاینت مقاوم با اتصال مستقیم کارت شبکه، مدیریت Retry و سقف نرخ سرور.
  * `extractor.py`: استخراج خودکار اسناد با قابلیت ثبت پیشرفت (Checkpointing) و ازسرگیری (Resume).
* **`preprocessor/` (فاز ۲ - نرمال‌سازی متون و ساختاردهی)**:
  * `normalizer.py`: نرمال‌سازی فارسی، تبدیل ارقام و کاراکترهای عربی، و استانداردسازی نیم‌فاصله‌ها.
  * `parser.py`: پارسر ساختار حقوقی، استخراج شماره مواد و استخراج مسیر موقعیت منبع (`section_path`).
  * `chunker.py`: استخراج متن گره‌های ماده و تبصره‌ها با هدر کانتکست جهت استفاده در گره‌های برداری.
* **`knowledge_graph/` (فاز ۳ - موتور گراف دانش)**:
  * `ontology.py`: تعاریف گره‌ها (`Document`, `Article`, `Version`, `Authority`, `Category`, `Attachment`) و یال‌ها (`AMENDS`, `REPEALS`, `REFERENCES`, `RELATED_TO`, `HAS_ARTICLE`).
  * `builder.py`: ساخت خودکار گراف دانش جهت‌دار (NetworkX) از روی اسناد و دسته‌بندی‌ها.
  * `traverser.py`: موتور پیمایش چندمرحله‌ای روابط (Relation Expansion) جهت کشف اسناد نسخ‌شده، اصلاحیه‌ها و پیوست‌ها.
  * `exporter.py`: صدور گراف به قالب‌های استاندارد JSON ،Triples TSV و کدهای Neo4j Cypher.
  * `visualizer.py`: تولید داشبورد گراف تعاملی و تحت وب (HTML) با امکان کلیک، جستجو و فیلتر.

---

## 🚀 راهنمای سریع اجرا

### ۱. اجرای استخراج اسناد (فاز ۱)
```bash
# استخراج کامل اسناد با قابلیت Resume خودکار:
python run_crawler.py --all
```

### ۲. نرمال‌سازی متون و چانکینگ حقوقی (فاز ۲)
```bash
# پردازش و استانداردسازی متون خام:
python run_preprocessor.py
```

### ۳. ساخت و کاوش گراف دانش (فاز ۳ - Knowledge Graph)
```bash
# ساخت کامل گراف دانش و صدور فایل‌های Triples، Neo4j و HTML تعاملی:
python run_graph.py --build

# پیمایش و توسعه روابط یک سند مشخص (Relation Expansion):
python run_graph.py --expand 71485

# مشاهده آمار گره‌ها و یال‌های موجودیت‌ها:
python run_graph.py --stats
```

داشبورد تعاملی گراف در مسیر `data/graph/graph_explorer.html` با هر مرورگری قابل باز شدن و کاوش بصری است.
