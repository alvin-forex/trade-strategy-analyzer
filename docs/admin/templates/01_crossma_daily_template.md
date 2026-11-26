---
模板: CrossMA 日報（純文字 markdown；{{}} 為腳本替換位）
數據檔: docs/admin/crossma/crossma_daily_{{YYYYMMDD}}.csv｜174 行＝29 symbol × 6 TF，rank=1
死線: 每日 06:15｜交: exchange/from_autoclaw/{{YYYYMMDD}}_HHMM_CrossMA日報.md
---

# CrossMA 日報 {{YYYY-MM-DD}}

## ① XAUUSD Top 5（按 net_pips）

| TF | Fast/Slow | 勝率 | Net pips | 交易數 | 連任日數 |
|---|---|---|---|---|---|
| {{tf}} | {{fast}}/{{slow}} | {{win_rate}}% | {{net_pips}} | {{trades}} | {{n}} |

對比 {{prev_date}}：{{升 n／跌 m；最大變動 {{tf}} {{±pips}}}}。

## ② 冠軍存活率

- 今日 Top10 ∩ {{prev_date}} Top10：**{{k}}/10 = {{pct}}%** → {{綠｜黃｜紅}}（≥50% 綠、30–50% 黃、<30% 紅）
- 新入 Top10：{{symbol tf…｜無}}
- 連續紅燈：{{n}} 日{{；≥3 日已發 904 告警}}

## ③ 一句判讀

判讀：{{趨勢延續｜轉震盪｜結構斷裂}}——Top10 換血 {{n}} 席、{{m}}/174 組合負 pips、XAU 六 TF 合計 {{sum}} pips。

## ④ 異常

- 無：異常：無。174/174 行齊、rank1 完整、與昨日 Top10 可比對。
- 有：{{現象}}｜證據：{{檔名＋行號}}｜影響：{{…}}｜上報：{{904／工單}}

## ⑤ 數據注記

{{檔名、產出時間、行數}}；net_pips 為回測累計，非實盤；存活率基準 {{prev_date}} Top10。

**缺數據固定句**（照抄，只填日期與原因）：
> ⚠️ 缺數據：未取得 `crossma_daily_{{YYYYMMDD}}.csv`（原因：{{MT5 未開／掃描失敗／未出版}}）。本期不出 Top5 與存活率，連續日數暫停、不計紅燈；下份以 {{下一個交易日}} 補回。

## 唔准寫

- 唔准把缺數據寫成「無異常」或搶眼標題；缺就照固定句寫。
- 唔准用 rank>1、推算或昨日數字填今日 Top5。
- 唔准把回測 net_pips 講成實盤盈利。
- 唔准未滿連續 3 日紅就預告 904 告警。
- 唔准改昨日 Top10 名單湊存活率；基準日期要明寫。
