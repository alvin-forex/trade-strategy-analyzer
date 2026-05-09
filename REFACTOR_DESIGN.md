# TSA 層級偵測重構設計

> 日期：2026-05-09
> 狀態：設計完成，待執行

## 1. 核心改動：從 Pip-Based 改為 Lot-Based 層級

### 1.1 現有問題
- 層級用硬編碼 pip 範圍：L1=0-50, L2=50-100, L3=100-150, L4+=150+
- 同 EA 實際設定嘅馬丁層級完全無關
- Global baselines 基於錯誤嘅分層

### 1.2 新做法

**層級偵測優先級：**
1. **SET 檔 lot mapping**（primary）— 已有 `signal_lot_mapping.json`
2. **CSV Lots 分佈推算**（fallback）— 分析 unique lot values
3. **AutoLot 偵測** — unique lots >> SET layers 時標記 AL

**層級顯示：** L1 到 L9+（統一截斷）

### 1.3 Lot → Level 映射邏輯

```python
def assign_level(trade_lot, lot_layers):
    """
    trade_lot: CSV 中的 Lots 值
    lot_layers: SET 定義的 [(level, lot_size), ...]
    
    Returns: (level_name, is_autolot)
    """
    if not lot_layers:
        return None  # trigger fallback
    
    # 找最接近的 lot layer
    best_level = min(lot_layers, key=lambda x: abs(x[1] - trade_lot))
    
    # AutoLot: 如果距離太大（>20%偏差），標記 AL
    tolerance = best_level[1] * 0.2
    is_autolot = abs(trade_lot - best_level[1]) > tolerance
    
    level = best_level[0]
    if level >= 9:
        return ('L9+', is_autolot)
    return (f'L{level}', is_autolot)
```

### 1.4 Fallback（無 SET 檔）

當 signal 冇 SET mapping 時：
1. 收集所有交易嘅 unique lots
2. 按 lots 值排序，細 lots = 低層級
3. 最多 9 級，多餘嘅歸入 L9+
4. 如果 lots 值全部一樣 → 只有 L1（flat bet 如 S10/GEM）

```python
def infer_levels_from_lots(trades):
    unique_lots = sorted(set(round(t['lots'], 4) for t in trades))
    if len(unique_lots) == 1:
        return {unique_lots[0]: 'L1'}
    
    mapping = {}
    for i, lot in enumerate(unique_lots):
        if i >= 8:  # L9+
            mapping[lot] = 'L9+'
        else:
            mapping[lot] = f'L{i+1}'
    return mapping
```

### 1.5 AutoLot 偵測

**判定規則：** 
- SET 有 N 層，但 CSV 出現超過 N×2 種 unique lots → AutoLot
- 標記方式：層級顯示為 `AL` 而非具體層數

**受影響 signals：**
- 10437 (DW): 40 unique vs 10 SET
- 10864 (SMA): 27 unique vs 10 SET
- 1470 (MKD): 29 unique vs 9 SET
- 1980 (SMA): 23 unique vs 10 SET
- 23617 (MKD): 21 unique vs 8 SET
- 3291 (DW): 23 unique vs 10 SET
- 16596 (S10): 1 unique → flat bet, 非AutoLot
- 19849 (Flash): 17 unique vs 1 SET → AutoLot + CheckLevels

## 2. Global Baselines 重計算

### 2.1 現有 baselines（基於 pip 範圍，作廢）
```python
GLOBAL_TP_BASELINES = {'L1': 53.0, 'L2': 129.8, 'L3': 137.3, 'L4+': 195.5}
GLOBAL_SL_BASELINES = {'L1': 44.7, 'L2': 63.3, 'L3': 58.4, 'L4+': 70.9}
```

### 2.2 新 baselines（基於 lot-based 層級）
需要跑一次全部 signals，按 lot-based 層級重新計算：
- L1-L9+ 各層嘅 P85 TP/SL
- L1-L9+ 各層嘅 P50/P75 profit

**策略：** 先用程式掃一次生成新的 baseline 常數，再硬編碼回腳本。

## 3. UI 改動

### 3.1 公式改為 Mouseover
- CoP/CoL 評分表嘅 Score Details 欄 → 改為 info icon (ℹ️)
- Hover 時顯示完整公式拆解
- 精簡表格闊度

### 3.2 可排序
- 所有表頭加上 click-to-sort
- JavaScript 排序（client-side）
- 默認按值博率（期望值）降序排列

### 3.3 Summary 表格
- 從 L1/L2/L3/L4+ 改為動態顯示 L1 到 L{max_achieved}
- 如果只有 L1 和 L2 有交易，只顯示兩欄

## 4. 受影響檔案

| 檔案 | 改動內容 |
|---|---|
| `generate_all_levels_from_csv.py` | 重構所有層級偵測 + HTML 生成 |
| `dde_v4_scorer.py` | LEVEL_RANGES 改為動態 + lot-based |
| `generate_signal_ranking.py` | LEVEL_RANGES 改為動態 |
| `signal_lot_mapping.json` | 可能需要擴展加入 AutoLot 標記 |
| `PRD.md` | 更新文件 |

## 5. 執行順序

1. 寫 `compute_lot_based_levels()` 核心函數
2. 寫 baseline 重計算腳本，生成新常數
3. 重構 `generate_all_levels_from_csv.py`
4. 加入 UI 改動（mouseover + sorting）
5. 測試 + 部署
