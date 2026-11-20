# 開發藍圖（系統／工具應用與改善）

> 版本：2026-11-20｜作者：AUTOCLAW（AC lane）｜狀態：草案，待老闆與 OC 拍板
> 配套：`docs/admin/WORK_PLAN.md`（卡與依賴）、`docs/admin/AI_WORK_RULES.md`（協作規則）

## 一、資產盤點（現有系統／工具，實測狀態）

| # | 資產 | 現況 | 可用性 | 主要風險 |
|---|---|---|---|---|
| A1 | **CCY Power 原版指標**（FF，4 input） | 面板正常、Data Window 10 條 buffer 有值 | 可作 ground truth | 數值不在文字層；要靠 iCustom／截圖 |
| A2 | **PowerHistory 樣本** 50 檔（D1/H1/H4/M15/M30，106MB） | 解碼 100% 通過（D1_8 末筆九值全中）；96.96% 值為 k/7 或 k/8 | **即刻可用**（離線） | 只到 2026-05-26；貨幣碼順序兩批不同 |
| A3 | **MT4 本機數據** 33 個 D1 hst＋28 個 H1 hst（Alpari） | 解析器已驗證（148B header／60B record） | 可即時補數據 | XAU 五對冇 H1；斷線會停更 |
| A4 | **TierB probe**（ZCODE） | 0/9；文字讀法與 bitmap 面板不匹配 | 只提供 bars 部分 | 需改 iCustom 或轉截圖 |
| A5 | **martin_v4 報告頁** ×165 | 生成器可重跑；AC 審查發現 5 個實錯 | 頁面可睇，數值未可信 | base lot／倍數／歸層／理論 lot 全錯向 |
| A6 | **TradingHistory v8.5 Excel** | 演算法權威（LotTiers I3–I7） | 可作 golden fixture | 版本與網頁／白皮書不一致（v3.1 vs v3.5） |
| A7 | **TSA 網站** 900+ 頁（Pages） | 正常出街；sidebar 未統一（#20 逾期） | 可作對外門面 | 模板兩套風格不一（#28） |
| A8 | **EA／Risk Analyzer 需求書** | REQUIREMENT v0.1／v1.1 已入庫 | 可開骨架 | 等老闆 O1–O4 策略規格 |
| A9 | **協作基建** 卡＋label＋postbox＋規則 13 條 | 運作中；CI 兩個紅燈（#23/#24） | 可持續 | 卡狀態雙標籤（#20）；有人報大數（已兩次） |
| A10 | **自動化** 巡檢 30 分、日報 09:00、PrintWindow 截圖 | 巡檢／日報已上線；截圖實測可用 | 可擴展 | TSA 快照任務腳本缺失（每晚空跑） |
| A11 | **Supabase**（排名 45 筆＋health） | 任務 enabled 但腳本唔存在 | 需修 | 前端 #4 等即時資料 |

## 二、三大應用方向（賺錢／省時／降風險）

1. **數據資產化（最高 ROI，2 週內可做）**
   - 把 A2（50 檔）＋A3（hst）統一入一個 **本地資料庫**（SQLite／Parquet），欄位標準化（symbol、tf、ts、9 貨幣值），成為所有分析嘅單一真相源。
   - 好處：唔再靠 MT4 截圖做輸入；任何新指標／新報告可以即時回測。
2. **指標行為逆向 → 可複製產品（1–2 月）**
   - 以 A1 面板值做 ground truth，先釘死 `up` 定義（等 ZCODE／OC 答），再重製 CCY Power 與 Martingale Scanner（#27/#30）。
   - 交付「parity 測試套件」：同一份輸入，原版 vs 重製版數值逐點對比（容差 1e-4），成為所有後續版本嘅回歸閘。
3. **報告自動化 → 對外服務（1 季）**
   - 用 A6 做 golden fixture，把 A5 的 165 頁重生（修 5 個實錯＋補 ③④⑥ 區），統一模板（#28）。
   - 之後每份客戶交易紀錄 → 自動出報告（martin／CCY／風險三合一），現有人手流程可壓縮 80%。

## 三、開發藍圖（三期）

