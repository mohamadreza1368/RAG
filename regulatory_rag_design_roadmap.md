# طراحی فنی و نقشه راه پیاده‌سازی Regulatory RAG

## سامانه هوشمند جست‌وجو و پاسخ‌گویی مبتنی بر قوانین، مقررات، دستورالعمل‌ها و پیوست‌ها

**نسخه سند:** 1.0\
**تاریخ تهیه:** ۱۴۰۵/۰۸/۱۸\
**وضعیت:** سند پیشنهادی برای شروع طراحی و توسعه\
**دامنه نمونه:** پایگاه قوانین و مقررات سازمان بورس و اوراق بهادار و
صفحات مشابه در سامانه‌های رسمی

------------------------------------------------------------------------

## 1. خلاصه اجرایی

هدف پروژه ساخت یک سامانه RAG تخصصی برای اسناد حقوقی و مقرراتی است.
برخلاف RAG عمومی که معمولاً اسناد را به متن تبدیل، قطعه‌بندی و در پایگاه
برداری ذخیره می‌کند، این سامانه باید ساختار حقوقی اسناد و روابط بین آن‌ها
را حفظ کند.

در صفحه نمونه، یک سند اصلی با عنوان «دستورالعمل نحوه افزایش سرمایه از
محل تجدید ارزیابی دارایی‌ها در شرکت‌های سهامی عام ثبت‌شده نزد سازمان» و
شناسه صفحه `71485` وجود دارد. در کنار محتوای سند، بخش «نوع پیوند» به
اسناد دیگر اشاره می‌کند و بخش پیوست‌ها می‌تواند شامل دستورالعمل، فرم یا
فایل مستقل باشد.

بنابراین سامانه باید سه لایه اطلاعات را هم‌زمان مدیریت کند:

1.  **محتوای سند:** متن، فصل، ماده، بند، تبصره، جدول و صفحه.
2.  **فراداده سند:** عنوان، نوع، مرجع تصویب/انتشار، تاریخ‌ها، وضعیت و
    شناسه منبع.
3.  **روابط سندی:** ارتباط با سایر مقررات، پیوست بودن، اصلاح، نسخ،
    جایگزینی و ارجاع.

### تصمیم معماری پیشنهادی

برای نسخه اول:

-   PostgreSQL: اطلاعات اسناد، نسخه‌ها، ساختار مواد و روابط.
-   Qdrant: بردارهای متن و بازیابی معنایی.
-   موتور BM25: جست‌وجوی واژگانی و عبارت دقیق.
-   Python و FastAPI: سرویس‌های پردازش و API.
-   EmbeddingGemma: مدل Embedding فعلی.
-   Qwen: مدل زبانی پاسخ‌گو.
-   Reranker: مرتب‌سازی مجدد نتایج بازیابی‌شده، در صورت دسترس بودن مدل
    مناسب فارسی.
-   Object Storage یا فایل‌سیستم مدیریت‌شده: نگهداری فایل اصلی و نسخه‌های
    استخراج‌شده.

در نسخه اول استفاده از Neo4j الزامی نیست. روابط را می‌توان در PostgreSQL
نگهداری و با Recursive CTE یا چند Query کنترل‌شده پیمایش کرد. در صورت رشد
پیچیدگی و نیاز به پیمایش‌های چندمرحله‌ای گسترده، Graph Database قابل اضافه
شدن است.

------------------------------------------------------------------------

## 2. اهداف و خارج از دامنه

### 2.1 اهداف

-   دریافت خودکار صفحات و فایل‌های رسمی.
-   استخراج فراداده و محتوای اسناد.
-   شناسایی و نگهداری رابطه میان اسناد.
-   حفظ ساختار حقوقی شامل فصل، ماده، بند و تبصره.
-   جست‌وجوی ترکیبی معنایی و واژگانی.
-   بازیابی اسناد مرتبط و پیوست‌ها در کنار سند اصلی.
-   مدیریت اصلاحیه‌ها، نسخ و نسخه‌های تاریخی.
-   ارائه پاسخ همراه با ارجاع دقیق به سند، ماده، بند و URL.
-   جلوگیری از ارائه پاسخ قطعی در صورت ناکافی بودن مستندات.

### 2.2 خارج از دامنه نسخه اول

-   تفسیر حقوقی مستقل و جایگزینی نظر متخصص حقوقی.
-   تشخیص خودکار قطعی اعتبار قانونی بدون سند رسمی پشتیبان.
-   استخراج کامل تمام روابط ضمنی از متن بدون بازبینی انسانی.
-   پوشش تمام وب‌سایت‌های حقوقی کشور از روز اول.
-   اجرای خودکار اقدامات حقوقی یا اداری بر اساس پاسخ مدل.

------------------------------------------------------------------------

## 3. اصول طراحی

1.  **منبع رسمی مقدم است:** متن استخراج‌شده باید به URL و فایل اصلی قابل
    ردیابی باشد.
2.  **عدم حدس در فراداده:** فیلد ناموجود باید `NULL` بماند؛ مدل نباید
    تاریخ یا وضعیت را حدس بزند.
3.  **تفکیک نوع رابطه:** «مرتبط با»، «پیوست»، «اصلاح‌کننده» و «نسخ‌کننده»
    معانی متفاوت دارند.
4.  **حفظ متن خام:** خروجی Parser و OCR باید همراه با متن نرمال‌شده
    نگهداری شود.
5.  **ردیابی‌پذیری:** هر Chunk باید به سند، نسخه و موقعیت اصلی خود متصل
    باشد.
6.  **نسخه‌پذیری:** به‌روزرسانی سند نباید نسخه قبلی را بدون ردپا از بین
    ببرد.
7.  **بازیابی قابل توضیح:** سامانه باید بتواند توضیح دهد هر سند چرا وارد
    Context شده است.
8.  **احتیاط حقوقی:** ارتباط دو سند به‌تنهایی اثبات‌کننده اصلاح، نسخ یا
    تقدم یکی بر دیگری نیست.
9.  **تفکیک استخراج از تأیید:** استخراج ماشینی رابطه با تأیید حقوقی آن
    یکسان نیست.
10. **پاسخ مستند:** ادعاهای مهم پاسخ باید به منابع بازیابی‌شده متصل
    باشند.

------------------------------------------------------------------------

## 4. مدل مفهومی دامنه

### 4.1 موجودیت‌های اصلی

  موجودیت            شرح
  ------------------ ---------------------------------------------------
  Document           هویت پایدار یک سند حقوقی
  DocumentVersion    یک نسخه مشخص از سند در یک بازه زمانی یا انتشار
  SourceRecord       رکورد صفحه وب یا سامانه‌ای که سند از آن دریافت شده
  Attachment         فایل پیوست متصل به سند یا نسخه
  DocumentRelation   رابطه جهت‌دار میان دو سند
  Section            ساختار فصل، بخش، ماده، بند و تبصره
  Chunk              قطعه قابل بازیابی از محتوای سند
  IngestionRun       سابقه هر بار دریافت و پردازش
  ExtractionReview   نتیجه بازبینی انسانی داده‌های استخراج‌شده

### 4.2 تفاوت سند، نسخه و صفحه منبع

-   `Document` هویت منطقی سند است؛ مثلاً دستورالعمل مشخص.
-   `DocumentVersion` نسخه مشخصی از همان سند است.
-   `SourceRecord` صفحه‌ای است که اطلاعات یا فایل را منتشر کرده است.
-   شناسه `71485` در نمونه، در ابتدا باید به‌عنوان شناسه منبع ذخیره شود؛
    تا زمانی که معنای آن از ساختار سامانه تأیید نشده، نباید آن را شناسه
    حقوقی یا شماره مصوبه فرض کرد.

