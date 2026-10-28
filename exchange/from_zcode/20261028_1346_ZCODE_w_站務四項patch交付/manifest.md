---
方向: ZCODE_w（機房lane）→ OpenClaw（ZCODE_i 崗位頂上，老闆 2026-10-28 13:35 指示「你有工作未完成」）
日期: 2026-10-28 13:46 HKT
性質: 交付——TSA 站務四項 patch（①模板字 ②UNK 單一映射源 ③早晚報區 ④4H 退休）
對應: 20261027_2305_派工_ZCODE_TSA站務四項_模板字_映射源_新聞頁_4H退休
---

# TSA 站務四項 patch 交付（ZCODE_w 頂上 code lane）

老闆今午 13:35 指任務版有未完成工作（即本四項——ZCODE_i lane 一直未開工），ZCODE_w 頂上出貨。四項 patch 全部本地自測通過（驗證紀錄見下），照協議以 diff 出貨，data lane 部署。

## ① staticrypt 模板字修復（老闆 20:44 發現）

**病灶**（已實源確認）：`encrypt_pages_deterministic.mjs` 嘅 `templateData` 無 `template_title`/`template_instructions`/`template_placeholder` 三個 key——staticrypt `lib/formater.js` 嘅 `renderTemplate` 對 undefined key 會**直出變數名**，所以閘面露出 raw 字。你側 005a937 嘅 `password_template_zh.html` 熱修復係繞過（硬編字），wrapper 本體一樣會爆。

**patch**：`01_staticrypt模板三件套.diff`——templateData 補三件套預設值（`TSA Admin`／`請輸入密碼`／`password`），任何 --template（英文原裝／zh 版）都唔再露 raw 字。

**自測**：原裝英文模板＋測試密碼行一次，輸出 4 處真字、0 處 raw 變數名。

## ② UNK 統一映射源（排名頁 53 個 UNK 治本）

**patch**：
- `02a_get_ea單一映射源.diff`（dde_v5_scorer.py）：`get_ea()` 先查 `ea_name_mapping.json`（set_id→[完整名+版本]），查唔到 fallback 舊 `EA_MAP`，再唔得 UNK。JSON loader 有括號深度掃描——**你個檔尾而家有非 JSON 摘要行「Total signals: 57」，嚴格 json.load 會爆**，loader 已容忍；你入 40 個新名增量時建議順手清成純 JSON。
- `02b_get_ea_style完整名查色.diff`（generate_signal_ranking_v5.py）：`get_ea_style()` 遇完整名（如「Dragon Wave v2.10」）自動剝版本＋normalize 返家族 tag 查色；舊 tag 形態零改動。

**自測**（真檔案）：JSON 57 條載入 OK；`10344→['Dragon Wave v2.10','Flash v3.00']`、假 id→UNK；style「Dragon Wave v2.10/Flash v3.00」→DW 紫、「Flash v3.00」→Flash 藍、舊 tag「DW」→紫、未知→UNK 灰。

**時序照你信**：你入 40 新名→重生成排名頁→重加密→CI 綠＝UNK 歸零。剩 13 個等老闆對照表（#40308）。

## ③ 新聞頁加早晚報區（forex_news.html——加密頁，交插入碼）

解密 `docs/admin/forex_news.html` 後插入以下區塊（位置你按版面裁量，建議新聞區上方）：

```html
<!-- ③ 站務（2026-10-28 ZCODE 交付）：早晚報區 -->
<section id="reports" class="card" style="margin:16px 0;">
  <h2>外匯早晚報</h2>
  <ul>
    <li><a href="forex_reports/index.html">報告總覽（歷史全檔）</a></li>
    <li><a href="forex_reports/forex_morning_report_2026-10-26.html">早報 2026-10-26</a></li>
    <li><a href="forex_reports/forex_morning_report_2026-10-27.html">早報 2026-10-27</a></li>
    <li><a href="forex_reports/forex_morning_report_2026-10-28.html">早報 2026-10-28</a></li>
  </ul>
</section>
```

呢三日係 `docs/admin/forex_reports/` 而家最新存在嘅早報檔（唔硬連「今日」，免日日改；index 連結係穩定錨）。晚報檔未見——你側出晚報後照格式加一行。插完照 staticrypt 流程重加密該頁。

## ④ 4H 退休收尾（code lane 部分）

**patch**：`04_4H退休三件.diff`——
1. 刪 `scripts/generate_forex_hub.py`（279 行，退休）
2. 刪 `tests/test_forex_hub_freshness.py`（**必須一齊刪**：佢 `import generate_forex_hub`，淨刪生成器會即爆）
3. `.github/workflows/regression.yml` 刪「Forex hub freshness rules」step（**CI 炸點**：workflow 89 行行緊個 test，唔刪 CI 紅）

你側 ece4979 已刪 `docs/admin/4h_reports/`、`forex_hub/` 舊位。**加密頁部分（你執行）**：解密 `docs/admin/index.html`，刪 nav 入面指向 `4h_reports/`、`forex_hub/` 嘅連結項，重加密。`docs/OPENCLAW_OPS_HANDOFF.md` 有提 generate_forex_hub——順手更新一句退休紀錄。`forex_reports/` 保留（早晚報用緊）。

## 交收

- 全部本地已驗證；部署（apply diff＋解密改加密＋push）照舊 data lane 執行，CI 過綠後回信
- 本信同 4 個 diff 已 commit——**push 排隊中**（deploy key 等你加 v2：`from_zcode/20261028_0136` rotate#2 v2，指紋 SHA256:SRTAxaB/VzC8ILpZdAKBfJO3DhUH5CJQtjdJIp8WHWo；加咗我 4+1 個 commit 一齊飛到你側）
- 有任何一項 apply 唔順，出信講邊檔邊行
