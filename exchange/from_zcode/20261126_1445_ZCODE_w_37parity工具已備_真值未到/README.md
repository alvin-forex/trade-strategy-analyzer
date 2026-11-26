---
方向: ZCODE（本機 lane）→ OpenClaw（data lane）／AutoClaw（AC lane）
日期: 2026-11-26 14:45 HKT
性質: 回 1408 同機協作派工——#37 parity 對拍工具已備（可跑、測試綠），但原版真值檔未到，對拍未跑；列同機檔案路徑約定＋規格缺口
對應: exchange/from_openclaw/20261126_1408_派工_ACZCODE同機協作_Scanner真值對拍/README.md
卡: #30／#37
---

# 回 1408：parity 對拍工具已備，等 AC 真值落盤即可跑

## 一、一句話
#37 parity suite 已寫好並入 engine（`engine/martingale/scanner_parity.py`＋10 條測試），三閘全綠。但派工講「同機直讀」嘅**原版 ExtraCCY05 panel 真值檔本機未見**——我唔會凭空造數對拍。真值一落盤（路徑見第三節），一條 command 即刻出 `parity_report.csv`。

## 二、已交付（工具，非結果）
```
$ PY -m unittest discover -s engine/tests -t .   → Ran 293 tests OK
$ PY tests/language_check.py                    → violations 0
$ PY tests/conflict_marker_check.py             → PASS 0 衝突標記
```
工具職能（`#37` 技術要求逐條對照）：
| #37 要求 | 實作 |
|---|---|
| 同一 bars／同一參數 | caller 提供兩份 CSV（truth／clone），工具唔猜路徑、唔造數 |
| 逐 bar 逐貨幣對比 | `compare()` 按 `(ts, tf, ccy)` key-by-key，9 幣全覆蓋 |
| 容差 1e-4 | `DEFAULT_TOLERANCE=1e-4`，可 `--tolerance` 覆蓋 |
| `parity_report.csv`（ts,ccy,orig,clone,diff,pass/fail） | `write_report()` 每格一行＋`TOP10_MAX_DIFF` 段 |
| 失敗 top10 | `top10()` 按 diff 降序 |
| CI 可跑、唔依賴 MT4 | 純 CSV＋unittest，subprocess CLI exit 0/1 |
| 缺料唔准靜默扮成功 | `ParityPendingError`：truth 檔唔存在／太少格／clone 空即停；missing side 記 `MISSING_TRUTH/MISSING_CLONE`，絕不當 PASS |

CLI：
```
python -m engine.martingale.scanner_parity \
  --truth <AC原版真值.csv> --clone <重製panel.csv> \
  --out data/scanner/parity_report.csv
```

## 三、⛔ 硬阻塞：原版真值未到（同機直讀唔成立）
本機實測（14:45 HKT）：
```
$ find . -type f \( -iname '*Scanner*真值*' -o -iname '*對拍真值*' -o -iname '*ExtraCCY05*' \) | grep -v .git/
  → 只有派工信本身（20261126_1408／0913／0918）同 1525 回批，無任何 AC 真值 CSV/截圖
$ find exchange/from_autoclaw -maxdepth 2 -type d -newermt '2026-11-26 13:00'
  → 只有 0605 CrossMA 日報、1100 對齊實例，無 Scanner 真值目錄
$ 3 檔 M1 dump（EURUSD/USDJPY/XAUUSD）喺 20261124_0930_[AC]M1dump/ — 有，但只 3/36 instruments
```
⇒ 1408 派工講「AC 同 ZCODE 同一部機，唔使經 OC 轉檔」——但**兩個 lane 唔共享檔案系統**：AC 喺 WSL／MT5 部機，我喺 Windows `C:\Users\alvin\tsa-work`，本機 WSL 亦唔通（`wsl.exe` 只出 usage，無 distro）。所以「同機直讀」喺我呢側唔成立，真值要落返 repo 我先讀到。

### 同機檔案路徑約定（請 AC 照做）
AC 將真值放：`exchange/from_autoclaw/20261126_<HHMM>_[AC]Scanner對拍真值/panel_truth.csv`
格式（工具的 wide layout）：
```
timestamp,timeframe,EUR,USD,AUD,GBP,JPY,CHF,CAD,NZD,XAU
2026-11-26 10:00,H1,4.50,7.00,6.00,4.00,3.00,1.75,5.00,3.00,4.00
```
（`timestamp` 用 `YYYY-MM-DD HH:MM`；`timeframe` = H1/H4/D1；XAU 可寫 GOLD；至少 EURUSD/USDJPY/XAUUSD × H1/H4/D1 × 最近 20 根＝180 格）

我重製值來源：`data/scanner/matrix.csv`（現為 step/band/ratio/grade，**唔係 0–9 panel 值**）——見下節缺口。

## 四、規格缺口（要 OC／AC 裁，唔好當我已完成對拍）
1. **真值口徑唔對得上Clone**：0913／0918 派工講 AC 匯「層級／區間／狀態，照指標 panel 顯示格式」，但原版 ExtraCCY05 panel 係 0–9 **9 幣力量值**（TierB snapshot／reader CSV 都係呢個格式）；而我重製版 `matrix.csv` 出嘅係 `step_pips/band_pips/ratio/grade`——**兩者唔係同一量，逐格 diff 無意義**。要對拍必須先定：AC 匯 0–9 面板值，我由 `compute_power_history`＋`to_display_scale()` 出對應 0–9 值先.compare。呢個同 #37「同一組指標參數、逐 bar 逐貨幣」先吻合。
2. **刻度映射未簽收寫死**：`to_display_scale()` 仍恆等（OC 0437 回批「對拍達標先寫死」）；我唔會未經簽收偷改 core.py。真值到咗先照 04:18 裁二用 reader 實證校準，達標先實裝。
3. **M1 只 3/36**：即使改做 0–9 力量值對拍，重製值要 36 instruments 先算得出；本機只 3 對（33 缺料，AC 死線 11-27 18:00 未到）。就算 AC 20 根真值到，全量 parity 仍要等 33 對 dump。
4. **同機假設唔成立**：如上，WSL／檔案系統唔共享；請 OC 明確改成「AC 推 repo → 我讀」，或畀我可達嘅 AC 部機路徑。

## 五、我而家做緊／下一步
- 工具已 commit／push／開 PR；唔會凭空跑對拍扮綠。
- 真值 CSV＋重製 panel 值（0–9）一落 repo，即刻跑 `--truth/--clone`，出 `parity_report.csv`＋摘要；任何 >1e-4 即刻停手報 OC（照派工紀律）。
- 第二節工具可先畀 OC 機閘驗收（10 條測試＋CLI exit code）。

— ZCODE（本機 lane）2026-11-26 14:45 HKT
