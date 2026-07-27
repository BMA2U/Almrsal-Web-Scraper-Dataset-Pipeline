# خطة Web Scraping لموقع المرسال (almrsal.com)

## الهدف
سحب مقالات موقع المرسال مصنفة بتصنيفات متداخلة (رئيسي > فرعي) لإنتاج مجموعة بيانات (dataset) بصيغة JSONL جاهزة لتدريب نموذج لغوي عربي.

---

## تحليل بنية الموقع (نتائج البحث الفعلي)

### حجم الموقع
- **7,147 صفحة** من المقالات (Pagination)
- **143 ملف Sitemap** للمقالات (`post-sitemap1.xml` إلى `post-sitemap143.xml`)
- تقدير عدد المقالات: **~143,000 مقال** (بافتراض ~1000 رابط لكل sitemap)
- الموقع يعمل على **WordPress** مع إضافة **All in One SEO Pro v4.9.8**

### هيكل التصنيفات المتداخل

الموقع يحتوي على **27 تصنيف رئيسي** مع تصنيفات فرعية متعددة. هذا هو الهيكل الكامل:

```
📁 صحة (health) ← 14 تصنيف فرعي
├── أدوية (drugs)
├── السكري (diabetes)
├── أمراض الأسنان (dental-diseases)
├── أمراض العظام (bone-diseases)
├── أمراض العيون (eyes-illnesses)
├── أمراض القلب (heart-diseases)
├── أمراض جلدية (skin-diseases)
├── أمراض معدية (infectious-diseases)
├── أمراض نفسية (psychiatric-illness)
├── تحاليل طبية (medical-tests)
├── دراسات حديثة (recent-studies)
├── ضغط الدم (blood-pressure)
├── كريمات (creams)
└── نصائح طبية (medical-advice)

📁 الوقاية الصحية (protection) ← 11 تصنيف فرعي
├── أضرار (damaged)
├── إنقاص الوزن (weight-loss)
├── تمارين (exercises)
├── رجيم (diet)
├── زيادة الوزن (overweight)
├── فوائد (benefits)
├── فوائد الأعشاب (benefits-of-herbs)
├── فوائد الأغذية (food-benefits)
├── فيتامينات (vitamins)
├── فيتامينات مكملة (supplements)
└── ممارسة الرياضة (playing-sports)

📁 تكنولوجيا (tech) ← 8 تصنيفات فرعية
├── آيفون (iphone)
├── كاميرات (cameras)
├── برامج (software)
├── ألعاب (games)
├── سناب شات (snapchat)
├── واتساب (whatsapp)
├── فيسبوك (facebook)
└── دروس تقنية (technical-lessons)

📁 الأم والطفل (mother-and-child) ← 8 تصنيفات فرعية
├── صحة الطفل (child-health)
├── الحمل (pregnancy)
├── صحة الأم (maternal-health)
├── تربية الأبناء (raising-children)
├── أعياد الميلاد (birthday)
├── الدورة الشهرية (pms)
├── اختبارات الحمل (pregnancy-test)
├── الرضاعة (breast-feeding-ppt)
├── صعوبات التعلم (learning-difficulties)
└── قصص أطفال (childrens-stories)

📁 تعليم (education) ← 7 تصنيفات فرعية
├── جامعات سعودية (saudi-universities)
├── جامعات (universities)
├── أبحاث (research)
├── تعلم لغات (learning-languages)
├── مدارس (school)
├── إذاعة مدرسية (school-radio)
├── تخصصات جامعية (university-majors)
└── نظريات (theories)

📁 العالم (the-world) ← 6 تصنيفات فرعية
├── سياحة (tourism)
├── حروب (wars)
├── مدن (cities)
├── دول (country)
├── سياسيون (politicians)
└── اتفاقيات (agreements)

📁 الخليج العربي (the-arabian-gulf) ← 5 تصنيفات فرعية
├── البحرين (bahrain)
├── قطر (qatar)
├── عمان (oman)
├── الإمارات (emirates-news)
└── الكويت (kuwait-news)

📁 الرياضة (sport) ← 4 تصنيفات فرعية
├── أخبار رياضية (news-sports)
├── رياضة سعودية (saudi-sports)
├── مشاهير الرياضة (sports-celebrities)
└── أندية (clubs)

📁 نسائيات (all-womens) ← 7 تصنيفات فرعية
├── العناية بالبشرة (skin-care)
├── المرأة (women)
├── العناية بالشعر (hair-care)
├── إكسسوارات (accessories)
├── مكياج (makeup)
├── شخصيات نسائية (female-characters)
├── العناية الشخصية (personal-care)
├── الحياة الزوجية (marriage-life)
└── حب (love)

📁 أدب (literature) ← 6 تصنيفات فرعية
├── قصص (stories)
├── كتب (books)
├── روايات (novels)
├── شعر (the-poem)
├── أقوال (sayings)
└── مؤلفون (authors)

📁 مال وأعمال (business) ← 7 تصنيفات فرعية
├── شركات سعودية (saudi-companies)
├── وظائف (job)
├── شركات عالمية (international-companies)
├── رجال أعمال (businessmen)
├── دراسات جدوى (project-feasibility-study)
├── فوركس (forex)
├── اقتصاد عالمي (world-economy)
└── عملات (currencies)

📁 حيوانات (animals) ← 5 تصنيفات فرعية
├── طيور (birds)
├── كلاب (dog)
├── قطط (cats)
├── حيوانات منقرضة (extinction-of-animals)
└── تربية حيوانات (animal-husbandry)

📁 الطبيعة (nature) ← 6 تصنيفات فرعية
├── براكين (volcano)
├── انهيارات (it-collapsed)
├── جزر (islands)
├── طقس (weather)
├── زراعة (agriculture)
└── الفضاء (the-space)

📁 منوعات (info) ← 5 تصنيفات فرعية
├── الأفضل (best)
├── مقارنات (comparison)
├── عجائب (wonders)
├── كيف (how)
└── المجتمع (the-society)

📁 زد معلوماتك (informations) ← 4 تصنيفات فرعية
├── معلومات عامة (general)
├── من هو (who-is-he)
├── حقائق (facts)
├── تاريخ (history)
└── عسكرية (military)

📁 إسلاميات (islam) ← 3 تصنيفات فرعية
├── شخصيات إسلامية (islamic-figures)
├── الصلاة (prayer-in-islam)
└── أحكام (ahkam)

📁 المنزل (home) ← 3 تصنيفات فرعية
├── ديكور (decor)
├── طبخ (cooking)
└── صيانة المنزل (home-maintenance)

📁 علم وعلماء (science-and-scientists) ← 3 تصنيفات فرعية
├── منح دراسية (scholarship)
├── علم نفس (psychology)
└── مخترعون (inventors)

📁 الإنسان (human) ← 2 تصنيفات فرعية
├── أبراج (constellation)
└── تنمية بشرية (human-development)

📁 سيارات (car) ← 2 تصنيفات فرعية
├── عروض (offers)
└── صيانة سيارات (car-maintenance)

📁 سعوديتنا (saudi-arabia-news) ← بدون تصنيفات فرعية
📁 التجارة الالكترونية (e-commerce) ← بدون تصنيفات فرعية
📁 تفسير الأحلام (interpretation-of-dreams) ← بدون تصنيفات فرعية
📁 دروس (tutorials) ← بدون تصنيفات فرعية
📁 عملات رقمية (currencies-business) ← بدون تصنيفات فرعية
📁 الموسوعة العقارية (real-estate) ← بدون تصنيفات فرعية
```

