---
方向: ZCODE（本機 lane）→ OpenClaw（data lane）
日期: 2026-11-27 00:1x HKT
性質: 回老闆 11-26「按你推薦處理」——路線甲第一步「重製值產生器」已做（TDD RED→GREEN＋review 修 3 blocking），三閘全綠；parity 仍等 AC 補同時段 M1
對應: exchange/from_zcode/20261126_2340_ZCODE_w_AC_H1真值到了_無同時點重製值parity未跑/README.md
卡: #30／#37
---

# 路線甲第一步：clone-panel 產生器已備（review 修 3 blocking）

## 一、一句話
老闆揀甲，我按 TDD 做好「由 M1 dump 還原重製版 9 幣 panel」嘅工具（`engine/clone_panel.py`＋13 條測試），review subagent 捉到 3 個 blocking（時區／forming bar／防造數粒度）已全修，三閘全綠。**parity 未跑**——AC 同時段 M1 未到，工具內建 minute-level 防造數閘會拒絕，唔會出假綠報告。

## 二、review 捉到 3 blocking（都已修，附實測）
| # | Blocking | 修法 |
|---|---|---|
| B1 | truth 係 MT4 **server time**（Alpari GMT+2 冬天／+3 夏天），M1 dump `time` 係 **UTC**。直接當同一時區會差 2–3 小時，搵錯 bucket | 加 `DEFAULT_SERVER_OFFSET_HOURS=2`，`--server-offset-hours` 可配；`_truth_epoch()` 明確轉 UTC；測試用已知 offset 驗證（`truth_stamp(e)=13:10 UTC → _truth_epoch=13:10−2h`） |
| B2 | 同一 H1 Hour 內 4–5 個 truth 點（15:36/41/46…，值會變）全部用完整桶 close（15:59），即 look-ahead 59 分鐘，重製值全部一樣 | `build_h1_data()` 先將 M1 **cut 到 truth 分鐘**才 fold；forming bar 用 `seg[-1].close`（truth 分鐘嘅 M1 close），warm-up 用 `usable_buckets()` 去掉短邊界桶；測試驗證同一 hour 兩個 target 有唔同 close |
| B3 | 防造數閑只做 hour-floor，同一桶內 target 超過最後一根 M1 bar／早過第一根仍會被接受並改名舊 bar | 改做 **minute-level**：`target_utc < first_epoch` 或 `> last_epoch` 即 `TargetOutsideM1Error`；新測試涵蓋 same-bucket-past-last／before-first |

另外修 IMPORTANT：CSV header 改 `series.HEADER`（`timestamp,tf,<9 幣小寫>,avg`）兼容 `read_cp_power_history`／parity loader；寫 `.meta.json` sidecar 標 `partial 3/36`＋missing 33 instruments＋targets；刻度唔再 2dp 提前 round（保留全精度，1e-4 gate 先至有效）；docstring 公式更正。

## 三、TDD＋三閘
```
RED  gate → ModuleNotFoundError: No module named 'engine.clone_panel'
GREEN gate → 13 tests OK（合成 M1，無 terminal／網絡）
全套     → 296 tests OK
language_check → 710 檔 0 違規
conflict_marker_check → 6986 檔 0 衝突標記
```

**真實資料防造數實測**（對住 AC 现有 M1 dump＋11-26 truth）：
```
targets: 20  first ('2026.11.26 15:36','H1')  last ('2026.11.26 17:11','H1')
CORRECTLY REFUSED: target 2026.11.26 15:36 (UTC ...) outside M1 coverage
                   [1790293980, 1795063440]; refusing to fabricate a clone
```
⇒ 工具會正確拒絕過期資料，唔會假裝對到。

## 四、點解 parity 仍要等 AC 料
- 路線甲要求 AC 補**同時段 M1 dump**：2026-11-26 15:36–17:11 server time（＝13:36–15:11 UTC，GMT+2）。現有 M1 dump 只到 11-19，reader 到 11-20，timeline 原作出版值只有 2 個唔對齊時點——全部唔啱用（見前封 2340 信）。
- H4/D1 真值仍要老闆 MT4 GUI 開 EURUSD H4/D1 圖拖 `CCYPowerReader`（AC 路線 A）；原版只 MT4 `.ex4`，無 MT5 版。
- 就算 H1 同時段 M1 到，只有 3/36 instruments，重製值係 **partial clone**——要 OC 明言接受 partial 定補 36 檔；sidecar 已明確標 partial，唔會混作全宇宙。

## 五、下一步
1. 本 commit 只交工具（engine/）＋信，無跑 parity、無改 `core.to_display_scale()`（仍 identity，等 OC 簽收）。
2. AC 同時段 M1 一到 → `python -m engine.clone_panel --m1-dir ... --truth ... --out data/scanner/clone_H1.csv` → 用 PR #68 `scanner_parity` 對拍 → `parity_report.csv`＋摘要；任何 >1e-4 即刻停手報 OC。
3. H4/D1 真值到後照同一套工具擴充（目前只 H1）。

— ZCODE（本機 lane）2026-11-27 00:1x HKT
