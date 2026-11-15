# TSA Martingale Risk & Currency Fit Analyzer

## Complete Technical Specification v1.0

**Status:** Formal development specification  
**Date:** 2026-11-15  
**Source model:** `20261109_Fixed_SMA_MKD_Martingale_Calculator_Ver.5.3 (FF56) .xlsx`  
**Related data:** `Volatility Table.xlsx`, MartingaleScanner v1.0 output, SMA/MKD SET files  

---

## 1. Purpose

This module converts the intent of the existing Excel calculator into a maintainable web architecture for TSA (Trade Strategy Analyzer).

The module is a **risk estimator and strategy-fit analyzer**, not an EA tick-by-tick simulator.

The module answers six questions:

1. How does the SET build its Martingale grid?
2. How many lots can accumulate at each level?
3. How many pips does the grid cover?
4. What is the estimated drawdown and margin requirement at each level?
5. How far must price retrace from the last level to reach the weighted average entry price?
6. Is the grid coverage suitable for the selected symbol when compared with MartingaleScanner volatility ranges at the SET's intended timeframe and higher stress timeframes?

### 1.1 Design principle

The website must not reproduce spreadsheet cells. It must extract the spreadsheet's business logic into independent services:

```text
SET File
   |
   v
EA Adapter / SET Parser
   |
   v
Canonical Strategy Model
   |
   v
Martingale Grid Engine
   |
   +--------------------+
   |                    |
   v                    v
Risk Engine       Symbol / Capital Engine
   |                    |
   +----------+---------+
              |
              v
      TF Volatility Fit Engine
              |
              v
     Summary / Detail / Report
```

---

# 2. Excel-to-Web Mapping

| Existing Excel function | Web module | Responsibility |
|---|---|---|
| CCY1 | Grid & Risk Engine + Level Detail View | Single-strategy, level-by-level analysis |
| CCY28 | Multi-Symbol Evaluator | Apply one grid to multiple FX symbols |
| PipValue / D.Pip | Symbol Specification & Pip Value Service | Convert pips to account-currency money |
| Volatility Collection | Volatility Repository | Normalized, versioned MartingaleScanner data |
| Volatility Analysis | TF Fit Engine | Compare grid coverage with symbol volatility |
| Yellow input cells | SET Parser + Review/Override UI | User-editable assumptions and parameters |
| Strategy Highlight | Risk Summary | Consolidated decision-oriented output |

CCY1 and CCY28 must **not** become separate calculation engines. They are two views over the same calculation core.

---

# 3. Functional Architecture

## 3.1 Modules

### A. SET Upload

Responsibilities:

- accept `.set`, `.csv`, `.txt`;
- auto-detect UTF-8 / UTF-16LE when possible;
- calculate source-file hash;
- pass raw key/value pairs to the correct EA adapter;
- never silently discard an unknown parameter.

### B. EA Adapter Registry

Supported adapters in Phase 1:

```text
SMA_V3
SMA_PRO_V5
MKD_V3
MKD_PRO_V5
```

Every adapter converts vendor/EA-specific parameter names into the same Canonical Strategy Model.

### C. Grid Engine

Responsibilities:

- construct effective Martingale levels;
- calculate lot per level;
- calculate distance between levels;
- calculate cumulative distance;
- calculate cumulative lot;
- calculate weighted average entry;
- calculate recovery/breakeven distance.

### D. Risk Engine

Responsibilities:

- calculate estimated floating loss at every grid level;
- calculate estimated maximum drawdown scenario;
- expose loss-per-additional-pip after the final modeled level;
- maintain a distinction between pips risk and money risk.

### E. Symbol & Capital Engine

Responsibilities:

- Pip Size / Point / Digits normalization;
- Contract Size;
- Pip Value;
- FX conversion to account currency;
- margin requirement;
- XAU / CFD handling.

### F. Volatility Repository

Responsibilities:

- import Volatility Table.xlsx;
- normalize MartingaleScanner output;
- detect data errors;
- preview changes;
- publish immutable versions;
- retain rollback history.

### G. TF Fit Engine

Responsibilities:

- determine Primary TF from SET design;
- compare grid coverage against the same TF;
- run higher-TF stress comparisons;
- return raw 80% / 15% / 5% coverage ratios.