### بنية المقال الداخلية (من التحليل الفعلي)
كل مقال يحتوي على:

| العنصر | الوصف | الموقع |
|--------|-------|--------|
| **العنوان** | عنوان المقال الكامل | `<title>` tag |
| **الوصف** | ملخص المقال | `<meta name="description">` |
| **الكاتب** | اسم كاتب المقال | رابط `/post/author/...` |
| **المحتوى** | النص الكامل للمقال | محتوى `article` أو `entry-content` |
| **التصنيفات** | التصنيف الرئيسي + الفرعي | روابط `/post/category/...` |
| **الوسوم (Tags)** | كلمات مفتاحية | روابط `/post/tag/...` |
| **التاريخ** | تاريخ النشر | metadata المقال |
| **جدول المحتويات** | قائمة بعناوين الفقرات | عنصر "محتويات" |
| **Pagination** | أزرار الصفحة التالية/السابقة | أسفل كل صفحة |

### نمط URLs

| النوع | النمط |
|-------|-------|
| الصفحة الرئيسية | `https://www.almrsal.com/` |
| مقال | `https://www.almrsal.com/post/{id}` |
| تصنيف رئيسي | `https://www.almrsal.com/post/category/{slug}` |
| تصنيف فرعي | `https://www.almrsal.com/post/category/{parent}/{child}` |
| صفحة تصنيف (pagination) | `https://www.almrsal.com/post/category/{slug}/page/{n}` |
| وسم | `https://www.almrsal.com/post/tag/{tag}` |
| Sitemap | `https://www.almrsal.com/post-sitemap{n}.xml` |
| Category Sitemap | `https://www.almrsal.com/category-sitemap.xml` |

