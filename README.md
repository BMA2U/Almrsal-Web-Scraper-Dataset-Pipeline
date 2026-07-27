# 🕷️ Almrsal Web Scraper & Dataset Pipeline

A professional, high-performance Python web scraper and data processing pipeline designed to extract, clean, and structure articles from **Almrsal (`almrsal.com`)**. Engineered specifically for gathering large-scale, high-quality Arabic text datasets for **Custom LLM Pre-training and Fine-Tuning**.

Developed and Maintained by: **Eng. Bassem Al-Taheri**

---

## 🌟 Key Features

- **🛡️ Anti-Ban & Cloudflare Bypass:** Powered by `curl_cffi` to perform browser TLS fingerprint impersonation (`impersonate="chrome"`), successfully bypassing strict Cloudflare WAF protections.
- **⚡ High-Speed Multi-Threading:** Employs `concurrent.futures.ThreadPoolExecutor` coupled with thread-safe synchronization (`threading.Lock`) for concurrent article downloading without race conditions or data corruption.
- **🔄 Fault-Tolerant Checkpoint System:** Automatically tracks progress in `checkpoint.json`. Supports seamless interruption and resumption, guaranteeing zero data loss or duplicate scraping upon network or power failures.
- **🧹 Arabic Text Cleaning & Structure Preservation:** Strips boilerplate elements (ads, sidebars, popups, related posts) while preserving Markdown headers (`##`), bullet points (`•`), and nested category taxonomies (`Primary > Secondary`).
- **📁 Multi-Format Dataset Export:** Generates ready-to-train datasets in multiple standard formats:
  - `dataset_full.json`: Complete dataset containing all metadata fields.
  - `dataset_training.jsonl`: Standard JSON Lines format for LLM fine-tuning datasets.
  - `dataset_text_only.jsonl`: Clean text stream for Causal Language Modeling / Pre-training.
  - `by_category/`: Partitioned JSON files grouped by primary category slugs.

---

## 🛠️ Prerequisites & Installation

### Dependencies
- Python 3.8+
- `curl_cffi`
- `beautifulsoup4`
- `lxml`
- `tqdm`
- `requests`

### Installation
Install all required libraries using `pip`:

```bash
pip install curl_cffi beautifulsoup4 lxml tqdm requests
```

---

## 🚀 Getting Started

### 1️⃣ Local Execution (Recommended)
Run the core scraper script locally:

```bash
python almrsal_scraper.py
```

### 2️⃣ Google Colab Execution
Open `almrsal_scraper.ipynb` in Google Colab and run cells sequentially. Google Drive mounting is automatically detected and configured.

---

## 📂 Repository Structure

```text
.
├── almrsal_scraper.py        # Core scraping engine & dataset generator
├── almrsal_scraper.ipynb     # Interactive Jupyter Notebook for Google Colab
├── convert_to_ipynb.py       # Helper script to compile Python code into .ipynb
├── README.md                 # Project documentation
├── .gitignore                # Git exclusion configuration
└── almrsal_dataset/          # Output directory (auto-created)
    ├── categories.json       # Parsed hierarchical category tree
    ├── article_urls.json     # Extracted article URL database (~143k URLs)
    ├── checkpoint.json       # State tracker for resumable execution
    ├── raw_articles/         # Batch raw JSON extractions (batch_000100.json, ...)
    └── dataset/              # Final processed datasets ready for AI training
        ├── dataset_full.json
        ├── dataset_training.jsonl
        ├── dataset_text_only.jsonl
        └── by_category/
```

---

## 📊 Dataset Schema

Each processed article entry is structured as follows:

```json
{
  "id": 1575776,
  "url": "https://www.almrsal.com/post/1575776",
  "title": "كيف تستكشف دبي كأحد سكانها: مزايا استئجار سيارة فاخرة",
  "description": "معاينة لمزايا استئجار السيارات الفاخرة في دبي...",
  "author": "مشاري الحربي",
  "date": "2026-07-27T03:17:55+00:00",
  "content": "محتويات\n## لماذا تُغيّر السيارة الفاخرة طريقة استكشافك لدبي؟\nدبي مدينة صُممت للسيارات أكثر من المشي...\n• نخلة جميرا: طريق دائري بإطلالات بحرية...",
  "category": {
    "primary": "الخليج العربي",
    "primary_slug": "the-arabian-gulf",
    "secondary": "الامارات",
    "secondary_slug": "emirates-news",
    "path": "الخليج العربي > الامارات"
  },
  "tags": [],
  "word_count": 900,
  "scraped_at": "2026-07-27T15:47:04.944243+00:00"
}
```

---

## 👨‍💻 Author & Credits

**Eng. Bassem Al-Taheri**  
*AI & Data Systems Engineer*  

---

## 📜 License

This project is licensed under the MIT License - feel free to use and adapt for AI research and dataset construction.
