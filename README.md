# Trade Strategy Analyzer 🦀

上傳 CSV + SET 檔案，即時生成策略分析報告。

## 使用方法

1. 打開 [GitHub Pages](https://alvincyleungtw2-beep.github.io/trade-strategy-analyzer/)
2. 上傳交易數據 CSV
3. 上傳策略設定 SET（可多個）
4. 點擊「開始分析」
5. 查看報告 / 下載 HTML

## 功能

- CSV 交易數據解析
- 倉位重構（按 Symbol + Direction + CloseTime 分組）
- 整體統計（勝率、PF、Max DD、Sharpe 等）
- 貨幣對排名
- 收益曲線 SVG
- 倉位明細
- 純瀏覽器運算，無需伺服器

## 馬丁剖析法 V3

分析馬丁格爾策略嘅交易歷史，生成完整 V3 剖析報告。

### 用法

```bash
python generate_martin_autopsy_v3.py <csv_path> [--output OUTPUT_PATH]
```

### 分析模組

| Part | 模組 | 說明 |
|------|------|------|
| 1 | CCY×Direction 總覽 | 按貨幣對×方向嘅完整統計（EV$、Odds$、MFE/MAE）|
| 2 | MFE/MAE 散點圖 | 每層交易嘅最大有利/不利偏移可視化 |
| 3 | TP/SL 混合方案 | Soft SL = MAE×1.2, Hard SL = MaxMAE×1.3, TP = AvgMFE |
| 4 | 排行榜 | A級以上層級按 Rating + EV$ 排序 |
| 5 | 黑名單 | 5因子 Danger Score 量化風險 |
| 6 | 恢復力 | 最深層虧損 vs 最佳層 EV，計算恢復所需交易次數 |

### V3 核心改動

- ❌ 百分比評分 → ✅ 絕對數據（PIP、金額）
- ❌ 主觀評級為主 → ✅ Odds$ + EV$ 為核心指標
- ✅ MFE/MAE 散點圖（每層可視化）
- ✅ 混合方案 SL（Soft + Hard）
- ✅ 恢復力分析（輸一次要追幾耐）
- ✅ 黑名單 Danger Score（5因子量化）

## 支援的 EA

- SMA v3.00（維加斯通道）
- MKD v3.00（STC + 方向控制）
- Flash / S10 / DragonWave

## 技術

- 純 HTML + JavaScript
- 無外部依賴
- 離線可用
- 移動端友好