---

## User Review Required

> [!IMPORTANT]
> **حجم البيانات**: الموقع يحتوي على ~143,000 مقال. السحب الكامل قد يستغرق **عدة أيام**. هل تريد:
> 1. سحب كل المقالات (~143K)
> 2. سحب تصنيفات محددة فقط (حدد أي تصنيفات)
> 3. سحب عينة محدودة (مثلاً 1000 مقال من كل تصنيف)

> [!WARNING]
> **الاعتبارات الأخلاقية والقانونية**: يجب التأكد من:
> - احترام ملف `robots.txt` للموقع
> - استخدام Rate Limiting مناسب (1-2 طلب/ثانية) حتى لا نُجهد السيرفر
> - البيانات المسحوبة ستُستخدم لأغراض تدريب نموذج (وليس إعادة نشر)

---

## Open Questions

> [!IMPORTANT]
> 1. **ما النموذج الذي ستدربه؟** (Fine-tuning GPT/LLaMA/مودل مخصص) — هذا يؤثر على صيغة البيانات المطلوبة
> 2. **هل تريد تنسيق معين للبيانات؟** مثلاً:
>    - JSONL عادي (سؤال/جواب)
>    - Instruction tuning format
>    - Plain text مع metadata
> 3. **هل تريد سحب الصور أيضاً** أم النصوص فقط؟
> 4. **ما حجم التخزين المتاح عندك؟** البيانات الكاملة قد تصل لـ 5-10 GB نص صافي

---

## Proposed Changes

### المرحلة 1: إعداد البنية التحتية للمشروع

#### [NEW] [requirements.txt](file:///d:/lastYear/help/requirements.txt)
المكتبات المطلوبة:
```
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
aiohttp>=3.9.0
aiofiles>=23.0
tqdm>=4.65.0
```

#### [NEW] [config.py](file:///d:/lastYear/help/config.py)
إعدادات المشروع:
- Base URL
- Rate Limiting (تأخير بين الطلبات)
- عدد المحاولات (retries)
- مسارات التخزين
- قائمة التصنيفات مع التصنيفات الفرعية

---

### المرحلة 2: سحب شجرة التصنيفات (Category Tree Crawler)

#### [NEW] [category_crawler.py](file:///d:/lastYear/help/category_crawler.py)
سحب الهيكل الكامل للتصنيفات من `category-sitemap.xml`:
- قراءة ملف الـ sitemap وتحليله
- بناء شجرة التصنيفات (parent → children)
- تخزين الشجرة في ملف `categories.json`
- اكتشاف عدد الصفحات لكل تصنيف

```python
# مثال على بنية الشجرة الناتجة
{
    "health": {
        "name_ar": "صحة",
        "url": "https://www.almrsal.com/post/category/health",
        "total_pages": 1081,
        "children": {
            "drugs": {"name_ar": "أدوية", "url": "...", "total_pages": 150},
            "diabetes": {"name_ar": "السكري", "url": "...", "total_pages": 45},
            ...
        }
    }
}
```

---

### المرحلة 3: سحب روابط المقالات (Article URL Collector)

#### [NEW] [article_collector.py](file:///d:/lastYear/help/article_collector.py)

**استراتيجية مزدوجة للسحب:**

