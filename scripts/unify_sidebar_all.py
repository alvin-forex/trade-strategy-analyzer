#!/usr/bin/env python3
"""
TSA Sidebar 統一腳本
- 移除所有 top-nav / topnav HTML + CSS + JS
- 為所有無 sidebar.js 嘅頁面加入 sidebar.css + sidebar.js 引用
- 統一 body padding-left
- 保持每個頁面原有內容不變
"""

import os
import re
import glob

DOCS_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../docs'

def get_depth(html_path, docs_dir):
    """計算相對路徑深度"""
    rel = os.path.relpath(html_path, docs_dir)
    parts = rel.split(os.sep)
    if len(parts) == 1:
        return ''
    depth = '../' * (len(parts) - 1)
    return depth

def has_sidebar_ref(content):
    """檢查是否已引用 sidebar.js"""
    return 'sidebar.js' in content

def has_sidebar_css(content):
    """檢查是否已引用 sidebar.css"""
    return 'sidebar.css' in content

def remove_topnav(content):
    """移除 top-nav 相關 HTML/CSS/JS"""
    original = content
    
    # 移除 top-nav HTML 區塊（<nav class="top-nav">...</nav> 或 <div class="top-nav">...</div>）
    content = re.sub(r'<nav[^>]*class="[^"]*top-nav[^"]*"[^>]*>.*?</nav>\s*', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<div[^>]*class="[^"]*top-nav[^"]*"[^>]*>.*?</div>\s*', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<header[^>]*class="[^"]*top-nav[^"]*"[^>]*>.*?</header>\s*', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除 topnav class HTML
    content = re.sub(r'<nav[^>]*class="[^"]*topnav[^"]*"[^>]*>.*?</nav>\s*', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<div[^>]*class="[^"]*topnav[^"]*"[^>]*>.*?</div>\s*', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除 CSS 中 .top-nav / .topnav 相關規則
    content = re.sub(r'\.top-nav\s*\{[^}]*\}', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\.topnav\s*\{[^}]*\}', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\.top-nav\s+[^\{]*\{[^}]*\}', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\.topnav\s+[^\{]*\{[^}]*\}', '', content, flags=re.IGNORECASE)
    
    # 移除 top-nav JS
    content = re.sub(r'//\s*top[-]?nav.*?(?=\n)', '', content, flags=re.IGNORECASE)
    
    return content, content != original

def add_sidebar_refs(content, depth):
    """加入 sidebar.css 和 sidebar.js 引用"""
    
    # 加入 sidebar.css（在 </head> 前）
    if not has_sidebar_css(content):
        sidebar_css = f'<link rel="stylesheet" href="{depth}sidebar.css">'
        if '</head>' in content:
            content = content.replace('</head>', f'{sidebar_css}\n</head>')
        elif '</HEAD>' in content:
            content = content.replace('</HEAD>', f'{sidebar_css}\n</HEAD>')
    
    # 加入 sidebar.js（在 </body> 前）
    if not has_sidebar_ref(content):
        sidebar_js = f'<script src="{depth}sidebar.js"></script>'
        if '</body>' in content:
            content = content.replace('</body>', f'{sidebar_js}\n</body>')
        elif '</BODY>' in content:
            content = content.replace('</BODY>', f'{sidebar_js}\n</BODY>')
    
    # 加入 body padding-left 如果無（俾 sidebar 空間）
    # sidebar.css 已經處理 .has-sidebar body padding
    
    return content

def remove_old_theme_toggle(content):
    """移除舊嘅 theme-toggle 按鈕（sidebar.js 自帶）"""
    
    # 移除 <button class="theme-toggle"> 或類似
    content = re.sub(
        r'<button[^>]*class="[^"]*theme-toggle[^"]*"[^>]*>.*?</button>\s*',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )
    content = re.sub(
        r'<button[^>]*id="theme-toggle[^"]*"[^>]*>.*?</button>\s*',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # 移除舊 theme-toggle CSS
    content = re.sub(r'\.theme-toggle\s*\{[^}]*\}', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\.theme-toggle\s+[^\{]*\{[^}]*\}', '', content, flags=re.IGNORECASE)
    
    # 移除舊 theme-toggle JS（局部，唔好刪 sidebar.js 嘅）
    # 只刪 <script> 區塊內嘅 theme toggle 邏輯
    # 呢個太危險，跳過 — sidebar.js 嘅 toggle 會 override
    
    return content

def process_file(filepath, docs_dir):
    """處理單個檔案"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        try:
            with open(filepath, 'r', encoding='big5') as f:
                content = f.read()
        except:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    content = f.read()
            except:
                return 'read_error'
    
    original = content
    changes = []
    
    # 1. 移除 top-nav
    content, removed = remove_topnav(content)
    if removed:
        changes.append('removed_topnav')
    
    # 2. 移除舊 theme-toggle
    old_content = content
    content = remove_old_theme_toggle(content)
    if content != old_content:
        changes.append('removed_old_theme_toggle')
    
    # 3. 加入 sidebar.css + sidebar.js
    depth = get_depth(filepath, docs_dir)
    old_content = content
    content = add_sidebar_refs(content, depth)
    if content != old_content:
        changes.append('added_sidebar_refs')
    
    # 4. 如果有改動先寫入
    if content != original:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return ','.join(changes)
        except Exception as e:
            return f'write_error: {e}'
    
    return 'no_change'

def main():
    docs_dir = DOCS_DIR
    
    # 搵所有 HTML 檔案
    html_files = []
    for root, dirs, files in os.walk(docs_dir):
        for f in files:
            if f.endswith('.html') or f.endswith('.htm'):
                html_files.append(os.path.join(root, f))
    
    print(f'找到 {len(html_files)} 個 HTML 檔案')
    
    stats = {
        'no_change': 0,
        'read_error': 0,
        'write_error': 0,
    }
    changed = []
    
    for filepath in sorted(html_files):
        result = process_file(filepath, docs_dir)
        if result in stats:
            stats[result] += 1
        elif 'write_error' in result:
            stats['write_error'] += 1
            print(f'  ❌ WRITE ERROR: {filepath}: {result}')
        else:
            changed.append((os.path.relpath(filepath, docs_dir), result))
    
    print(f'\n=== 結果 ===')
    print(f'總檔案: {len(html_files)}')
    print(f'已修改: {len(changed)}')
    print(f'無改動: {stats["no_change"]}')
    print(f'讀取錯誤: {stats["read_error"]}')
    print(f'寫入錯誤: {stats["write_error"]}')
    
    # 顯示修改類型統計
    type_stats = {}
    for _, changes in changed:
        for c in changes.split(','):
            type_stats[c] = type_stats.get(c, 0) + 1
    
    print(f'\n修改類型統計:')
    for t, count in sorted(type_stats.items(), key=lambda x: -x[1]):
        print(f'  {t}: {count}')
    
    # 顯示前 20 個修改嘅檔案
    print(f'\n修改嘅檔案（前 20 個）:')
    for path, changes in changed[:20]:
        print(f'  {path}: {changes}')
    
    if len(changed) > 20:
        print(f'  ... 同其他 {len(changed) - 20} 個檔案')
    
    return len(changed), stats

if __name__ == '__main__':
    main()
