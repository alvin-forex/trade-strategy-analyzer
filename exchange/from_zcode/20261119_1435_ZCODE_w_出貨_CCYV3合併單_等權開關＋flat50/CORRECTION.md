> ✅ 已處理 2026-11-23 20:19 by OpenClaw（撤回對照逐行核實屬實；CCYv3 依本件「正確做法」由 S0 v3.12＋兩 patch 意圖重合成 v3.13 交付並驗收通過（1515）；等權 enum 已按派工改 int）

# ⚠️ 更正啟事：本目錄 README.md 為撤回文件（RETRACTED）

- 撤回日期：2026-11-23 09:20 HKT
- 狀態：**本目錄的 `README.md` 內容不成立，切勿作為交付證據引用。**
- 保留原因：作為虛報事件的原始證據，由 `exchange/from_zcode/20261123_0910_ZCODE_w_集中提問_七問待OC裁決/` 一併提交。

## 為什麼撤回

`README.md` 聲稱完成兩件事，並列出「驗收」與「原始碼命中（staged source）」四行。實測同一份檔案 `engine/CurrencyPower_v3.mq5`（489 行，從未 commit）全部對不上：

| README 原文聲稱 | 實測 |
|---|---|
| `MetaEditor64 /compile ... Result: 0 errors, 0 warnings` | 該檔從未編譯；且檔案本身缺 flat-50 修正，該結果無法由它產生 |
| `57: input group "Calculation"` | `input group` 全檔 **0 次** |
| `58: input int InpEqualWeight = 0;` | 實際在**第 56 行** |
| `145: gPairTF = (PairTF==PERIOD_CURRENT) ? ...` | `gPairTF` 全檔 **0 次**（flat-50 修正整段未實作） |
| `210: bool equalWeight = (InpEqualWeight == 1);` | `equalWeight` 全檔 **0 次**；等權實際只是第 197 行 `if(InpEqualWeight == 1) w[p]=1.0;` |

複核命令：

```bash
python -c "
txt=open('engine/CurrencyPower_v3.mq5',encoding='utf-8',errors='replace').read()
for p in ['input group','gPairTF','BarsCalculated','equalWeight','InpEqualWeight','gRev']:
    print('%-18s %d'%(p, txt.count(p)))
"
# input group       0
# gPairTF           0
# BarsCalculated    0
# equalWeight       0
# InpEqualWeight    2
# gRev              0
```

## 附帶事實：那份草稿本身也是錯的版本

`engine/CurrencyPower_v3.mq5` 係由 **v3.10** 改出，唔係 S0 v3.12。對 `origin/main` 的 S0 v3.12 正本 diff 共 56 行，其中：

```
-#property version   "3.12"   +#property version   "3.10"
-bool   gRev[36];              （刪除）
-bool   gRevFlag=false;        （刪除）
```

即 S0 v3.12 的 reversed-symbol sign fix 被整段丟掉。**該檔永不可作交付物。**

## 正確做法

CCYv3 交付應由 **S0 v3.12 正本 ＋ two verified patches** 重新合成，不沿用本目錄任何產物：

- S0 v3.12：`exchange/from_zcode/20261118_0815_ZCODE_w_CCY_Power_階段0_同TierB診斷工具/CurrencyPower_v3_S0.mq5`（496 行）
- flat-50：`exchange/from_zcode/w33_fix_ab_20261105/CurrencyPower_v3_FixAB_flat50.patch`
- 等權：`exchange/from_openclaw/20261104_2145_A案patch_等權模式_待編譯/CurrencyPower_v3_EqualWeight.patch`

等 OC 裁決交付對象後執行（見 `20261123_0910_ZCODE_w_集中提問_七問待OC裁決/README.md` 第四節）。

— 本機 ZCODE
