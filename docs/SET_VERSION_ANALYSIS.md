# SET Version Active Period Analysis

## Problem Statement

TSA (Trade Strategy Analyzer) 系統中，每個 Signal 可能有多個 SET（EA 參數設定檔）版本。SET 檔案包含 `lot_layers`（如 L1=0.01, L2=0.02, L3=0.04），用於評估 Martin Discipline 分數。

**核心問題**：如何判斷 SET 版本的切換點（`active_from` / `active_to`）？

---

## 已知數據源

### 1. SET 檔案元數據
- **修改時間**：檔名中的日期（如 `2025-09-28`, `2026-05-24`, `2026-02-18`)
- **EA_VERSION**：內部版本號（如 `20250410`, `20260424`, `20241128`)
- **Lot Layers**：`lot1-5`, `EntryLot`, `lotExp`, `Lots`, `LotMul` 等
- **Comment/Magic**：`commentB`, `MagicNumberB` 等

### 2. CSV 交易數據
- **Open Time**：每筆交易的開倉時間（如 `2025-05-05` → `2026-05-01`)
- **Lots**：實際下單手數
- **Comment**：交易備註（可能含版本信息，如 `Wayne Class`, `Dragon Wave_XZ2`)
- **Magic Number**：EA 識別碼

### 3. 交易行為特徵
- **Lot 分佈**：某時段用 `L1=0.01, L2=0.02`，另一時段用 `L1=0.02, L2=0.04`
- **Comment 格式變化**：如 `Wayne Class v1` → `Wayne Class v2`
- **交易頻率/模式**：不同版本的進場邏輯可能不同

---

## 範例分析

### Signal #3291（Dragon Wave）

**已知數據：**
- 958 個 Comment 後綴（`_AZ2`, `_BZ2`, `_FZ2`...），Magic=1
- SET 版本：
  - v1（無日期）：`(3291)Dragon Wave v1.00AUDCAD_M15_Both_.set`
  - v2（2026-02-18）：`(3291)Dragon Wave v1.00AUDCAD_M15_Both_2026-02-18_13-39-22.set`
- CSV：2024-01-20 → 2026-06-12
- Lot 模式：`Lots=0.01, LotMul=2.5` → L1=0.01, L2=0.025, L3=0.0625...

**觀察：**
- SET v1 和 v2 的 `EA_VERSION=20241128` **相同**
- SET v1 和 v2 的 `Lots=0.01, LotMul=2.5` **相同**
- CSV 中所有 Dragon Wave 交易的 Lot 都是 `0.01`（Level 1），無明顯 Lot 變化
- Comment 後綴 `_AZ2`, `_BZ2` 是 **動態生成**（可能是 order ticket 或 instance ID），不反映版本

**結論**：SET v1 和 v2 **實際上是同一版本**，只是檔案保存時間不同。`active_from` = CSV 開始日期 `2024-01-20`，`active_to` = `null`（仍在活躍）。

---

### Signal #12023（Wayne Class / SMA Pro）

**已知數據：**
- Comment = `Wayne Class`, Magic = 1313
- SET 版本：
  - v1（2025-09-28）：`EA_VERSION=20250410`
  - v2（2026-05-24）：`EA_VERSION=20260424`
- CSV：2025-05-05 → 2026-05-01（最新交易在 2026-04-30）
- Lot 模式：兩版本 `EntryLot=0.02, lotExp=1.5` **相同**

**關鍵問題：**
- SET v1 日期 `2025-09-28` **晚於** CSV 首筆交易 `2025-05-05`
- SET v2 日期 `2026-05-24` **晚於** CSV 最後交易 `2026-05-01`
- 兩版本的 Lot 配置相同，無法從 Lot 分佈判斷切換點

**可能的解釋：**
1. **SET 檔案是「設定保存時間」而非「開始使用時間」**
2. Signal owner 在 2025-05-05 開始使用 SMA Pro，但直到 2025-09-28 才保存 SET 檔案
3. 2026-05-24 的 SET v2 可能是**更新後保存**，但 CSV 中尚未有使用新版本的交易