### H. Report Composer

Responsibilities:

- Strategy Summary;
- Level Detail;
- Capital Risk;
- Currency Fit;
- Stress Fit;
- assumptions and limitations;
- reproducibility metadata.

---

# 4. Canonical Strategy Model

All EA adapters MUST return this logical structure.

```text
Strategy
- strategyId
- sourceHash
- eaFamily
- eaVersion
- symbol (optional)
- primaryTf
- primaryTfSource
- lotMode
- pipstepMode
- entryLot
- lotExponent (optional)
- effectivePipstep (optional)
- maxTrades (optional)
- evaluationLevel (optional)
- manualLevels[]
- protectionRules[]
- assumptions[]
- parseWarnings[]
```

## 4.1 Modes

```text
lotMode:
  MANUAL
  DYNAMIC

pipstepMode:
  MANUAL
  DYNAMIC
```

The parser must store the **semantic mode**, not merely the numeric SET value.

For the current SMA Pro parameter interpretation:

- `PipstepMode=1` -> Manual.
- `LotsizeMode=0` -> Dynamic.

This mapping belongs in the SMA Pro adapter, not in the generic risk engine.

---

# 5. Grid Level Model

Each effective level becomes:

```text
GridLevel
- sequence
- sourceLevel
- lot
- stepPips
- distancePips
- cumulativeLot
- weightedEntryDistance
- averageEntryDistance
- breakevenPips
- estimatedDrawdown
- sourceFlags[]
```

Example source flags:

```text
MANUAL_LOT
DYNAMIC_LOT
MANUAL_STEP
MINIMUM_DYNAMIC_STEP
SPECIAL_ORDER
NORMAL_ORDER
ESTIMATED
```

---

# 6. EA Adapter Rules

## 6.1 SMA v3

### Lot logic

Dynamic lot progression:

```text
lot(n) = round(entryLot * lotExponent^(n-1), 2)
```

Rounding follows the documented two-decimal example.

After mathematical rounding, normalize against broker/symbol lot constraints if available.

### Pip Step logic

The correct simplified interpretation is:

- Level 1-6: individually configured Pips Step;
- Level 7 and later: reuse the configured Level 7+ Pips Step;
- Martingale level count is not inherently finite.

Therefore the web engine must never create infinite levels.

One of the following must terminate analysis:

1. SET-level stop/protection;
2. user-supplied `evaluationLevel`;
3. a product policy maximum used only as a computational guardrail.

The guardrail must not be presented as an EA rule.

---

## 6.2 SMA Pro v5

### Manual mode

Manual mode uses the values in Manual Setup.

Phase 1 supports the explicitly defined manual levels 1-16.

The engine must **not invent Level 17+ behavior**.

### Dynamic lot mode

```text
rawLot(n) = entryLot * lotExponent^(n-1)
lot(n) = round(rawLot(n), 2)
```

Then apply lotMin / lotStep / lotMax normalization if the Symbol Specification is available.

### Dynamic Pip Step

The manual states that **Effective Pips Step (Dynamic Mode)** is the minimum effective spacing and that the EA can dynamically increase that distance.

The exact internal dynamic formula is not required for this risk-estimation product.

For TSA:

```text
estimatedStep(n) = effectivePipstep
```

and mark the level:

```text
MINIMUM_DYNAMIC_STEP
ESTIMATED
```

Interpretation:

> this is a minimum-distance / dense-grid estimate, not a prediction of exact live order spacing.

### Lot-Charge

Lot-Charge is treated as an internal grid lot-compensation mechanism.

It is **not** modeled as a separate block of positions opened simultaneously with the first trade.

Phase 1 deliberately does not reconstruct exact Lot-Charge execution timing.

The report must disclose:

```text
Lot-Charge timing not simulated; simplified SET-visible lot exposure used.
```

---

## 6.3 MKD v3

Convert the explicit lot and PipStep fields into levels.

Conceptually:

```text
Level 1 -> lot1
Level 2 -> lot2, PipStep2
Level 3 -> lot3, PipStep3
...
```

For the simplified estimator, a zero/disabled lot terminates the effective chain unless the adapter has an explicit EA rule saying otherwise.

