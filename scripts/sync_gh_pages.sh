#!/bin/bash
# ============================================================
# sync_gh_pages.sh — 將 main branch 嘅部署檔案同步到 gh-pages
# 用法：bash scripts/sync_gh_pages.sh [--commit-only | --push]
#   --commit-only : 只 commit 唔 push
#   --push        : commit + push（預設）
#   無參數         : commit + push
# ============================================================

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BRANCH=$(git -C "$REPO_DIR" branch --show-current)

echo "============================================================"
echo "🔄 sync_gh_pages.sh — main → gh-pages"
echo "============================================================"
echo "Repo: $REPO_DIR"
echo "Current branch: $BRANCH"
echo ""

# 確保喺 main branch
if [ "$BRANCH" != "main" ]; then
    echo "❌ 必須在 main branch 執行。當前: $BRANCH"
    exit 1
fi

# 確保 working tree 乾淨
if ! git -C "$REPO_DIR" diff --quiet 2>/dev/null; then
    echo "⚠️ Working tree 有未 commit 嘅改動，先 stash..."
    git -C "$REPO_DIR" stash push -m "auto-stash before sync_gh_pages"
    STASHED=1
fi

# 記錄 main 嘅 commit hash
MAIN_HASH=$(git -C "$REPO_DIR" rev-parse --short HEAD)
echo "📦 main branch: $MAIN_HASH"

# 切到 gh-pages
echo "🔀 切換到 gh-pages..."
git -C "$REPO_DIR" checkout gh-pages

# 清理 gh-pages 上需要同步嘅目錄（保留 .git）
echo "🧹 清理 gh-pages 舊檔案..."
# 刪除要同步嘅檔案（保留 CNAME 等特殊檔案）
git -C "$REPO_DIR" ls-files | grep -E "^(signal_ranking|index\.html|ccy_timeframe|dashboard|detailed_comparison)" | while read f; do
    rm -f "$REPO_DIR/$f"
done
# 清理 output/, reports/, docs/
rm -rf "$REPO_DIR/output"
rm -rf "$REPO_DIR/reports"
rm -rf "$REPO_DIR/docs/index.html"
rm -rf "$REPO_DIR/docs/dashboard.html"
rm -rf "$REPO_DIR/docs/martin_autopsy_v3_14581.html"
rm -rf "$REPO_DIR/docs/merged_report_11141.html"
rm -rf "$REPO_DIR/docs/reports"
rm -rf "$REPO_DIR/docs/admin"
rm -rf "$REPO_DIR/docs/data"
rm -rf "$REPO_DIR/__pycache__"
rm -rf "$REPO_DIR/scripts"
rm -rf "$REPO_DIR/secrets"
rm -rf "$REPO_DIR/src"
rm -rf "$REPO_DIR/ea_manuals"

echo "📋 複製 main 嘅檔案..."

# 從 git tree (main) 取得檔案，避免 working tree 問題
# 方法：用 git show main:file > file

# 1. Root HTML files
for f in index.html signal_ranking_dde_v4.html ccy_timeframe_volatility.html dashboard.html; do
    if git -C "$REPO_DIR" show "main:$f" > /dev/null 2>&1; then
        git -C "$REPO_DIR" show "main:$f" > "$REPO_DIR/$f"
        echo "  ✅ $f"
    fi
done

# 2. output/ directory (reports + JSON)
echo "  📁 output/"
mkdir -p "$REPO_DIR/output"
for f in $(git -C "$REPO_DIR" ls-tree -r --name-only main -- output/ | grep -E "\.(html|json)$"); do
    git -C "$REPO_DIR" show "main:$f" > "$REPO_DIR/$f"
done
OUT_COUNT=$(ls "$REPO_DIR/output/"*.html 2>/dev/null | wc -l)
echo "    ✅ $OUT_COUNT HTML + JSON files"

# 3. reports/ directory
echo "  📁 reports/"
mkdir -p "$REPO_DIR/reports"
for f in $(git -C "$REPO_DIR" ls-tree -r --name-only main -- reports/ | grep -E "\.(html|json)$"); do
    git -C "$REPO_DIR" show "main:$f" > "$REPO_DIR/$f"
done
RPT_COUNT=$(ls "$REPO_DIR/reports/"*.html 2>/dev/null | wc -l)
echo "    ✅ $RPT_COUNT HTML files"

# 4. docs/ directory (index + dashboard + data)
echo "  📁 docs/"
mkdir -p "$REPO_DIR/docs"
for f in $(git -C "$REPO_DIR" ls-tree -r --name-only main -- docs/ | grep -E "\.(html|json|js|css)$"); do
    mkdir -p "$REPO_DIR/$(dirname "$f")"
    git -C "$REPO_DIR" show "main:$f" > "$REPO_DIR/$f"
done
DOCS_COUNT=$(find "$REPO_DIR/docs" -name "*.html" 2>/dev/null | wc -l)
echo "    ✅ $DOCS_COUNT HTML files in docs/"

# 5. sidebar assets (if exist)
for f in sidebar.css sidebar.js; do
    if git -C "$REPO_DIR" show "main:docs/$f" > /dev/null 2>&1; then
        git -C "$REPO_DIR" show "main:docs/$f" > "$REPO_DIR/docs/$f"
        echo "  ✅ docs/$f"
    fi
done

echo ""
echo "📊 同步統計："
echo "  Root HTML: $(ls "$REPO_DIR"/*.html 2>/dev/null | wc -l)"
echo "  output/: $(ls "$REPO_DIR/output/"*.html 2>/dev/null | wc -l) HTML"
echo "  reports/: $(ls "$REPO_DIR/reports/"*.html 2>/dev/null | wc -l) HTML"
echo "  docs/: $(find "$REPO_DIR/docs" -name "*.html" 2>/dev/null | wc -l) HTML"

# Git add & commit
echo ""
echo "📝 Git commit..."
git -C "$REPO_DIR" add -A
git -C "$REPO_DIR" status --short | head -20

CHANGED=$(git -C "$REPO_DIR" diff --cached --stat | wc -l)
if [ "$CHANGED" -eq 0 ]; then
    echo "✅ 沒有變動，不需要 commit"
else
    COMMIT_MSG="🔄 sync from main ($MAIN_HASH) — $(date '+%Y-%m-%d %H:%M')"
    git -C "$REPO_DIR" commit -m "$COMMIT_MSG"
    echo "✅ Committed: $COMMIT_MSG"
fi

# Push or not
PUSH=1
if [ "$1" = "--commit-only" ]; then
    PUSH=0
fi

if [ "$PUSH" = "1" ]; then
    echo "🚀 Pushing to origin gh-pages..."
    git -C "$REPO_DIR" push origin gh-pages
    echo "✅ Pushed!"
else
    echo "⏸️ --commit-only 模式，未 push。確認後手動執行："
    echo "   git push origin gh-pages"
fi

# 切回 main
echo "🔀 切換回 main..."
git -C "$REPO_DIR" checkout main

# Restore stash if any
if [ "$STASHED" = "1" ]; then
    echo "📦 恢復 stash..."
    git -C "$REPO_DIR" stash pop
fi

echo ""
echo "============================================================"
echo "✅ Sync 完成！"
if [ "$PUSH" = "1" ]; then
    echo "🌐 https://alvin-forex.github.io/trade-strategy-analyzer/"
fi
echo "============================================================"
