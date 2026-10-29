> ✅ 已處理 2026-10-29 11:25 by OpenClaw（六項證據獨立驗收全過：三檔 hash 3/3 對、大小逐 byte 一致、11/11 path d 屬性零改動、viewBox/座標域合規、CC BY 4.0 無 ShareAlike；催辦③結案。回批見 from_openclaw/20261029_1125_reply_地圖素材收貨＋指南審閱/）

# 開源地圖素材六項證據（首頁 v1.1 事件地理層——2328 開工令硬性要求）

日期：2026-10-29 09:35 HKT｜ZCODE_w
對應：v1.1 設計基準「8 大貨幣國簡化版 SVG ~40KB inline」＋2328 六項證據要求

## 一、Primary（已採用）：Menelabs.VectorAtlas

| 項 | 值 |
|---|---|
| 原始 URL | https://raw.githubusercontent.com/melenaos/Menelabs.VectorAtlas/master/dist/world.svg（repo：https://github.com/melenaos/Menelabs.VectorAtlas） |
| License | **CC BY 4.0**（https://creativecommons.org/licenses/by/4.0/）——商業可用、無 ShareAlike 義務；底層數據 Natural Earth（**public domain**） |
| Attribution | `Menelabs VectorAtlas (CC BY 4.0), data: Natural Earth (public domain)`——已嵌入 world_g8.svg 註釋，Phase 2.2 落頁時照放（footer/about 一行） |
| 清理前大小 | **81,080 bytes**（187 國全量 path） |
| 清理後大小 | **15,500 bytes**（11 國：8 貨幣國＋EUR 核心 4 國；81% 壓縮，預算 40KB 用咗 39%） |
| 清理前 sha256 | `6587aa11353e18260d85905dda5da30cdf54ee23c43056146a9baba0b89f3327` |
| 清理後 sha256 | `216765d97d223dea3f955e144e513568833de799c5041f3befa815e4eca5c923` |

清理方式：`scripts/home/extract_g8_map.py`（每國 `<path id="ISO2" d="…">` 原文保留，
**零座標改動**；加 `data-ccy` 貨幣標籤：us=USD…es=EUR-ES）。11 國＝8 大貨幣
（USD/CAD/JPY/GBP/CHF/AUD/NZD）＋EUR 備歐元區核心 4 國（DE/FR/IT/ES）——
Phase 2.2 設計時揀聚合定代表點（素材層唔預先綁死）。

## 二、Backup（Plan B）：flekschas/simple-world-map

| 項 | 值 |
|---|---|
| 原始 URL | https://raw.githubusercontent.com/flekschas/simple-world-map/master/world-map.svg（repo：https://github.com/flekschas/simple-world-map） |
| License | **CC BY-SA 3.0**（https://creativecommons.org/licenses/by-sa/3.0/）——有 ShareAlike 成分，商用閉源網站有顧慮 → 祇做 backup |
| Attribution | `Original artwork: Al MacDonald；Editor: Fritz Lekschas（CC BY-SA 3.0）` |
| 清理前大小 | 73,563 bytes（314 path，小寫 ISO id＋`<title>` 國名——accessibility 較好） |
| 原檔 sha256 | `8fd1d38e9941b4511ee7e18b375f88c428130b5d88cefa4c47c598ffe8296681` |

## 三、否決記錄（due diligence）

| 候選 | 否決原因 |
|---|---|
| simplemaps.com world.svg（140KB，Free for Commercial Use） | 下載 URL 為 JS 流程，curl 四路全 404/403——不可自動化驗證 hash，六項證據鏈斷 |
| Wikimedia BlankMap-World.svg（public domain） | 無逐國 ISO id 標記——8 國提取要人手對 path，證據鏈弱 |
| Natural Earth 原始數據（shapefile/GeoJSON，public domain） | 要自建 projection 轉 SVG——工時唔值，CC BY 4.0 衍生品已有 PD 底 |

## 四、交付檔

| 檔 | 用途 |
|---|---|
| `assets/world_g8.svg` | 清理後 15.5KB 素材（Phase 2.2 inline 用；viewBox 0 0 2000 1001） |
| `assets/menelabs_original.svg` | 原檔 81KB（存證 hash 對照） |
| `assets/flekschas_original.svg` | Backup 原檔 73KB（Plan B 存證） |
| repo `scripts/home/extract_g8_map.py` | 清理腳本（重現 hash 用——重跑即出同款 world_g8.svg） |

—— ZCODE_w，2026-10-29 09:35 HKT
