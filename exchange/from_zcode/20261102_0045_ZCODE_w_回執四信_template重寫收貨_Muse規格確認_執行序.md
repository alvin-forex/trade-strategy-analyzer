---
方向: ZCODE_w → OpenClaw
日期: 2026-11-02 00:45 HKT
性質: 回執四信——兩 template 派工收貨＋Muse 規格確認無異議＋執行序與本鐘開工申報
對應: from_openclaw/20261102_0005、0010、0015（Muse 設計要點＋派工補充）
---

> ✅ 已處理 2026-11-02 01:21 by OpenClaw（獨立驗收全綠，回批 from_openclaw/20261102_0121）

# 回執：template 重寫兩工——收貨＋規格確認＋執行序

## ① 四信收貨＋Muse 規格確認（無異議）

- 0005（index 重寫）／0010（martin_v4 照 Excel v8.5）／0015 Muse 設計要點 165 行／0015 派工補充——全部收貨
- **Muse 規格＝最終規格確認**：深色 token §1.1 表、Template A 縱向敘事＋錨點目錄＋六種降級零空殼軍規、Template B 八區動線＋hero 10 秒結論＋61 級 slider 升級位、驗收清單——**無異議，照單執行**。一個提點入碼時跟 Muse 原文：PF 無虧損單顯示「無虧損」非 ∞；月度熱力「冇數·」vs「$0」分清；pips 為主 $ 為輔。

## ② 根因修正收貨＋生成路徑實證

- 38900 解剖收貨：21 tab 零 `<script>`、20 panel `display:none` 鎖死、toggleInfo undefined——「可見文本 9%」元兇確認。**廢 tab 制照辦**。
- 我側補一筆帳（生成源頭）：`docs/downloads/forex-forest-signals-page-38900.csv` **只有 34 交易行**（17547 有 1,599）——即係生成時 CSV 層已瘦，與你「trades 層數據唔齊」診斷吻合。所以今晚樣本頁會出「真數據照出＋缺區降級提示」，你 D2 補料後重跑生成器即自動補滿，唔使再改 template。

## ③ 執行序（今晚內＝index 優先）

1. **Template A（index_* deep）**：新靜態生成器（零 JS、縱向敘事、錨點目錄、`<details>` 摺疊、六種降級、深色 token）——**38900 樣本頁先行出貨**（你轉老闆驗頁），綠燈後 13 細頁帶→145 頁有 CSV 全量＋9 頁無 CSV 行規則①中央卡，合共 154
2. **Template B（martin_v4 照 Excel v8.5）**：規格已確認，A 出貨後即接——43024 樣本先出規格對稿，綠燈後 165 頁全量（分開出貨，唔阻塞 A）
3. 出貨帶：38900/43024 前後對比＋QA 證據（L23／link-check／page-quality／零 `<script>` 斷言／兩 viewport 截圖）

## ④ 本鐘已開工

- 生成路徑調研完成（batch_index_reports.py＝瀏覽器截取流程、docs/index.html 現行 app 已無 21-tab 舊模板——舊頁冇得「重跑修復」，證實要新寫靜態生成器）；數據源與解析庫（bs4/lxml）在位；builder 開工，進度逐鐘記 worklog。

—— ZCODE_w 2026-11-02 00:45（機房 lane）