### 4.3 انواع رابطه

مجموعه پیشنهادی اولیه:

  -----------------------------------------------------------------------
  کد رابطه                معنا                    توضیح
  ----------------------- ----------------------- -----------------------
  RELATED_TO              مرتبط با                ارتباط اعلام‌شده در سایت
                                                  یا تأییدشده

  HAS_ATTACHMENT          دارای پیوست             رابطه از سند اصلی به
                                                  پیوست

  ATTACHMENT_OF           پیوستِ                   جهت معکوس رابطه بالا

  REFERENCES              ارجاع می‌دهد به          ارجاع در متن سند

  AMENDS                  اصلاح می‌کند             فقط با شواهد صریح

  AMENDED_BY              اصلاح شده توسط          جهت معکوس AMENDS

  REPEALS                 نسخ می‌کند               فقط با شواهد رسمی

  REPEALED_BY             نسخ شده توسط            جهت معکوس REPEALS

  REPLACES                جایگزین می‌کند           جایگزینی رسمی

  SUPERSEDES              مقدم/جایگزین نسخه پیشین با تعریف دقیق سیاست
                                                  حقوقی پروژه

  IMPLEMENTS              در اجرای سند دیگر       رابطه اجرایی، در صورت
                                                  تصریح

  UNKNOWN                 نامشخص                  برای داده مبهم و
                                                  نیازمند بررسی
  -----------------------------------------------------------------------

**قاعده:** روابط معکوس را می‌توان هنگام Query محاسبه کرد یا به شکل صریح
ذخیره کرد؛ اما از ایجاد روابط متناقض و تکراری جلوگیری شود.

### 4.4 ویژگی‌های رابطه

هر رابطه علاوه بر نوع باید این مشخصات را داشته باشد:

-   منبع استخراج: فیلد سایت، متن سند، تطبیق شناسه یا بازبینی کارشناس.
-   شواهد: عبارت یا عنوانی که رابطه از آن استخراج شده است.
-   محل شواهد: URL، بخش صفحه، شماره صفحه یا قطعه متن.
-   میزان اطمینان استخراج.
-   وضعیت تأیید: تأییدنشده، تأییدشده، ردشده.
-   تاریخ مشاهده و تاریخ آخرین بررسی.

------------------------------------------------------------------------

## 5. معماری کلان سامانه

``` mermaid
flowchart TD
    A[Official Websites] --> B[Crawler]
    B --> C[Raw HTML and Files]
    C --> D[Parser and OCR]
    D --> E[Document Normalization]
    E --> F[Metadata Extraction]
    E --> G[Legal Structure Extraction]
    E --> H[Attachment Extraction]
    F --> I[Document Registry]
    G --> J[Sections and Chunks]
    H --> I
    I --> K[Relation Extraction]
    K --> L[Relation Validation]
    J --> M[Embedding Service]
    M --> N[Qdrant]
    I --> O[(PostgreSQL)]
    L --> O
    J --> O
    P[User Query] --> Q[Query Understanding]
    Q --> R[Hybrid Retrieval]
    R --> N
    R --> O
    O --> S[Relation Expansion]
    S --> T[Context Builder]
    R --> T
    T --> U[Qwen LLM]
    U --> V[Answer and Citations]
```

### 5.1 جریان Ingestion

1.  دریافت URL صفحه.
2.  ذخیره HTML خام و اطلاعات دریافت.
3.  استخراج عنوان، شناسه منبع، نوع سند و لینک فایل‌ها.
4.  دریافت فایل‌های پیوست.
5.  استخراج متن از HTML/PDF/DOCX یا اجرای OCR در صورت نیاز.
6.  نرمال‌سازی متن فارسی.
7.  استخراج ساختار حقوقی.
8.  ایجاد یا به‌روزرسانی Document و DocumentVersion.
9.  استخراج روابط و شواهد رابطه.
10. اعتبارسنجی قواعد و در صورت نیاز ارسال برای بازبینی انسانی.
11. ساخت Chunkها.
12. تولید Embedding.
13. ذخیره داده‌ها در PostgreSQL و Qdrant.
14. ثبت نتیجه و خطاهای اجرای Ingestion.

### 5.2 جریان Query

1.  دریافت سؤال.
2.  تشخیص نوع سؤال: محتوایی، شناسایی سند، روابط، وضعیت اعتبار یا سؤال
    ترکیبی.
3.  استخراج شناسه‌ها، عنوان‌ها، شماره مواد و تاریخ مورد سؤال.
4.  اجرای جست‌وجوی واژگانی و برداری.
5.  ادغام و Rerank نتایج.
6.  شناسایی اسناد اصلی مرتبط.
7.  پیمایش روابط مجاز و بازیابی اسناد وابسته.
8.  فیلتر زمانی و وضعیت نسخه‌ها.
9.  ساخت Context با سقف توکن مشخص.
10. تولید پاسخ با ارجاع.
11. اعتبارسنجی ارجاعات و نمایش محدودیت‌ها.

------------------------------------------------------------------------

## 6. طراحی پایگاه داده PostgreSQL

طرح زیر نقطه شروع نسخه اول است و پیش از Production باید با نمونه واقعی
صفحات و نیازهای گزارش‌گیری نهایی شود.

### 6.1 جدول documents

``` sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    source_system VARCHAR(100) NOT NULL,
    source_id VARCHAR(200),
    canonical_key VARCHAR(300) UNIQUE,
    title TEXT NOT NULL,
    normalized_title TEXT,
    document_type VARCHAR(80),
    issuing_authority TEXT,
    approval_number VARCHAR(200),
    approval_date DATE,
    publication_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_source_id
    ON documents(source_system, source_id);

CREATE INDEX idx_documents_title
    ON documents USING GIN (to_tsvector('simple', title));
```

### 6.2 جدول document_versions

``` sql
CREATE TABLE document_versions (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id),
    version_number INTEGER NOT NULL,
    source_url TEXT,
    file_uri TEXT,
    raw_content_uri TEXT,
    extracted_text_uri TEXT,
    content_hash VARCHAR(128) NOT NULL,
    valid_from DATE,
    valid_until DATE,
    approval_date DATE,
    publication_date DATE,
    effective_date DATE,
    status VARCHAR(40) DEFAULT 'UNKNOWN',
    is_current BOOLEAN DEFAULT FALSE,
    extraction_status VARCHAR(40) DEFAULT 'PENDING',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(document_id, version_number)
);

CREATE INDEX idx_document_versions_document
    ON document_versions(document_id);

CREATE INDEX idx_document_versions_current
    ON document_versions(document_id, is_current);
```

وضعیت‌هایی مانند `ACTIVE`، `REPEALED`، `SUPERSEDED` و `UNKNOWN` باید بر
اساس شواهد رسمی تعیین شوند. `is_current` نیز وضعیت نسخه در پایگاه دانش
را نشان می‌دهد و لزوماً معادل اعتبار حقوقی نیست.

### 6.3 جدول document_relations

``` sql
CREATE TABLE document_relations (
    id UUID PRIMARY KEY,
    source_document_id UUID NOT NULL REFERENCES documents(id),
    target_document_id UUID NOT NULL REFERENCES documents(id),
    relation_type VARCHAR(60) NOT NULL,
    evidence_text TEXT,
    evidence_url TEXT,
    evidence_location TEXT,
    extraction_method VARCHAR(40),
    confidence NUMERIC(5,4),
    review_status VARCHAR(30) DEFAULT 'UNREVIEWED',
    observed_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    CHECK (source_document_id <> target_document_id),
    UNIQUE(source_document_id, target_document_id, relation_type)
);

CREATE INDEX idx_relations_source
    ON document_relations(source_document_id, relation_type);

CREATE INDEX idx_relations_target
    ON document_relations(target_document_id, relation_type);
```

