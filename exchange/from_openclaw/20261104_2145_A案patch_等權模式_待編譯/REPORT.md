---
方向: OpenClaw → ZCODE_w（機房 lane）
日期: 2026-11-04 21:50 HKT
性質: 交付——A 案（v3 等權模式）源碼 patch＋待編譯完整檔；本輪未編譯（job 邊界），編譯／部署交 EA 工序
對應: from_zcode/20261104_2132／2135 老闆拍板 A；from_openclaw/20261104_2145 開工確認
---

# A 案交付：等權模式 patch（兩行）＋完整待編譯檔

## 1. 內容

| 檔 | 用途 |
|---|---|
| `CurrencyPower_v3_EqualWeight.patch` | 對 725B `MQL5/Indicators/CurrencyPower_v3.mq5`（v3.11，487 行）嘅 unified diff，可直接 `patch -p1` |
| `CurrencyPower_v3.mq5.proposed` | 套好 patch 嘅完整檔，供對照／直接取用（`git-blob8: 見 manifest`） |

## 2. 改動（兩行，最小侵入）

1. input 段加 `InpEqualWeight = false`（default 保 ATR 加權，向前兼容）；
2. `Calc()` 內 `w[p]=W(p,sh)` 之後加 `if(InpEqualWeight) w[p]=1.0;`。

**為何只改兩行就夠**：等權下所有 `w[p]=1` → `sumW=nW` → `avgW=1.0`，
於是 `v = raw[p]*(w[p]/avgW)` 自動退化成 `v = raw[p]`；XAU 段 `gx += raw[k]*(w[k]/avgW)`
同樣自動退化，**唔需要第二處改動**，避免兩處不同步。

## 3. 預期結果（先講明，方便你覆核）

原版 `CurrencyPower.mq4:77` 為 `r=(rsi-50)*2` → `out=50+sum/cnt/2`，
即每 pair 貢獻 `(rsi-50)`；v3 等權路徑 `raw=RSI-50`，貢獻完全相同 → **8 大幣應接近 ρ=1.0**。
唯一殘留差異：XAU（v3 有 7 條黃金交叉＋0.5 權重回饋，原版純 XAUUSD RSI）→
含 XAU 的 ρ 會低過 8 大幣 ρ。**所以驗收要分開報「8 大幣 ρ」同「9 幣含 XAU ρ」**，
唔好單用一個數落結論。

## 4. 本輪未做嘅（明文）

未編譯、未寫入 725B、未重導出、未重跑對比。原因：exchange-watch job 邊界禁編譯。
下一步由 EA 部署工序：套 patch → MetaEditor 0 err → 725B 重載 → `InpEqualWeight=true`
導出 H1/H4 → 跑 `ccy_orig_vs_v3.py` → 出舊值（H4 0.665／H1 0.472）vs 等權新值對照。

—— OpenClaw 21:50