**切換點判斷策略：**
- **保守策略**：假設 SET v1 從 CSV 首筆交易開始使用 → `active_from = 2025-05-05`
- **激進策略**：使用 SET 檔案日期 → `active_from = 2025-09-28`
- **混合策略**：取 CSV 首筆交易和 SET 日期的中間值

---

## 判斷策略建議

### 策略一：SET 檔案日期優先（適用於有明確日期的 SET）

```
active_from = SET filename date（如 2026-02-18）
active_to = 下一版本的 active_from，或 null（無下一版本）
```

**優點**：簡單直接
**缺點**：無法覆蓋 SET 保存前的交易（如 #12023 的情況）

---

### 短策略二：CSV Comment/Magic 變化優先

```
按 Open Time 排序交易
檢測 Comment 或 Magic Number 的變化點
變化點 = SET 版本切換點
```

**優點**：能捕捉實際行為變化
**缺點**：
- 很多 EA 不改 Comment（如 Wayne Class 兩版本 Comment 相同）
- Comment 後綴可能是動態生成的（如 Dragon Wave 的 `_AZ2`）

---

### 短策略三：Lot 分佈變化優先

```
統計每月/每週的 Lot 分佈
檢測 Lot 模式變化（如 0.01 → 0.02）
變化點 = SET 版本切換點
```

**優點**：能捕捉 Martin 配置變化
**缺點**：
- 如果 SET 版本只是改進場邏輯，Lot 可能不變（如 #12023）
- 需要足夠的交易數據才能統計

---

### 短策略四：EA_VERSION 內部版本號優先

```
比較 SET 檔案的 EA_VERSION 參數
不同 EA_VERSION = 確定的版本切換
```

**優點**：最準確的版本判斷
**缺點**：
- 不是所有 SET 都有 EA_VERSION
- 有些版本更新不改 EA_VERSION

---

### 推薦：混合策略（Confidence-Based）

**核心邏輯**：結合多種數據源，計算 Confidence Factor。

```
confidence = {
  'ea_version_match': bool,    // EA_VERSION 是否變化
  'lot_config_match': bool,    // Lot 配置是否變化
  'comment_match': bool,       // Comment 是否變化
  'set_date_coverage': bool,   // SET 日期是否覆蓋 CSV 區間
  'lot_distribution_shift': bool  // 實際 Lot 分佈是否有 shift
}
```

---

## Pseudo-Code：SET Version Active Period Detector