**الطريقة الأولى (الأساسية): عبر Sitemaps ✅**
- قراءة الـ 143 ملف sitemap (`post-sitemap1.xml` إلى `post-sitemap143.xml`)
- استخراج كل روابط المقالات مع تاريخ آخر تحديث
- **ميزة**: أسرع وأشمل، يحصل على كل الروابط دفعة واحدة

**الطريقة الثانية (التكميلية): عبر صفحات التصنيفات 🔄**
- زيارة كل صفحة تصنيف مع pagination
- ربط كل مقال بتصنيفه (رئيسي + فرعي)
- **ميزة**: تضمن الربط الصحيح للتصنيفات

**النتيجة**: ملف `article_urls.json`
```python
{
    "https://www.almrsal.com/post/1559191": {
        "categories": ["protection", "food-benefits"],
        "category_path": "الوقاية الصحية > فوائد الأغذية",
        "last_modified": "2026-07-21"
    }
}
```

---

### المرحلة 4: سحب محتوى المقالات (Article Scraper)

#### [NEW] [article_scraper.py](file:///d:/lastYear/help/article_scraper.py)
السكربت الأساسي لسحب محتوى كل مقال:

**البيانات المستخرجة من كل مقال:**
```python
{
    "id": 1559191,
    "url": "https://www.almrsal.com/post/1559191",
    "title": "أسرار القيمة الغذائية الكاملة في البيض...",
    "description": "تعتبر التغذية السليمة...",
    "author": "Sana Mallah",
    "date": "2026-07-21",
    "content": "النص الكامل للمقال بعد التنظيف...",
    "categories": {
        "primary": "الوقاية الصحية",
        "primary_slug": "protection",
        "secondary": "فوائد الأغذية",
        "secondary_slug": "food-benefits"
    },
    "tags": ["البيض", "التغذية", "الكالسيوم"],
    "table_of_contents": ["المكونات الغذائية...", "الكنز المنسي..."],
    "word_count": 850,
    "char_count": 5200
}
```

**آليات التنظيف:**
- إزالة عناصر التنقل (header, footer, sidebar)
- إزالة الإعلانات والسكريبتات
- إزالة عناصر "مقالات أعجبت الزوار" و"مقالاتنا الجديدة"
- إزالة أزرار المشاركة
- تنظيف النص العربي (إزالة التشكيل الزائد، توحيد الهمزات)
- الحفاظ على تنسيق الفقرات والعناوين

---

### المرحلة 5: نظام الاستئناف والمتابعة (Checkpoint System)

#### [NEW] [checkpoint.py](file:///d:/lastYear/help/checkpoint.py)
نظام checkpoint ذكي:
- حفظ حالة السحب كل 100 مقال
- إمكانية الاستئناف من آخر نقطة عند الانقطاع
- تسجيل المقالات الفاشلة لإعادة المحاولة
- تقرير تقدم مباشر (progress bar)

```python
checkpoint = {
    "total_articles": 143000,
    "scraped": 45230,
    "failed": 12,
    "failed_urls": [...],
    "last_scraped_url": "https://...",
    "started_at": "2026-07-27T17:00:00",
    "elapsed_time": "12h 30m"
}
```

---

### المرحلة 6: معالجة وتحويل البيانات (Data Pipeline)

#### [NEW] [data_processor.py](file:///d:/lastYear/help/data_processor.py)
تحويل البيانات الخام إلى صيغ جاهزة للتدريب:

**صيغة JSONL للتدريب (الأساسية):**
```jsonl
{"text": "العنوان: أسرار القيمة الغذائية...\nالتصنيف: صحة > فوائد الأغذية\n\nالمحتوى: ...", "category": "protection/food-benefits"}
```

**صيغة Instruction Tuning:**
```jsonl
{"instruction": "اكتب مقالاً عن القيمة الغذائية للبيض", "output": "...", "category": "protection/food-benefits"}
```

**الإحصائيات الناتجة:**
- عدد المقالات لكل تصنيف
- متوسط طول المقال
- توزيع الكلمات
- التصنيفات الأكثر تمثيلاً

---

### المرحلة 7: السكربت الرئيسي (Orchestrator)

#### [NEW] [main.py](file:///d:/lastYear/help/main.py)
السكربت الرئيسي الذي يُنسق كل المراحل:

