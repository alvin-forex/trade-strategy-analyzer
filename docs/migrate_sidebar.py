#!/usr/bin/env python3
"""
TSA 系統框架統一遷移腳本 v3
使用純 regex 操作（避免逐行處理 4.9M 行）
使用：python3 migrate_sidebar.py [--dry-run]
"""

import os
import re
import glob
import sys

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))

UNIFIED_THEME_CSS = '\n/* === TSA 統一主題系統 === */\n[data-theme="dark"]{--bg:#0a0e17;--bg-card:#111520;--bg-hover:#1a1f2e;--text:#d0d0d0;--text2:#888;--primary:#FFD700;--accent:#64b5f6;--green:#4CAF50;--red:#FF5722;--yellow:#FFC107;--orange:#fd7e14;--border:#1e2433;--th-bg:#111520}\n[data-theme="light"]{--bg:#f5f7fa;--bg-card:#ffffff;--bg-hover:#eef2f7;--text:#333;--text2:#666;--primary:#0f3460;--accent:#e94560;--green:#28a745;--red:#dc3545;--yellow:#ffc107;--orange:#fd7e14;--border:#ddd;--th-bg:#eef2f7}\n'

THEME_INIT_SCRIPT = '<script>(function(){var s=localStorage.getItem(\'tsa-theme\')||\'dark\';document.documentElement.setAttribute(\'data-theme\',s);})();</script>'


def get_depth(filepath):
    rel = os.path.relpath(filepath, DOCS_DIR)
    d = os.path.dirname(rel)
    if not d or d == '.':
        return ''
    depth = d.count(os.sep) + 1
    return '../' * depth


def find_matching_div_close(text, start_pos):
    """找到配對的 </div>（考慮嵌套）"""
    depth = 0
    i = start_pos
    while i < len(text):
        next_open = text.find('<div', i)
        next_close = text.find('</div>', i)
        if next_close == -1:
            return -1
        if next_open != -1 and next_open < next_close:
            depth += 1
            i = next_open + 4
        else:
            depth -= 1
            i = next_close + 6
            if depth == 0:
                return i
    return -1


def remove_topnav(content):
    """移除 topnav HTML 區塊"""
    changes = []
    
    topnav_start = content.find('<div class="topnav"')
    if topnav_start == -1:
        topnav_start = content.find("<div class='topnav'")
    
    if topnav_start != -1:
        line_start = topnav_start
        while line_start > 0 and content[line_start - 1] in ' \t\r\n':
            line_start -= 1
        
        end_pos = find_matching_div_close(content, topnav_start)
        if end_pos != -1:
            # 檢查後面是否有獨立的 theme-toggle 按鈕
            rest = content[end_pos:end_pos + 200]
            btn_match = re.match(r'\s*<button[^>]*theme-toggle[^>]*>.*?</button>', rest, re.DOTALL)
            if btn_match:
                end_pos += btn_match.end()
            
            while end_pos < len(content) and content[end_pos] in '\r\n':
                end_pos += 1
            content = content[:line_start] + content[end_pos:]
            changes.append('removed topnav')
    
    # 移除獨立 theme-toggle 按鈕
    btn_pat = re.compile(r'\s*<button[^>]*class="theme-toggle"[^>]*>.*?</button>', re.DOTALL)
    content_new, n = btn_pat.subn('', content)
    if n > 0:
        content = content_new
        changes.append(f'removed {n} theme-toggle btn')
    
    # 移除 topnav CSS 規則
    for pat in [r'\.topnav\s*\{[^}]*\}', r'\.topnav-logo\s*\{[^}]*\}',
                r'\.topnav-links?\s*\{[^}]*\}', r'\.topnav-link\s*\{[^}]*\}',
                r'\.topnav-link:hover\s*\{[^}]*\}', r'\.topnav-link\.active\s*\{[^}]*\}']:
        content = re.sub(pat, '', content)
    
    # 移除 theme-btn class 按鈕（reports 頁面用的）
    btn_pat2 = re.compile(r'<button[^>]*class="theme-btn"[^>]*>.*?</button>', re.DOTALL)
    content_new, n = btn_pat2.subn('', content)
    if n > 0:
        content = content_new
        changes.append(f'removed {n} theme-btn')
    
    return content, changes


