#!/usr/bin/env python3
"""
TSA 系統框架統一腳本
===================
目標：移除頂部導航（topnav），統一使用左側 Sidebar + Theme Toggle

功能：
1. 移除 topnav HTML 區塊
2. 移除內聯的 topnav CSS
3. 移除獨立的 theme-toggle 按鈕（sidebar 已內建）
4. 確保注入 sidebar.css + sidebar.js
5. 統一 CSS 變數（光暗主題）

作者：TSA Subagent
日期：2026-06-24
"""

import os
import re
import sys
from pathlib import Path
from typing import Tuple, List

# === 配置 ===
DRY_RUN = False  # 設為 True 可預覽變更而不寫入
VERBOSE = True   # 顯示詳細輸出

# docs 目錄路徑
SCRIPT_DIR = Path(__file__).parent
DOCS_DIR = SCRIPT_DIR.parent / "docs"

# 統計計數器
stats = {
    "total_files": 0,
    "modified_files": 0,
    "removed_topnav": 0,
    "removed_theme_toggle": 0,
    "injected_sidebar": 0,
    "errors": 0
}


def log(msg: str, level: str = "INFO"):
    """日誌輸出"""
    if VERBOSE or level == "ERROR":
        prefix = {"INFO": "✅", "WARN": "⚠️", "ERROR": "❌", "MODIFY": "📝"}
        print(f"{prefix.get(level, '•')} {msg}")


def remove_topnav_html(content: str) -> Tuple[str, bool]:
    """
    移除 topnav HTML 區塊
    
    匹配模式：
    <div class="topnav">...</div>
    <nav class="topnav">...</nav>
    """
    modified = False
    
    # 模式 1: <div class="topnav">...</div>（多行）
    pattern1 = r'<div\s+class=["\']topnav["\'][^>]*>.*?</div>'
    if re.search(pattern1, content, re.DOTALL | re.IGNORECASE):
        content = re.sub(pattern1, '', content, flags=re.DOTALL | re.IGNORECASE)
        modified = True
        stats["removed_topnav"] += 1
    
    # 模式 2: <nav class="topnav">...</nav>
    pattern2 = r'<nav\s+class=["\']topnav["\'][^>]*>.*?</nav>'
    if re.search(pattern2, content, re.DOTALL | re.IGNORECASE):
        content = re.sub(pattern2, '', content, flags=re.DOTALL | re.IGNORECASE)
        modified = True
        stats["removed_topnav"] += 1
    
    # 模式 3: id="topnav" 或 id='topnav'
    pattern3 = r'<[^>]+id=["\']topnav["\'][^>]*>.*?</(?:div|nav)>'
    if re.search(pattern3, content, re.DOTALL | re.IGNORECASE):
        content = re.sub(pattern3, '', content, flags=re.DOTALL | re.IGNORECASE)
        modified = True
        stats["removed_topnav"] += 1
    
    return content, modified


def remove_topnav_css(content: str) -> Tuple[str, bool]:
    """
    移除內聯的 topnav 相關 CSS
    
    注意：只移除 topnav 相關樣式，保留其他樣式
    """
    modified = False
    
    # 移除 .topnav{...} 區塊
    patterns = [
        r'\.topnav\s*\{[^}]*\}',  # .topnav{...}
        r'\.topnav-logo\s*\{[^}]*\}',  # .topnav-logo{...}
        r'\.topnav-links\s*\{[^}]*\}',  # .topnav-links{...}
        r'\.topnav-link\s*\{[^}]*\}',  # .topnav-link{...}
        r'\.topnav-link\.active\s*\{[^}]*\}',  # .topnav-link.active{...}
        r'\.topnav-link:hover\s*\{[^}]*\}',  # .topnav-link:hover{...}
    ]
    
    for pattern in patterns:
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, '', content, flags=re.DOTALL)
            modified = True
    
    return content, modified


def remove_standalone_theme_toggle(content: str) -> Tuple[str, bool]:
    """
    移除獨立的 theme-toggle 按鈕（sidebar 已內建）
    
    匹配：
    <button class="theme-toggle" ...>
    <button id="theme-toggle" ...>
    """
    modified = False
    
    # 模式 1: <button class="theme-toggle">...</button>
    pattern1 = r'<button[^>]*class=["\'][^"\']*theme-toggle[^"\']*["\'][^>]*>.*?</button>'
    if re.search(pattern1, content, re.DOTALL | re.IGNORECASE):
        content = re.sub(pattern1, '', content, flags=re.DOTALL | re.IGNORECASE)
        modified = True
        stats["removed_theme_toggle"] += 1
    
    # 模式 2: <button id="theme-toggle">...</button>
    pattern2 = r'<button[^>]*id=["\']theme-toggle["\'][^>]*>.*?</button>'
    if re.search(pattern2, content, re.DOTALL | re.IGNORECASE):
        content = re.sub(pattern2, '', content, flags=re.DOTALL | re.IGNORECASE)
        modified = True
        stats["removed_theme_toggle"] += 1
    
    return content, modified


def remove_inline_theme_script(content: str) -> Tuple[str, bool]:
    """
    移除內聯的主題切換腳本（sidebar.js 已包含）
    
    匹配：
    <script>...toggleTheme()...</script>
    """
    modified = False
    
    # 匹配包含 toggleTheme 的內聯腳本
    pattern = r'<script>\s*\(function\(\)\{[^}]*tsa-theme[^}]*\}[^)]*\)\s*\);?\s*function\s+toggleTheme\(\)[^}]*\}[^<]*</script>'
    if re.search(pattern, content, re.DOTALL | re.IGNORECASE):
        content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
        modified = True
    
    return content, modified


