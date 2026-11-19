# 派工：AC 本機跑 TierB 診斷 ＋ PowerHistory 樣本解碼

方向：OpenClaw（data lane）→ AUTOCLAW（AC lane）
日期：2026-11-18 11:10 HKT
性質：派工（老闆 11-18 11:02 指示：改由 AC 本機做）
卡號：GitHub #19（TierB 診斷跑數）

---

## 0. 為什麼改派給你（老闆原話）

> 「要掛EA或INDICATOR取資料, 我想在AUTOCLAW本機, 由AUTOCLAW做, 你搵佢」

> 「我有啲POWER HISTORY的檔案, 我放了在AUTOCLAW的主機, `C:\Users\alvin\Downloads\AutoClaw\Power History`」

所以本單全部在你本機做。我方（OC）已停手，**MT4-2 不再改動**（已重啟復原：6 張圖，probe 未掛）。

---

## 1. 交付物一：TierB 診斷（最重要）

### 1.1 檔案

源碼在 repo（已驗證 raw 200）：
```
https://raw.githubusercontent.com/alvin-forex/trade-strategy-analyzer/main/exchange/from_zcode/20261118_0815_ZCODE_w_CCY_Power_%E9%9A%8E%E6%AE%B50_%E5%90%8CTierB%E8%A8%BA%E6%96%B7%E5%B7%A5%E5%85%B7/CcyPower_TierB_Probe.mq4
```
本地：`exchange/from_zcode/20261118_0815_ZCODE_w_CCY_Power_階段0_同TierB診斷工具/CcyPower_TierB_Probe.mq4`
12,874 B｜v1.10｜md5 `96cdd301ac07462deb0f3906df579ef5`

### 1.2 步驟

1. 放 `CcyPower_TierB_Probe.mq4` 到 `MQL4\Experts\`
2. MetaEditor（F4）開檔 → **F7 編譯** → 要 **0 errors**
   （我方在 MT4-2 已編過：`Result: 0 errors, 0 warnings, 80 msec elapsed`，你部機應該一樣）
3. 開一張 **EURUSD H1** 圖
4. 掛原版 **`CCY Power Indicator v1.00`**
   - `displayMode = 0`（All Power）
   - `TF_1 = 60`
   - `Period_1 = 10`
   - `showPanelTable = 1`
5. 同一張圖拖上 **`CcyPower_TierB_Probe`**
   - `InpTF = 60`（必須與第 4 步一致）
   - `InpPeriod = 10`
   - `InpBars = 14`
   - `InpPollSeconds = 60`
   - `InpEveryPoll = true`
6. 等 **≥10 分鐘**（每 60 秒一行 → 10 行以上）
7. 收 4 個檔（全部在 `MQL4\Files\`）：
   - `ccyprobe_panel.csv`
   - `ccyprobe_bars.csv`
   - `ccyprobe_candidates.txt` ← **最關鍵**
   - `ccyprobe_objects.txt`（若有）

### 1.3 若 Journal 出現 `panel 0/9` 或 `panel <9/9`

**唔緊要**。`ccyprobe_candidates.txt` 就係為此而設 —— 佢會傾印原作 object 的真實命名與文字。
交回即可，ZCODE 會照真實命名改 parser。

### 1.4 交回方式

放入 `exchange/from_autoclaw/20261118_<hhmm>_CCY_Power_TierB樣本/`，然後在
`exchange/postbox/ac-to-oc.md` 寫一行：
```
2026-11-18 HH:MM  TierB 4 檔已入 exchange/from_autoclaw/20261118_HHMM_...／commit <hash>
```

---

## 2. 交付物二：PowerHistory 樣本清點 ＋ 解碼

老闆說檔案在：**`C:\Users\alvin\Downloads\AutoClaw\Power History`**（你本機）

### 2.1 清點

1. 列出該目錄**所有檔案**：檔名 ＋ 大小(bytes) ＋ 修改時間
2. **特別留意有冇不同時間框版本**：
   - `PowerHistory_D1_*.dat`（已知一份 `PowerHistory_D1_8.dat`，154,680 B）
   - `PowerHistory_H1_*.dat` ← 若存在，價值極高
   - `PowerHistory_H4_*.dat` ← 同上
   - `PowerHistory_M30_*.dat`
3. 全部原檔上傳到 `exchange/from_autoclaw/20261118_<hhmm>_PowerHistory樣本/`

### 2.2 解碼規格（ZCODE 已 100% 逆向成功，照此驗證）

```
int32   count = 9                      // header 前 4 bytes
char[4] × 9                            // 40 bytes header 全部
   貨幣碼順序：EUR GBP AUD NZD CHF JPY XAU CAD USD
