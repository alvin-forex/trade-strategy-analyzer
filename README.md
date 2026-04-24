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

## 支援的 EA

- SMA v3.00（維加斯通道）
- MKD v3.00（STC + 方向控制）
- Flash / S10 / DragonWave

## 技術

- 純 HTML + JavaScript
- 無外部依賴
- 離線可用
- 移動端友好