### 6.4 جدول attachments

``` sql
CREATE TABLE attachments (
    id UUID PRIMARY KEY,
    owner_document_version_id UUID NOT NULL
        REFERENCES document_versions(id),
    attachment_document_id UUID REFERENCES documents(id),
    title TEXT,
    original_filename TEXT,
    mime_type VARCHAR(120),
    source_url TEXT,
    file_uri TEXT,
    content_hash VARCHAR(128),
    attachment_order INTEGER,
    extraction_status VARCHAR(40) DEFAULT 'PENDING',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

اگر فایل پیوست خودش یک سند مستقل باشد، `attachment_document_id` به سند
مربوط متصل می‌شود. اگر صرفاً یک تصویر یا فایل کمکی باشد و هویت حقوقی
مستقلی نداشته باشد، می‌تواند فقط رکورد Attachment باقی بماند.

### 6.5 جدول sections

``` sql
CREATE TABLE sections (
    id UUID PRIMARY KEY,
    document_version_id UUID NOT NULL
        REFERENCES document_versions(id),
    parent_section_id UUID REFERENCES sections(id),
    section_type VARCHAR(40) NOT NULL,
    section_number VARCHAR(80),
    title TEXT,
    content TEXT,
    page_start INTEGER,
    page_end INTEGER,
    order_index INTEGER NOT NULL,
    source_anchor TEXT
);

CREATE INDEX idx_sections_version_order
    ON sections(document_version_id, order_index);
```

مقادیر نمونه `section_type`:

-   PREAMBLE
-   CHAPTER
-   SECTION
-   ARTICLE
-   PARAGRAPH
-   CLAUSE
-   NOTE
-   TABLE
-   ANNEX

### 6.6 جدول chunks

``` sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_version_id UUID NOT NULL
        REFERENCES document_versions(id),
    section_id UUID REFERENCES sections(id),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    contextual_content TEXT,
    token_count INTEGER,
    page_start INTEGER,
    page_end INTEGER,
    article_number VARCHAR(80),
    paragraph_number VARCHAR(80),
    content_hash VARCHAR(128),
    embedding_model VARCHAR(120),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(document_version_id, chunk_index)
);

CREATE INDEX idx_chunks_version
    ON chunks(document_version_id);

CREATE INDEX idx_chunks_section
    ON chunks(section_id);
```

### 6.7 جدول ingestion_runs

``` sql
CREATE TABLE ingestion_runs (
    id UUID PRIMARY KEY,
    source_url TEXT NOT NULL,
    source_system VARCHAR(100),
    source_id VARCHAR(200),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL,
    http_status INTEGER,
    content_hash VARCHAR(128),
    documents_created INTEGER DEFAULT 0,
    documents_updated INTEGER DEFAULT 0,
    chunks_created INTEGER DEFAULT 0,
    error_message TEXT
);
```

### 6.8 ملاحظات دیتابیسی

-   برای شناسه‌های سایت از `source_system + source_id` استفاده شود؛ شناسه
    منبع را با شناسه داخلی UUID مخلوط نکنید.
-   حذف فیزیکی سند توصیه نمی‌شود؛ برای عدم نمایش یا حذف از چرخه بازیابی
    از وضعیت استفاده کنید.
-   برای تاریخ شمسی، در صورت نیاز UI می‌تواند تبدیل انجام دهد؛ ذخیره
    تاریخ استاندارد در دیتابیس باید با سیاست مشخص و یکسان انجام شود.
-   اگر تاریخ منبع فقط به‌صورت متن شمسی در دسترس است، مقدار خام آن نیز
    نگهداری شود تا تبدیل اشتباه قابل ردیابی باشد.
-   برای جست‌وجوی فارسی، نرمال‌سازی و تحلیلگر متن باید جداگانه تست شوند؛
    `to_tsvector('simple')` فقط نمونه اولیه است.

------------------------------------------------------------------------

## 7. استاندارد JSON سند

نمونه زیر قرارداد داده پیشنهادی است. مقادیر محتوایی نمونه و غیرواقعی
هستند، مگر شناسه و عنوان نمونه‌ای که در دامنه پروژه معرفی شده‌اند.

``` json
{
  "document": {
    "id": "internal-uuid",
    "source_system": "seo_cmr",
    "source_id": "71485",
    "title": "دستورالعمل نحوه افزایش سرمایه از محل تجدید ارزیابی دارایی‌ها در شرکت‌های سهامی عام ثبت‌شده نزد سازمان",
    "document_type": "INSTRUCTION",
    "issuing_authority": "سازمان بورس و اوراق بهادار",
    "source_url": "https://cmr.seo.ir/ShowRules?Id=71485"
  },
  "version": {
    "version_number": 1,
    "content_hash": "sha256-value",
    "status": "UNKNOWN",
    "is_current": false,
    "approval_date": null,
    "publication_date": null,
    "effective_date": null
  },
  "relations": [
    {
      "target_source_id": "RELATED-SOURCE-ID",
      "relation_type": "RELATED_TO",
      "evidence_text": "عنوان یا متن نوع پیوند",
      "extraction_method": "PAGE_FIELD",
      "confidence": 1.0,
      "review_status": "UNREVIEWED"
    }
  ],
  "attachments": [
    {
      "title": "عنوان پیوست",
      "source_url": "https://example.invalid/attachment.pdf",
      "mime_type": "application/pdf",
      "attachment_order": 1
    }
  ],
  "sections": []
}
```

### قرارداد نرمال‌سازی نوع سند

نمونه مقادیر استاندارد:

-   LAW
-   REGULATION
-   BYLAW
-   INSTRUCTION
-   CIRCULAR
-   RESOLUTION
-   NOTICE
-   FORM
-   OTHER
-   UNKNOWN

عنوان اصلی فارسی همیشه حفظ شود. مقدار استاندارد انگلیسی فقط برای فیلتر و
پردازش استفاده شود.

------------------------------------------------------------------------

## 8. طراحی Crawler و استخراج صفحه

### 8.1 مراحل Crawler

برای هر صفحه:

1.  درخواست HTTP با Timeout و Retry محدود.
2.  ثبت URL نهایی پس از Redirect.
3.  ذخیره HTML خام.
4.  استخراج عنوان و شناسه.
5.  استخراج نوع سند و سایر فراداده‌های قابل مشاهده.
6.  استخراج فهرست روابط و نوع پیوند.
7.  استخراج لینک پیوست‌ها.
8.  دریافت فایل‌ها با کنترل MIME و حجم.
9.  ثبت Hash فایل و صفحه.
10. ارسال به Pipeline پردازش.

### 8.2 تکنولوژی‌ها

  نیاز                    ابزار پیشنهادی
  ----------------------- ------------------------------
  درخواست HTTP            httpx
  استخراج HTML            BeautifulSoup یا selectolax
  سایت JavaScript-heavy   Playwright فقط در صورت ضرورت
  PDF متنی                PyMuPDF یا pdfplumber
  PDF اسکن‌شده             OCR موجود در زیرساخت
  DOCX                    python-docx
  صف پردازش               Celery + Redis یا Dramatiq
  زمان‌بندی Crawl          APScheduler یا Celery Beat
  Hash                    hashlib / SHA-256

### 8.3 نکات عملیاتی

-   نرخ درخواست به سایت رعایت شود.
-   `robots.txt`، شرایط استفاده و محدودیت‌های دسترسی بررسی شوند.
-   دانلود فایل از دامنه‌های مجاز محدود شود تا SSRF رخ ندهد.
-   پسوند فایل به‌تنهایی برای تشخیص نوع فایل قابل اعتماد نیست؛ MIME و
    امضای فایل نیز بررسی شود.
-   فایل‌های خام و پاسخ HTTP برای عیب‌یابی نگهداری شوند.
-   خطای یک سند نباید کل Batch را متوقف کند.

### 8.4 استخراج روابط صفحه

روابطی که در قسمت «نوع پیوند» صفحه نمایش داده می‌شوند باید مستقیماً از DOM
و ساختار HTML استخراج شوند. برای هر ردیف رابطه، موارد زیر ذخیره شود:

-   متن دقیق نوع پیوند.
-   عنوان سند مقصد.
-   URL مقصد.
-   شناسه مقصد، در صورت وجود.
-   شناسه سند مبدأ.
-   محل استخراج در HTML.

در صورت وجود URL مقصد، شناسه آن از الگوی URL استخراج شود؛ اما فقط پس از
اعتبارسنجی با ساختار واقعی سایت. اگر شناسه قابل استخراج نیست، رکورد موقت
ایجاد و برای Resolve شدن نگهداری شود.

------------------------------------------------------------------------

## 9. پردازش فایل و استخراج ساختار حقوقی

### 9.1 زنجیره پردازش

``` text
Raw File
  -> File Type Detection
  -> Text Extraction
  -> OCR if Needed
  -> Persian Normalization
  -> Layout and Table Detection
  -> Legal Structure Parsing
  -> Metadata Validation
  -> Sections
  -> Chunks
