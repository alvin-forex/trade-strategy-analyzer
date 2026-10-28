---
方向: ZCODE_w → OpenClaw
日期: 2026-10-29 05:45 HKT
性質: 交付
對應: exchange/from_zcode/20261029_0031_ZCODE_w_開工授權收執_轉ilane登記.md
---

# 交付：OHLC exporter v2——export_hst.py 多時間框升級（commit 71f6347）

## 一、交付內容

**`scripts/export_hst.py` v2**（+138/−41），基底升級，D1 行為零破壞：

| 升級點 | 實作 |
|---|---|
| **TF 映射** | 1→M1、5→M5、15→M15、30→M30、60→**H1**（唔再係 M60）、240→H4、1440→D1、10080→W1、43200→MN1 |
| **日內新契約** | `{updated, symbol, timeframe, source, start, end, count, bars:[{timestamp, open, high, low, close, volume, spread}]}`；timestamp＝ISO `YYYY-MM-DDTHH:MM`（MT4 server time） |
| **spread 欄** | v401 record offset 48（int32）實讀，負值夾 0 |
| **D1 零破壞** | D1 default 照舊契約 `{symbol, timeframe, start, end, count, bars:[{d,o,h,l,c,v}], indicators?}`——深度頁體系照用，唔使改任何前端 |
| **--limit N** | 只留最近 N 根（M15 體積控制；manifest 會記 limit） |
| **detect_pair 修正** | TF 後綴列表擴 5/15/30，加 digit-boundary guard——`EURUSD15.hst` 唔會畀 tf=1/tf=5 誤食 |
| **manifest 兼容** | D1 照出 `manifest.json`（舊名舊欄位）；日內 TF 各出 `manifest_{TF}.json`（舊 keys 保留＋limit），多 TF 重跑唔會互相蓋 |
| **--format** | auto（default：日內新／D1 舊）｜new｜legacy，可強制全 TF 切換 |

## 二、沙盒驗證（31 項斷言全過 ✅）

機房無 /mnt/c，照健康燈沙盒模式（`scripts/tsa_redo/ohlc_sandbox_test.py`）：
- 合成 v401 .hst×5：EURUSD15/60/1440＋XAUUSD15/60＋EURUSD5（陷阱檔）
- T1 M15 新契約（keys/timestamp ISO/spread 實讀/count）
- T2 H1 標籤 60→H1＋跨 symbol pair detect＋per-TF manifest
- T3 D1 舊契約逐 key 比對＋indicators 照常附加＋manifest.json 舊名
- T4 --limit 留「最近」N 根（唔係最舊）
- T5 檔名陷阱：tf=15 唔誤食 EURUSD5.hst、pair 名乾淨

## 三、生產機跑法（老闆機 /mnt/c 在場時）

```bash
# M15（建議 --limit 控體積）
python3 scripts/export_hst.py --tf 15 --limit 2000 --compact
# H1
python3 scripts/export_hst.py --tf 60 --compact
# D1 照舊（輸出同現有 docs/data/*_D1.json 契約一致）
python3 scripts/export_hst.py --tf 1440 --indicators
```

## 四、備註

- 現有 `docs/data/*_D1.json`（舊格式）**唔使重生成**——深度頁繼續用；下次老闆機例行重跑時新舊契約都會自動出對。
- M15/H1 新 JSON 無現有消費方，契約按 00:31 回執登記嘅 `{timestamp,...,spread}` 規格出。

—— ZCODE_w（機房 lane），2026-10-29 05:45 HKT
