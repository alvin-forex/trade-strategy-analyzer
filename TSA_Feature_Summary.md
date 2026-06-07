# TSA Feature Summary for Claude Code Optimization

> **Generated:** 2026-06-07
> **Version:** v0.8 (PRD.md)
> **Target:** Claude Code optimization task

---

## 1. System Overview

### 1.1 Purpose

**Trade Strategy Analyzer (TSA)** analyzes trading signals from AlgoForest platform to:
- Evaluate strategy accuracy and efficiency
- Identify best Copy Trade opportunities
- Generate ranking reports for 69+ signals
- Provide TP/SL recommendations per currency pair

### 1.2 Current Architecture

```
trade_strategy_analyzer/
├── PRD.md                              # Full specification (v0.8)
├── generate_all_levels_from_csv.py     # Main scoring engine (52KB/1356 lines)
├── generate_signal_ranking.py          # Signal ranking HTML (~10KB/294 lines)
├── dde_v4_scorer.py                    # DDE v4 scorer
├── dde_v5_scorer.py                    # DDE v5 scorer (designed, not implemented)
├── output/                             # HTML reports (GitHub Pages deployed)
│   ├── signal_ranking_dde_v3.html
│   ├── ccy_ranking.html
│   ├── detailed_comparison_all_levels_*.html (69 files)
│   └── martin_v4_*.html (69 files)
├── scripts/
│   ├── api_server.py                   # FastAPI (localhost:8787)
│   └── history_manager.py              # SQLite analysis history
├── samples/                            # 69 CSV data files
└── docs/reports/                       # Martin Autopsy reports
```

### 1.3 Deployment

- **GitHub Pages:** https://alvin-forex.github.io/trade-strategy-analyzer/
- **API Server:** localhost:8787 (FastAPI)
- **Telegram Bot:** HTML report delivery

---

## 2. Implemented Features (v0.8)

### 2.1 DDE Scoring System (v3/v4/v5)

| Version | Status | Description |
|---|---|---|
| **DDE v3** | ✅ Implemented | Trigger Rate 40% + Alpha Capture 40% + DDE 20% |
| **DDE v4** | ✅ Implemented | Martin Discipline (WAL) + 7 dimensions |
| **DDE v5** | 🔜 Designed | Unified ranking-based scoring (4 dimensions) |

**DDE v5 Design (approved by user 2026-05-26):**

| Dimension | Weight | Calculation |
|---|---|---|
| Win Rate | 15% | True win rate × 100 (no normalization) |
| Profit Factor | 20% | Avg profit pips / Avg MAX LOSE pips (trim 3σ outliers) |
| $1K DD% | 25% | Real DD% for $1,000 account |
| Martin Discipline | 40% | WAL (Weighted Average Layer) |

**Ranking-based logic:**
```python
# 1. Calculate raw values for all Signal×CCY pairs
# 2. Rank within each dimension (higher/lower is better)
# 3. Convert rank to percentile: (rank - 1) / (N - 1) × 100
# 4. Weighted sum = WR×15% + PF×20% + DD×25% + Martin×40%
```

### 2.2 Lot-Based Level Detection

- **Fixed (2026-05-25):** Replaced pip-based LEVEL_RANGES with lot-based mapping
- **Source:** SET file `signal_lot_mapping.json` (primary), CSV lots (fallback)
- **Levels:** L1 to L9+ (unified truncation)
- **AutoLot Detection:** 6 signals flagged (unique lots >> SET layers)

### 2.3 Signal Ranking

- **69 signals** ranked by DDE v4/v5 score
- **Columns:** Signal, EA, CCY count, Score, Win%, Trades, Profit, DD, PF, TF, LV
- **EA Tags:** DW/SMA/MKD/S10/Flash/GEM with CSS colors
- **DD Color Grading:** 🟢 <$3K, 🟡 $3K-$6K, 🔴 >$6K

### 2.4 CCY Ranking

