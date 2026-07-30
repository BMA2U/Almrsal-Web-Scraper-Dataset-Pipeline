import os
import json
import glob

def count_total_articles(directory):
    # مسار المجلد الذي يحتوي على الدفعات
    pattern = os.path.join(directory, "batch_*.json")
    files = glob.glob(pattern)
    
    total_articles = 0
    total_files = len(files)
    
    print(f"Checking {total_files} files in the directory...")
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    total_articles += len(data)
                elif isinstance(data, dict):
                    # في حالة كان الملف يحتوي على عنصر واحد كقاموس
                    total_articles += 1
        except Exception as e:
            print(f"Error reading file {os.path.basename(file_path)}: {e}")
            
    print("=" * 50)
    print(f"Total files checked: {total_files}")
    print(f"Total articles scraped: {total_articles:,}")
    print("=" * 50)

if __name__ == "__main__":
    # مسار مجلد raw_articles
    TARGET_DIR = r"d:\lastYear\help\almrsal_dataset\raw_articles"
    
    if os.path.exists(TARGET_DIR):
        count_total_articles(TARGET_DIR)
    else:
        print(f"Folder not found: {TARGET_DIR}")
