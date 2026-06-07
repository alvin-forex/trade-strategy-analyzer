#!/usr/bin/env python3
"""
Sidebar QA Gate — 验证所有 HTML 文件是否包含 sidebar 引用
防止 sidebar 消失问题再次发生
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / 'docs'

# 需要检查 sidebar 的 HTML 文件列表
HTML_FILES = [
    'admin/signal_ranking.html',
    'admin/ccy_ranking.html',
    'admin/symbol_ranking.html',
    'index.html',
]

def check_sidebar(html_path: Path) -> tuple[bool, str]:
    """检查 HTML 文件是否包含 sidebar.css 和 sidebar.js"""
    if not html_path.exists():
        return False, f"❌ 文件不存在: {html_path}"
    
    content = html_path.read_text()
    
    # 检查 sidebar.css
    if 'sidebar.css' not in content:
        return False, f"❌ 缺少 sidebar.css: {html_path}"
    
    # 检查 sidebar.js
    if 'sidebar.js' not in content:
        return False, f"❌ 缺少 sidebar.js: {html_path}"
    
    return True, f"✅ OK: {html_path}"

def main():
    """主函数：检查所有文件，返回结果"""
    errors = []
    for file in HTML_FILES:
        html_path = DOCS_DIR / file
        ok, msg = check_sidebar(html_path)
        print(msg)
        if not ok:
            errors.append(msg)
    
    if errors:
        print("\n" + "="*50)
        print("🚨 Sidebar QA Gate FAILED")
        print("="*50)
        for err in errors:
            print(err)
        sys.exit(1)
    else:
        print("\n" + "="*50)
        print("✅ Sidebar QA Gate PASSED")
        print("="*50)
        sys.exit(0)

if __name__ == '__main__':
    main()