```

### 9.2 نرمال‌سازی فارسی

مواردی که باید با دقت و به‌صورت قابل برگشت مدیریت شوند:

-   تبدیل ي به ی و ك به ک برای متن نرمال‌شده.
-   مدیریت نیم‌فاصله.
-   یکسان‌سازی فاصله‌ها و خطوط خالی.
-   مدیریت ارقام فارسی، عربی و لاتین.
-   حفظ نسخه خام متن.
-   حفظ نشانه‌گذاری و شماره مواد.
-   عدم حذف علائم و شماره‌گذاری‌هایی که در ارجاع حقوقی اهمیت دارند.

پیشنهاد: دو فیلد نگهداری شود:

-   `raw_text`: خروجی اصلی استخراج.
-   `normalized_text`: متن استانداردشده برای جست‌وجو و پردازش.

### 9.3 تشخیص ساختار

Parser باید الگوهای زیر را تشخیص دهد:

-   فصل اول، فصل دوم و ...
-   ماده ۱، ماده ۲ و ...
-   بند الف، بند ب و ...
-   تبصره ۱، تبصره ۲ و ...
-   پیوست شماره ۱ و ...
-   جدول‌ها و عنوان ستون‌ها.

تشخیص صرفاً با Regex کافی نیست؛ بهتر است Parser ترکیبی باشد:

1.  Regex و قواعد قطعی برای الگوهای شماره‌گذاری.
2.  بررسی ترتیب و سلسله‌مراتب.
3.  مدل زبانی برای موارد مبهم.
4.  Validation برای اطمینان از عدم جابه‌جایی مواد.
5.  بازبینی انسانی برای موارد کم‌اطمینان.

------------------------------------------------------------------------

## 10. استراتژی Legal Chunking

### 10.1 قواعد پیشنهادی

-   هر ماده کوتاه تا متوسط یک Chunk مستقل.
-   تبصره‌ها همراه ماده مربوط، مگر طول یا استقلال معنایی زیاد داشته
    باشند.
-   ماده طولانی به بندهای معنادار تقسیم شود.
-   عنوان سند، فصل و ماده در Context هر Chunk تکرار شوند.
-   جدول‌ها با عنوان، سرستون‌ها و توضیح ارتباط سطرها ذخیره شوند.
-   پیوست‌ها به‌صورت محتوای مستقل پردازش شوند و رابطه پیوست بودن حفظ شود.
-   مقدمه و تعاریف نیز قابل بازیابی باشند.
-   Chunk از مرز دو ماده عبور نکند، مگر در شرایط استثنایی و با ثبت
    ساختار.

### 10.2 نمونه Chunk

``` json
{
  "chunk_id": "chunk-uuid",
  "document_source_id": "71485",
  "document_title": "دستورالعمل نحوه افزایش سرمایه...",
  "document_type": "INSTRUCTION",
  "version_id": "version-uuid",
  "chapter": "فصل دوم",
  "article_number": "4",
  "paragraph_number": null,
  "section_path": [
    "فصل دوم",
    "ماده ۴"
  ],
  "content": "متن کامل ماده و تبصره‌های مرتبط...",
  "contextual_content": "سند: ... | فصل دوم | ماده ۴\nمتن: ...",
  "page_start": 5,
  "page_end": 6,
  "source_url": "https://cmr.seo.ir/ShowRules?Id=71485"
}
```

### 10.3 اندازه Chunk

عدد ثابت برای همه اسناد تعیین نشود. معیار اصلی، مرز معنایی و حقوقی است.
به‌عنوان نقطه شروع:

-   ماده کوتاه: یک Chunk.
-   ماده متوسط: یک Chunk.
-   ماده بسیار طولانی: تقسیم بر اساس بند یا موضوع، با حفظ شماره ماده.
-   اندازه اولیه قابل آزمایش: حدود 300 تا 800 توکن.
-   هم‌پوشانی فقط در صورت نیاز و با حفظ مرز ساختاری.

این اعداد باید با مدل Embedding، طول Context مدل پاسخ‌گو و مجموعه ارزیابی
تنظیم شوند.

------------------------------------------------------------------------

## 11. Embedding و Vector Store

### 11.1 سیاست Embedding

EmbeddingGemma فعلی می‌تواند در نسخه اول حفظ شود؛ اما باید کیفیت آن روی
متون فارسی حقوقی ارزیابی شود.

موارد مهم:

-   عنوان سند همراه Chunk در متن Embedding قرار گیرد.
-   شماره ماده و فصل در Metadata ذخیره شود.
-   متن اصلی و متن Contextual جداگانه نگهداری شوند.
-   نسخه مدل و تنظیمات تولید Embedding ثبت شوند.
-   تغییر مدل Embedding نیازمند Re-Embedding کنترل‌شده است.

### 11.2 Payload پیشنهادی Qdrant

``` json
{
  "chunk_id": "chunk-uuid",
  "document_id": "document-uuid",
  "document_source_id": "71485",
  "version_id": "version-uuid",
  "document_type": "INSTRUCTION",
  "title": "دستورالعمل نحوه افزایش سرمایه...",
  "chapter": "فصل دوم",
  "article_number": "4",
  "paragraph_number": null,
  "status": "UNKNOWN",
  "is_current": false,
  "source_url": "https://cmr.seo.ir/ShowRules?Id=71485",
  "page_start": 5,
  "page_end": 6
}
```

متن کامل و روابط اصلی در PostgreSQL نگهداری شوند. Qdrant برای جست‌وجوی
برداری و فیلترهای بازیابی استفاده شود؛ Payload نباید تنها منبع حقیقت
سیستم باشد.

### 11.3 مدیریت تغییر

اگر Hash محتوا تغییر نکرده باشد، Embedding مجدداً تولید نشود. اگر فقط
Metadata تغییر کرده باشد، Payload به‌روزرسانی شود. اگر متن تغییر کرده
باشد، Chunkهای نسخه جدید و بردارهای جدید ایجاد شوند و نسخه قبلی برای
تاریخچه حفظ شود.

------------------------------------------------------------------------

## 12. Hybrid Retrieval و Graph Expansion

### 12.1 چرا Hybrid Search؟

در اسناد حقوقی، کاربر ممکن است سؤال مفهومی بپرسد یا شماره دقیق ماده،
شناسه سند و عبارت خاصی را جست‌وجو کند.

Vector Search برای شباهت معنایی مناسب است؛ BM25 برای عبارت و اصطلاح
دقیق. ترکیب این دو معمولاً از استفاده مستقل هر کدام قابل اتکاتر است.

### 12.2 جریان بازیابی

``` text
User Query
   |
