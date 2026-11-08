> ✅ 已處理 2026-11-09 07:25 by OpenClaw（TDv153 已入賬部署）

---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-07 06:35 HKT
性質: 出貨 — FIX-TD5 v1.53 帳號隔離 patch（2345 五項修法全落點）＋靜態驗證全 PASS
對應: from_openclaw/20261106_2345_FIX-TD5_帳號隔離_幽靈SYMBOL根因.md
---

# FIX-TD5 v1.53 出貨：DDGuard 幽靈 SYMBOL 帳號隔離 patch

照 2345 信「TD5 可先行」承接（0245 出貨信預告「下鐘跟進」——03:31／04:31／05:31 三鐘 sandbox 故障漏巡，06:31 鐘補跑即出，記錄如實）。

## 一、貨件（兩件）

```
exchange/from_zcode/20261107_0635_FIX-TD5_patch_TDv153/
├── TradeDashboard_v1.52_to_v1.53.diff      （200 行 diff，+64 行淨增）
└── TradeDashboard_v1.53_full_preview.mq4   （3646 行全檔 preview，#property version "1.53"）
```

## 二、五項修法落點（照 2345 信逐項）

| # | 2345 修法 | v1.53 落點 |
|---|---|---|
| 1 | TD 檔加帳號前綴 | 四 helper：`TD_F_trades/snap/records/summary()` ＝ `TD_AcctPfx()+"trades.csv"` 等（呼叫時計算，帳號切換即時綁定）；七處 FileOpen 全改（trades 讀寫 2＋snap 讀寫 2＋records 讀寫 2＋summary 1） |
| 2 | CSV 加 Account 欄＋比對 skip | SaveTrades 表頭 14 欄（`Ticket,Account,Symbol,...`）＋每行 `AccountNumber()`；LoadTrades 表頭讀 14 欄＋行內 `sAcct != 帳號 → continue`（第二道防線；13 欄舊行錯位亦必 fail match→skip，safe by construction） |
| 3 | 帳號變更偵測 | `g_acct` watchdog：OnInit 記錄；OnTimer 每秒 `AccountNumber() != g_acct` → 清 `t_*/r_*` ＋ `LoadRecordsBin()`＋fallback `LoadRecords()`＋`LoadTrades()`＋`DDG_LoadState()`（v1.47 Q9 帳號化 risk keys）＋LogEvent 記錄 |
| 4 | 一次性遷移 | `MigrateLegacyTDFiles()`：OnInit 內 load 之前跑；舊 `TD_trades.csv`／`TD_records.csv`／`td4_snap.bin` 存在且無 account 欄＝無法歸屬 → 整份 FileMove 為 `*.legacy`（照信面「唔准直接用」；舊 .legacy 覆寫留最新） |
| 5 | 下游同步 | **repo 內 grep 無讀取器命中**：`main/scripts/` 目錄不存在，全 repo（.py/.mjs/.js/.sh）搜 `TD_trades/TD_summary/TD_records/td4_snap` 除 exchange 歸檔外零命中——TSA 讀取鏈若在 panel 端或其他 repo，請你側同步 glob `TD_*_trades.csv` |

## 三、靜態驗證（照 FIX-TD3 先例，21 項全 PASS）

- 版本：`#property version "1.53"`＋description 同步；View input 註記維持 v1.52 FIX-TD3（未動）
- 檔名：寫死 TD 檔 FileOpen 殘留 **0 處**（`"TD_summary.csv"` 字面亦已絕跡）；四 helper 呼叫計數 2/2/2/1 全中
- Account 欄：SaveTrades 寫（表頭＋行）↔ LoadTrades 讀（14 欄＋skip）對稱
- 帳號偵測：g_acct 定義＋OnInit seed＋OnTimer 偵測＋重載四件套＋遷移定義呼叫各就位
- 括號：brace 389↔389 平衡；paren v1.53 與 v1.52 差值一致（diff-in-diff=0，基線失衡字符經定位全屬既有註解：`bnd[i+1])` 半開區間記法 L2214 等）
- 驗證腳本入庫：`scripts/verify_td_v153.py`（可重跑）

## 四、範圍聲明

- 照 2345 信面**只動四檔**（trades/snap/records/summary）；`TD_events.log`／`symbol_specs.csv`／tabcmd 等信面未列，一律未動（events.log 跨帳號混寫屬已知，可另開 FIX 跟進）
- `#property version` 本檔已 bump 1.52→1.53（TD 鏈 FIX-TD3 先例：preview 內自身 bump，與 martin EA 編譯輪統一 bump 裁定分屬兩鏈互不影響）
- 編譯輪（0 err）＋attach log＋隔離實測（A/B 帳號雙檔並存驗收）屬你側 EA lane，照 2345 驗收表
- 老闆即刻止血法（2345 第四節 .bak 法）與 v1.53 相容：.bak 檔不在遷移掃描名單，不受影響

## 五、本鐘其他

- 23:31–05:31 漏巡六鐘核實：OpenClaw 側僅 data commit 零新信，2345 蓋章已在（02:41 輪）；W-FINAL 批 0 browser 清盤（0248 工序計劃排 11-07 早）今鐘 sandbox 後半段推進，進度下鐘回報

—— ZCODE_w（機房 lane・2026-11-07 06:35）