`slDist`, `beDist`, trailing and similar protection fields are captured as metadata/protection rules but Phase 1 does not reproduce their exact trigger timing.

---

## 6.4 MKD Pro v5

The normalized order chain is:

```text
Special 1st
   |
   | PipStepS2
   v
Special 2nd
   |
   | PipStep1  = Next Effective Pipstep
   v
Normal 1st
   |
   | PipStep2
   v
Normal 2nd
   |
   | PipStep3
   v
...
Normal 9th
   |
   v
10th+ shared settings
```

Confirmed mapping for the risk model:

```text
PipStepS2 = Special 1st -> Special 2nd
PipStep1  = Special 2nd -> Normal 1st
PipStep2  = Normal 1st -> Normal 2nd
...
```

Use `MaxTrades` and effective/valid lot configuration when determining the modeled endpoint.

STC, Power, Teleport and other entry filters are not reconstructed by the estimator.

---

# 7. Primary Timeframe Resolution

The original Excel included multi-TF thinking, but the website must make TF selection explicit.

## 7.1 Principle

Primary Fit must be based on the SET's intended strategy / Martingale timeframe.

D1 must **not** be used as a universal primary threshold.

## 7.2 Resolution order

Adapter should search for:

1. explicit strategy timeframe;
2. entry timeframe;
3. Core/Martingale timeframe;
4. EA period parameter;
5. user confirmation if multiple valid candidates remain.

Return:

```text
primaryTf
primaryTfSource
primaryTfConfidence
primaryTfCandidates[]
```

If confidence is insufficient, analysis pauses for user selection.

The user's selection becomes an auditable assumption/override.

---

# 8. Martingale Grid Calculation

Let:

```text
lot_i = lot of level i
s_i   = distance from previous effective level
D_i   = cumulative distance from first effective order
L_i   = cumulative lot through level i
```

## 8.1 Cumulative distance

```text
D_1 = 0
D_i = D_(i-1) + s_i
```

## 8.2 Cumulative lot

```text
L_i = SUM(lot_j), j=1..i
```

## 8.3 Weighted entry

```text
W_i = SUM(lot_j * D_j), j=1..i
```

Average entry distance from the first order:

```text
A_i = W_i / L_i
```

## 8.4 Breakeven / recovery distance

At the location of the latest level:

```text
BE_i = D_i - A_i
```

Interpretation:

> after level i has opened, price needs to retrace approximately `BE_i` pips from that level to return to the weighted average entry price, before considering spread, commission, swap and configured profit target.

---

# 9. Drawdown Calculation

Let `PV` be account-currency value per pip per one lot.

At level k:

```text
DD_k = PV * SUM[ lot_i * (D_k - D_i) ], i=1..k
```

Equivalent incremental form:

```text
DD_k = DD_(k-1) + PV * L_(k-1) * s_k
```

Both implementations must produce the same result in tests.

## 9.1 Why the formula matters

Drawdown is not determined only by final grid width.

Two SETs can both cover 500 pips but have materially different risk because lots are placed at different locations.

The engine therefore must preserve **lot-by-level placement**.

## 9.2 Loss slope after final modeled level

Once no additional modeled trade is added:

```text
lossPerExtraPip = PV * totalLot
```

This is a useful stress metric and should appear in Level Detail / Risk Summary.

---

# 10. Pip Value Engine

Money calculations must be driven by Symbol Specifications.

Required fields:

```text
symbol
baseCurrency
quoteCurrency
point
pipSize
digits
contractSize
lotMin
lotStep
lotMax
```

Account configuration:

```text
accountCurrency
leverage
```

## 10.1 Generic pip value

Per one lot:

```text
pipValueInQuote = pipSize * contractSize
```

If Quote Currency equals Account Currency:

```text
pipValueAccount = pipValueInQuote
```

Otherwise:

```text
pipValueAccount = pipValueInQuote * quoteToAccountConversion
```

Direction of conversion must follow the actual currency pair used by the rate service.

Never assume every pair is USD 10/pip.

---

# 11. Margin Engine

For one position:

```text
marginBase = lot * contractSize / leverage
```

Convert base-currency margin into account currency:

```text
marginAccount = marginBase * baseToAccountConversion
```

Total grid margin:

```text
totalMargin = SUM(marginAccount_i)
```

or equivalently use total lot exactly once if the same contract specification applies to every modeled order.

## 11.1 Excel issue that must not be migrated

The existing workbook contains Deposit Load logic where total lot can be multiplied by another already-aggregated total-lot field.

The web implementation must not reproduce that behavior.

Test invariant:

```text
marginBySummingLevels == marginUsingTotalLot
```

within the defined rounding tolerance.

---

# 12. XAU / Non-FX Normalization

XAU and CFDs must not inherit a hard-coded FX pip definition.

The Symbol Specification must provide:

```text
Point
Digits
Pip Size
Contract Size
Lot Step
```

### Behavior

| Available specification | Result |
|---|---|
| complete | calculate pips, DD and margin |
| Point/Digits only | allow normalized distance if possible; money result is incomplete |
| Contract Size/Pip Size missing | do not emit money DD or margin |

The UI must explain why a money result is unavailable rather than silently substituting FX defaults.

---

# 13. Volatility Data Model

The Volatility Table is generated from **MartingaleScanner v1.0 Indicator** output.

TSA does not reconstruct these distributions from OHLC.

Normalized record:

```text
VolatilityRecord
- symbol
- year
- timeframe
- band       // 80, 15, 5
- lowerPips
- upperPips
- scannerVersion
- sourceFileHash
- datasetVersion
```

Until the exact statistical interpretation of the three bands is formally documented, the website must retain the names:

```text
80% Range
15% Range
5% Range
```

Do not relabel them as P80, P95 or Pmax.

---

# 14. Volatility Import Pipeline

```text
Upload XLSX
   |
   v
Schema detection
   |
   v
Parse Range values
   |
   v
Normalize symbol / year / TF
   |
   v
Validate
   |
   v
Diff against Published version
   |
   v
Preview
   |
   v
User Publish
   |
   v
Immutable versioned dataset
```

## 14.1 Validation rules

Reject or flag:

- non-numeric lower/upper values;
- formulas/text accidentally embedded in range strings;
- repeated separators;
- missing range boundary;
- lower > upper;
- unknown timeframe;
- malformed year/timeframe heading;
- implausible large jumps compared with adjacent historical values.

Known examples that the validation layer must catch include malformed values such as:

```text
83103
32+152
395=632
286-546.
1667--2258
5820-5223   // reversed direction if interpreted as lower-upper
```

System behavior:

> never silently repair and publish source data.

Corrections require user confirmation and must be auditable.

---

# 15. Timeframe-Driven Volatility Fit

## 15.1 Core rule

```text
Primary Fit = SET Primary TF vs same-TF volatility
```

Higher timeframes are stress tests.

Typical ladder:

| Strategy TF | Primary | Stress +1 | Stress +2 |
|---|---|---|---|
| M5 | M5 | M15/M30 | H1 |
| M15 | M15 | M30 | H1/H4 |
| M30 | M30 | H1 | H4 |
| H1 | H1 | H4 | D1 |
| H4 | H4 | D1 | W1 if available |
| D1 | D1 | W1 | optional |

The ladder must adapt to the TFs actually present in the published Volatility dataset.

## 15.2 Coverage

```text
gridCoverage = distancePips of final modeled level
```

For each available band:

```text
coverage80 = gridCoverage / upper(80% Range)
coverage15 = gridCoverage / upper(15% Range)
coverage5  = gridCoverage / upper(5% Range)
```

Display the ratios directly.

Example interpretation:

```text
Grid Coverage: 690 pips
H1 80% Range Upper: 420
Coverage: 1.64x

H1 15% Range Upper: 650
Coverage: 1.06x

H1 5% Range Upper: 910
Coverage: 0.76x
```

This is more informative than reducing the result immediately to a single letter grade.

---

# 16. Primary Fit vs Stress Fit

The website should return two separate market concepts.

## 16.1 Primary Fit

Answers:

> Is this SET's grid appropriate for the symbol at the timeframe it was designed for?

Inputs:

```text
SET Primary TF
Grid Coverage
Same-TF 80/15/5 Ranges
```

## 16.2 Stress Fit