```bash
# سحب شجرة التصنيفات
python main.py --step categories

# سحب روابط المقالات
python main.py --step collect-urls

# سحب محتوى المقالات (مع استئناف)
python main.py --step scrape --resume

# معالجة البيانات للتدريب
python main.py --step process --format jsonl

# تشغيل كامل
python main.py --all
```

---

## هيكل المشروع النهائي

```
d:\lastYear\help\
├── main.py                    # السكربت الرئيسي
├── config.py                  # الإعدادات
├── requirements.txt           # المكتبات
├── category_crawler.py        # سحب التصنيفات
├── article_collector.py       # جمع روابط المقالات
├── article_scraper.py         # سحب محتوى المقالات
├── data_processor.py          # معالجة البيانات
├── checkpoint.py              # نظام الاستئناف
├── utils/
│   ├── arabic_cleaner.py      # تنظيف النص العربي
│   ├── rate_limiter.py        # التحكم بسرعة الطلبات
│   └── logger.py              # نظام التسجيل
├── data/
│   ├── categories.json        # شجرة التصنيفات
│   ├── article_urls.json      # روابط المقالات
│   ├── raw/                   # المقالات الخام (مقسمة بالتصنيف)
│   │   ├── health/
│   │   ├── tech/
│   │   └── ...
│   ├── processed/             # البيانات المعالجة
│   │   ├── dataset.jsonl      # البيانات بصيغة JSONL
│   │   ├── stats.json         # الإحصائيات
│   │   └── by_category/       # مقسم بالتصنيف
│   └── checkpoints/           # نقاط الحفظ
└── logs/                      # سجلات التشغيل
```

---

## مواصفات تقنية مهمة

### Rate Limiting & Politeness
```python
# الإعدادات المقترحة
DELAY_BETWEEN_REQUESTS = 1.5      # ثانية بين كل طلب
MAX_CONCURRENT_REQUESTS = 3       # طلبات متزامنة (aiohttp)
MAX_RETRIES = 3                   # محاولات إعادة
RETRY_DELAY = 5                   # ثواني بين المحاولات
REQUEST_TIMEOUT = 30              # timeout للطلب الواحد
USER_AGENT = "AlmrsalScraper/1.0 (Research Purpose)"
RESPECT_ROBOTS_TXT = True
```

### تنظيف النص العربي
```python
# العمليات المطبقة على كل مقال:
1. إزالة HTML tags
2. إزالة JavaScript و CSS
3. إزالة التشكيل (اختياري - قابل للتعديل)
4. توحيد الهمزات (إ/أ/آ → ا - اختياري)
5. إزالة الأرقام اللاتينية أو تحويلها (اختياري)
6. تطبيع المسافات والأسطر الفارغة
7. إزالة روابط وإعلانات
8. الحفاظ على بنية الفقرات
```

---

## Verification Plan

### Automated Tests
```bash
# 1. اختبار سحب التصنيفات
python -m pytest tests/test_category_crawler.py

# 2. اختبار سحب مقال واحد
python article_scraper.py --test-single "https://www.almrsal.com/post/1559191"

# 3. التحقق من صحة JSONL
python data_processor.py --validate data/processed/dataset.jsonl

# 4. إحصائيات البيانات
python data_processor.py --stats
```

### Manual Verification
1. مراجعة عينة عشوائية من 50 مقال مسحوب
2. مقارنة المحتوى المسحوب بالمحتوى الأصلي على الموقع
3. التأكد من صحة ربط التصنيفات
4. التحقق من جودة تنظيف النص العربي
5. مراجعة توزيع المقالات على التصنيفات

---

## الجدول الزمني المقدر

| المرحلة | الوقت المقدر |
|---------|-------------|
| إعداد المشروع والمكتبات | 30 دقيقة |
| سحب التصنيفات | 5 دقائق |
| سحب روابط المقالات (Sitemaps) | 30-60 دقيقة |
| سحب محتوى المقالات (الكامل) | 2-5 أيام (حسب Rate Limit) |
| سحب محتوى عينة (1000 لكل تصنيف) | 6-12 ساعة |
| معالجة وتحويل البيانات | 1-2 ساعة |
