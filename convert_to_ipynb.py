import json
import sys

def convert():
    try:
        content = open('d:/lastYear/help/almrsal_scraper.py', encoding='utf-8').read()
    except Exception as e:
        print("Error reading file:", e)
        return

    blocks = content.split('# %%')
    cells = []
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
            
        if block.startswith('[markdown]'):
            lines = block.split('\n')[1:] # Skip the [markdown] line
            # Remove the leading '# ' or '#' from markdown lines
            cleaned_lines = []
            for line in lines:
                if line.startswith('# '):
                    cleaned_lines.append(line[2:] + '\n')
                elif line.startswith('#'):
                    cleaned_lines.append(line[1:] + '\n')
                else:
                    cleaned_lines.append(line + '\n')
                    
            cells.append({
                'cell_type': 'markdown',
                'metadata': {},
                'source': cleaned_lines
            })
        else:
            cells.append({
                'cell_type': 'code',
                'metadata': {},
                'outputs': [],
                'execution_count': None,
                'source': [line + '\n' for line in block.split('\n')]
            })
            
    nb = {
        'cells': cells,
        'metadata': {},
        'nbformat': 4,
        'nbformat_minor': 5
    }
    
    with open('d:/lastYear/help/almrsal_scraper.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)
        
    print("Notebook converted successfully.")

if __name__ == '__main__':
    convert()