```python
def detect_set_active_periods(signal_id, csv_data, set_files):
    """
    Detect active_from/active_to for each SET version.
    
    Returns: dict {
        signal_id: int,
        set_versions: [
            {
                'version_id': str,
                'active_from': date,
                'active_to': date | None,
                'confidence': float,  // 0.0 ~ 1.0
                'confidence_factors': dict,
                'lot_config': dict,
                'ea_version': str
            }
        ],
        'uncovered_trades': [  // SET 日期未能覆蓋的交易
            {
                'date': date,
                'lot': float,
                'comment': str,
                'magic': int
            }
        ]
    }
    """
    
    # Step 1: Parse all SET files for this signal
    set_versions = []
    for set_file in set_files:
        config = parse_set_file(set_file)
        set_versions.append({
            'version_id': extract_version_id(set_file.filename),  # v1, v2...
            'filename': set_file.filename,
            'file_date': extract_date_from_filename(set_file.filename),  # 2026-02-18 or None
            'ea_version': config.get('EA_VERSION', ''),
            'lot_config': extract_lot_config(config),  # {L1: 0.01, L2: 0.02...}
            'comment': config.get('commentB', ''),
            'magic': config.get('MagicNumberB', 0)
        })
    
    # Sort by file_date (earliest first)
    set_versions.sort(key=lambda x: x['file_date'] or '9999-99-99')
    
    # Step 2: Analyze CSV trade distribution
    trade_timeline = analyze_trade_timeline(csv_data)
    # {
    #   'date_range': {'min': '2025-05-05', 'max': '2026-05-01'},
    #   'lot_distribution': {'2025-05': [0.01, 0.02], '2026-04': [0.01, 0.02]},
    #   'comment_changes': [('2025-09-28', 'Wayne Class v1', 'Wayne Class v2')],
    #   'magic_changes': []
    # }
    
    # Step 3: Match SET versions to trade periods
    
    for i, version in enumerate(set_versions):
        confidence_factors = {
            'ea_version_match': False,
            'lot_config_match': False,
            'comment_match': False,
            'set_date_coverage': False,
            'lot_distribution_shift': False
        }
        
        # Strategy A: EA_VERSION change detection
        if i > 0 and version['ea_version'] != set_versions[i-1]['ea_version']:
            confidence_factors['ea_version_match'] = True
        
        # Strategy B: Lot config change detection
        if i > 0 and version['lot_config'] != set_versions[i-1]['lot_config']:
            confidence_factors['lot_config_match'] = True
        
        # Strategy C: Comment change detection (from CSV)
        comment_change_date = find_comment_change_date(
            trade_timeline['comment_changes'],
            version['comment']
        )
        if comment_change_date:
            confidence_factors['comment_match'] = True
        
        # Strategy D: SET date coverage check
        if version['file_date']:
            if trade_timeline['date_range']['min'] <= version['file_date'] <= trade_timeline['date_range']['max']:
                confidence_factors['set_date_coverage'] = True
        
        # Strategy E: Lot distribution shift detection
        if version['file_date']:
            lot_before = get_lot_distribution_before(csv_data, version['file_date'])
            lot_after = get_lot_distribution_after(csv_data, version['file_date'])
            if lot_before != lot_after:
                confidence_factors['lot_distribution_shift'] = True
        
        # Calculate active_from
        active_from_candidates = []
        
        if confidence_factors['ea_version_match']:
            # Highest confidence: EA_VERSION changed
            # Find first trade after previous version's EA_VERSION
            active_from_candidates.append(find_first_trade_after_ea_version_change(csv_data, set_versions[i-1]))
        
        if confidence_factors['lot_config_match']:
            # High confidence: Lot config changed
            active_from_candidates.append(find_first_trade_with_new_lot_pattern(csv_data, version['lot_config']))
        
        if confidence_factors['comment_match'] and comment_change_date:
            # Medium confidence: Comment changed in CSV
            active_from_candidates.append(comment_change_date)
        
        if version['file_date']:
            # Low confidence: Use SET file date
            active_from_candidates.append(version['file_date'])
        
        # If no SET date, use CSV start date
        if not version['file_date']:
            active_from_candidates.append(trade_timeline['date_range']['min'])
        
        # Choose the most confident candidate
        # Priority: EA_VERSION > Lot Config > Comment > SET Date > CSV Start
        if confidence_factors['ea_version_match']:
            active_from = active_from_candidates[0]  # EA_VERSION change date
        elif confidence_factors['lot_config_match']:
            active_from = active_from_candidates[1]  # Lot change date
        elif confidence_factors['comment_match']:
            active_from = active_from_candidates[2]  # Comment change date
        elif version['file_date']:
            active_from = version['file_date']
        else:
            active_from = trade_timeline['date_range']['min']
        
        # Calculate active_to
        if i < len(set_versions) - 1:
            active_to = set_versions[i+1]['active_from']
        else:
            active_to = None  # Still active
        
        # Calculate confidence score
        confidence_score = calculate_confidence_score(confidence_factors)
        # score = (ea_version_match * 0.4 + lot_config_match * 0.3 + 
        #          comment_match * 0.15 + set_date_coverage * 0.1 + 
        #          lot_distribution_shift * 0.05)
        
        version['active_from'] = active_from
        version['active_to'] = active_to
        version['confidence'] = confidence_score
        version['confidence_factors'] = confidence_factors
    
    # Step 4: Identify uncovered trades
    uncovered_trades = []
    for trade in csv_data:
        trade_date = trade['Open Time']
        covered = False
        for version in set_versions:
            if version['active_from'] <= trade_date <= (version['active_to'] or '9999-99-99'):
                covered = True
                break
        if not covered:
            uncovered_trades.append(trade)
    
    return {
        'signal_id': signal_id,
        'set_versions': set_versions,
        'uncovered_trades': uncovered_trades,
        'analysis_summary': generate_summary(set_versions, uncovered_trades)
    }


def calculate_confidence_score(factors):
    """
    Calculate confidence score based on factor weights.
    
    Weights:
    - ea_version_match: 0.4 (highest - definitive version change)
    - lot_config_match: 0.3 (high - Martin config change)
    - comment_match: 0.15 (medium - might be cosmetic)
    - set_date_coverage: 0.1 (low - SET might be saved later)
    - lot_distribution_shift: 0.05 (supplementary evidence)
    """
    weights = {
        'ea_version_match': 0.4,
        'lot_config_match': 0.3,
        'comment_match': 0.15,
        'set_date_coverage': 0.1,
        'lot_distribution_shift': 0.05
    }
    
    score = sum(weights[k] for k, v in factors.items() if v)
    return round(score, 2)


def extract_lot_config(set_params):
    """
    Extract lot layer configuration from SET params.
    
    Different EA types have different lot parameters:
    - SMA Pro: EntryLot + lotExp + pipstep2-8 + lotsize2-8
    - Dragon Wave: Lots + LotMul
    - MKD Pro: lot1-5 + PipStep1-5
    - Flash: Lot (fixed)
    """
    ea_type = detect_ea_type(set_params.get('EA_NAME', ''))
    
    if ea_type == 'SMA':
        return {
            'mode': 'multiplier',
            'base_lot': float(set_params.get('EntryLot', 0)),
            'lot_exp': float(set_params.get('lotExp', 1)),
            'levels': [float(set_params.get(f'lotsize{i}', 0)) for i in range(2, 9)],
            'pipsteps': [float(set_params.get(f'pipstep{i}', 0)) for i in range(2, 9)]
        }
    elif ea_type == 'DragonWave':
        return {
            'mode': 'multiplier',
            'base_lot': float(set_params.get('Lots', 0)),
            'lot_mul': float(set_params.get('LotMul', 1)),
            'pipstep_mul': float(set_params.get('PipStepMul', 1))
        }
    elif ea_type == 'MKD':
        return {
            'mode': 'explicit',
            'levels': [float(set_params.get(f'lot{i}', 0)) for i in range(1, 6)],
            'pipsteps': [float(set_params.get(f'PipStep{i}', 0)) for i in range(1, 6)]
        }
    else:
        return {'mode': 'unknown'}


def find_lot_distribution_shift(csv_data, set_versions):
    """
    Analyze monthly Lot distribution to find potential version shift points.
    
    Returns: list of potential shift dates with Lot pattern change.
    """
    monthly_lot_stats = {}
    
    for trade in csv_data:
        month = trade['Open Time'][:7]  # '2025-05'
        lot = float(trade['Lots'])
        
        if month not in monthly_lot_stats:
            monthly_lot_stats[month] = {'unique_lots': set(), 'lot_counts': {}}
        
        monthly_lot_stats[month]['unique_lots'].add(lot)
        monthly_lot_stats[month]['lot_counts'][lot] = monthly_lot_stats[month]['lot_counts'].get(lot, 0) + 1
    
    # Find months with Lot pattern change
    shift_candidates = []
    months = sorted(monthly_lot_stats.keys())
    
    for i in range(1, len(months)):
        prev_pattern = monthly_lot_stats[months[i-1]]['unique_lots']
        curr_pattern = monthly_lot_stats[months[i]]['unique_lots']
        
        if prev_pattern != curr_pattern:
            shift_candidates.append({
                'shift_month': months[i],
                'prev_pattern': sorted(prev_pattern),
                'curr_pattern': sorted(curr_pattern)
            })
    
    return shift_candidates
```