Answers:

> If the position persists into a larger market timeframe, what happens to coverage?

Inputs:

```text
Higher TF volatility
Same Grid Coverage
```

Do not replace Primary Fit with D1 simply because D1 represents a larger move.

---

# 17. Capital Survivability

Capital analysis is separate from market coverage.

The website should show:

```text
Estimated DD
Estimated Margin
DD + Margin
Initial Deposit
Raw Capital Load Ratio
```

Raw ratio:

```text
capitalLoad = (estimatedDD + margin) / initialDeposit
```

However, the **formal pass/caution/fail thresholds are not fixed in v1.0**.

Capital Threshold and Final-Level Buffer must be configurable policy settings added/confirmed during implementation.

Until then:

- show the raw number;
- do not claim that 50% is the official TSA pass/fail standard;
- Excel historical defaults may be shown only as legacy reference.

---

# 18. Result Model

```text
AnalysisResult
- strategySummary
- gridMetrics
- riskMetrics
- capitalMetrics
- primaryFit
- stressFits[]
- symbolComparison[]
- assumptions[]
- warnings[]
- sourceMetadata
```

## 18.1 Strategy Summary

Display:

```text
EA / Version
Symbol
Primary TF
Lot Mode
Pipstep Mode
Mode source
Entry Lot
Lot Exponent
Modeled Levels
Total Lot
Grid Coverage
```

## 18.2 Risk Summary

Display:

```text
Estimated Maximum Drawdown
Margin Requirement
DD + Margin
Loss per Additional Pip
Last-Level Breakeven Distance
```

## 18.3 Market Fit

Display by symbol:

```text
Primary TF
80% Range coverage
15% Range coverage
5% Range coverage
Stress +1
Stress +2
```

---

# 19. Website User Flow

## Step 1 - Upload SET

User action:

```text
Upload .set / .csv / .txt
```

System:

- hash file;
- identify EA;
- parse parameters;
- identify TF candidates;
- build Parse Warnings.

## Step 2 - Review Strategy

Show parsed values with a source label:

```text
SET
DERIVED
USER OVERRIDE
POLICY
```

User confirms:

- EA interpretation;
- Primary TF if ambiguous;
- Symbol if required;
- evaluation level if model is open-ended.

## Step 3 - Account / Symbol Configuration

Select or enter:

```text
Account Currency
Leverage
Initial Deposit
Symbol Specification
```

## Step 4 - Volatility Dataset

Default to latest Published dataset.

Show:

```text
Dataset Version
MartingaleScanner Version
Published Date
Source Hash
```

## Step 5 - Run Analysis

Execution order:

```text
Parse
-> Normalize
-> Build Grid
-> Calculate Pip Value
-> Calculate Level DD
-> Calculate Margin
-> Calculate Recovery
-> Resolve Primary TF
-> Calculate Primary Fit
-> Calculate Stress Fit
-> Compose Report
```

## Step 6 - Results

Tabs/views:

```text
Summary
Level Detail
Currency Fit
Assumptions & Warnings
```

## Step 7 - Export

Export must include reproducibility metadata.

---

# 20. UI Specification

## 20.1 Strategy Upload

Required components:

- drop zone;
- supported-format text;
- detected EA;
- parser status;
- parse warnings;
- file hash.

## 20.2 Strategy Review

Required fields:

- EA/version;
- Symbol;
- Primary TF;
- Lot Mode;
- Pipstep Mode;
- Entry Lot;
- Exponent;
- Effective Pipstep;
- Level count/evaluation level;
- protection metadata.

Each value must display its source.

## 20.3 Risk Summary

Cards/rows:

```text
Grid Coverage
Total Lot
Estimated MDD
Margin
Capital Load
Breakeven Distance
Loss / Extra Pip
```

No risk meaning may depend on color alone.

## 20.4 Level Detail

Columns:

```text
Level
Lot
Step Pips
Accumulated Pips
Cumulative Lot
Average Entry
Breakeven Pips
Estimated DD
Flags
```

## 20.5 Currency Fit

Columns:

```text
Symbol
Pip Value
Primary TF
Grid Coverage
80% Range Ratio
15% Range Ratio
5% Range Ratio
Stress +1
Stress +2
Estimated DD
Margin
Warnings
```

