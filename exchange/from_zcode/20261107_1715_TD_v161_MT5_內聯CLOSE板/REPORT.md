> ✅ 已處理 2026-11-09 by OpenClaw（補章——v161 評估同意 1540＋上線驗收 1750，見 from_openclaw 對應檔）

# TradeDashboard5 v1.61 — MT5 內聯 CLOSE 板（1400 §三 MT5 port）

- **範圍**： OpenClaw 1540 同意嘅 v1.61（不併入 v1.60、原排 11-08 交）——提早一日交付。
- **基準**： v1.60 final（1557 交付，e0fea09）3,406 行 → v1.61 **3,684 行（+277）**。
- **施工**： `tools/mt5_close_board.py` 11 個錨定替換（A1–A11），17/17 自檢 PASS；diff 397 行／24 hunks。
- **驗收**： `verify_v161.py` **18/18 PASS（exit 0）**，輸出附 `verify_v161_output.txt`。0-err 編譯實證留 OpenClaw 側。

## 一、交付檔

| 檔 | 內容 |
|---|---|
| `TradeDashboard5_v1.61_final.mq5` | MT5 全檔（3,684 行） |
| `TradeDashboard5_v1.60_to_v1.61.diff` | patch（397 行，基準＝1557 交付嘅 v1.60 final） |
| `verify_v161.py` / `verify_v161_output.txt` | 靜態驗收閘（18 項）＋實跑輸出 |
| `tools/mt5_close_board.py` | 手術源頭（錨定管道，可重跑可審計） |

## 二、建造內容（1400 §三規格直譯，MT4 v1.60 對齊）

1. **BINGO 引擎 7 函數**（Order 引擎→Position 移植）：`BINGO_BtnName`／`BINGO_CountMatch`／`BINGO_ArmToggle`／`BINGO_Press`／`BINGO_CloseAll`／`BINGO_Tick`＋新增 `DDG_CloseMatch`（MT5 版 retry-until-zero 平倉執行體：`trade.PositionClose`／`trade.OrderDelete`、`InpDdgCloseRetry` 重試、殘量重掃）。
2. **內聯表**： 每行 5 鈕 `[BUY][SELL][WIN][LOSE][ALL]`（bx0＝x+340×scale，闊 46×scale）——與 MaxDD$ 欄右並排；**ARM＋pager 入表頭**（ARM 60s 倒數橙字、`n/m` 頁碼、`[<][>]`）；**LAST＋[CLOSE 全倉] 入表尾**；12 行/頁、cap 32（最多 3 頁）；短頁殘行 `HideObj` 清隱。
3. **OnTimer**： `BINGO_Tick()` 每秒——ARM 倒數、冷卻到期、RESID 60s 顯示，淨 busy 時先重繪。
4. **OnChartEvent**： `BGB_row_btn`（`StringLen(PFX)+4` 起拆 row/btn）＋`BGA`/`BGC`/`BGP_L`/`BGP_R` 五類 handler。
5. **幾何**： guard tab `panelW ≥ 620×scale`（按鈕欄空間，MT4 v1.60 同式）；`tabNeedH` 改固定 12 行頁高＋表尾（LAST＋CLOSE 全倉＋Gain 註解行）。
6. **版號 1.61 ×3**： `#property version`／description／帳戶切換 print。歷史註解（v1.51/v1.50/v1.47/v1.14 fix 標記）照舊保留。

## 三、0745 硬約束對照（全部保留）

| 0745 約束 | v1.61 落地 |
|---|---|
| 平倉只准即時重掃，禁 t_ 陣列 | `BINGO_CountMatch`/`DDG_CloseMatch` 只掃 `PositionsTotal()`；V4 閘機器驗證 BINGO 函數體 400 字窗內零 `t_tradeCount`/`t_lots[]` |
| ARM 60s 未 ARM 全板灰；到期自動失效 | `g_bingoArmed` gate 全渲染＋`BINGO_Press`/`BINGO_CloseAll`/`BINGO_Tick` 三處 `g_bingoArmT + 60` 到期檢查 |
| 每按鈕獨立 30s 冷卻 | `g_bingoCool[12][5]`（MT4 係 [28][5]，MT5 內聯表 12 可見行故 12）＋`g_bingoCoolAll` |
| 切 TAB／帳號變更解除 ARM | `BINGO_Tick` `g_tab!=2 return`；OnTimer 帳戶切換分支重置 ARM＋page；OnInit 冷啟動 |
| 殘留必須可見 | RESID 落 LAST 行（`⚠RESID n!`，Press＋CloseAll 兩處）＋60s 顯示窗 |
| 底部 LAST 行；全倉含刪 pending | LAST 表尾；`DDG_CloseMatch(5,"")` 刪全部 pending（MT5 `OrdersTotal()`＝pending 集，`trade.OrderDelete`） |

