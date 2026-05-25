# 🚨 Bug Report：Pip-based Level 分類錯誤

> 發現日期：2026-05-25
> 影響範圍：55/73 個信號（75%）
> 嚴重程度：**HIGH**

## 問題描述

`dde_v4_scorer.py` 第 28-32 行同第 72-86 行用 **淨利潤（Net Profit）** 去判斷交易層級：

```python
# 錯誤方法：用 profit 硬分層
def compute_layer_net_profit(profit):
    if profit < 50:    return 'L1'
    elif profit < 100: return 'L2'
    elif profit < 150: return 'L3'
    elif profit < 200: return 'L4'
    ...
```

但 EA 嘅馬丁層級係用 **手數（Lot Size）** 決定嘅，同賺幾多無關。

## 影響數據

### L1 分類差異（最關鍵）

| 指標 | 數值 |
|------|------|
| 差異超過 10% 嘅 signal | **45/55（82%）** |
| 平均 L1% 差異 | **32.6%** |
| 最大差異 | Signal 1470 (MKD) = **+69.9%** |

**解讀：** 用 pip-based 分類，1470 號信號有 80.9% 被歸為 L1，但實際 lot-based 只有 11.1%。即係話大量高層級交易被錯誤歸入 L1，令 L1 嘅勝率同盈虧數據完全失真。

### WAL（加權平均層級）差異

| 指標 | Pip-based | Lot-based | 差異 |
|------|-----------|-----------|------|
| 平均 WAL | 1.35 | 1.83 | +0.48 |

**結果：** Pip-based 系統性低估咗馬丁深度，令 Martin Discipline 分數偏高。

### ML 分數（Martin Layers, 佔總分 25%）影響

| 指標 | 數值 |
|------|------|
| 平均 ML 分數差異 | 36.5 分 |
| 對總分影響 | **9.1 分** |
| 最大單一信號影響 | **23.4 分** |

### Top 排名變化

**大跌嘅信號：**
| Signal | EA | 舊分 | 新分 | 跌幅 |
|--------|-----|------|------|------|
| 21698 | DW | 85.5 | 69.3 | -16.2 |
| 13461 | MKD | 86.5 | 76.1 | -10.4 |
| 12962 | MKD | 96.6 | 90.7 | -5.9 |
| 14592 | MKD | 89.4 | 83.5 | -5.8 |

**大升嘅信號：**
| Signal | EA | 舊分 | 新分 | 升幅 |
|--------|-----|------|------|------|
| 19849 | Flash | 62.2 | 85.6 | +23.4 |
| 33101 | DW | 72.5 | 82.3 | +9.8 |
| 17547 | DW | 81.0 | 88.0 | +7.0 |

## 根本原因分析

### 點解會發生？

1. **歷史遺留：** 初版系統（v1.0）用 pip-based 分類係因為當時冇 SET 檔案數據
2. **重構唔完整：** v0.7 已經將 detailed reports 改為 lot-based，但 `dde_v4_scorer.py` 漏改
3. **冇整合測試：** 冇測試對比兩種分類方式嘅結果差異
4. **`compute_layer_net_profit()` 仍然存在：** 作為 fallback 被調用

### 調用鏈

```python
# dde_v4_scorer.py:140-142
if lot_layers:
    lv = compute_layer_lot(t['lots'], lot_layers)    # ✅ 正確
else:
    lv = compute_layer_net_profit(t['net_profit'])    # ❌ 錯誤 fallback
```

**問題：** 當 `score_v4()` 冇傳入 `lot_layers` 時，就會觸發錯誤嘅 pip-based fallback。

### 邊度調用咗但冇傳 lot_layers？

需要檢查所有調用 `score_v4()` 嘅地方，確認係咪都有傳入 `lot_layers`。

## 修復方案

1. **刪除 `compute_layer_net_profit()`** — 呢個函數不應存在
2. **修改 fallback 為 CSV lot-based** — 從交易嘅 unique lot 值推算層級
3. **新增測試** — 確保 pip-based 唔會再出現
4. **新增 CI check** — 檢測任何用 profit/pips 判斷層級嘅代碼

## 防止再犯

1. **Code Review Checklist：** 新增「層級判斷必須用 lot-based」
2. **Lint Rule：** 搜尋 `net_profit` 同 `level` 喺同一函數出現
3. **單元測試：** 用已知 lot 對照表驗證分類結果
4. **PRD 明確記錄：** Section 13 已記錄 lot-based 為唯一正確方法

---

_丁蟹 🦀 | 2026-05-25_