record × N (每筆 80 bytes)
    offset 0 : int64   epoch seconds (UTC 00:00)
    offset 8 : double × 9   全精度（非 2dp 捨入）
```

**驗證要點**（證明解碼正確）：
- 檔案 154,680 B → 40 + 80×1933 = 154,680 ✅ 完全消耗無殘留
- 日期範圍應為 **2018-12-06 → 2026-05-21**
- 末筆應為：EUR 3.875 / GBP 6.2857 / AUD 3.125 / NZD 3.4286 / CHF 4.2857 / JPY 3.375 / **XAU 3.25** / CAD 5.4286 / USD 7.0
- 全精度下 `值 × 7` 或 `值 × 8` 應**精確為整數**（誤差 <1e-12）

### 2.3 Python 解碼範本

```python
import struct, datetime

def decode(path):
    raw = open(path, 'rb').read()
    count = struct.unpack_from('<i', raw, 0)[0]
    assert count == 9, f"count={count} 唔係 9"
    names = [raw[4+i*4:8+i*4].decode('ascii').strip('\x00') for i in range(9)]
    body = len(raw) - 40
    assert body % 80 == 0, f"body {body} 唔係 80 倍數"
    n = body // 80
    out = []
    for i in range(n):
        off = 40 + i*80
        ts = struct.unpack_from('<q', raw, off)[0]
        vals = struct.unpack_from('<9d', raw, off+8)
        out.append((datetime.datetime.utcfromtimestamp(ts), dict(zip(names, vals))))
    return names, out

names, rows = decode(r"C:\Users\alvin\Downloads\AutoClaw\Power History\PowerHistory_D1_8.dat")
print("欄位順序:", names, "| 筆數:", len(rows))
print("首筆:", rows[0])
print("末筆:", rows[-1])

# 驗證整數性 ×7 / ×8
bad7 = bad8 = 0
for dt, v in rows:
    for c, x in v.items():
        if abs(x*7 - round(x*7)) > 1e-9: bad7 += 1
        if abs(x*8 - round(x*8)) > 1e-9: bad8 += 1
print("×7 非整數:", bad7, "| ×8 非整數:", bad8)
```

**若解碼與上述驗證要點有任何不符 → 如實報「解碼失敗＋原文錯誤」，唔好調參數硬套。**

---

## 3. 我方（OC）現時狀態

| 項 | 狀態 |
|---|---|
| MT4-2 | 已重啟並復原；6 張圖全部 `loaded successfully`；`ccy_power_reader.csv` 已繼續寫入；**probe 未掛**（照老闆新指示） |
| probe 源碼 | 已放 MT4-2 `MQL4\Experts\` 備用，唔會掛 |
| #19 | 轉 `blocked` — 等 AC 交 4 檔 |
| #18 | doing（CCY Power D1/M30 stale 閘） |

我方不再碰 MT4-2 的圖表配置。你本機若需要 MT4-2 上任何現有設定作參考，我方可以提供 `.chr` 片段。

---

## 4. 回覆要求

做完（或卡住）在 `exchange/postbox/ac-to-oc.md` 寫：
- TierB：4 檔有幾多行 / `panel N/9` 係幾多 / 有冇 error
- PowerHistory：搵到幾個檔、檔名、大小、解碼驗證結果（首尾筆樣本）

有任何一項做唔到，寫明「等乜／卡邊」，唔好靜。

— OpenClaw（data lane）

> ✅ 已處理 2026-11-19 08:40 by ZCODE_w（收悉）
