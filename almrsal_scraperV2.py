# %% [markdown]
# # 🕷️ أداة سحب مقالات موقع المرسال (almrsal.com)
# ### لأغراض تدريب نموذج ذكاء اصطناعي مخصص
#
# **المخرج النهائي:** ملفات JSON مصنفة بتصنيفات متداخلة (رئيسي > فرعي)
#
# ---
# #### المراحل:
# 1. ⚙️ التهيئة والإعدادات
# 2. 🌳 سحب شجرة التصنيفات
# 3. 🔗 جمع روابط المقالات عبر Sitemaps
# 4. 📄 سحب محتوى المقالات مع نظام الاستئناف
# 5. 🧹 تنظيف ومعالجة النص العربي
# 6. 💾 تصدير البيانات بصيغة JSON للتدريب
# 7. 📊 إحصائيات وتوثيق عملية السحب

# %% [markdown]
# ## المرحلة 0: تركيب المكتبات وربط Google Drive

# %%
# ============================================================
# [CELL 1] تركيب المكتبات وربط Google Drive
# ============================================================
import subprocess
import sys

def install_packages():
    """تركيب المكتبات المطلوبة"""
    packages = [
        'requests',
        'curl_cffi',
        'beautifulsoup4',
        'lxml',
        'tqdm',
    ]
    for pkg in packages:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', pkg])
    print("✅ تم تركيب جميع المكتبات بنجاح")

install_packages()

# ربط Google Drive (في Colab فقط)
try:
    from google.colab import drive
    drive.mount('/content/drive')
    BASE_DIR = '/content/drive/MyDrive/almrsal_dataset'
    IN_COLAB = True
    print("✅ تم ربط Google Drive")
except ImportError:
    BASE_DIR = './almrsal_dataset'
    IN_COLAB = False
    print("⚠️ ليس في بيئة Colab - سيتم الحفظ محلياً")

import os
os.makedirs(BASE_DIR, exist_ok=True)
print(f"📁 مجلد البيانات: {BASE_DIR}")

# %% [markdown]
# ## المرحلة 1: التهيئة والإعدادات

# %%
# ============================================================
# [CELL 2] الاستيراد والإعدادات العامة
# ============================================================
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin, unquote
from collections import defaultdict
from tqdm import tqdm
import xml.etree.ElementTree as ET
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
# ⚙️ الإعدادات - يمكنك تعديلها حسب حاجتك
# ──────────────────────────────────────────────

