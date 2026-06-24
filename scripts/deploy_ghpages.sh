#!/bin/bash
# TSA GitHub Pages 部署腳本
# 將 main branch 的 docs/ 部署到 gh-pages branch root
# 用法: bash scripts/deploy_ghpages.sh

set -e

REPO_DIR="/home/alvin/.openclaw/workspace/trade_strategy_analyzer"
cd "$REPO_DIR"

echo "🏗️ TSA GitHub Pages 部署"
echo "========================"

# 1. 確認在 main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo "❌ 請先切到 main branch（當前: $CURRENT_BRANCH）"
  exit 1
fi

# 2. 確認 main 是最新的
echo "📋 當前 main HEAD: $(git rev-parse --short HEAD)"

# 3. 複製 docs/ 到臨時目錄
TMPDIR=$(mktemp -d)
echo "📂 複製 docs/ 內容..."
cp -r docs/* "$TMPDIR/"
cp docs/.nojekyll "$TMPDIR/" 2>/dev/null

FILES=$(find "$TMPDIR" -type f | wc -l)
echo "   $FILES 個檔案"

# 4. 切到 gh-pages
echo "🔄 切到 gh-pages branch..."
git checkout gh-pages 2>/dev/null || {
  echo "❌ gh-pages branch 不存在"
  rm -rf "$TMPDIR"
  exit 1
}

# 5. 清空 gh-pages root（保留 .git）
echo "🧹 清空 gh-pages root..."
find . -maxdepth 1 -not -name '.git' -not -name '.' -not -name '..' | xargs rm -rf

# 6. 複製新內容
echo "📥 複製新內容到 gh-pages root..."
cp -r "$TMPDIR/"* .
cp "$TMPDIR/.nojekyll" . 2>/dev/null

# 7. Commit + push
git add -A
COMMIT_MSG="🚀 Deploy from main:$(git rev-parse --short main) $(date '+%Y-%m-%d %H:%M')"
git commit -m "$COMMIT_MSG"
git push --force origin gh-pages

echo ""
echo "✅ 部署完成！"
echo "   https://alvin-forex.github.io/trade-strategy-analyzer/"
echo "   Commit: $COMMIT_MSG"

# 8. 切返 main
git checkout main
rm -rf "$TMPDIR"