---

## Confidence Factor 應用於 Martin Discipline 分數

### 問題：SET 版本 Uncertainty 如何反映在 Martin 分數？

**建議方案**：

```
final_martin_score = raw_martin_score * confidence_weight

confidence_weight = {
    'high': 1.0,    // confidence >= 0.8
    'medium': 0.85, // confidence >= 0.5
    'low': 0.7,     // confidence >= 0.3
    'very_low': 0.5 // confidence < 0.3
}
```

### 視覺化呈現

在 Martin Autopsy Report 中：

```html
<div class="confidence-indicator">
  <div class="confidence-bar" style="width: 85%"></div>
  <span class="confidence-label">85% Confidence</span>
</div>

<div class="confidence-factors">
  <span class="factor positive">✓ EA_VERSION changed</span>
  <span class="factor positive">✓ Lot config changed</span>
  <span class="factor neutral">○ Comment unchanged</span>
  <span class="factor negative">✗ SET date outside CSV range</span>
</div>
```

---

## 特殊 Case 處理

### Case 1: SET 檔案日期晚於 CSV 最後交易

**範例**：#12023 SET v2（2026-05-24）晚於 CSV 最後交易（2026-05-01）

**處理**：
- `active_from = 2026-05-24`（未來日期）
- 記錄為「SET version not yet reflected in trades」
- Confidence = 0.1（very low）