## 20.6 Volatility Admin

Functions:

```text
Upload
Validate
View Errors
Diff
Preview
Publish
Rollback
```

Publishing requires explicit confirmation.

---

# 21. Function Contracts

Language-independent contracts:

```text
parseSet(rawFile)
  -> CanonicalStrategy
  -> ParseWarning[]

buildGrid(strategy, symbolSpec)
  -> GridLevel[]
  -> Assumption[]

calculatePipValue(symbolSpec, accountCurrency, fxRates)
  -> PipValueResult

calculateRisk(grid, pipValue)
  -> RiskMetrics

calculateMargin(grid, symbolSpec, leverage, fxRates)
  -> MarginMetrics

resolvePrimaryTf(strategy)
  -> TimeframeResolution

compareVolatility(gridCoverage, primaryTf, dataset)
  -> PrimaryFit
  -> StressFit[]

composeAnalysis(...)
  -> AnalysisResult
```

---

# 22. Error Handling / Guardrails

| Condition | Required behavior |
|---|---|
| EA unsupported | stop calculation; show recognized SET keys |
| Primary TF ambiguous | request user selection; log override |
| Dynamic Pipstep missing minimum | do not invent distance; stop DD/coverage calculation |
| Open-ended grid without evaluation level | request evaluation level |
| Pip Value unavailable | still calculate pips coverage; money risk unavailable |
| XAU specification incomplete | do not use FX defaults |
| higher-TF data missing | return Primary Fit only; Stress = No Data |
| malformed volatility value | prevent dataset publish |
| conversion rate stale | flag date/age in result |
| NaN/Infinity/negative invalid input | fail fast with field-specific message |

---

# 23. Reproducibility Metadata

Every exported report should contain:

```text
Engine Version
EA Adapter Version
SET File Hash
Volatility Dataset Version
MartingaleScanner Version
Symbol Specification Version
FX Rate Timestamp
Account Currency
Leverage
Initial Deposit
Manual Overrides
Assumptions
Calculation Timestamp
```

This ensures the same result can later be reproduced.

---

# 24. Test Specification

## 24.1 Calculation parity

Use fixed Excel examples as regression fixtures after correcting known Excel formula errors.

Required checks:

```text
Lot sequence
Accumulated pips
Cumulative lot
Estimated DD
Breakeven distance
Pip Value
Margin
```

Target numerical tolerance:

```text
<= 0.5%
```

except where Excel itself contains a known incorrect formula.

## 24.2 Required unit tests

### Dynamic Lot

Given:

```text
entryLot = 0.05
lotExponent = 1.2
```

Expected progression includes documented rounding behavior such as:

```text
0.0864 -> 0.09
```

### SMA v3 Level 7+

Create more than 7 modeled levels and verify every Level 7+ uses the shared Level 7+ step rule.

### SMA Pro Manual

Verify the engine does not invent Level 17.

### Dynamic Pipstep

Verify:

```text
modeledStep >= minimumEffectivePipstep
```

and result has the `ESTIMATED` flag.

### Margin invariant

Verify:

```text
SUM(level margins) == margin(total lot)
```

within rounding tolerance.

### TF Fit

For an M30 strategy:

```text
Primary = M30
Stress +1 = H1
Stress +2 = H4
```

D1 must not automatically replace M30.

### Volatility validation

Test malformed values including:

```text
83103
32+152
395=632
1667--2258
reversed ranges
```

Dataset publication must be blocked for unresolved errors.

### XAU

Remove Contract Size from the fixture and verify that TSA does not fabricate a money DD value.

---

# 25. Known Simplifications

Phase 1 intentionally does not model:

- exact Dynamic Pipstep algorithm;
- actual Lot-Charge execution timing;
- RSI/Band/STC signal timing;
- Teleport exact movement;
- spread widening;
- slippage;
- gap risk;
- swaps;
- broker stop-out engine;
- exact SMA Pro Level 17+ behavior;
- portfolio correlation between simultaneously active symbols.

These limitations are acceptable because the system's stated purpose is **risk estimation and strategy comparison**.

---

# 26. Legacy Excel Behaviors to Remove

Do not port:

1. spreadsheet row-number-dependent business rules;
2. `#REF!` references;
3. `_xludf` formulas;
4. Excel Stocks Data Type dependency;
5. Google `IMPORTHTML` dependency;
6. duplicate Total Lot multiplication in Deposit Load;
7. A/B/C volatility classification as a strategy safety conclusion;
8. fixed 28-column architecture;
9. formulas duplicated independently between CCY1 and CCY28.

---

# 27. Development Work Breakdown

| Start | Duration | Work | Owner | Definition of Done |
|---|---:|---|---|---|
| W1 | 3 days | Canonical Model + Adapter interfaces | Developer | 4 sample SET families parse into canonical model |
| W1 | 2 days | Corrected Excel regression fixtures | Alvin + Developer | expected results frozen |
| W2 | 5 days | Grid / Risk / Pip Value / Margin engines | Developer | unit tests pass |
| W3 | 5 days | Volatility import / validation / versioning | Developer | invalid data cannot publish |
| W4 | 4 days | TF Fit Engine | Developer | same-TF + higher-TF mapping correct |
| W4 | 4 days | Strategy Review + Summary UI | Front-end | source/assumption visible for every key input |
| W5 | 5 days | Level Detail + Multi-Symbol Fit | Front-end + Developer | single/multi-symbol views use same engine |
| W6 | 5 days | Export + reproducibility + UAT | Team | full acceptance matrix passes |

---

# 28. Recommended Repository Structure

```text
docs/martingale/
├── README.md
├── architecture.md
├── calculation-engine.md
├── set-parser.md
├── ea-mapping/
│   ├── sma-v3.md
│   ├── sma-pro-v5.md
│   ├── mkd-v3.md
│   └── mkd-pro-v5.md
├── volatility-fit.md
├── symbol-pip-margin.md
├── data-model.md
└── test-cases.md
```

Recommended code separation:

```text
src/
├── parsers/
├── models/
├── engines/
│   ├── grid/
│   ├── risk/
│   ├── margin/
│   └── volatility-fit/
├── data/
│   ├── volatility/
│   └── symbol-specs/
├── reports/
└── ui/
```

---

# 29. Master Calculation Flow

```text
[1] Upload SET
      |
      v
[2] Identify EA Adapter
      |
      v
[3] Parse to Canonical Strategy
      |
      v
[4] Resolve / Confirm Primary TF
      |
      v
[5] Resolve Symbol Specification
      |
      v
[6] Build Simplified Martingale Grid
      |
      +--> Manual values
      |
      +--> Dynamic Lot formula
      |
      +--> Dynamic minimum Pipstep estimate
      |
      v
[7] Calculate cumulative pips / lots / weighted entry
      |
      v
[8] Calculate Pip Value
      |
      v
[9] Calculate Level DD / MDD estimate / recovery
      |
      v
[10] Calculate Margin / Raw Capital Load
      |
      v
[11] Load Published MartingaleScanner dataset
      |
      v
[12] Compare same-TF 80/15/5 Ranges
      |
      v
[13] Compare higher-TF Stress Ranges
      |
      v
[14] Compose Summary + Level Detail + Currency Fit
      |
      v
[15] Attach assumptions + source versions + hashes
      |
      v
[16] Display / Export
```

---

# 30. Product Boundary Statement

Every report should include the following concept prominently:

> **Estimated Risk Analysis** — TSA uses SET-visible parameters and MartingaleScanner historical ranges to estimate Martingale grid risk and symbol suitability. Dynamic entry logic, filters and live execution conditions can cause actual trading behavior to differ from the estimate.

The module is intended for strategy design comparison, risk screening and review. It is not a guarantee of future loss, drawdown, execution or profitability, and it is not investment advice.

---

# 31. Final Engineering Decision

The core architecture is:

```text
EA-specific logic stays in Adapters.
Financial mathematics stays in Engines.
Market history stays in versioned Volatility data.
Symbol mechanics stay in Symbol Specifications.
UI only orchestrates and displays results.
```

This separation preserves the original Excel's intent while removing its main weaknesses: duplicated formulas, spreadsheet-position dependencies, fragile external-data functions, unclear assumptions and difficulty supporting multiple EA families.