Query Classification
   |
   +--> Exact ID / Article Search
   |
   +--> BM25 Search
   |
   +--> Vector Search
   |
   v
Candidate Fusion
   |
Reranker
   |
Primary Documents
   |
Relation Expansion
   |
Related Document Retrieval
   |
Temporal and Status Filtering
   |
Context Builder
```

### 12.3 Relation Expansion

پس از یافتن سند اصلی:

-   روابط مستقیم سند بازیابی شوند.
-   پیوست‌های همان نسخه دریافت شوند.
-   اصلاحیه‌ها و اسناد نسخ‌کننده بررسی شوند.
-   در صورت نیاز، یک سطح دیگر از روابط پیمایش شود.
-   عمق پیش‌فرض پیمایش محدود باشد؛ مثلاً یک یا دو سطح.
-   از گسترش نامحدود گراف جلوگیری شود.

### 12.4 سیاست رابطه در بازیابی

  رابطه            رفتار پیشنهادی
  ---------------- -------------------------------------------
  HAS_ATTACHMENT   بازیابی پیوست در صورت مرتبط بودن با سؤال
  RELATED_TO       بررسی عنوان و بازیابی محتوای مرتبط
  REFERENCES       بازیابی بخش ارجاع‌شده در صورت نیاز
  AMENDS           بررسی نسخه و مواد اصلاح‌شده
  REPEALS          هشدار درباره وضعیت سند و بررسی تاریخ سؤال
  REPLACES         اولویت بررسی سند جایگزین برای وضعیت جاری
  UNKNOWN          عدم استفاده به‌عنوان رابطه قطعی حقوقی

صرف وجود رابطه `RELATED_TO` نباید باعث شود کل محتوای سند مقصد وارد
Context شود. ابتدا باید بخش مرتبط آن سند بازیابی شود.

### 12.5 جلوگیری از Context بیش از حد

-   ابتدا مواد مرتبط سند اصلی انتخاب شوند.
-   سپس بخش‌های مرتبط اسناد پیوست و مرتبط اضافه شوند.
-   اسناد با رابطه ضعیف یا محتوای نامرتبط حذف شوند.
-   محدودیت توکن برای هر سند و کل Context تعریف شود.
-   منابع و دلایل ورود هر Chunk ثبت شوند.

------------------------------------------------------------------------

## 13. مدیریت اعتبار زمانی و نسخه‌ها

در RAG حقوقی، «جدیدترین سند» همیشه معادل «تنها سند معتبر» نیست. ممکن است
سندی در زمان مشخصی معتبر بوده و سپس اصلاح یا نسخ شده باشد.

### 13.1 فیلدهای زمانی

-   approval_date: تاریخ تصویب.
-   publication_date: تاریخ انتشار.
-   effective_date: تاریخ لازم‌الاجرا شدن.
-   valid_from: شروع بازه اعتبار ثبت‌شده در سامانه.
-   valid_until: پایان بازه اعتبار ثبت‌شده.
-   observed_at: زمان مشاهده سند توسط Crawler.

### 13.2 رفتار Query

اگر کاربر بپرسد «در حال حاضر چه حکمی معتبر است؟»:

1.  نسخه‌های مرتبط پیدا شوند.
2.  روابط اصلاح و نسخ بررسی شوند.
3.  تاریخ‌های مؤثر و شواهد رسمی ارزیابی شوند.
4.  اگر وضعیت روشن نیست، پاسخ صریحاً عدم قطعیت را بیان کند.

اگر کاربر بپرسد «در تاریخ مشخصی چه حکمی برقرار بوده؟»، بازیابی باید بر
اساس تاریخ مورد سؤال انجام شود، نه فقط `is_current`.

### 13.3 سیاست نسخه‌بندی

-   نسخه قبلی حذف نشود.
-   هر نسخه Hash مستقل داشته باشد.
-   تغییر فایل یا متن به‌عنوان تغییر نسخه ثبت شود.
-   تغییر صرفاً ظاهری صفحه لزوماً نسخه حقوقی جدید محسوب نشود.
-   تشخیص نسخه حقوقی جدید باید بر اساس شماره، تاریخ، متن تغییر و شواهد
    منبع انجام شود.

------------------------------------------------------------------------

## 14. Context Builder و Prompt مدل پاسخ‌گو

### 14.1 ساختار Context

``` text
QUESTION:
{user_question}

TEMPORAL_SCOPE:
{current_date_or_requested_date}

PRIMARY_DOCUMENTS:
- Document title
- Document ID
- Version
- Status evidence

RELEVANT_EXCERPTS:
[Source 1]
Document:
Version:
Article:
Paragraph:
Text:
URL:

RELATED_DOCUMENTS:
[Source 2]
Relation:
Evidence for relation:
Relevant article:
Text:
URL:

ATTACHMENTS:
[Source 3]
Parent document:
Attachment title:
Relevant content:
URL:

INSTRUCTIONS:
- Use only supplied evidence for legal claims.
- Distinguish explicit legal text from inference.
- Cite every material claim.
- Do not infer repeal or amendment from a generic relation.
- State when current validity cannot be established.
- If sources conflict, explain the conflict rather than silently choosing.
```

### 14.2 اصول Prompt

-   مدل نباید شماره ماده، تاریخ یا عنوان منبع را بسازد.
-   هر ادعای حقوقی باید ارجاع داشته باشد.
-   اگر سند مرتبط فقط از نظر موضوعی مرتبط است، نباید حکم آن به سند اصلی
    نسبت داده شود.
-   اگر پیوست متن مستقل دارد، پاسخ باید آن را به‌عنوان پیوست معرفی کند.
-   اگر شواهد برای نتیجه کافی نیست، مدل باید عدم کفایت شواهد را اعلام
    کند.
-   نقل‌قول مستقیم باید از متن بازیابی‌شده باشد و تغییر نکند.
-   تفسیر مدل باید از متن صریح سند جدا شود.

### 14.3 قالب پاسخ پیشنهادی

1.  پاسخ کوتاه و مستقیم.
2.  مبنای مقرراتی.
3.  مواد و بندهای مرتبط.
4.  اسناد مرتبط یا پیوست‌های مؤثر.
5.  وضعیت زمانی و محدودیت اعتبارسنجی.
6.  منابع و لینک‌ها.

------------------------------------------------------------------------

## 15. APIهای پیشنهادی

  Method   Endpoint                               شرح
  -------- -------------------------------------- ----------------------
  POST     `/api/v1/ingestion/url`                ثبت URL برای دریافت
  POST     `/api/v1/ingestion/batch`              ثبت Batch اسناد
  GET      `/api/v1/ingestion/{run_id}`           وضعیت پردازش
  GET      `/api/v1/documents`                    جست‌وجو و فهرست اسناد
  GET      `/api/v1/documents/{id}`               جزئیات سند
  GET      `/api/v1/documents/{id}/versions`      نسخه‌های سند
  GET      `/api/v1/documents/{id}/relations`     روابط سند
  GET      `/api/v1/documents/{id}/attachments`   پیوست‌ها
  GET      `/api/v1/documents/{id}/chunks`        قطعات سند
  POST     `/api/v1/search`                       جست‌وجوی ترکیبی
  POST     `/api/v1/chat`                         پرسش و پاسخ مستند
  POST     `/api/v1/relations/review`             تأیید یا رد رابطه
  POST     `/api/v1/documents/{id}/reprocess`     پردازش مجدد

### 15.1 نمونه درخواست Chat

``` json
{
  "question": "شرایط افزایش سرمایه از محل تجدید ارزیابی چیست؟",
  "as_of_date": null,
  "include_related_documents": true,
  "include_attachments": true,
  "max_relation_depth": 1,
  "top_k": 10
}
```

### 15.2 نمونه پاسخ

``` json
{
  "answer": "پاسخ مستند تولیدشده...",
  "citations": [
    {
      "document_id": "document-uuid",
      "source_id": "71485",
      "title": "عنوان سند",
      "version_id": "version-uuid",
      "article_number": "4",
      "paragraph_number": null,
      "source_url": "https://cmr.seo.ir/ShowRules?Id=71485",
      "excerpt": "بخش کوتاهی از متن مستند"
    }
  ],
  "related_documents": [],
  "attachments": [],
  "temporal_scope": "CURRENT",
  "limitations": []
}
```

------------------------------------------------------------------------

## 16. تکنولوژی‌های مورد نیاز

### 16.1 پشته پیشنهادی

  لایه            تکنولوژی                         ضرورت
  --------------- -------------------------------- -----------------------
  زبان            Python 3.11+                     اصلی
  API             FastAPI                          اصلی
  ORM             SQLAlchemy 2                     اصلی
  Migration       Alembic                          اصلی
  Database        PostgreSQL                       اصلی
  Vector DB       Qdrant                           اصلی
  Embedding       EmbeddingGemma                   موجود/قابل ارزیابی
  LLM             Qwen                             موجود
  HTTP            httpx                            اصلی
  HTML Parser     BeautifulSoup / selectolax       اصلی
  PDF             PyMuPDF                          اصلی
  DOCX            python-docx                      در صورت نیاز
  OCR             سرویس OCR موجود                  در صورت نیاز
  Queue           Celery + Redis                   برای پردازش غیرهمزمان
  Reranker        مدل چندزبانه/فارسی مناسب         مرحله دوم
  Observability   Prometheus + Grafana             Production
  Logging         structlog یا logging استاندارد   اصلی
  Testing         pytest                           اصلی
  Container       Docker / Docker Compose          توصیه‌شده

### 16.2 آیا LangChain یا LlamaIndex لازم است؟

خیر، اجباری نیستند. برای این پروژه بهتر است بخش‌های مهم مانند Chunking
حقوقی، Relation Expansion، Context Builder و Citation Manager به‌صورت
ماژول‌های اختصاصی پیاده‌سازی شوند.

استفاده از کتابخانه‌های RAG برای اجزای عمومی اشکالی ندارد، اما نباید منطق
روابط حقوقی به رفتار پیش‌فرض یک Framework وابسته شود.

### 16.3 آیا Neo4j لازم است؟

نسخه اول: خیر.

PostgreSQL برای روابط مستقیم و پیمایش یک یا دو سطح کافی است. Neo4j زمانی
ارزش افزوده دارد که:

-   تعداد روابط بسیار زیاد شود.
-   پرس‌وجوهای چندمرحله‌ای و مسیرمحور زیاد شوند.
-   تحلیل شبکه‌ای اسناد نیاز باشد.
-   Queryهای گرافی پیچیده و پرتکرار شوند.

------------------------------------------------------------------------

## 17. ساختار پیشنهادی پروژه

``` text
regulatory-rag/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── security.py
│   ├── api/
│   │   └── v1/
│   │       ├── documents.py
│   │       ├── search.py
│   │       ├── chat.py
│   │       ├── ingestion.py
│   │       └── relations.py
│   ├── ingestion/
│   │   ├── crawler.py
│   │   ├── downloader.py
│   │   ├── html_parser.py
│   │   ├── pdf_parser.py
│   │   ├── document_detector.py
│   │   └── pipeline.py
│   ├── extraction/
│   │   ├── metadata_extractor.py
│   │   ├── relation_extractor.py
│   │   ├── legal_structure_parser.py
│   │   └── validators.py
│   ├── processing/
│   │   ├── persian_normalizer.py
│   │   ├── legal_chunker.py
│   │   └── content_hash.py
│   ├── storage/
│   │   ├── database.py
│   │   ├── models/
│   │   ├── repositories/
│   │   └── vector_store.py
│   ├── retrieval/
│   │   ├── query_classifier.py
│   │   ├── lexical_search.py
│   │   ├── vector_search.py
│   │   ├── fusion.py
│   │   ├── reranker.py
│   │   ├── relation_expander.py
│   │   └── temporal_filter.py
│   ├── generation/
│   │   ├── context_builder.py
│   │   ├── prompt_templates.py
│   │   ├── llm_client.py
│   │   └── citation_validator.py
│   └── workers/
│       ├── tasks.py
│       └── scheduler.py
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── retrieval/
│   └── evaluation/
├── scripts/
│   ├── ingest_one.py
│   ├── reindex.py
│   └── validate_relations.py
├── data/
│   ├── raw/
│   ├── extracted/
│   └── samples/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

------------------------------------------------------------------------

## 18. نقشه راه اجرایی

برنامه زیر برای یک تیم کوچک با یک یا دو توسعه‌دهنده Backend/AI تخمین
اولیه است. زمان واقعی به کیفیت HTML، تعداد فایل‌ها، پیچیدگی PDFها و
دسترسی به داده بستگی دارد.

### فاز صفر: شناخت منبع و نمونه‌برداری

**زمان تخمینی: 2 تا 3 روز**

کارها:

-   بررسی 20 تا 30 صفحه نمونه.
-   بررسی HTML و ساختار DOM.
-   شناسایی انواع فایل پیوست.
-   بررسی شناسه و URL اسناد مرتبط.
-   بررسی ساختار تاریخ‌ها و وضعیت‌ها.
-   تهیه نمونه طلایی از 5 تا 10 سند با داده استخراج‌شده و بازبینی‌شده.

خروجی:

-   Source Specification
-   فهرست فیلدها
-   نمونه HTML/PDF
-   فهرست ابهامات و محدودیت‌ها

معیار پذیرش:

-   ساختار صفحه و محل استخراج فیلدهای اصلی مشخص باشد.
-   حداقل یک نمونه از هر نوع پیوست بررسی شده باشد.
-   رابطه‌های قابل استخراج از صفحه مستند شده باشند.

### فاز یک: مدل داده و Ingestion پایه

**زمان تخمینی: 4 تا 6 روز**

کارها:

-   راه‌اندازی PostgreSQL و Migrationها.
-   ساخت Crawler.
-   ذخیره HTML خام.
-   استخراج عنوان، شناسه و URL.
-   دانلود فایل‌ها.
-   Hash و تشخیص تغییر محتوا.
-   ثبت Ingestion Run.

خروجی:

-   Crawler قابل اجرا برای یک URL و Batch.
-   ذخیره قابل ردیابی صفحات و فایل‌ها.

معیار پذیرش:

-   اجرای مجدد یک URL باعث رکورد تکراری نشود.
-   خطای یک سند اجرای Batch را متوقف نکند.
-   فایل خام و Hash قابل بازیابی باشند.

### فاز دو: Parser و ساختار حقوقی

**زمان تخمینی: 5 تا 8 روز**

کارها:

-   HTML/PDF Parser.
-   استخراج متن.
-   نرمال‌سازی فارسی.
-   تشخیص فصل، ماده، بند و تبصره.
-   استخراج پیوست‌ها.
-   ساخت Sections و Chunks.

خروجی:

-   سند ساختاریافته با متن و موقعیت منبع.

