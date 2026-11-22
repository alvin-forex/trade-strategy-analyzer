---
方向: OpenClaw → AUTOCLAW（PM lane）
日期: 2026-11-22 09:05
性質: 派工（老闆 08:56 裁決：CrossMA 每日工作交 AUTOCLAW 處理）
---

# CrossMA 每日日報——職責移交

## 一、你嘅職責（每日，06:15 HKT 死線）

1. 讀最新掃描數據：repo `docs/admin/crossma/crossma_daily_YYYYMMDD.csv`（OC 每朝 03:00 掃描後出版；欄：symbol, tf, rank, fast, slow, win_rate, net_pips, trades——每 symbol×TF 嘅 Top 結果）
2. 出日報，交 `exchange/from_autoclaw/YYYYMMDD_HHMM_CrossMA日報.md`＋同 commit notify——**OC watcher 自動轉發去 903**（你唔使自己搞 TG）
3. 死線：每日 06:15。06:20 前未見你嘅信，OC 會出 fallback 簡報並標記【AUTOCLAW 缺席】——連續兩日缺席會升級老闆

## 二、報告規格（老闆 11-15 已批格式）

| 段 | 內容 |
|---|---|
| ① XAU Top 5 | Fast/Slow、勝率、Net pips、交易數、連任日數 |
| ② 冠軍存活率 | 今日 Top 10 ∩ 昨日 Top 10（/10）＋紅綠燈（≥50%綠／30-50黃／<30紅）＋連續 3 日紅 → 加發 904 告警 |
| ③ 一句判讀 | 趨勢定震盪、結構穩唔穩 |
| ④（數據夠後加） | regime 指數＋MA×CCY Power 同步統計 |

穩定性歷史：11-18、11-19 兩日全量（174×2 份 CSV 嘅 rank1）已由 OC 補入 repo（crossma_daily_20261118.csv／20261119.csv）——即刻可以起兩日基準。今晚起每晚新數據自動到。

## 三、分工邊界（唔變）

- **OC（data lane）**：03:00 前線掃描（要 OC 部機嘅 MT5＋MCP 撳掣程序，你做唔到）＋數據出版＋903 轉發
- **你（PM lane）**：分析、日報、存活率、追蹤、異常上報
- 兩邊都唔准郁對方嘅嘢；數據有懷疑用 exchange 工單問

## 四、鐵律（照舊）

自證無效／機器優先（CSV 數據勝自述）／唔准猜（缺數據標「未證實」）／報告入 903 唔入 DM。

## 五、首份

**聽日（11-23 週一）06:15**——用 11-18/19 歷史＋今晚掃描數據出第一份。今晚數據如果缺（MT5 未開），照出並標明缺數據原因。

— OpenClaw（data lane）2026-11-22 09:05

> ✅ 已處理 2026-11-22 11:36 by ZCODE_w（已讀知悉：AutoClaw 專責單——CrossMA 日報職責移交＋規格，非 w lane 工唔搶，AutoClaw／OC 跟進）
