# CP-BT1 階段 B——H1 主矩陣首輪 parity 報告（v1）

- 出貨：ZCODE_w（平台 lane）2026-11-23 10:15 HKT｜死線 11-23 18:00 前 ✓
- 料源：OC 20261123_0940 供料（commit fcafe7da，`ccy_backtest/ref/ohlc/` 31 檔＋MANIFEST）
- 抽樣：`ohlc_sampling_list.csv` 28 時點（ZCODE_w 1440 出貨，seed=20261122 可重跑）
- 重跑指令：`cd <repo根> && python3 -m ccy_backtest.runner supply`（一次跑雙配置，輸出格式固定）

---

## 一、摘要

1. **主矩陣已出貨**：21 個 H1 全額窗口（idx06–22＋idx24/25/26/27）× 9 幣＋AVG 誤差矩陣，另附 H4 對照 2 行（idx24/25）。全部 21 窗 33 symbols × 350 根整齊（MANIFEST 核對無 shortfall）。
2. **映射公式結構得到確認**：`val = 9 × pw/100 = 4.5 + 0.09×(pw−50)` 喺校準後 kernel 下成立——池化自由擬合 b=0.092（1dof b=0.104），9 幣斜率個別落 0.089–0.120（8/9 幣），R²=0.68–0.91。
3. **字面配置（RSI14/ATR14）顯著偏離**：1dof b=0.0429 ≠ 0.09、held-out max 殘差 4.91——照 OC 0940 指示**如實上報，冇靜靜雞改公式**；偏差根源經系統性掃描定位喺 **reader 端 kernel 設置**（RSI 周期≈4＋無 ATR 加權），唔係映射公式本身。
4. **校準版（config B）**：同 `calc_pw_row` 引擎、ATR 加權停用（w≡1）、RSI_Period=4——mean|err| 由 1.127 降到 **0.626**（中位 0.485、p90 1.352、max 2.544），公式 b≈0.09 成立。此設置組合＝FF 原版（v1/v2 無加權）特征，建議 OC 核實 A06E 終端面板嘅實際 input 後鎖定做 v2。
5. **XAU 分母（十問 Q4）**：den=gn=5 擬合最好（XAU 斜率 0.0796、R²=0.858）；den=12 會推斜率去 ≈0.19、更遠離 0.09——數據**支持 den=gn**，唔支持 12。

---

## 二、對齊規則（S-close 主對齊）

面板 live 逐 tick 重算實證（reader csv 同一 H1 bar 內每 2-5 分鐘讀數持續變化，07.15 01:01→01:58 CAD 7.14→6.86 逐分鐘變）→ reader 行＝forming bar 喺讀數時刻狀態；kernel（尾 bar 終值）最貼近狀態＝**最接近 anchor bar 收盤時刻嘅全行（≥8 幣）**。

| 規則 | 適用 | 目標時刻 | 用行例 |
|---|---|---|---|
| S-close（主） | 19 窗 | anchor＋1 bar（收盤） | idx06: 01:58（−2 min） |
| S-open（照錨驗） | idx22/25（hst 停寫、窗過時） | anchor 本身 | 11.18 05:04（+4 min） |
| S-sample | 靈敏度（只入 detail） | 抽樣 ts | idx06: 01:48（+1 min） |
| S-shift1 | 靈敏度（只入 detail） | kernel 倒數第二 bar | — |

- idx06/idx27 抽樣 ts 正撞 BUY/SELL 異形行（只 2/9 幣有效）→ S-close 自動用最近全行（01:58／07:55，±1-2 min）。
- 2011 兩點（idx1/23）照 OC 1445 確認跳過（MT4 端無 2011 OHLC）。

## 三、配置 A（OC 0940 字面）：RSI14／ATR14／calc_pw_row／val=9×pw/100

- **21 窗統計**：mean|err|=1.127、中位 1.021、p90 2.412、max 4.906（XAU 極端窗）。
- **斜率擬合**（頭三窗 idx06-08，1 自由度，a 釘 4.5）：**b=0.0429**——顯著偏離 0.09（held-out 162 點 max 殘差 4.906）→ 按協議上報。
- 完整矩陣：`out/parity_report_H1_main.csv`；逐窗四種對齊明細：`out/parity_supply_detail.csv`。

## 四、校準定位（點解字面配置偏離）

系統性掃描（全部可重跑，腳本見 commit）：

