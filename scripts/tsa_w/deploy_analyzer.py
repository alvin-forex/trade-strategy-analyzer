#!/usr/bin/env python3
"""deploy_analyzer.py — Phase 1 (TSA 新首頁 v1.1 1.2)

把 repo 根目錄嘅原版策略分析器（index.html, 288KB 單檔 client-side app，
未被 Pages 部署過）部署為 docs/analyzer.html，只做兩件事：
  1. 位元組原樣複製（零改動 app 本體——鐵律「原封」）
  2. 喺最後一個 </script> 前注入一段 postMessage 接收器（~16 行），
     令新首頁上載 drawer 揀好嘅 File 物件可以直接交接入 app 自己嘅
     csvFile/setFiles/csv2File 狀態（ids/邏輯全部沿用 app 原有：
     refreshUploadUI() 處理 UI 更新）。

接收器獨立 try/catch，唔影響 app 原行為； standalone 打開時零副作用。
"""
from pathlib import Path

REPO = Path("/home/z/my-project/exchange-repo")
SRC = REPO / "index.html"
DST = REPO / "docs" / "analyzer.html"

RECEIVER = """
// === TSA 新首頁 Phase 1 上載交接（2026-10-30 加入，app 本體零改動） ===
// 接收新首頁上載 drawer postMessage 過嚟嘅 File 物件，載入本頁原有上載狀態。
window.addEventListener('message', function (e) {
  var d = e && e.data;
  if (!d || d.type !== 'tsa-analyzer-files') return;
  try {
    if (d.csv) csvFile = d.csv;
    if (Array.isArray(d.sets)) setFiles.push.apply(setFiles, d.sets);
    if (d.csv2) csv2File = d.csv2;
    window._csv2Text = null; window._csv2Label = '';
    refreshUploadUI();
    var card = document.getElementById('uploadCard');
    if (card) card.scrollIntoView({ block: 'start', behavior: 'auto' });
  } catch (err) { console.error('[analyzer] 上載交接失敗:', err); }
});
"""

src = SRC.read_text(encoding="utf-8")
assert "csvZone" in src and "function analyze()" in src, "源檔唔似原版分析器"

# 注入點：全檔最後一個 </script>（app 單一 script 區塊結尾）
idx = src.rfind("</script>")
assert idx > 0, "搵唔到 </script>"
out = src[:idx] + RECEIVER + src[idx:]

DST.write_text(out, encoding="utf-8")
print(f"analyzer deployed: {DST} ({len(out.encode('utf-8'))} bytes; receiver {len(RECEIVER)} chars injected)")
print("原封核對：app 本體 = 源檔前綴", idx, "chars →", DST, "前", idx, "chars same:",
      out[:idx] == src[:idx])