معیار پذیرش:

-   شماره مواد و ترتیب آن‌ها حفظ شود.
-   تبصره به ماده درست متصل شود.
-   متن جدول و پیوست در صورت وجود قابل بازیابی باشد.
-   خطاهای OCR و Parser قابل مشاهده باشند.

### فاز سه: استخراج و مدیریت روابط

**زمان تخمینی: 4 تا 6 روز**

کارها:

-   استخراج روابط از فیلدهای صفحه.
-   Resolve کردن سند مقصد با شناسه یا URL.
-   ذخیره شواهد رابطه.
-   ایجاد وضعیت بازبینی.
-   پیاده‌سازی API روابط.
-   جلوگیری از روابط تکراری و خودارجاع.

خروجی:

-   Document Relation Registry.

معیار پذیرش:

-   رابطه مبدأ و مقصد درست باشد.
-   نوع پیوند دقیقاً مطابق منبع ذخیره شود.
-   رابطه نامشخص به‌عنوان رابطه قطعی ثبت نشود.
-   پیوست از سند مرتبط تفکیک شده باشد.

### فاز چهار: Embedding و جست‌وجوی ترکیبی

**زمان تخمینی: 4 تا 6 روز**

کارها:

-   تولید Embedding.
-   ساخت Collection در Qdrant.
-   ذخیره Payload.
-   جست‌وجوی Vector.
-   جست‌وجوی واژگانی.
-   ادغام نتایج.
-   ارزیابی اولیه Reranker.

خروجی:

-   Search API با نتایج قابل ردیابی.

معیار پذیرش:

-   جست‌وجوی عنوان و شناسه سند کار کند.
-   جست‌وجوی شماره ماده و عبارت دقیق نتیجه مناسب بدهد.
-   سؤال مفهومی Chunkهای مرتبط را بازیابی کند.

### فاز پنج: Relation-aware Retrieval و پاسخ‌گویی

**زمان تخمینی: 5 تا 8 روز**

کارها:

-   Query Classification.
-   Relation Expansion.
-   بازیابی پیوست‌ها.
-   بررسی اصلاحیه و نسخ.
-   Context Builder.
-   اتصال Qwen.
-   Citation Manager.
-   Citation Validation.

خروجی:

-   Chat API با پاسخ و ارجاعات دقیق.

معیار پذیرش:

-   پاسخ به سؤال درباره سند، مواد مرتبط را بازیابی کند.
-   سؤال درباره پیوست، متن پیوست را بازیابی کند.
-   سؤال درباره مقررات مرتبط، سند مقصد و محتوای مرتبط آن را ارائه کند.
-   مدل رابطه عمومی را به‌اشتباه اصلاح یا نسخ معرفی نکند.
-   ارجاع ساختگی تولید نشود.

### فاز شش: ارزیابی، امنیت و آماده‌سازی Production

**زمان تخمینی: 5 تا 7 روز**

کارها:

-   ساخت مجموعه سؤال و پاسخ مرجع.
-   ارزیابی Retrieval و Citation.
-   تست بار و زمان پاسخ.
-   تست امنیت فایل و URL.
-   Monitoring و Logging.
-   Backup و Recovery.
-   مستندسازی و استقرار.

خروجی:

-   نسخه آزمایشی قابل ارائه به کاربران محدود.

### جمع زمان تخمینی

برای نسخه MVP با یک دامنه منبع و پوشش نمونه‌ای: حدود 4 تا 6 هفته کاری،
بسته به کیفیت داده و پیچیدگی استخراج. این تخمین تعهد زمانی قطعی نیست.

------------------------------------------------------------------------

## 19. مجموعه ارزیابی (Evaluation Dataset)

پیش از توسعه کامل، حداقل 50 تا 100 سؤال واقعی یا بازبینی‌شده تهیه شود.

### دسته‌بندی سؤال‌ها

  دسته          نمونه سؤال
  ------------- ------------------------------------------------------
  جست‌وجوی سند   دستورالعمل افزایش سرمایه از تجدید ارزیابی را پیدا کن
  سؤال ماده‌ای   ماده ۴ چه شرایطی دارد؟
  سؤال مفهومی   شرایط کلی افزایش سرمایه چیست؟
  رابطه‌ای       چه مقرراتی به این دستورالعمل مرتبط‌اند؟
  پیوست         پیوست‌های این سند چه محتوایی دارند؟
  اصلاحیه       کدام سند این دستورالعمل را اصلاح کرده است؟
  نسخ           آیا سندی آن را نسخ کرده است؟
  زمانی         در تاریخ مشخص چه نسخه‌ای معتبر بوده است؟
  تعارض         دو سند در یک موضوع چه تفاوتی دارند؟
  عدم کفایت     آیا منبع موجود برای پاسخ کافی است؟

### معیارها

  معیار                   هدف ارزیابی
  ----------------------- ------------------------------------
  Recall@5 / Recall@10    بازیابی منابع صحیح
  MRR / nDCG              کیفیت رتبه‌بندی
  Relation Precision      صحت نوع رابطه
  Relation Recall         پوشش روابط واقعی
  Citation Accuracy       صحت ارجاع به ماده و سند
  Citation Completeness   کامل بودن ارجاعات لازم
  Temporal Accuracy       صحت انتخاب نسخه در تاریخ مورد سؤال
  Faithfulness            وفاداری پاسخ به شواهد
  Answer Relevance        ارتباط پاسخ با سؤال

اعداد هدف باید پس از ایجاد Baseline و مشاهده داده واقعی تعیین شوند؛ از
ابتدا عدد تضمینی تعریف نشود.

------------------------------------------------------------------------

## 20. تست‌های ضروری

### Unit Tests

-   نرمال‌سازی حروف فارسی.
-   تبدیل ارقام.
-   استخراج شناسه از URL.
-   تشخیص ماده و تبصره.
-   Hash فایل.
-   تشخیص MIME.
-   Deduplication.
-   اعتبارسنجی نوع رابطه.

### Integration Tests

-   دریافت صفحه و استخراج روابط.
-   دانلود پیوست.
-   ثبت سند در PostgreSQL.
-   تولید Chunk و Embedding.
-   جست‌وجو در Qdrant.
-   پیمایش روابط.
-   ساخت Context و پاسخ نهایی.

### Regression Tests

هر بار تغییر Parser، Chunker یا Prompt باید روی مجموعه طلایی اجرا شود تا
کیفیت قبلی افت نکند.

### سناریوهای خطا

-   صفحه بدون پیوست.
-   پیوست غیرقابل دانلود.
-   PDF اسکن‌شده.
-   سند با متن ناقص.
-   دو سند با عنوان مشابه.
-   سند مقصد حذف‌شده یا در دسترس نبودن آن.
-   رابطه مبهم.
-   اصلاحیه بدون اشاره مستقیم به شناسه سند قبلی.
-   تاریخ ناقص یا ناسازگار.
-   محتوای تکراری با URL متفاوت.

------------------------------------------------------------------------

## 21. امنیت و حاکمیت داده

-   محدود کردن Crawler به دامنه‌های مجاز.
-   جلوگیری از SSRF و دسترسی به IPهای داخلی.
-   محدودیت حجم و نوع فایل.
-   اسکن فایل‌های ورودی در صورت نیاز.
-   نگهداری URL و Hash فایل.
-   کنترل دسترسی API.
-   ثبت Audit Log برای تغییر وضعیت روابط و اسناد.
-   عدم اجازه به مدل برای تغییر مستقیم داده حقوقی.
-   جداسازی نقش استخراج ماشینی از تأیید کارشناس.
-   پشتیبان‌گیری از PostgreSQL و فایل‌های اصلی.
-   نگهداری نسخه Prompt و مدل برای قابلیت بازتولید پاسخ.

