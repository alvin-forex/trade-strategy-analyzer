---
方向: AUTOCLAW → OpenClaw（PM lane）
日期: 2026-11-27 10:45
性質: [AC] TSA 全站 404 巡修 — 報告（根因、修復、證據）
卡: #24
---

# [AC] TSA 全站 404 巡修報告

## 一、掃描（機器實測）

| 項 | 數字 |
|---|---|
| docs/ 內 HTML 頁 | **746** |
| HTTP HEAD 全部 200 | **746（100%）** |
| 抽出唯一內部連結 | 315 |
| 非 200 連結 | 3（全部係 JS 樣板字串 `${...}` 假命中，非真壞連結） |

即：**檔案層面完全冇 404**。

## 二、真根因（老闆見到的 404）

側邊導航由 `docs/sidebar.js` 執行期注入，計算相對深度時把 GitHub Pages 專案名前綴都算一層：

```
舊：/trade-strategy-analyzer/tha/v52.html
    path.split('/').length - 2 = 2  →  depth = '../../'
    產生 ../../index.html  →  https://alvin-forex.github.io/index.html  → 404（走出站外）
```

影響：**所有子目錄頁**（admin／tha／ccy_power／reports／reviews／data／portfolios…）的側欄每一條連結都指向站外 → 全部 404。純 HTML 掃描見不到，因為連結是 JS 生成。

## 三、修復

`docs/sidebar.js` 改為先剝掉 `/trade-strategy-analyzer/` 前綴，再按剩餘目錄層數計 depth：

| 頁面 | 新 depth | 解析後連結 | 實測 |
|---|---|---|---|
| index.html | '' | /trade-strategy-analyzer/index.html | **200** |
| tha/v52.html | '../' | /trade-strategy-analyzer/index.html | **200** |
| admin/index.html | '../' | 同上 | **200** |
| ccy_power/index.html | '../' | 同上 | **200** |
| reviews/monthly/xxx.html | '../../' | 同上 | **200** |

舊錯誤目標（github.io/index.html、github.io/tha/index.html）實測 **404**，證實機制。

## 四、未完成

1. **Vercel 私有站部署**（`20261126_0410`，原死線 11-26 12:00）：CLI 已具備（67.0.0），**等老闆授權登入**。
2. **修復後全站 JS 導航實測**：因瀏覽器自動化今晚不可用，已改用「模擬 depth 公式 + URL 解析 + HEAD」代替（結果如上）；待瀏覽器可用時補一次真人點擊驗證。

## 五、紀律檢討（我認）

兩項過期未做（404 巡修 11-26 18:00、Vercel 11-26 12:00）。原因：被 THA 與 MT4 真值佔用、無過期卡自查、誤把「等授權」當「未開始」。
已加：每次開工先掃本 lane 卡的死線；晚間自報「過期未做」清單。

— AUTOCLAW 2026-11-27 10:45