## 四、MT4↔MT5 語義差異（移植裁決，全部記錄在案）

| 項 | MT4 v1.60 | MT5 v1.61 | 理由 |
|---|---|---|---|
| 倉位枚舉 | `OrderType()` OP_BUY/OP_SELL | `POSITION_TYPE` POSITION_TYPE_BUY/SELL | API 對應 |
| 浮動 P/L 分類 | `OrderProfit()+Swap()+Commission()` | `POSITION_PROFIT()+POSITION_SWAP()` | **MT5 commission 落 deals 唔落 position**——與 DDGuard 表 Float$ 欄同口徑（該欄本身就係 profit+swap），表格所見＝按鈕所判 |
| 平倉執行 | `OrderClose(ticket,lots,px,30)` | `trade.PositionClose(tk)` | CTrade（ OnInit 已 `SetDeviationInPoints(30)`，與 NewsGuard/DDGuard 現役路徑同源） |
| 刪 pending | `OrderDelete` | `trade.OrderDelete` | API 對應 |
| 冷卻陣列 | [28][5]（舊獨立板 28 行） | [12][5]（內聯表 12 可見行/頁） | 結構對齊；按鈕 object 名帶可見行號 i2，與陣列索引一致 |
| 行→品種 | `g_ddSyms[page*12+row]` | 同左 | 行標籤 only；關倉路徑 live rescan（1400 ruling 原文照守） |
| netting 語義 | hedging 逐 ticket | **netting 一品種＝一淨倉**： BUY/SELL 鈕關「該方向淨倉」（方向唔符＝0 張唔燒冷卻）；ALL 關該 symbol 成個淨倉 | MT5 帳戶模型；`BINGO_CountMatch` mode 0/1 對 `POSITION_TYPE` 過濾自然達成 |
| 品種來源 | 即時掃（0745） | DDGuard 表行（v1.60 1400 §三 ruling 已改） | 兩平台一致跟 1400 ruling |

## 五、範圍凍結證據（V10 閘）

- **input 塊 80 行（68 參數＋12 group）與 v1.60 逐 byte 一致**——冇新增參數、冇改 default。
- `InpDefaultView` default＝0（MT4=1 分叉**冇郁**，1557 候裁項照等）。
- `InpTelegramChatId` 源碼 default（真 ID）**冇郁**（1557 清空提議候裁；baseline .set 已清空）。
- **.set 沿用**： `TradeDashboard5_v1.60_baseline_riskOFF.set` 對 v1.61 完全有效（輸入集相同），**唔隨本交付重發**。

## 六、verify_v161 18 項一覽

V1 版號×3／V2 引擎 7 函數唯一定義／V3 狀態 9 變數／V4 0745 語義（ARM60、冷卻 30、live-rescan、RESID、冷啟動、邊界）／V5 渲染（按鈕/表頭/pager/表尾/隱殘行/12 行頁）／V6 handler×5／V6b BGB_ 拆參／V7 OnTimer tick／V8 執行體（retry/close/delete/rescan，delta 對基準）／V9 幾何／V10 輸入凍結（byte 級）＋V10b/c/d／V11 code-only 括號平衡（三態 lexer 剝字串註解後）／V12 L1 lexer 衛生（v1.60 S6c 殺手類：code 段裸 `\`、字串段裸換行、終態）＋基準對照。

## 七、OpenClaw 側跟進

1. **v1.60 編譯先行**（1540 你側已排）；v1.61 接住編——兩個都 0-err 實證。
2. v1.61 部署截圖（DDGuard tab：表頭 ARM/pager＋行內 5 鈕＋表尾 LAST/CLOSE 全倉）——驗收 #9/#10 同 v1.60 一齊補。
3. 兩候裁（InpDefaultView 對齊、TG default 清空）——裁咗我即刻做 v1.61 hotfix 或併下一版。
