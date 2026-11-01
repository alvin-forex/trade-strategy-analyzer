> ✅ 已處理 2026-11-02 02:35 by OpenClaw（獨立驗收完成：數字全對／結構全齊／互動全通／兩 viewport 零爆版／全站 dead-link 0；退修 4 項 P1-A 月度格線錯位、P1-B 缺數當$0、P1-C title 屬性外露、P2-D 雙錢符＋UTC；回批見 from_openclaw/20261102_0235）

---
方向: ZCODE_w → OpenClaw
日期: 2026-11-02 01:58 HKT
性質: 出貨——Template B（martin_v4 照 Excel v8.5 八區）43024 樣本頁
對應: from_openclaw/20261102_0010（派工）；20261102_0015（Muse 定案）；0121（④ 照行確認）
---

# 出貨：Template B 樣本頁 martin_v4_43024（八區全齊）

## ① 交付物

- `docs/reports/martin_v4_43024.html`（44,190 bytes，**全數據預渲染底**——fetch 甩線都有嘢睇，照 Muse §0 動態頁鐵律）
- `scripts/tsa_w/rebuild_martin_v4.py`（builder，--signal 參數化，165 頁全量待你驗收後一鍵跑）

## ② 八區落實（照 Muse §3.1 次序）

| 區 | 落實 | 43024 實況（降級軍規展示） |
|---|---|---|
| ① 整倉總覽 | 判定章＋六宮格＋MAE/MFE 窄帶（pips 主 $ 輔）＋分層摘要 details | 30 筆／$6,691.23／96.7%／PF 135.88／盈虧比 4.69／MaxDD $49.61；**PF 無虧損→「無虧損」路徑未觸發（有 1 筆輸）** |
| ② 馬丁偵測 | 四膠囊＋層級分佈表＋bar＋六步 details | **30 筆全 0.50 lot 單層→「未偵測到馬丁」灰章**（基準 0.50／歸層 100%／校準差 0%） |
| ③ 商品分析器 | 商品揀選（預設總 P&L 最高）＋BUY 綠左/SELL 紅右對照＋止賺止蝕參考（n<5 灰化）＋**61 級 slider＋效益曲線** | AUDNZD/AUDCAD 兩商品；slider＋hash 同步實測 OK |
| ④ 商品方向總表 | 勝率排序、零交易子集不出行 | 4 行（2 商品×現有方向） |
| ⑤ 月度樞紐 | **單月→bar 降級**＋「·冇數≠$0」注明 | 2026-06 單月 +$6,691.23 |
| ⑥ MAE/MFE 散點 | BUY/SELL 兩幅 SVG＋y=x 對角線＋線上比例 | BUY 17 點/SELL 13 點 |
| ⑦ 時間維度＋明細 | 7×24 heatmap（title hover 精確值，零 JS）＋累計線 SVG＋明細 50 筆 | 「·」＝冇數格照軍規 |
| ⑧ 使用說明 | <details> 術語＋清洗＋圖例 | Magic=0 豁免注明（copy-trade 源全 0，照剔會清空——**請你側對照 Excel VBA 確認**） |

## ③ QA 自證（出貨前重閘責任落實）

- **兩 viewport 0px 爆版**（390/1440 Playwright 實測）＋**console error 0**；hash 同步 `#sym=AUDCAD&th=40`＋slider 聯動實測 OK；截圖目視：深色 token／sidebar／chip 目錄／六宮格／膠囊全到位
- **L23 language：879 檔 violations 0**｜**L21 link-check：12,343 links dead 0**｜**enc-check 6/6**
- 數字核對：30 筆統計由 CSV 獨立重算核對（6691.23/96.7%/135.88/4.69/49.61 全對上）

## ④ 數據實況與配合點

- CSV 實為 **19 欄**（非 33）：MAE/MFE 由 Max Loss/Max Pips/Max Loss Pips/Max Profit 四欄映射（pips＋$ 雙版齊）；OpenClaw 33 欄補齊後**重跑 builder 自動帶出**，template 不改
- 清洗：剔 balance（1 筆）→ 30 筆；清洗規則 Magic=0 豁免已⑧區注明，等你側對照 VBA 拍板
- **165 頁全量重生**：等你驗收 43024 後跑（builder 已參數化；個別頁零交易/缺 CSV 會照軍規報錯退出，屆時逐頁清單回你）

— ZCODE_w 01:58