### Case 2: SET 檔案無日期

**範例**：#3291 SET v1 `(3291)Dragon Wave v1.00AUDCAD_M15_Both_.set`（無日期）

**處理**：
- 使用 CSV 首筆交易日期作為 `active_from`
- Confidence = 0.5（medium）

### Case 3: 多 EA Signal（如 #10437）

**範例**：#10437 有 Gemini Client + Flash + Stable Helper 三個 EA

**處理**：
- 按 Comment/Magic 分組交易
- 每組獨立判斷 SET 版本切換
- 需要 **多 SET 匹配邏輯**

---

## 實作建議

### Phase 1: 基礎版（SET 日期優先）

```python
# 最簡單實作：直接使用 SET 檔案日期
for set_file in set_files:
    version = {
        'active_from': set_file.file_date or csv_start_date,
        'active_to': next_version.file_date or None
    }
```

### Phase 2: 進階版（Confidence-Based）

```python
# 加入 Confidence Factor 計算
version['confidence'] = calculate_confidence_score(factors)
version['martin_score_weighted'] = raw_score * get_weight(version['confidence'])
```

### Phase 3: 自動化版（Algorithm Detection）

```python
# 自動檢測 Lot 分佈變化、Comment 變化
shift_points = detect_version_shifts_from_csv(csv_data)
version['active_from'] = shift_points[0]['date'] if shift_points else set_file.file_date
```

---

## 總結

### 最佳判斷策略（推薦）

| 優先級 | 策略 | Confidence Weight | 適用情況 |
|--------|------|-------------------|----------|
| 1 | EA_VERSION變化 | 0.4 | SET 有內部版本號，且版本號變化 |
| 2 | Lot Config變化 | 0.3 | SET lot1-5, EntryLot, LotMul 等參數變化 |
| 3 | CSV Comment變化 | 0.15 | CSV 中 Comment 格式有明確版本標記 |
| 4 | SET檔案日期 | 0.1 | SET 檔名有日期，且日期在 CSV區間內 |
| 5 | Lot分佈變化 | 0.05 | CSV每月Lot分佈有shift |

### Confidence Threshold 建議

- **High Confidence（≥0.8）**：可直接使用 SET lot_layers 計算 Martin 分數
- **Medium Confidence（0.5~0.8）**：使用 SET lot_layers，但加註「估計值」
- **Low Confidence（<0.5）**：使用 CSV 實際 Lot 分佈估算，不使用 SET lot_layers

---

## 下一步行動

1. **實作 `detect_set_active_periods()` 函數**（Phase 2）
2. **更新 Martin Autopsy V3/V4 引擎**，支援 Confidence Factor
3. **處理特殊 Cases**：#12023（SET晚於CSV）、#3291（無日期SET）、#10437（多EA）
4. **建立 SET↔CSV Cross-Reference Cache**，避免每次重新計算