------------------------------------------------------------------------

## 22. ریسک‌ها و راهکارها

  ریسک                  اثر                   راهکار
  --------------------- --------------------- --------------------------------
  تغییر HTML سایت       توقف استخراج          Parser ماژولار و تست نمونه
  PDF اسکن‌شده           متن ناقص              OCR و کنترل کیفیت
  اشتباه در رابطه       پاسخ حقوقی نادرست     ذخیره شواهد و بازبینی
  عنوان‌های مشابه        اتصال به سند اشتباه   Resolve با شناسه و URL
  نسخه‌های متعدد         پاسخ قدیمی            Version Management
  Chunking نامناسب      بازیابی ناقص ماده     Legal Chunking و Evaluation
  فارسی و نیم‌فاصله      افت جست‌وجو            Normalization و تست
  Context بیش از حد     افت کیفیت پاسخ        Relation-aware Context Builder
  ارجاع ساختگی          کاهش اعتماد           Citation Validation
  تغییر مدل Embedding   ناسازگاری بردار       ثبت نسخه و Reindex کنترل‌شده

------------------------------------------------------------------------

## 23. تصمیم‌های معماری که باید پیش از توسعه نهایی شوند

این موارد در فاز صفر با نمونه واقعی مشخص شوند:

1.  آیا تمام صفحات سایت یک Template مشترک دارند؟
2.  آیا شناسه سند در URL برای تمام اسناد یکتا و پایدار است؟
3.  آیا رابطه‌ها فقط در صفحه مبدأ دیده می‌شوند یا در هر دو سمت؟
4.  آیا فایل پیوست همیشه متعلق به یک نسخه مشخص است؟
5.  آیا سایت تاریخ تصویب، انتشار و اجرا را جداگانه نمایش می‌دهد؟
6.  آیا سوابق اصلاح و نسخ به‌صورت ساختاریافته وجود دارد؟
7.  آیا امکان دریافت فایل‌های تاریخی وجود دارد؟
8.  آیا محتوا در HTML قابل استخراج است یا نیاز به OCR دارد؟
9.  آیا اسناد مقصد در همان سامانه قرار دارند؟
10. چه سطحی از تأیید انسانی برای روابط و وضعیت اعتبار لازم است؟

------------------------------------------------------------------------

## 24. چک‌لیست شروع کار

### مرحله شناخت منبع

-   [ ] بررسی 20 تا 30 صفحه نمونه
-   [ ] ذخیره HTML خام
-   [ ] بررسی DOM بخش نوع پیوند
-   [ ] بررسی DOM بخش پیوست‌ها
-   [ ] بررسی نمونه PDF و DOCX
-   [ ] شناسایی شناسه پایدار اسناد
-   [ ] تهیه مستند Source Specification

### مرحله زیرساخت

-   [ ] راه‌اندازی PostgreSQL
-   [ ] راه‌اندازی Qdrant
-   [ ] راه‌اندازی Redis در صورت استفاده از Queue
-   [ ] ساخت Docker Compose
-   [ ] ساخت Migrationها
-   [ ] تعریف Logging و تنظیمات محیط

### مرحله Ingestion

-   [ ] Crawler
-   [ ] Downloader
-   [ ] HTML Parser
-   [ ] PDF Parser
-   [ ] OCR Adapter
-   [ ] Metadata Extractor
-   [ ] Relation Extractor
-   [ ] Legal Structure Parser
-   [ ] Legal Chunker
-   [ ] Embedding Pipeline

### مرحله Retrieval و پاسخ

-   [ ] Exact Search
-   [ ] BM25
-   [ ] Vector Search
-   [ ] Fusion
-   [ ] Reranker
-   [ ] Relation Expansion
-   [ ] Temporal Filter
-   [ ] Context Builder
-   [ ] Qwen Integration
-   [ ] Citation Validator

### مرحله ارزیابی و استقرار

-   [ ] مجموعه سؤال مرجع
-   [ ] تست کیفیت بازیابی
-   [ ] تست روابط
-   [ ] تست اعتبار زمانی
-   [ ] تست ارجاعات
-   [ ] تست امنیت
-   [ ] تست بار
-   [ ] Backup و Recovery
-   [ ] مستندات عملیاتی

------------------------------------------------------------------------

## 25. اولویت پیاده‌سازی پیشنهادی

برای جلوگیری از پیچیده شدن پروژه، توسعه را به این ترتیب انجام بده:

**اول:** یک صفحه را کامل دریافت کن و JSON استاندارد آن را بساز؛ شامل
عنوان، شناسه، نوع سند، نوع پیوندها و پیوست‌ها.

**دوم:** اسناد مقصد روابط را Resolve کن و در PostgreSQL ذخیره کن. هنوز
نیازی به LLM نیست.

**سوم:** متن سند اصلی و پیوست‌ها را استخراج و به ساختار فصل، ماده و تبصره
تبدیل کن.

**چهارم:** Chunkها را در Qdrant ایندکس کن و جست‌وجوی ساده را بساز.

**پنجم:** Relation Expansion را اضافه کن تا هنگام یافتن سند اصلی، مواد
مرتبط از اسناد وابسته نیز بازیابی شوند.

**ششم:** Qwen را به Context Builder وصل کن و پاسخ مستند تولید کن.

**هفتم:** مدیریت نسخه و اعتبار زمانی، ارزیابی، مانیتورینگ و مقیاس‌پذیری
را تکمیل کن.

### تعریف Done برای MVP

MVP زمانی آماده است که بتواند:

1.  صفحه نمونه را دریافت کند.
2.  سند اصلی و پیوست‌ها را تشخیص دهد.
3.  نوع پیوند و سند مقصد را استخراج کند.
4.  روابط را در دیتابیس ذخیره کند.
5.  مواد و تبصره‌ها را با ساختار صحیح استخراج کند.
6.  جست‌وجوی برداری و واژگانی انجام دهد.
7.  با پیدا کردن سند اصلی، اسناد مرتبط و پیوست‌های لازم را نیز بررسی کند.
8.  پاسخ فارسی با ارجاع به سند و ماده ارائه دهد.
9.  در نبود شواهد کافی، صریحاً عدم قطعیت را اعلام کند.
10. نسخه‌های قبلی و شواهد استخراج را حفظ کند.

------------------------------------------------------------------------

## 26. جمع‌بندی

این پروژه باید به‌عنوان یک **Regulatory Knowledge System** طراحی شود که
RAG یکی از اجزای آن است، نه تمام سامانه.

سه لایه اصلی که باید از روز اول مستقل بمانند:

-   **Document Layer:** اسناد، نسخه‌ها، فایل‌ها و ساختار مواد.
-   **Relationship Layer:** پیوندها، پیوست‌ها، اصلاحیه‌ها، نسخ و ارجاعات.
-   **Retrieval Layer:** جست‌وجوی واژگانی، برداری، پیمایش روابط و ساخت
    Context.

انتخاب پیشنهادی برای شروع، PostgreSQL + Qdrant + Python/FastAPI +
EmbeddingGemma + Qwen است. این ترکیب ضمن حفظ زیرساخت فعلی، امکان توسعه
تدریجی به یک پایگاه دانش حقوقی بزرگ را فراهم می‌کند.

**مهم‌ترین توصیه اجرایی:** قبل از Crawl گسترده، یک نمونه واقعی را از
ابتدا تا انتها پردازش کن و صحت استخراج رابطه، پیوست، ماده و ارجاع را با
بازبینی انسانی بسنج. کیفیت همین مسیر کوچک، تعیین‌کننده کیفیت کل سامانه
خواهد بود.