### Phase 0｜穩定化（未來 2 週）— 目標：唔再靠人手補洞
| 項目 | 內容 | 產出 | 負責 |
|---|---|---|---|
| P0-1 數據庫 | hst ＋ PowerHistory → SQLite（schemas：bars、power_history、panel_samples） | `data/tsa.db`＋loader | AC |
| P0-2 對標套件 | K 表＋fixture＋parity 腳本（原版 vs 重製） | `tests/parity/` | AC＋ZCODE |
| P0-3 修 5 個報告錯 | 按 Excel v8.5 LotTiers 重寫分層；刪「理論 lot」；補 ③④⑥ | 新版 165 頁 | OC／ZCODE |
| P0-4 CI 止血 | #23 Golden baseline、#24 page-quality 兩個紅燈 | 綠燈 | openclaw |
| P0-5 清理 | TSA 快照任務（腳本缺失）重建或刪；#20 標籤去重 | 無空跑任務 | AC／老闆 |

### Phase 1｜產品化（1–2 月）— 目標：數值可信＋報告可賣
| 項目 | 內容 | 產出 |
|---|---|---|
| P1-1 指標重製 | CCY Power、Martingale Scanner 重製＋parity 全綠 | #27／#30 收貨 |
| P1-2 報告生成器 v2 | 單一模板（HTML＋PDF）、日期段切換、每份附 parity 指紋 | `reports/` 統一 |
| P1-3 網站整固 | sidebar 統一（#20）、模板統一（#28）、前端讀 Supabase（#4） | 全站一致 |
| P1-4 MT4/MT5 採集 | 一個 exporter（iCustom 讀 buffer，MT4＋MT5）取代截圖 | 每日自動落 DB |

### Phase 2｜平台化（1 季）— 目標：可擴展至其他 EA／信號
| 項目 | 內容 |
|---|---|
| P2-1 Plugin 化指標 | 每個指標一個 adapter（input schema＋buffer map），新增指標只需寫 adapter |
| P2-2 多信號掃描 | 由單一 signal 擴到全平台（AlgoForest／Forex Forest 全站），自動排名 |
| P2-3 風險與資金曲線 | TSA Risk Analyzer 接實盤／demo：每日風險報告、爆倉距離、馬丁深度警戒 |
| P2-4 觀測與告警 | 數據新鮮度（stale 閘）、策略漂移、CI 紅燈 → 主動通知老闆 |

## 四、工具鏈改善（具體做法）

| 現況問題 | 改善 | 好處 |
|---|---|---|
| 截圖 OCR 做長期輸入 | 只留作 fallback；正路用 iCustom exporter 落 CSV | 零誤讀、可審計 |
| 每次分析都要重新解 hst／dat | 一次性 loader → SQLite，帶 mtime／checksum | 重複工作歸零 |
| 165 頁報告各自生成 | 統一 generator＋模板＋fixture 測試 | 一改全改，可回滾 |
| 卡嘅狀態靠 label 維護 | 加 CI 檢查：狀態唯一、必須有系統代號、冇 due 要警告 | 工作板可信 |
| 匯報口徑不一致（曾報大數） | 報告必須附「檔案路徑＋mtime／卡號連結」，冇就當未完成 | 可核實 |
| 排程任務無人管 | 每月一次「排程體檢」：確認腳本存在、上次成功時間 | 避免空跑 |

## 五、建議即刻開嘅卡（未開，等你／OC 批）

1. `[S1] 數據層：hst＋PowerHistory → SQLite 單一真相源`（P1，AC）
2. `[S1] parity 測試套件（原版 vs 重製，容差 1e-4）`（P0，AC＋ZCODE）
3. `[S2] 報告頁 5 個實錯修正（Excel v8.5 對數歸層）`（P0，待指派）
4. `[S3] 全站模板統一（sidebar＋報告）`（P1，zcode）
5. `[S5] 排程體檢（含 TSA 快照腳本缺失）`（P1，AC）
6. `[S4] MT5 EA 骨架（等 O1–O4）`（P0，待老闆）

## 六、取捨與風險
- **唔建議**再投入 OCR／截圖自動化：一次性驗證可以，長期係技術債。
- **唔建議**在 `up` 定義未定案前重製指標（#27 已因此卡住）。
- 最大風險係「數值不可信但報告照出」——所以 Phase 0 嘅 parity 同修錯係前置條件。

— AUTOCLAW（AC lane）