def inject_sidebar_assets(content: str, file_path: Path) -> Tuple[str, bool]:
    """
    確保注入 sidebar.css 和 sidebar.js
    
    計算相對路徑深度
    """
    modified = False
    
    # 計算相對路徑
    rel_path = file_path.relative_to(DOCS_DIR)
    depth = len(rel_path.parts) - 1  # -1 因為檔案本身不算
    
    if depth == 0:
        css_path = "./sidebar.css"
        js_path = "./sidebar.js"
    elif depth == 1:
        css_path = "../sidebar.css"
        js_path = "../sidebar.js"
    elif depth == 2:
        css_path = "../../sidebar.css"
        js_path = "../../sidebar.js"
    else:
        css_path = "../" * depth + "sidebar.css"
        js_path = "../" * depth + "sidebar.js"
    
    # 檢查是否已有 sidebar.css
    has_sidebar_css = bool(re.search(r'href=["\'][^"\']*sidebar\.css["\']', content, re.IGNORECASE))
    
    # 檢查是否已有 sidebar.js
    has_sidebar_js = bool(re.search(r'src=["\'][^"\']*sidebar\.js["\']', content, re.IGNORECASE))
    
    # 注入 sidebar.css（在 </head> 前）
    if not has_sidebar_css:
        css_link = f'<link rel="stylesheet" href="{css_path}">\n'
        if '</head>' in content:
            content = content.replace('</head>', f'{css_link}</head>')
            modified = True
            log(f"  注入 sidebar.css: {css_path}")
    
    # 注入 sidebar.js（在 </body> 前）
    if not has_sidebar_js:
        js_script = f'<script src="{js_path}"></script>\n'
        if '</body>' in content:
            content = content.replace('</body>', f'{js_script}</body>')
            modified = True
            log(f"  注入 sidebar.js: {js_path}")
            stats["injected_sidebar"] += 1
    
    return content, modified


def clean_empty_lines(content: str) -> str:
    """清理過多的空行（超過 2 個連續空行）"""
    return re.sub(r'\n{3,}', '\n\n', content)


def process_file(file_path: Path) -> bool:
    """
    處理單個 HTML 檔案
    
    Returns:
        bool: 是否有修改
    """
    stats["total_files"] += 1
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        any_modified = False
        
        # Step 1: 移除 topnav HTML
        content, modified = remove_topnav_html(content)
        if modified:
            any_modified = True
            log(f"  移除 topnav HTML")
        
        # Step 2: 移除 topnav CSS
        content, modified = remove_topnav_css(content)
        if modified:
            any_modified = True
            log(f"  移除 topnav CSS")
        
        # Step 3: 移除獨立 theme-toggle 按鈕
        content, modified = remove_standalone_theme_toggle(content)
        if modified:
            any_modified = True
            log(f"  移除 theme-toggle 按鈕")
        
        # Step 4: 移除內聯主題腳本
        content, modified = remove_inline_theme_script(content)
        if modified:
            any_modified = True
            log(f"  移除內聯主題腳本")
        
        # Step 5: 注入 sidebar.css 和 sidebar.js
        content, modified = inject_sidebar_assets(content, file_path)
        if modified:
            any_modified = True
        
        # Step 6: 清理空行
        content = clean_empty_lines(content)
        
        # 寫入檔案
        if any_modified and content != original_content:
            if DRY_RUN:
                log(f"[DRY RUN] 會修改: {file_path.name}", "WARN")
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                log(f"已修改: {file_path.name}", "MODIFY")
            stats["modified_files"] += 1
            return True
        
        return False
        
    except Exception as e:
        log(f"處理失敗 {file_path}: {e}", "ERROR")
        stats["errors"] += 1
        return False


def main():
    """主程式"""
    print("=" * 60)
    print("🦀 TSA 系統框架統一腳本")
    print("=" * 60)
    print(f"目標目錄: {DOCS_DIR}")
    print(f"模式: {'預覽模式（不寫入）' if DRY_RUN else '正式模式（會修改檔案）'}")
    print("=" * 60)
    
    if not DOCS_DIR.exists():
        log(f"目錄不存在: {DOCS_DIR}", "ERROR")
        sys.exit(1)
    
    # 找出所有 HTML 檔案
    html_files = list(DOCS_DIR.rglob("*.html"))
    log(f"找到 {len(html_files)} 個 HTML 檔案")
    
    # 處理每個檔案
    for i, file_path in enumerate(html_files, 1):
        rel_path = file_path.relative_to(DOCS_DIR)
        if VERBOSE:
            print(f"\n[{i}/{len(html_files)}] 處理: {rel_path}")
        process_file(file_path)
    
    # 輸出統計
    print("\n" + "=" * 60)
    print("📊 處理統計")
    print("=" * 60)
    print(f"總檔案數: {stats['total_files']}")
    print(f"已修改檔案: {stats['modified_files']}")
    print(f"移除 topnav: {stats['removed_topnav']}")
    print(f"移除 theme-toggle: {stats['removed_theme_toggle']}")
    print(f"注入 sidebar: {stats['injected_sidebar']}")
    print(f"錯誤: {stats['errors']}")
    print("=" * 60)
    
    if DRY_RUN:
        print("\n⚠️ 這是預覽模式，未實際修改檔案")
        print("要執行正式修改，請設定 DRY_RUN = False")
    
    print("\n✅ 完成！")


if __name__ == "__main__":
    # 可通過命令行參數控制
    if len(sys.argv) > 1:
        if sys.argv[1] == "--dry-run":
            DRY_RUN = True
        elif sys.argv[1] == "--verbose":
            VERBOSE = True
    
    main()