def remove_old_theme_js(content):
    """用 regex 移除舊的 theme JS（純 regex，不逐行處理）"""
    changes = []
    
    # 移除 theme init IIFE: (function(){ ... localStorage.getItem('tsa-theme') ... })();
    # 用非貪婪匹配 + 限定範圍
    def remove_iife(text):
        result = []
        last_end = 0
        for m in re.finditer(r'\(function\(\)\s*\{', text):
            # 從這裡找配對的 })()
            start = m.start()
            brace_pos = m.end() - 1  # 指向 {
            end_brace = find_brace_end(text, brace_pos)
            if end_brace == -1:
                continue
            # 檢查後面是否跟著 )()
            after = text[end_brace:end_brace + 10]
            if re.match(r'\s*\)\s*\(\s*\)\s*;?', after):
                block = text[start:end_brace + 1]
                full_end = end_brace + 1
                # 跳過 )();
                close_m = re.match(r'\s*\)\s*\(\s*\)\s*;?', after)
                if close_m:
                    full_end = end_brace + 1 + close_m.end()
                
                # 只有包含 tsa-theme 的才移除
                if 'tsa-theme' in block:
                    # 包含前面的空白
                    s = start
                    while s > 0 and text[s - 1] in ' \t\r\n':
                        s -= 1
                    result.append((s, full_end))
        
        # 執行移除
        for s, e in reversed(result):
            text = text[:s] + text[e:]
        return text
    
    # 移除 function toggleTheme(){...} - 單行版本（大多數情況）
    # 匹配到第一個 } 為止（注意單行函數）
    content_new = re.sub(
        r'function\s+toggleTheme\s*\(\)\s*\{[^}]*\}',
        '',
        content
    )
    if content_new != content:
        content = content_new
        changes.append('removed toggleTheme()')
    
    # 移除 function loadTheme(){...}
    content_new = re.sub(
        r'function\s+loadTheme\s*\(\)\s*\{[^}]*\}',
        '',
        content
    )
    if content_new != content:
        content = content_new
        changes.append('removed loadTheme()')
    
    # 移除 theme init IIFE
    content_new = remove_iife(content)
    if content_new != content:
        content = content_new
        changes.append('removed theme IIFE')
    
    # 移除 onclick="toggleTheme()"
    content_new = re.sub(r'\s+onclick="toggleTheme\(\)"', '', content)
    if content_new != content:
        content = content_new
        changes.append('removed toggleTheme onclick')
    
    # 移除 id="theme-toggle" 和 id="themeToggle"
    content_new = re.sub(r'\s+id="theme-toggle"', '', content)
    content_new = re.sub(r'\s+id="themeToggle"', '', content_new)
    if content_new != content:
        content = content_new
        changes.append('removed theme-toggle ids')
    
    # 移除 onload="loadTheme()"
    content_new = re.sub(r'\s+onload="loadTheme\(\)"', '', content)
    if content_new != content:
        content = content_new
    
    return content, changes


def find_brace_end(text, brace_start):
    """從 { 開始，找到配對的 }"""
    depth = 0
    i = brace_start
    while i < len(text):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def ensure_sidebar_refs(content, filepath):
    depth = get_depth(filepath)
    changes = []
    
    has_css = 'sidebar.css' in content
    has_js = 'sidebar.js' in content
    
    if has_css and has_js:
        return content, changes
    
    head_close = content.find('</head>')
    if head_close == -1:
        body_idx = content.find('<body')
        if body_idx == -1:
            return content, changes
        head_close = body_idx
    
    parts = []
    if not has_css:
        parts.append(f'<link rel="stylesheet" href="{depth}sidebar.css">')
        changes.append('+sidebar.css')
    if not has_js:
        parts.append(f'<script src="{depth}sidebar.js"></script>')
        changes.append('+sidebar.js')
    
    content = content[:head_close] + '\n'.join(parts) + '\n' + content[head_close:]
    return content, changes