class Config:
    """إعدادات السكريبت المركزية"""

    # المسارات
    BASE_URL = "https://www.almrsal.com"
    BASE_DIR = BASE_DIR  # من الخلية السابقة

    # مسارات الملفات
    CATEGORIES_FILE = os.path.join(BASE_DIR, "categories.json")
    ARTICLE_URLS_FILE = os.path.join(BASE_DIR, "article_urls.json")
    CHECKPOINT_FILE = os.path.join(BASE_DIR, "checkpoint.json")
    SCRAPE_LOG_FILE = os.path.join(BASE_DIR, "scrape_log.json")
    RAW_DIR = os.path.join(BASE_DIR, "raw_articles")
    OUTPUT_DIR = os.path.join(BASE_DIR, "dataset")
    LOG_FILE = os.path.join(BASE_DIR, "scraper.log")

    # التحكم بالسرعة
    DELAY_BETWEEN_REQUESTS = 1.5   # ثانية بين كل طلب
    MAX_RETRIES = 3                # عدد محاولات إعادة الطلب
    RETRY_DELAY = 5                # ثواني انتظار قبل إعادة المحاولة
    REQUEST_TIMEOUT = 30           # مهلة الطلب الواحد

    # حدود السحب (عدل حسب حاجتك)
    MAX_ARTICLES_PER_CATEGORY = None  # None = بدون حد، أو رقم مثل 500
    MAX_TOTAL_ARTICLES = None         # None = بدون حد، أو رقم مثل 10000

    # الحفظ
    CHECKPOINT_EVERY = 50          # حفظ checkpoint كل N مقال
    SAVE_RAW_EVERY = 100           # حفظ الملفات الخام كل N مقال

    # الهيدرز
    HEADERS = {
        'User-Agent': 'AlmrsalResearchBot/1.0 (Academic Research; +contact@example.com)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ar,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

# إنشاء المجلدات
for d in [Config.RAW_DIR, Config.OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

# إعداد التسجيل (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('almrsal_scraper')

print("✅ تم تهيئة الإعدادات والمسارات")
print(f"   📂 مجلد البيانات الخام: {Config.RAW_DIR}")
print(f"   📂 مجلد المخرجات: {Config.OUTPUT_DIR}")

# %%
# ============================================================
# [CELL 3] أدوات مساعدة (Rate Limiter, HTTP Client, Text Cleaner)
# ============================================================

class RateLimiter:
    """التحكم بسرعة الطلبات لاحترام السيرفر"""

    def __init__(self, delay=Config.DELAY_BETWEEN_REQUESTS):
        self.delay = delay
        self.last_request_time = 0

    def wait(self):
        """انتظار الوقت المطلوب بين الطلبات"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()


class HTTPClient:
    """عميل HTTP مع إعادة المحاولة والتسجيل"""

    def __init__(self):
        # استخدام curl_cffi لتخطي حماية Cloudflare وأخطاء 403
        self.session = cffi_requests.Session(impersonate="chrome")
        # لا نحتاج لإرسال headers مخصصة لأن curl_cffi يتكفل بمحاكاة متصفح حقيقي بالكامل
        self.rate_limiter = RateLimiter()
        self.total_requests = 0
        self.failed_requests = 0

    def get(self, url, retries=Config.MAX_RETRIES):
        """إرسال طلب GET مع إعادة المحاولة"""
        for attempt in range(retries):
            try:
                self.rate_limiter.wait()
                response = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
                self.total_requests += 1

                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    # Too Many Requests - انتظار أطول
                    wait_time = Config.RETRY_DELAY * (attempt + 2)
                    logger.warning(f"⚠️ Rate limited (429). انتظار {wait_time}s...")
                    time.sleep(wait_time)
                elif response.status_code == 404:
                    logger.warning(f"⚠️ صفحة غير موجودة (404): {url}")
                    return None
                else:
                    logger.warning(f"⚠️ استجابة {response.status_code} من: {url}")

            except TimeoutError:
                logger.warning(f"⏱️ انتهت المهلة (محاولة {attempt+1}/{retries}): {url}")
            except ConnectionError:
                logger.warning(f"🔌 خطأ اتصال (محاولة {attempt+1}/{retries}): {url}")
            except Exception as e:
                logger.error(f"❌ خطأ غير متوقع: {type(e).__name__}: {e}")

            if attempt < retries - 1:
                time.sleep(Config.RETRY_DELAY * (attempt + 1))

        self.failed_requests += 1
        logger.error(f"❌ فشل نهائي بعد {retries} محاولات: {url}")
        return None

    def get_stats(self):
        return {
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "success_rate": f"{((self.total_requests - self.failed_requests) / max(self.total_requests, 1)) * 100:.1f}%"
        }


class ArabicTextCleaner:
    """تنظيف ومعالجة النص العربي"""

    # أنماط regex مُجمّعة مسبقاً
    _DIACRITICS = re.compile(r'[\u064B-\u065F\u0670]')
    _TATWEEL = re.compile(r'\u0640+')
    _EXTRA_SPACES = re.compile(r' {2,}')
    _EXTRA_NEWLINES = re.compile(r'\n{3,}')
    _URLS = re.compile(r'https?://\S+')
    _EMAILS = re.compile(r'\S+@\S+\.\S+')
    _ENGLISH_NOISE = re.compile(r'[a-zA-Z]{20,}')  # كلمات إنجليزية طويلة جداً
    _NON_ARABIC_SYMBOLS = re.compile(r'[^\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF'
                                      r'a-zA-Z0-9\s\.\,\!\?\;\:\-\(\)\[\]\{\}'
                                      r'\"\'\/\\\%\#\@\*\+\=\<\>\~\&\|\^'
                                      r'\u060C\u061B\u061F\u0640\u066A-\u066D'
                                      r'\u200B-\u200F\u2028-\u202F'
                                      r'٠-٩\n]')

    @staticmethod
    def clean(text, remove_diacritics=False, remove_urls=True):
        """تنظيف النص العربي مع الحفاظ على بنية المقال"""
        if not text:
            return ""

        # إزالة الروابط
        if remove_urls:
            text = ArabicTextCleaner._URLS.sub('', text)
            text = ArabicTextCleaner._EMAILS.sub('', text)

        # إزالة التشكيل (اختياري)
        if remove_diacritics:
            text = ArabicTextCleaner._DIACRITICS.sub('', text)

        # إزالة التطويل الزائد (ـــ)
        text = ArabicTextCleaner._TATWEEL.sub('', text)

        # تطبيع المسافات
        text = ArabicTextCleaner._EXTRA_SPACES.sub(' ', text)
        text = ArabicTextCleaner._EXTRA_NEWLINES.sub('\n\n', text)

        # تنظيف كل سطر
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)

        text = '\n'.join(cleaned_lines)
        return text.strip()

    @staticmethod
    def count_arabic_words(text):
        """حساب عدد الكلمات العربية"""
        arabic_words = re.findall(r'[\u0600-\u06FF]+', text)
        return len(arabic_words)


# تهيئة العميل والأدوات
http_client = HTTPClient()
text_cleaner = ArabicTextCleaner()

print("✅ تم تهيئة أدوات الشبكة وتنظيف النصوص")

# %% [markdown]
# ## المرحلة 2: سحب شجرة التصنيفات 🌳

# %%
# ============================================================
# [CELL 4] سحب شجرة التصنيفات من category-sitemap.xml
# ============================================================

def crawl_category_tree():
    """
    سحب شجرة التصنيفات عبر تصفح صفحات HTML لتجنب الحظر على ملفات XML
    الخطوة 1: استخراج التصنيفات الرئيسية من الصفحة الرئيسية
    الخطوة 2: زيارة كل تصنيف رئيسي لاستخراج التصنيفات الفرعية وعدد الصفحات
    """
    logger.info("🌳 بدء سحب شجرة التصنيفات عبر HTML (لتجنب الحظر)...")
    
    category_tree = {}
    base_pattern = f"{Config.BASE_URL}/post/category/"

    # الخطوة 1: جلب التصنيفات الرئيسية من الصفحة الرئيسية
    logger.info("   🔍 جاري استخراج التصنيفات الرئيسية من الصفحة الرئيسية...")
    response = http_client.get(Config.BASE_URL)
    
    if not response:
        logger.error("❌ فشل في الوصول للصفحة الرئيسية. تأكد من أن الموقع لا يحظر الـ IP.")
        return None

    soup = BeautifulSoup(response.text, 'lxml')
    # استخراج كل الروابط التي تحتوي على تصنيفات رئيسية
    for link in soup.find_all('a', href=re.compile(r'/post/category/[^/]+$')):
        href = link['href']
        name = link.get_text().strip()
        slug = href.split('/post/category/')[-1].strip('/')
        
        # تأكد أنه تصنيف رئيسي (لا يحتوي على /) ولديه اسم
        if '/' not in slug and slug not in category_tree and name:
            category_tree[slug] = {
                'slug': slug,
                'url': href,
                'name_ar': name,
                'lastmod': None,
                'total_pages': 0,
                'article_count_estimate': 0,
                'children': {}
            }

    logger.info(f"   ✅ تم العثور على {len(category_tree)} تصنيف رئيسي.")

    # الخطوة 2: زيارة كل تصنيف رئيسي لاستخراج التصنيفات الفرعية وعدد الصفحات
    logger.info("   🔍 جاري استخراج التصنيفات الفرعية وعدد الصفحات لكل قسم...")

    for slug, cat_data in tqdm(category_tree.items(), desc="📂 التصنيفات الرئيسية"):
        response = http_client.get(cat_data['url'])
        if not response:
            continue
            
        cat_soup = BeautifulSoup(response.text, 'lxml')

        # استخراج عدد الصفحات من الـ pagination
        pagination = cat_soup.select('a.page-numbers')
        if pagination:
            try:
                pages_text = [a.get_text().replace('٬', '').replace(',', '')
                              for a in pagination
                              if a.get_text().replace('٬', '').replace(',', '').strip().isdigit()]
                if pages_text:
                    max_page = max(int(p) for p in pages_text)
                    cat_data['total_pages'] = max_page
                    # تقدير: ~20 مقال لكل صفحة
                    cat_data['article_count_estimate'] = max_page * 20
            except (ValueError, TypeError):
                cat_data['total_pages'] = 1
        else:
             cat_data['total_pages'] = 1
             cat_data['article_count_estimate'] = 20

        # استخراج التصنيفات الفرعية من الصفحة
        for link in cat_soup.find_all('a', href=re.compile(f'/post/category/{slug}/[^/]+$')):
            href = link['href']
            child_name = link.get_text().strip()
            child_slug = href.split(f'/post/category/{slug}/')[-1].strip('/')
            
            if child_slug and '/' not in child_slug and child_name:
                cat_data['children'][child_slug] = {
                    'slug': child_slug,
                    'url': href,
                    'name_ar': child_name,
                    'lastmod': None,
                    'total_pages': 0,
                    'article_count_estimate': 0,
                }

    # الخطوة 3: حفظ الشجرة
    with open(Config.CATEGORIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(category_tree, f, ensure_ascii=False, indent=2)

    # طباعة ملخص
    total_main = len(category_tree)
    total_sub = sum(len(c['children']) for c in category_tree.values())
    total_articles = sum(c['article_count_estimate'] for c in category_tree.values())

    logger.info(f"\n✅ تم سحب شجرة التصنيفات بنجاح!")
    logger.info(f"   📁 تصنيفات رئيسية: {total_main}")
    logger.info(f"   📂 تصنيفات فرعية: {total_sub}")
    logger.info(f"   📄 تقدير المقالات: ~{total_articles:,}")
    logger.info(f"   💾 حُفظت في: {Config.CATEGORIES_FILE}")

    return category_tree


# ── تنفيذ ──
category_tree = crawl_category_tree()

# عرض الشجرة
if category_tree:
    print("\n" + "="*60)
    print("🌳 شجرة التصنيفات:")
    print("="*60)
    for slug, data in sorted(category_tree.items(), key=lambda x: x[1].get('article_count_estimate', 0), reverse=True):
        name = data.get('name_ar', slug)
        pages = data.get('total_pages', 0)
        count = data.get('article_count_estimate', 0)
        children_count = len(data.get('children', {}))
        print(f"\n📁 {name} ({slug}) — ~{count:,} مقال | {children_count} فرعي")
        for child_slug, child_data in data.get('children', {}).items():
            child_name = child_data.get('name_ar', child_slug)
            print(f"   └── {child_name} ({child_slug})")

# %% [markdown]
# ## المرحلة 3: جمع روابط المقالات عبر Sitemaps 🔗

# %%
# ============================================================
# [CELL 5] جمع روابط المقالات من ملفات Sitemap
# ============================================================

def collect_article_urls_from_sitemaps():
    """
    جمع روابط المقالات. 
    يحاول أولاً عبر ملفات sitemap لأنه أسرع، 
    وإذا كان الموقع يحظر ملفات XML، ينتقل للسحب عبر تصفح صفحات التصنيفات (HTML Fallback)
    """
    logger.info("🔗 بدء جمع روابط المقالات...")

    all_article_urls = {}
    
    # محاولة 1: السحب عبر Sitemaps
    main_sitemap_url = f"{Config.BASE_URL}/sitemap.xml"
    response = http_client.get(main_sitemap_url)
    
    if response and '<sitemapindex' in response.text:
        logger.info("   ✅ ملف sitemap متاح. جاري جمع الروابط عبره...")
        root = ET.fromstring(response.content)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        post_sitemap_urls = []
        for sitemap in root.findall('.//ns:sitemap', ns):
            loc = sitemap.find('ns:loc', ns)
            if loc is not None and 'post-sitemap' in loc.text:
                post_sitemap_urls.append(loc.text.strip())

        logger.info(f"   تم العثور على {len(post_sitemap_urls)} ملف sitemap للمقالات")

        for sitemap_url in tqdm(post_sitemap_urls, desc="📋 قراءة Sitemaps"):
            resp = http_client.get(sitemap_url)
            if not resp:
                continue
            try:
                root = ET.fromstring(resp.content)
                for url_elem in root.findall('.//ns:url', ns):
                    loc = url_elem.find('ns:loc', ns)
                    lastmod = url_elem.find('ns:lastmod', ns)
                    if loc is not None:
                        article_url = loc.text.strip()
                        if '/post/' in article_url and re.search(r'/post/\d+', article_url):
                            all_article_urls[article_url] = {
                                'lastmod': lastmod.text.strip() if lastmod is not None else None,
                                'categories': [],
                                'scraped': False
                            }
            except ET.ParseError as e:
                logger.warning(f"⚠️ خطأ في تحليل {sitemap_url}: {e}")
                
    else:
        # محاولة 2: Fallback (تصفح صفحات التصنيفات HTML)
        logger.warning("   ⚠️ ملفات sitemap محظورة (أو فشل قراءتها). الانتقال للطريقة البديلة (HTML Fallback)...")
        
        # التأكد من وجود ملف التصنيفات
        if not os.path.exists(Config.CATEGORIES_FILE):
            logger.error("❌ ملف التصنيفات غير موجود. يرجى تشغيل المرحلة 2 أولاً!")
            return {}
            
        with open(Config.CATEGORIES_FILE, 'r', encoding='utf-8') as f:
            category_tree = json.load(f)
            
        # جمع الروابط من كل تصنيف
        for slug, cat_data in tqdm(category_tree.items(), desc="📂 فحص صفحات التصنيفات"):
            total_pages = cat_data.get('total_pages', 1)
            
            # نفحص فقط أول 5 صفحات من كل تصنيف للاختبار (يمكنك إزالة هذا الحد لسحب كل المقالات)
            # لتسريع العملية أثناء الاختبار، حددنا الصفحات. قم بتغييره إلى total_pages لسحب كامل.
            pages_to_scrape = min(total_pages, 5) 
            
            for page in range(1, pages_to_scrape + 1):
                page_url = cat_data['url'] if page == 1 else f"{cat_data['url']}/page/{page}"
                resp = http_client.get(page_url)
                if not resp:
                    continue
                    
                soup = BeautifulSoup(resp.text, 'lxml')
                
                # استخراج الروابط (نعتمد على وجود /post/ ورقم)
                for link in soup.find_all('a', href=re.compile(r'/post/\d+')):
                    href = link['href']
                    if href not in all_article_urls:
                        all_article_urls[href] = {
                            'lastmod': None,
                            'categories': [slug],
                            'scraped': False
                        }
                    else:
                        if slug not in all_article_urls[href]['categories']:
                            all_article_urls[href]['categories'].append(slug)

    logger.info(f"   ✅ تم جمع {len(all_article_urls):,} رابط مقال")

    # الخطوة 3: حفظ الروابط
    with open(Config.ARTICLE_URLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_article_urls, f, ensure_ascii=False, indent=2)

    logger.info(f"   💾 حُفظت الروابط في: {Config.ARTICLE_URLS_FILE}")

    return all_article_urls


# ── تنفيذ ──
article_urls = collect_article_urls_from_sitemaps()
print(f"\n📊 إجمالي روابط المقالات المجمعة: {len(article_urls):,}")

# %% [markdown]
# ## المرحلة 4: سحب محتوى المقالات 📄
# مع نظام checkpoint للاستئناف في حالة الانقطاع

# %%
# ============================================================
# [CELL 6] نظام الـ Checkpoint والاستئناف
# ============================================================

class CheckpointManager:
    """إدارة نقاط الحفظ للاستئناف عند الانقطاع"""

    def __init__(self, checkpoint_file=Config.CHECKPOINT_FILE):
        self.file = checkpoint_file
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file):
            with open(self.file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"📌 تم تحميل checkpoint: {data.get('scraped_count', 0)} مقال مُنجز")
                return data
        return {
            'scraped_urls': [],
            'failed_urls': [],
            'scraped_count': 0,
            'failed_count': 0,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'last_updated': None,
            'last_url': None,
        }

    def save(self):
        self.data['last_updated'] = datetime.now(timezone.utc).isoformat()
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def is_scraped(self, url):
        return url in self.data['scraped_urls']

    def mark_scraped(self, url):
        if url not in self.data['scraped_urls']:
            self.data['scraped_urls'].append(url)
            self.data['scraped_count'] = len(self.data['scraped_urls'])
            self.data['last_url'] = url

    def mark_failed(self, url, error=""):
        if url not in self.data['failed_urls']:
            self.data['failed_urls'].append(url)
            self.data['failed_count'] = len(self.data['failed_urls'])

    def get_progress(self, total):
        done = self.data['scraped_count']
        failed = self.data['failed_count']
        remaining = total - done - failed
        pct = (done / total * 100) if total > 0 else 0
        return {
            'done': done,
            'failed': failed,
            'remaining': remaining,
            'total': total,
            'percentage': f"{pct:.1f}%"
        }

    def reset(self):
        """إعادة تعيين الـ checkpoint (احذر!)"""
        self.data = {
            'scraped_urls': [],
            'failed_urls': [],
            'scraped_count': 0,
            'failed_count': 0,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'last_updated': None,
            'last_url': None,
        }
        self.save()
        logger.info("🔄 تم إعادة تعيين الـ checkpoint")


checkpoint = CheckpointManager()
progress = checkpoint.get_progress(len(article_urls) if 'article_urls' in dir() else 0)
print(f"📌 حالة التقدم: {progress['done']:,} مُنجز | {progress['failed']:,} فاشل | {progress['remaining']:,} متبقي")

# %%
# ============================================================
# [CELL 7] سحب محتوى المقالات - المحرك الأساسي
# ============================================================

def extract_article_data(url, response):
    """
    استخراج بيانات المقال من صفحة HTML
    يُرجع dict ببيانات المقال أو None في حالة الفشل
    """
    try:
        soup = BeautifulSoup(response.text, 'lxml')

        # ── العنوان ──
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().split('|')[0].strip()
        if not title:
            h1 = soup.find('h1')
            title = h1.get_text().strip() if h1 else ""

        # ── الوصف (meta description) ──
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '').strip()
        if not description:
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc:
                description = og_desc.get('content', '').strip()

        # ── الكاتب ──
        author = ""
        author_link = soup.find('a', href=re.compile(r'/post/author/'))
        if author_link:
            author = author_link.get_text().strip()

        # ── التاريخ ──
        date = ""
        time_tag = soup.find('time')
        if time_tag:
            date = time_tag.get('datetime', time_tag.get_text().strip())
        if not date:
            # محاولة بديلة من meta tags
            date_meta = soup.find('meta', attrs={'property': 'article:published_time'})
            if date_meta:
                date = date_meta.get('content', '')

        # ── التصنيفات ──
        categories = []
        category_links = soup.find_all('a', href=re.compile(r'/post/category/'))
        seen_cats = set()
        for link in category_links:
            href = link.get('href', '')
            cat_path = href.split('/post/category/')[-1].strip('/')
            cat_name = link.get_text().strip()
            if cat_path and cat_path not in seen_cats and cat_name:
                seen_cats.add(cat_path)
                categories.append({
                    'slug': cat_path,
                    'name_ar': cat_name
                })

        # تحديد التصنيف الرئيسي والفرعي
        primary_category = ""
        primary_slug = ""
        secondary_category = ""
        secondary_slug = ""
        category_path = ""

        if categories:
            # ترتيب: التصنيف الأقصر (رئيسي) أولاً
            sorted_cats = sorted(categories, key=lambda x: len(x['slug']))
            primary_category = sorted_cats[0]['name_ar']
            primary_slug = sorted_cats[0]['slug']
            if len(sorted_cats) > 1 and '/' in sorted_cats[-1]['slug']:
                secondary_category = sorted_cats[-1]['name_ar']
                secondary_slug = sorted_cats[-1]['slug'].split('/')[-1]

            category_path = primary_category
            if secondary_category:
                category_path += f" > {secondary_category}"

        # ── الوسوم (Tags) ──
        tags = []
        tag_links = soup.find_all('a', href=re.compile(r'/post/tag/'))
        for link in tag_links:
            tag_name = link.get_text().strip()
            if tag_name and tag_name not in tags:
                tags.append(tag_name)

        # ── المحتوى ──
        content = ""

        # محاولة 1: البحث عن entry-content (معيار WordPress)
        content_div = soup.find('div', class_=re.compile(r'entry-content|article-content|post-content|single-content'))

        if not content_div:
            # محاولة 2: عنصر article
            content_div = soup.find('article')

        if not content_div:
            # محاولة 3: أكبر div يحتوي على فقرات
            all_divs = soup.find_all('div')
            max_p_count = 0
            for div in all_divs:
                p_count = len(div.find_all('p'))
                if p_count > max_p_count:
                    max_p_count = p_count
                    content_div = div

        if content_div:
            # إزالة العناصر غير المرغوبة
            unwanted_selectors = [
                'script', 'style', 'nav', 'header', 'footer',
                'aside', 'iframe', 'noscript', 'form',
                '.sidebar', '.widget', '.navigation', '.post-navigation',
                '.related-posts', '.author-box', '.comments',
                '.social-share', '.share-buttons', '.breadcrumb',
                '.advertisement', '.ad-container',
                '[class*="share"]', '[class*="social"]',
                '[class*="popup"]', '[class*="modal"]',
                '[id*="sidebar"]', '[id*="comment"]',
            ]

            for selector in unwanted_selectors:
                for element in content_div.select(selector):
                    element.decompose()

            # أيضاً إزالة div يحتوي على "مقالات أعجبت" أو "مقالاتنا الجديدة"
            for h2 in content_div.find_all(['h2', 'h3', 'h4']):
                text = h2.get_text()
                if any(phrase in text for phrase in ['مقالات أعجبت', 'مقالاتنا الجديدة', 'الاقسام', 'زخرف اسمك']):
                    # إزالة هذا العنصر وكل ما بعده
                    for sibling in h2.find_next_siblings():
                        sibling.decompose()
                    h2.decompose()

            # استخراج النص مع الحفاظ على بنية الفقرات
            paragraphs = []
            for elem in content_div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
                text = elem.get_text().strip()
                if text and len(text) > 5:
                    if elem.name and elem.name.startswith('h'):
                        paragraphs.append(f"\n## {text}\n")
                    elif elem.name == 'li':
                        paragraphs.append(f"• {text}")
                    else:
                        paragraphs.append(text)

            content = '\n'.join(paragraphs)

        # تنظيف المحتوى
        content = text_cleaner.clean(content)

        # ── استخراج ID المقال ──
        article_id = None
        match = re.search(r'/post/(\d+)', url)
        if match:
            article_id = int(match.group(1))

        # ── حساب الإحصائيات ──
        word_count = text_cleaner.count_arabic_words(content) if content else 0

        # بناء النتيجة
        article_data = {
            'id': article_id,
            'url': url,
            'title': title,
            'description': description,
            'author': author,
            'date': date,
            'content': content,
            'category': {
                'primary': primary_category,
                'primary_slug': primary_slug,
                'secondary': secondary_category,
                'secondary_slug': secondary_slug,
                'path': category_path,
            },
            'tags': tags,
            'word_count': word_count,
            'scraped_at': datetime.now(timezone.utc).isoformat()
        }

        return article_data

    except Exception as e:
        logger.error(f"❌ خطأ في استخراج بيانات {url}: {e}")
        return None


def scrape_articles(article_urls_dict, max_articles=None, max_workers=5):
    """
    سحب محتوى المقالات مع نظام checkpoint والتوازي (Multithreading)
    """
    global checkpoint

    urls = list(article_urls_dict.keys())
    total = len(urls)

    if max_articles:
        total = min(total, max_articles)
        urls = urls[:total]

    logger.info(f"\n📄 بدء سحب محتوى المقالات ({total:,} مقال) باستخدام {max_workers} مسارات متوازية...")
    
    scraped_articles = []
    batch = []
    batch_count = 0
    skipped = 0
    lock = threading.Lock()

    # تحميل المقالات المسحوبة سابقاً
    existing_files = [f for f in os.listdir(Config.RAW_DIR) if f.endswith('.json')]
    for ef in existing_files:
        try:
            with open(os.path.join(Config.RAW_DIR, ef), 'r', encoding='utf-8') as f:
                existing_batch = json.load(f)
                if isinstance(existing_batch, list):
                    scraped_articles.extend(existing_batch)
        except (json.JSONDecodeError, IOError):
            pass

    logger.info(f"   📂 مقالات موجودة مسبقاً: {len(scraped_articles):,}")

    progress_bar = tqdm(total=total, desc="📄 سحب المقالات", initial=checkpoint.data['scraped_count'])
    
    def process_url(url):
        # تخطي إذا كان مسحوب مسبقاً
        with lock:
            if checkpoint.is_scraped(url):
                return url, "skipped", None

        response = http_client.get(url)
        if not response:
            return url, "failed_request", None

        article_data = extract_article_data(url, response)
        if article_data and article_data.get('content') and article_data['word_count'] > 20:
            return url, "success", article_data
        else:
            return url, "failed_extract", None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_url, url): url for url in urls}
        
        for future in as_completed(futures):
            url = futures[future]
            try:
                result_url, status, article_data = future.result()
                
                with lock:
                    if status == "skipped":
                        skipped += 1
                    else:
                        if status == "success":
                            batch.append(article_data)
                            checkpoint.mark_scraped(result_url)
                        elif status == "failed_request":
                            checkpoint.mark_failed(result_url, "HTTP request failed")
                        elif status == "failed_extract":
                            checkpoint.mark_failed(result_url, "Empty or too short content")
                        
                        progress_bar.update(1)
                        batch_count += 1
                        
                        # حفظ دوري
                        if batch_count % Config.CHECKPOINT_EVERY == 0:
                            checkpoint.save()
                        
                        if batch_count % Config.SAVE_RAW_EVERY == 0:
                            batch_file = os.path.join(Config.RAW_DIR, f"batch_{batch_count:06d}.json")
                            with open(batch_file, 'w', encoding='utf-8') as f:
                                json.dump(batch, f, ensure_ascii=False, indent=2)
                            scraped_articles.extend(batch)
                            batch = []
                            logger.info(f"   💾 حُفظت دفعة ({batch_count} مقال إجمالي)")

                        if batch_count % 500 == 0:
                            p = checkpoint.get_progress(total)
                            logger.info(f"   📊 تقدم: {p['done']:,}/{p['total']:,} ({p['percentage']})")
                            
            except Exception as e:
                logger.error(f"❌ استثناء غير متوقع للرابط {url}: {e}")
                with lock:
                    checkpoint.mark_failed(url, str(e))
                    progress_bar.update(1)

    # حفظ الدفعة الأخيرة
    with lock:
        if batch:
            batch_file = os.path.join(Config.RAW_DIR, f"batch_{batch_count:06d}.json")
            with open(batch_file, 'w', encoding='utf-8') as f:
                json.dump(batch, f, ensure_ascii=False, indent=2)
            scraped_articles.extend(batch)

        progress_bar.close()
        checkpoint.save()

        # إحصائيات نهائية
        final = checkpoint.get_progress(total)
        logger.info(f"\n✅ انتهى السحب!")
        logger.info(f"   📄 مقالات ناجحة: {final['done']:,}")
        logger.info(f"   ❌ مقالات فاشلة: {final['failed']:,}")
        logger.info(f"   ⏭️ مقالات مُتخطاة: {skipped:,}")
        logger.info(f"   🌐 إحصائيات الشبكة: {http_client.get_stats()}")

    return scraped_articles


# ──────────────────────────────────────────────
# ⚡ تنفيذ السحب
# ──────────────────────────────────────────────
# 💡 غيّر MAX_ARTICLES حسب حاجتك:
#    - None = سحب الكل (~143K مقال)
#    - 1000 = عينة صغيرة للاختبار
#    - 10000 = عينة متوسطة

MAX_ARTICLES = 1000  # ← غيّر هذا الرقم حسب حاجتك

scraped_data = scrape_articles(article_urls, max_articles=MAX_ARTICLES)
print(f"\n📊 إجمالي المقالات المسحوبة: {len(scraped_data):,}")

# %% [markdown]
# ## المرحلة 5: معالجة البيانات وتصديرها للتدريب 💾

# %%
# ============================================================
# [CELL 8] تجميع كل المقالات المسحوبة من الملفات الخام
# ============================================================

def load_all_scraped_articles():
    """تحميل جميع المقالات من ملفات الدفعات"""
    all_articles = []
    raw_files = sorted([f for f in os.listdir(Config.RAW_DIR) if f.endswith('.json')])

    for filename in raw_files:
        filepath = os.path.join(Config.RAW_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_articles.extend(data)
                elif isinstance(data, dict):
                    all_articles.append(data)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"⚠️ خطأ في قراءة {filename}: {e}")

    # إزالة المكررات
    seen_ids = set()
    unique_articles = []
    for article in all_articles:
        aid = article.get('id') or article.get('url', '')
        if aid not in seen_ids:
            seen_ids.add(aid)
            unique_articles.append(article)

    logger.info(f"📂 تم تحميل {len(unique_articles):,} مقال فريد من {len(raw_files)} ملف")
    return unique_articles


# تحميل المقالات
all_articles = load_all_scraped_articles()
print(f"📄 إجمالي المقالات: {len(all_articles):,}")

# %%
# ============================================================
# [CELL 9] تصدير البيانات بصيغة JSON للتدريب
# ============================================================

def export_training_dataset(articles, output_dir=Config.OUTPUT_DIR):
    """
    تصدير البيانات بعدة صيغ JSON مناسبة لتدريب نموذج مخصص
    """
    logger.info("💾 بدء تصدير بيانات التدريب...")

    os.makedirs(output_dir, exist_ok=True)

    # ─── الصيغة 1: JSON كامل (كل مقال بكامل بياناته) ───
    full_dataset = []
    for article in articles:
        if not article.get('content'):
            continue

        entry = {
            "id": article.get('id'),
            "title": article.get('title', ''),
            "content": article.get('content', ''),
            "description": article.get('description', ''),
            "author": article.get('author', ''),
            "date": article.get('date', ''),
            "category": article.get('category', {}).get('primary', ''),
            "category_slug": article.get('category', {}).get('primary_slug', ''),
            "subcategory": article.get('category', {}).get('secondary', ''),
            "subcategory_slug": article.get('category', {}).get('secondary_slug', ''),
            "category_path": article.get('category', {}).get('path', ''),
            "tags": article.get('tags', []),
            "word_count": article.get('word_count', 0),
            "source_url": article.get('url', ''),
        }
        full_dataset.append(entry)

    # حفظ JSON كامل
    full_file = os.path.join(output_dir, "dataset_full.json")
    with open(full_file, 'w', encoding='utf-8') as f:
        json.dump(full_dataset, f, ensure_ascii=False, indent=2)
    logger.info(f"   ✅ dataset_full.json ({len(full_dataset):,} مقال)")

    # ─── الصيغة 2: JSONL (سطر لكل مقال - للتدريب) ───
    jsonl_file = os.path.join(output_dir, "dataset_training.jsonl")
    with open(jsonl_file, 'w', encoding='utf-8') as f:
        for entry in full_dataset:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    logger.info(f"   ✅ dataset_training.jsonl")

    # ─── الصيغة 3: مقسم حسب التصنيفات (JSON لكل تصنيف) ───
    by_category_dir = os.path.join(output_dir, "by_category")
    os.makedirs(by_category_dir, exist_ok=True)

    category_groups = defaultdict(list)
    for entry in full_dataset:
        cat = entry.get('category_slug') or 'uncategorized'
        category_groups[cat].append(entry)

    for cat_slug, cat_articles in category_groups.items():
        cat_file = os.path.join(by_category_dir, f"{cat_slug}.json")
        with open(cat_file, 'w', encoding='utf-8') as f:
            json.dump(cat_articles, f, ensure_ascii=False, indent=2)

    logger.info(f"   ✅ by_category/ ({len(category_groups)} تصنيف)")

    # ─── الصيغة 4: نص فقط للتدريب (Plain Text) ───
    text_file = os.path.join(output_dir, "dataset_text_only.jsonl")
    with open(text_file, 'w', encoding='utf-8') as f:
        for entry in full_dataset:
            text_entry = {
                "text": f"العنوان: {entry['title']}\nالتصنيف: {entry['category_path']}\n\n{entry['content']}",
                "category": entry['category_path'],
            }
            f.write(json.dumps(text_entry, ensure_ascii=False) + '\n')
    logger.info(f"   ✅ dataset_text_only.jsonl")

    logger.info(f"\n💾 تم تصدير جميع الملفات في: {output_dir}")
    return full_dataset


# ── تنفيذ ──
dataset = export_training_dataset(all_articles)

# %% [markdown]
# ## المرحلة 6: الإحصائيات وتوثيق السحب 📊

# %%
# ============================================================
# [CELL 10] إحصائيات شاملة وتوثيق عملية السحب
# ============================================================

def generate_statistics_and_report(articles, dataset):
    """إنشاء تقرير إحصائي شامل وتوثيق عملية السحب"""

    logger.info("📊 إنشاء التقرير الإحصائي...")

    # ─── إحصائيات المحتوى ───
    total_articles = len(dataset)
    total_words = sum(a.get('word_count', 0) for a in dataset)
    avg_words = total_words // max(total_articles, 1)

    word_counts = [a.get('word_count', 0) for a in dataset]
    min_words = min(word_counts) if word_counts else 0
    max_words = max(word_counts) if word_counts else 0

    # توزيع التصنيفات
    category_dist = defaultdict(int)
    subcategory_dist = defaultdict(int)
    author_dist = defaultdict(int)

    for a in dataset:
        cat = a.get('category', 'غير مصنف') or 'غير مصنف'
        sub = a.get('subcategory', '') or ''
        author = a.get('author', 'غير معروف') or 'غير معروف'

        category_dist[cat] += 1
        if sub:
            subcategory_dist[f"{cat} > {sub}"] += 1
        author_dist[author] += 1

    # ─── بناء التقرير ───
    report = {
        "scrape_metadata": {
            "source_website": "https://www.almrsal.com",
            "scrape_date": datetime.now(timezone.utc).isoformat(),
            "scraper_version": "1.0.0",
            "purpose": "تدريب نموذج لغوي عربي مخصص",
            "content_type": "نص فقط (بدون صور)",
        },
        "content_statistics": {
            "total_articles": total_articles,
            "total_words": total_words,
            "average_words_per_article": avg_words,
            "min_words": min_words,
            "max_words": max_words,
            "total_characters": sum(len(a.get('content', '')) for a in dataset),
        },
        "category_distribution": dict(sorted(category_dist.items(), key=lambda x: x[1], reverse=True)),
        "subcategory_distribution": dict(sorted(subcategory_dist.items(), key=lambda x: x[1], reverse=True)[:50]),
        "top_authors": dict(sorted(author_dist.items(), key=lambda x: x[1], reverse=True)[:20]),
        "network_statistics": http_client.get_stats(),
        "checkpoint_status": checkpoint.data.get('scraped_count', 0),
        "output_files": {
            "dataset_full.json": f"{total_articles} مقال (بيانات كاملة)",
            "dataset_training.jsonl": f"{total_articles} سطر (للتدريب)",
            "dataset_text_only.jsonl": f"{total_articles} سطر (نص فقط مع تصنيف)",
            "by_category/": f"{len(category_dist)} ملف (ملف لكل تصنيف)",
        },
        "data_schema": {
            "id": "معرف المقال (رقم)",
            "title": "عنوان المقال",
            "content": "النص الكامل للمقال (منظف)",
            "description": "وصف مختصر",
            "author": "اسم الكاتب",
            "date": "تاريخ النشر",
            "category": "التصنيف الرئيسي (عربي)",
            "category_slug": "التصنيف الرئيسي (إنجليزي)",
            "subcategory": "التصنيف الفرعي (عربي)",
            "subcategory_slug": "التصنيف الفرعي (إنجليزي)",
            "category_path": "المسار الكامل: رئيسي > فرعي",
            "tags": "قائمة الوسوم",
            "word_count": "عدد الكلمات العربية",
            "source_url": "رابط المقال الأصلي",
        }
    }

    # حفظ التقرير
    report_file = os.path.join(Config.OUTPUT_DIR, "scrape_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # ─── طباعة التقرير ───
    print("\n" + "=" * 70)
    print("📊  تقرير سحب بيانات موقع المرسال")
    print("=" * 70)

    print(f"\n🌐 المصدر: {report['scrape_metadata']['source_website']}")
    print(f"📅 تاريخ السحب: {report['scrape_metadata']['scrape_date'][:10]}")
    print(f"🎯 الغرض: {report['scrape_metadata']['purpose']}")

    print(f"\n📄 إحصائيات المحتوى:")
    print(f"   • إجمالي المقالات: {total_articles:,}")
    print(f"   • إجمالي الكلمات: {total_words:,}")
    print(f"   • متوسط الكلمات/مقال: {avg_words:,}")
    print(f"   • أقل مقال: {min_words} كلمة")
    print(f"   • أطول مقال: {max_words:,} كلمة")

    print(f"\n📁 توزيع التصنيفات الرئيسية (أعلى 15):")
    for i, (cat, count) in enumerate(sorted(category_dist.items(), key=lambda x: x[1], reverse=True)[:15], 1):
        bar = '█' * min(int(count / max(category_dist.values()) * 30), 30)
        print(f"   {i:2d}. {cat:20s} │ {count:5,} │ {bar}")

    print(f"\n🌐 إحصائيات الشبكة:")
    net_stats = http_client.get_stats()
    print(f"   • إجمالي الطلبات: {net_stats['total_requests']:,}")
    print(f"   • الطلبات الفاشلة: {net_stats['failed_requests']:,}")
    print(f"   • نسبة النجاح: {net_stats['success_rate']}")

    print(f"\n💾 الملفات المنتجة:")
    for fname, desc in report['output_files'].items():
        print(f"   📄 {fname}: {desc}")

    print(f"\n📋 التقرير الكامل: {report_file}")
    print("=" * 70)

    return report


# ── تنفيذ ──
report = generate_statistics_and_report(all_articles, dataset)

# %%
# ============================================================
# [CELL 11] عرض عينة من البيانات المسحوبة
# ============================================================

def show_sample(dataset, n=3):
    """عرض عينة من المقالات للتحقق من جودة السحب"""
    print("\n" + "=" * 70)
    print(f"🔍 عينة من {n} مقالات مسحوبة:")
    print("=" * 70)

    import random
    sample = random.sample(dataset, min(n, len(dataset)))

    for i, article in enumerate(sample, 1):
        print(f"\n{'─' * 60}")
        print(f"📄 المقال #{i}")
        print(f"   🆔 ID: {article.get('id')}")
        print(f"   📌 العنوان: {article.get('title', '')[:80]}...")
        print(f"   📁 التصنيف: {article.get('category_path', 'N/A')}")
        print(f"   ✍️  الكاتب: {article.get('author', 'N/A')}")
        print(f"   📅 التاريخ: {article.get('date', 'N/A')[:10]}")
        print(f"   🏷️  الوسوم: {', '.join(article.get('tags', [])[:5])}")
        print(f"   📊 عدد الكلمات: {article.get('word_count', 0):,}")
        print(f"   📝 بداية المحتوى:")
        content = article.get('content', '')
        print(f"      {content[:200]}...")

    print(f"\n{'─' * 60}")

if dataset:
    show_sample(dataset)

# %% [markdown]
# ## 🛠️ أدوات مساعدة إضافية

# %%
# ============================================================
# [CELL 12] أدوات إضافية: استئناف / إعادة / تصفية
# ============================================================

def resume_scraping():
    """استئناف السحب من آخر نقطة حفظ"""
    logger.info("🔄 استئناف السحب من آخر checkpoint...")

    # تحميل الروابط
    if os.path.exists(Config.ARTICLE_URLS_FILE):
        with open(Config.ARTICLE_URLS_FILE, 'r', encoding='utf-8') as f:
            urls = json.load(f)
    else:
        logger.error("❌ ملف الروابط غير موجود! شغّل مرحلة جمع الروابط أولاً")
        return

    global checkpoint
    checkpoint = CheckpointManager()

    progress = checkpoint.get_progress(len(urls))
    logger.info(f"   📌 التقدم الحالي: {progress['done']:,}/{progress['total']:,}")

    return scrape_articles(urls, max_articles=MAX_ARTICLES)


def retry_failed():
    """إعادة محاولة المقالات الفاشلة"""
    logger.info("🔄 إعادة محاولة المقالات الفاشلة...")

    global checkpoint
    checkpoint = CheckpointManager()

    failed_urls = checkpoint.data.get('failed_urls', [])
    if not failed_urls:
        logger.info("✅ لا توجد مقالات فاشلة!")
        return

    logger.info(f"   🔁 {len(failed_urls)} مقال للإعادة")

    # إزالتها من قائمة الفاشلة لإعادة المحاولة
    urls_dict = {url: {} for url in failed_urls}
    checkpoint.data['failed_urls'] = []
    checkpoint.data['failed_count'] = 0
    checkpoint.save()

    return scrape_articles(urls_dict)


def filter_dataset_by_category(category_slug):
    """تصفية Dataset حسب تصنيف معين"""
    cat_file = os.path.join(Config.OUTPUT_DIR, "by_category", f"{category_slug}.json")
    if os.path.exists(cat_file):
        with open(cat_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"📁 تصنيف '{category_slug}': {len(data)} مقال")
        return data
    else:
        print(f"❌ التصنيف '{category_slug}' غير موجود")
        return []


print("🛠️ الأدوات المتاحة:")
print("   • resume_scraping()        - استئناف السحب")
print("   • retry_failed()           - إعادة المقالات الفاشلة")
print("   • filter_dataset_by_category('health')  - تصفية حسب التصنيف")

# %% [markdown]
# ## 📋 ملاحظات الاستخدام
#
# ### لتغيير عدد المقالات:
# ```python
# MAX_ARTICLES = 5000  # غيّر في [CELL 7]
# ```
#
# ### لاستئناف السحب بعد الانقطاع:
# ```python
# resume_scraping()
# ```
#
# ### لسحب كل المقالات:
# ```python
# MAX_ARTICLES = None
# scraped_data = scrape_articles(article_urls, max_articles=None)
# ```
#
# ### الملفات المنتجة:
# | الملف | الوصف | الاستخدام |
# |-------|-------|-----------|
# | `dataset_full.json` | كل المقالات ببيانات كاملة | تحليل البيانات |
# | `dataset_training.jsonl` | سطر لكل مقال | تدريب النموذج |
# | `dataset_text_only.jsonl` | نص + تصنيف فقط | Pre-training |
# | `by_category/*.json` | ملف لكل تصنيف | تدريب مستهدف |
# | `scrape_report.json` | تقرير التوثيق | التوثيق |