- **Currency pair × Signal combinations** (972 pairs)
- **$1K DD% 6-tier grading:** S(<5%), A(5-10%), B(10-15%), C(15-20%), D(20-30%), F(>30%)
- **Red Card Rules:** Net Pips ≤ 0, Trades < 20, Max Loss > 500 pips, WR < 50%

### 2.5 Martin Autopsy V3

- **Complete analysis:** CCY×Direction overview, MFE/MAE scatter plots, TP/SL hybrid solution
- **Rating system:** Odds$ + EV$ based (no subjective grading)
- **Blacklist:** 5-factor Danger Score quantification
- **Recovery analysis:** How many trades to recover from deepest loss

### 2.6 TP/SL Recommendation Engine

- **Formula:** TP = P85 of Max Pips, SL = P85 of Max Loss Pips (trim outliers)
- **Small sample fallback:** n < 30 → use global percentiles
- **Only in CoP section** (CoL is recovery strategy, different logic)

### 2.7 Copy Trade Suggestion Engine

- **Decision logic:** Expectancy, Martin dependency, Win Rate, CoP/CoL best scores
- **Confidence levels:** 🟢 High / 🟡 Medium / 🔴 Low
- **Output:** Recommended strategy + Wait Pips + TP/SL + rationale

---

## 3. Known Issues (P0-P1 Priority)

### 3.1 P0 - Critical Issues

| # | Issue | Impact | File |
|---|---|---|---|
| 1 | **CoP Win Rate always 100%** | 20% weight wasted, scoring distorted | `generate_symbol_ranking.py` |
| 2 | **v3/v4/v5 scoring not unified** | Rankings don't interoperate | Multiple files |
| 3 | **$1K DD dimension missing** | Fatal for small accounts | `dde_v4_scorer.py` |

### 3.2 P1 - High Impact Issues

| # | Issue | Impact | File |
|---|---|---|---|
| 4 | **HTML string concatenation** | Hard to maintain, UI changes require Python edits | All generators |
| 5 | **Pickle storage (reboot clears)** | No persistence, unreliable | Multiple files |
| 6 | **EA_MAP duplicated 3 times** | Maintenance inconsistency | `config.py`, `ea_detector.py`, generators |
| 7 | **No portfolio correlation analysis** | May pick highly correlated CCYs | Not implemented |
| 8 | **Small sample handling weak** | n < 10 may inflate scores unfairly | Scoring functions |

### 3.3 P2 - Long-term Improvements

| # | Issue | Status |
|---|---|---|
| 9 | No Walk-Forward Analysis | Not implemented |
| 10 | No ML signal quality prediction | Not implemented |
| 11 | No market state detection | Not implemented |

---

## 4. Refactor Design (from REFACTOR_DESIGN.md)

### 4.1 Proposed Modular Architecture

```
tsa/
├── config.py                 # Global config (EA_MAP, LEVEL_RANGES, paths) - single source of truth
├── models.py                 # Data models (dataclass/TypedDict)
├── data/
│   ├── csv_loader.py         # CSV reading (unified read_csv_trades)
│   ├── lot_mapping.py        # SET file parsing + lot→level mapping
│   ├── ea_detector.py        # EA detection + mapping (defined once)
│   └── store.py              # SQLite unified storage interface
├── scoring/
│   ├── dde_v5.py             # score_v5 pure function (no I/O, no HTML)
│   ├── layer_stats.py        # Layer analysis
│   ├── tpsl.py               # TP/SL recommendation
│   └── blacklist.py          # Blacklist logic
├── ranking/
│   ├── signal.py             # Signal ranking logic
│   ├── ccy.py                # CCY ranking logic
│   └── symbol.py             # Symbol ranking logic
├── render/
│   ├── templates/            # Jinja2 .html template files
│   │   ├── _base.html
│   │   ├── signal_ranking.html
│   │   ├── ccy_ranking.html
│   │   └ martin_autopsy.html
│   └── *.py                  # Page renderers
├── api/
│   └ server.py               # FastAPI app
└── cli.py                    # Unified CLI entry point
```

### 4.2 SQLite Storage (replace Pickle)