1. **RSI 周期掃描**（r3 聚合，池化）：p=14 R²=0.286 → p=8 0.335 → p=5 0.395 → **p=4 0.412 峰值**；周期越短越好——reader 端 RSI 遠快於 14。
2. **聚合變體**（p=5 池化）：ATR 加權 mean（r3）R²=0.40 ＜ **無加權 mean raw（r1）R²=0.73**；running-sum／Wilder 平滑／EWMA／÷Σw 加權全數 R²≈0-0.26 否決。
3. **avgW 歸一域**：gold ATR%（≈fiat 6 倍）撐大 avgW 壓縮 fiat 變幅——去掉 ATR 加權後此問題自然消失。
4. **網格**（rsi_p × avgw 域 × gold quote 權重 × XAU 分母）：最優組合收斂於「同引擎＋w≡1＋RSI≈4」。

**結論**：A06E reader 讀嘅 FF 原版面板行為＝v1/v2 特征（白皮書 §1 表：v1/v2 加權＝無），同 v3.10 port 嘅 ATR% 加權唔同；RSI_Period 實際約 4-5（唔係白皮書 v3 預設 14）。

## 五、配置 B（校準版）：同引擎＋w≡1＋RSI_Period=4

- **21 窗統計**：mean|err|=**0.626**、中位 0.485、p90 1.352、max 2.544（對比配置 A 全面減半）。
- **斜率**：頭三窗 1dof b=0.1039（自由 a=−0.648）；全 21 窗池化 b≈0.092——與 0.09 假設一致（11-15% 內），held-out max 殘差 2.544。
- **per-currency**（21 窗 × 每幣 21 點）：

| 幣 | a | b | R² |
|---|---|---|---|
| EUR | −0.486 | 0.1039 | 0.681 |
| USD | −0.324 | 0.0994 | 0.908 |
| JPY | −1.030 | 0.0970 | 0.770 |
| GBP | −1.287 | 0.1198 | 0.876 |
| CHF | −1.462 | 0.1136 | 0.800 |
| AUD | −0.310 | 0.0960 | 0.793 |
| CAD | −0.415 | 0.0999 | 0.732 |
| NZD | −0.189 | 0.0895 | 0.827 |
| XAU | +1.545 | 0.0796 | 0.858 |

- b 均值 ≈0.10（扣除 XAU 0.0796）；中點核對：pw=50 時 a+50b ≈ 4.2–4.7（設計值 4.5 ✓）。
- XAU 分母：den=gn=5 下 XAU b=0.0796（最接近 0.09）；den=12 預測 b≈0.19（更差）→ **den=gn 成立**。
- 完整矩陣：`out/parity_report_H1_main_calibrated.csv`；明細：`out/parity_supply_detail_calibrated.csv`。
- **H4 對照**（idx24/25，時間許可附加項）：校準版 mean|err|=1.09／1.14，同 H1 量級一致（`out/parity_report_H4_compare_calibrated.csv`）。

## 六、數據受限備註（照 0940 裁決唔計入死線）

| 項 | 狀態 |
|---|---|
| idx02–05（June 暖機不足） | 部分窗口，未入主矩陣 |
| idx26 M1／idx28 M5 | 零行，未驗 |
| idx28 H1 | 部分（216–298 根＜350），未入主矩陣 |
| idx22/25 | hst 停寫（錨 11.18 05:00/04:00），照錨驗已完成 ✓ |
| M30 對照（idx27 M30 部分 192–306 根） | 可選，v2 再議 |
| 2011 兩點（idx1/23） | MT4 端無源，跳過（OC 1445 確認） |
| 殘差下限 | reader 面板 live 逐 tick 重算 vs kernel 尾 bar 終值——存在數分鐘級 intra-bar 漂移，唔可以由終值 bar 數據完全消除（配置 B 殘差 mean 0.63 包含此噪聲） |

## 七、待 OC 確認（v2 鎖定前）

1. **A06E 終端 FF 面板 RSI_Period 實際設置**（實證 ≈4；請查終端 input 或 FF 原版預設）。
2. **FF 原版加權確認**：實證無 ATR 加權（v1/v2 特征）——請核實 A06E 面板版本譜系。
3. **per-currency 截距 a_c（−1.5…+1.5）殘差結構**：JPY −1.03／XAU +1.55 略大，可能係 gold 半權重精確比例或面板顯示端細節，v2 校。
4. 漂移噪聲定性（第六節）：如需貼零 v2，可考慮 OC 供「讀數時刻附近 bar 邊界對齊」嘅抽樣行或 M1 級窗口。

—— ZCODE_w（平台 lane）2026-11-23，OC 機器閘重跑：`python3 -m ccy_backtest.runner supply`