def ensure_theme_vars(content):
    changes = []
    
    if '[data-theme="dark"]' in content or "[data-theme='dark']" in content:
        return content, changes
    
    style_match = re.search(r'<style[^>]*>', content)
    if style_match:
        pos = style_match.end()
        content = content[:pos] + UNIFIED_THEME_CSS + content[pos:]
        changes.append('+theme CSS vars')
    else:
        head_close = content.find('</head>')
        if head_close != -1:
            block = f'<style>{UNIFIED_THEME_CSS}</style>\n'
            content = content[:head_close] + block + content[head_close:]
            changes.append('+theme CSS vars (new block)')
    
    return content, changes


def ensure_theme_init_script(content):
    changes = []
    
    head_end = content.find('</head>')
    if head_end != -1:
        head_content = content[:head_end]
        if 'tsa-theme' in head_content:
            return content, changes
    else:
        return content, changes
    
    charset_match = re.search(r'<meta\s+charset=[^>]+>', content)
    if charset_match:
        pos = charset_match.end()
        content = content[:pos] + '\n' + THEME_INIT_SCRIPT + content[pos:]
        changes.append('+theme init script')
    else:
        content = content[:head_end] + THEME_INIT_SCRIPT + '\n' + content[head_end:]
        changes.append('+theme init script')
    
    return content, changes


def process_file(filepath, dry_run=False):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return filepath, [], f'Error: {e}'
    
    original = content
    all_changes = []
    
    content, ch = remove_topnav(content)
    all_changes.extend(ch)
    
    content, ch = remove_old_theme_js(content)
    all_changes.extend(ch)
    
    content, ch = ensure_sidebar_refs(content, filepath)
    all_changes.extend(ch)
    
    content, ch = ensure_theme_vars(content)
    all_changes.extend(ch)
    
    content, ch = ensure_theme_init_script(content)
    all_changes.extend(ch)
    
    if content == original:
        return filepath, [], 'skip'
    
    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return filepath, all_changes, 'OK' if not dry_run else 'DRY'


def main():
    dry_run = '--dry-run' in sys.argv
    os.chdir(DOCS_DIR)
    
    html_files = sorted(glob.glob('**/*.html', recursive=True))
    print(f'Files: {len(html_files)} | Mode: {"DRY" if dry_run else "EXECUTE"}')
    print('=' * 60)
    
    stats = {'total': len(html_files), 'changed': 0, 'unchanged': 0, 'errors': 0}
    log = []
    
    for fp in html_files:
        f, changes, status = process_file(fp, dry_run)
        if 'Error' in status:
            stats['errors'] += 1
            log.append(f'❌ {f}: {status}')
        elif changes:
            stats['changed'] += 1
            log.append(f'✅ {f}: {", ".join(changes)}')
        else:
            stats['unchanged'] += 1
    
    print(f'\nTotal:{stats["total"]} Changed:{stats["changed"]} Skip:{stats["unchanged"]} Err:{stats["errors"]}')
    
    if log:
        print(f'\nLog (first 30):')
        for line in log[:30]:
            print(f'  {line}')
        if len(log) > 30:
            print(f'  ... +{len(log) - 30} more')
    
    with open('migration_log.txt', 'w') as f:
        f.write(f'TSA Sidebar Migration\nMode: {"DRY" if dry_run else "EXECUTE"}\n')
        f.write(f'Total:{stats["total"]} Changed:{stats["changed"]} Skip:{stats["unchanged"]} Err:{stats["errors"]}\n\n')
        for line in log:
            f.write(line + '\n')
    
    return stats


if __name__ == '__main__':
    main()
