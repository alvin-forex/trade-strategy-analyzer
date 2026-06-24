#!/usr/bin/env python3
"""
TSA 連結統一修復腳本
1. 刪除 dashboard.html（用 index.html 做唯一首頁）
2. signal_ranking_dde_v4.html → signal_ranking.html
3. ccy_timeframe_volatility.html → admin/volatility.html
4. 確保所有頁面連結路徑正確
"""

import os
import re
import glob

DOCS_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../docs'

def fix_links_in_file(filepath):
    """修正檔案中嘅連結"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return False, 'read_error'
    
    original = content
    rel_path = os.path.relpath(filepath, DOCS_DIR)
    
    # 計算相對深度
    parts = rel_path.split(os.sep)
    if len(parts) == 1:
        depth = ''
    else:
        depth = '../' * (len(parts) - 1)
    
    # === 連結修正規則 ===
    
    # 1. signal_ranking_dde_v4.html → signal_ranking.html
    #    出現形式：./signal_ranking_dde_v4.html, signal_ranking_dde_v4.html, ../signal_ranking_dde_v4.html
    content = re.sub(
        r'href="([^"]*)signal_ranking_dde_v4\.html"',
        lambda m: f'href="{m.group(1) if m.group(1) else depth}signal_ranking.html"',
        content
    )
    # 也修正 signal_ranking_dde_v5.html → signal_ranking.html（統一）
    content = re.sub(
        r'href="([^"]*)signal_ranking_dde_v5\.html"',
        lambda m: f'href="{m.group(1) if m.group(1) else depth}signal_ranking.html"',
        content
    )
    
    # 2. ccy_timeframe_volatility.html → admin/volatility.html
    #    根目錄的連結需要加 admin/，子目錄的需要 ../admin/
    #    先統一移除任何現有前綴，再加正確前綴
    content = re.sub(
        r'href="(?:\./|\.\./|\.\./\.\./)?(?:admin/)?ccy_timeframe_volatility\.html"',
        f'href="{depth}admin/volatility.html"',
        content
    )
    # volatility.html → admin/volatility.html（如果喺根目錄連結但實際喺 admin/）
    # 只改根目錄連結（無 admin/ 前綴的）
    content = re.sub(
        r'href="(?!admin/|http|//|\.{1,2}/admin/)([^"]*)volatility\.html"',
        f'href="{depth}admin/volatility.html"',
        content
    )
    
    # 3. dashboard.html → index.html
    content = re.sub(
        r'href="([^"]*)dashboard\.html"',
        lambda m: f'href="{m.group(1) if m.group(1) else depth}index.html"',
        content
    )
    
    if content != original:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, 'fixed'
        except Exception as e:
            return False, f'write_error: {e}'
    
    return False, 'no_change'

def main():
    docs_dir = DOCS_DIR
    
    # 1. 刪除 dashboard.html（index.html 先至係正嘢）
    dashboard = os.path.join(docs_dir, 'dashboard.html')
    if os.path.exists(dashboard):
        os.remove(dashboard)
        print('✅ 刪除 dashboard.html')
    
    # 2. 刪除 signal_ranking_dde_v5.html（signal_ranking.html 先至係正嘢）
    v5 = os.path.join(docs_dir, 'signal_ranking_dde_v5.html')
    if os.path.exists(v5):
        os.remove(v5)
        print('✅ 刪除 signal_ranking_dde_v5.html')
    
    # 3. 修正所有連結
    html_files = []
    for root, dirs, files in os.walk(docs_dir):
        for f in files:
            if f.endswith('.html') or f.endswith('.htm'):
                html_files.append(os.path.join(root, f))
    
    fixed_count = 0
    for filepath in sorted(html_files):
        if filepath == dashboard or filepath == v5:
            continue
        success, result = fix_links_in_file(filepath)
        if success:
            fixed_count += 1
    
    print(f'✅ 修正了 {fixed_count} 個檔案的連結')
    
    # 4. 驗證
    print('\n=== 驗證 ===')
    
    # 檢查 dead links
    dead_patterns = [
        'signal_ranking_dde_v4',
        'ccy_timeframe_volatility',
        'dashboard.html',
    ]
    
    for pattern in dead_patterns:
        count = 0
        for filepath in html_files:
            if filepath == dashboard or filepath == v5:
                continue
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    if pattern in f.read():
                        count += 1
            except:
                pass
        status = '✅' if count == 0 else '❌'
        print(f'{status} 殘留 "{pattern}": {count} 個檔案')
    
    # 檢查 sidebar.js 連結
    sidebar_path = os.path.join(docs_dir, 'sidebar.js')
    with open(sidebar_path, 'r') as f:
        sidebar_content = f.read()
    
    if 'signal_ranking_dde_v4' in sidebar_content:
        print('⚠️ sidebar.js 仍有 signal_ranking_dde_v4 引用')
    else:
        print('✅ sidebar.js 連結正確')
    
    # 檢查 dashboard.html 是否被刪除
    if not os.path.exists(dashboard):
        print('✅ dashboard.html 已刪除')
    else:
        print('❌ dashboard.html 仍存在')
    
    print(f'\n總檔案: {len(html_files) - 2}（刪除了 dashboard.html 和 signal_ranking_dde_v5.html）')

if __name__ == '__main__':
    main()