```sql
CREATE TABLE signal_scores (
    signal_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    ea_type TEXT,
    dde_v5_score REAL,
    wr_score REAL, pf_score REAL, dd_score REAL,
    ml_score REAL, sc_score REAL, he_score REAL,
    red_card INTEGER DEFAULT 0,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(signal_id, symbol)
);
```

### 4.3 Jinja2 Templates (replace HTML string concatenation)

- HTML completely separated from Python
- Templates in `render/templates/`
- Renderer Python files only handle data → template rendering

---

## 5. Priority Tasks for Claude Code

### Phase 1 (P0 - Critical)

| Task | Description | Acceptance Criteria |
|---|---|---|
| **Task 1** | Implement DDE v5 unified scoring | pytest passes, HTML reports render correctly |
| **Task 2** | Fix CoP Win Rate calculation | Win Rate based on all trades, not just profitable |
| **Task 3** | Add $1K DD% dimension to scoring | 6-tier grading (S/A/B/C/D/F) in all rankings |
| **Task 4** | SQLite storage (replace Pickle) | Data persists after reboot, queries work |

### Phase 1 (P1 - High Impact)

| Task | Description | Acceptance Criteria |
|---|---|---|
| **Task 5** | EA_MAP de-duplication | Single definition in `config.py` |
| **Task 6** | Jinja2 templates for HTML | Templates in separate files, Python only renders |
| **Task 7** | Portfolio correlation analysis | Pearson correlation matrix for CCY returns |

---

## 6. Input Files for Claude Code

### Required Reading

1. **PRD.md** - Full specification (v0.8, 15KB+)
2. **TSA_Feature_Summary.md** - This file
3. **REFACTOR_DESIGN.md** - Modular architecture design
4. **TSA_Risk_Management_Optimization.md** - $1K account risk framework

### Key Python Files

1. `dde_v4_scorer.py` - Current scorer (needs v5 replacement)
2. `generate_signal_ranking.py` - Signal ranking generator
3. `generate_ranking_ccy_v5.py` - CCY ranking generator
4. `generate_all_levels_from_csv.py` - Main analysis pipeline

### Test Files

1. `tests/test_dde_v4_scorer.py` - Existing pytest tests (32 tests pass)
2. Sample CSV files in `samples/` directory

---

## 7. Verification Standards

### Testing

- `pytest tests/` - All tests pass
- New unit tests for v5 scoring functions
- Integration tests for SQLite storage

### Deployment

- GitHub Pages auto-deploy from `output/` directory
- HTML reports render correctly in browser
- Mobile-friendly (horizontal scroll for tables)

### Regression Check

- Compare new v5 rankings with v4 baseline
- Top 10 signals should be similar (high WR + low WAL + low DD)
- Red card counts should be consistent

---

## 8. Quick Reference

### EA Families

| EA | Entry Logic | Martin Type | Layers | TP Mode |
|---|---|---|---|---|
| DW (Dragon Wave) | Wave pattern | LotMul×2.5 | 8 | VirtualTP |
| SMA | Vegas tunnel | lotExp + pipstep | 7-15 | DollarMode + DynamicTP |
| MKD | STC + direction | PipStep grid | 6-10 | PipStep tracking |
| S10 | Fixed lotSize | Flat bet Martin | 0 or 10 | Trailing |
| Flash | CheckLevels | — | 11 | — |
| GEM | No Martin | — | 0 | — |

### Level Detection

- **Primary:** SET file `signal_lot_mapping.json` (lot → level mapping)
- **Fallback:** CSV unique lots → infer levels by sorting
- **AutoLot:** Flag when unique lots >> SET layers

### Red Card Rules

- Net Pips ≤ 0
- Trade Count < 20
- Max Loss Pips > 500 (single trade)
- Win Rate < 50%

---

## 9. Contact & Context

- **User:** Alvin (Hong Kong, Cantonese speaker)
- **AI Assistant:** 丁蟹 (Ding Xie style)
- **Platform:** OpenClaw + Claude Code
- **Deployment:** GitHub Pages + Telegram Bot

---

*This summary provides Claude Code with complete context for TSA optimization task.*