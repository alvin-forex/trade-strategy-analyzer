---
方向: ZCODE（本機 lane）→ OpenClaw（data lane）／AutoClaw（AC lane）
日期: 2026-11-26 23:40 HKT
性質: AC H1 真值到了——PR #68 parity 工具成功讀 180 格；但**對拍所需「同時間點重製值」全部數據源過期/口徑唔對**，1e-4 parity 未能跑，列可行方案請裁
對應: exchange/from_autoclaw/20261126_2140_[AC]Scanner對拍真值_首批H1/README.md（commit 6208702f1／7e84889d8）
卡: #30／#37
---

# AC H1 真值到了：工具讀到 180 格，但 parity 未跑得出（無對應重製值）

## 一、一句話
AC 首批 H1 真值已落 repo（`panel_truth_H1_last20.csv`，9 幣 × 20 時點＝180 格），我 PR #68 嘅 parity 工具**實測成功讀晒 180 格**。但 #37 對拍要「重製版喺同一時間點嘅 9 幣值」，本機所有重製數據源喺真值時段（2026-11-26 15:36–17:11）**全部冇對應值** ⇒ 唔會造數、唔會攞原作出版值冒充重製值去氹 1e-4 過關。列三條可行路線請 OC／老闆裁。

## 二、已實測（工具側 OK）
```
$ 用 PR#68 工具 load_truth(panel_truth_H1_last20.csv)
truth cells: 180
tfs: ['H1']
ccys: ['AUD','CAD','CHF','EUR','GBP','JPY','NZD','USD','XAU']   ← 9 幣齊
ts: 2026.11.26 15:36 -> 2026.11.26 17:11                        ← 20 時點，5 分鐘粒度
sample: ('2026.11.26 15:36','H1','AUD') = 4.38
```
⇒ AC 交嘅格式同我工具 wide layout 完全吻合，工具唔使改就讀到。呢部分**已達標**。

## 三、 parity 卡住：無「同時點重製值」（逐源核實，唔照抄）
| 重製/面板數據源 | 最後 timestamp | 對 15:36–17:11 窗口 |
|---|---|---|
| AC M1 gz dump（3 對） | EURUSD 2026-11-19 04:44／USDJPY 11-18 13:06／XAUUSD 11-18 14:18（epoch 1795063440 等） | ❌ 過期 7 日，而且只 3/36 instruments |
| MT4 M1 hst（EURUSD1.hst） | 2026-11-19 05:37 | ❌ 過期 7 日 |
| `ccy_power_reader.csv` | 2026-11-20 23:53 | ❌ 過期 6 日 |
| `docs/ccy_power/timeline.json`（H1/H4） | 2026-11-26 16:57 | ⚠️ 窗口內只有 **15:57／16:57 兩個點**，真值 5 分鐘粒度（15:36/41/46/51/56/16:01…）**精確重合 0 個**；而且 timeline 係 OC 出版嘅**原作面板值**，唔係我哋重製版輸出——攞佢對真值係「原作 vs 原作」，唔係 #37 要嘅「重製 vs 原作」 |

```
$ 逐源 time overlap（truth_first=15:36, truth_last=17:11）
H1 in truth window: ['2026.11.26 15:57', '2026.11.26 16:57']
H4 in truth window: ['2026.11.26 15:57', '2026.11.26 16:57']
exact ts overlap with 20 truth points: H1=0, H4=0
```
⇒ **呢個係數據窗口錯位，唔係公式錯**。1e-4 容差要有「同一 timestamp 嘅重製值」先有意義；而家一個都無。

## 四、H4／D1 真值亦未到（AC 已書面講明）
AC 信 §二：原版指標**只有 MT4 `.ex4`**（老闆確認無 MT5 版，見 ac-to-oc 21:55 更正）；MT4 現時只有一張 EURUSD H1 圖掛咗指標＋reader。要 H4/D1 要老闆 GUI 開圖拖 reader（路線 A，建議）或重啟 MT4（路線 B，會失效 GEMS，唔建議）。所以我最多只有 H1 一批，3×3×20 完整真值未齊。

## 五、可行路線（請 OC／老闆揀一條，我唔自行選）
1. **路線甲（推薦，最乾淨）**：老闆照 AC 路線 A 開 H4/D1 圖拖 reader；**同時**叫 AC 補一份「覆蓋 2026-11-26 15:36–17:11 嘅 EURUSD/USDJPY/XAUUSD M1 dump（或 reader 同時段面板值）」。有咗同時段 M1，我可以用 `ccy_backtest.core`（M1→H1 聚合＋9 幣分解＋刻度映射）計出重製值，再同真值逐格 1e-4 對拍。注意：完整公式要 36 instruments，若只補 3 對仍係 partial，要 OC 明講接受 partial 定補 36。
2. **路線乙**：授權我本機用 `copy_rates_range`（`engine/api.py` 已修好可接受）即時抓 11-26 15:36–17:11 嘅 36 instruments M1，自己計重製值。呢個要明確解除「只改 engine/」以外嘅數據抓取限制，且要確認 broker history 真係有咁舊資料（hst 目前只到 11-19，未必有）。
3. **路線丙（唔係真正 parity，要老闆明確放鬆口徑）**：接受用 `timeline.json` 原作出版值同 AC reader 真值做「原作交叉驗證」（2 個重叠時點），號稱 sanity check 而**唔叫 parity 1e-4**。我唔會未經批准就用呢個冒充 #37 收貨。

## 六、我而家做緊／狀態
- PR #68 工具已具備，讀真值 OK；**未跑 parity、未出 parity_report.csv**（因為無 clone 值，跑咗都係 MISSING_CLONE，違反「唔靜默扮成功／唔造數」）。
- 分支 `local/scanner-parity-truth`（base `origin/main 368c8c329`），本 commit 只係交付信＋notify，無改 engine 邏輯。
- 收到路線裁定＋同時段 M1（或授權路線乙）即刻跑：loader → compare → parity_report.csv → 摘要，任何 >1e-4 即刻停手報 OC。

— ZCODE（本機 lane）2026-11-26 23:40 HKT
