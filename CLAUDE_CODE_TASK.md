# Claude Code Optimization Task: TSA Phase 1

## Context

You are optimizing the **Trade Strategy Analyzer (TSA)** system — a Python-based trading signal analysis tool that generates HTML ranking reports deployed to GitHub Pages.

## Task Priority

### P0 — Critical (Must Complete)

1. **Implement DDE v5 Unified Scoring** (ranking-based, 4 dimensions)
2. **Fix CoP Win Rate Calculation** (currently always 100%, should use all trades)
3. **Add $1K DD% Dimension** (6-tier grading: S/A/B/C/D/F)
4. **Replace Pickle with SQLite Storage** (persist after reboot)

### P1 — High Impact

5. **EA_MAP De-duplication** (single source of truth in config.py)
6. **Jinja2 Templates** (separate HTML from Python)
7. **Portfolio Correlation Analysis** (Pearson correlation matrix)

## Key Files to Read

1. `PRD.md` — Full specification (v0.8)
2. `TSA_Feature_Summary.md` — Feature overview + architecture
3. `REFACTOR_DESIGN.md` — Modular architecture design
4. `TSA_Risk_Management_Optimization.md` — $1K risk framework

## DDE v5 Scoring Formula (User Approved 2026-05-26)

| Dimension | Weight | Calculation |
|---|---|---|
| Win Rate | 15% | True win rate × 100 (no normalization) |
| Profit Factor | 20% | Avg profit pips / Avg MAX LOSE pips (trim 3σ) |
| $1K DD% | 25% | Real DD% (lower is better) |
| Martin Discipline | 40% | WAL (Weighted Average Layer) |

**Ranking logic:**
```python
# 1. Calculate raw values for all Signal×CCY pairs
# 2. Rank within each dimension
# 3. Percentile = (rank - 1) / (N - 1) × 100
# 4. Score = WR×15% + PF×20% + DD×25% + Martin×40%
```

## Red Card Rules

- Net Pips ≤ 0
- Trade Count < 20
- Max Loss Pips > 500 (single trade)
- Win Rate < 50%

## Acceptance Criteria

- `pytest tests/` — All tests pass
- HTML reports render correctly
- GitHub Pages auto-deploy from `output/`
- Mobile-friendly (horizontal scroll)
- Top 10 signals similar to v4 baseline

## Architecture Target

```
tsa/
├── config.py                 # EA_MAP single source of truth
├── models.py                 # Data models
├── data/
│   ├── csv_loader.py         # Unified CSV reading
│   ├── lot_mapping.py        # SET file parsing
│   ├── ea_detector.py        # EA detection (defined once)
│   └── store.py              # SQLite storage
├── scoring/
│   ├── dde_v5.py             # Pure scoring function
│   ├── layer_stats.py        # Layer analysis
│   ├── tpsl.py               # TP/SL recommendations
│   └── blacklist.py          # Blacklist logic
├── ranking/
│   ├── signal.py             # Signal ranking
│   ├── ccy.py                # CCY ranking
│   └── symbol.py             # Symbol ranking
├── render/
│   ├── templates/            # Jinja2 templates
│   └── *.py                  # Page renderers
├── api/
│   └── server.py             # FastAPI app
└── cli.py                    # Unified CLI
```

## SQLite Schema

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

## Important Notes

- User language: Cantonese (Hong Kong)
- Deployment: GitHub Pages + Telegram Bot
- All reports must be mobile-friendly
- Use Chinese labels (except technical terms)
- DO NOT modify existing v4 tests without adding v5 equivalents

---

*Prepared by 丁蟹 🦀 | 2026-06-07*