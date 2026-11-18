# 已遷移：50 個原始 .dat → GitHub Release

日期：2026-11-18 19:25 HKT
決定：老闆 19:18「2 A」

## 為何搬

50 個 `.dat` 共 101.6 MB 直接 commit 入 `main`，令 repo 膨脹至 ~685 MB（`.git` 1.1 GB），
接近 GitHub 單檔 100 MB 硬限與 repo 1 GB 建議上限。

## 搬去邊

Release `powerhistory-20261118`
https://github.com/alvin-forex/trade-strategy-analyzer/releases/download/powerhistory-20261118/PowerHistory_50dat_20261118.tar.gz

- tarball 19,361,561 bytes（102 MB → 19 MB）
- sha256 `8d2041cdf6ce6ba4f2993c766859999be44fa853c8c7ff4c51d47b02985dddf3`
- 下載回驗證：sha256 一致、tar 內 50 檔齊

## repo 保留

| 檔 | 用途 |
|---|---|
| `PowerHistory_MANIFEST.json` | 50 檔逐檔 sha256＋大小＋TF＋period＋格式規格 |
| `D1_8_decoded_fixture.csv` | 解碼 golden fixture（1933 行） |
| `PowerHistory解碼報告.md` | 解碼驗證報告全文 |
| 本檔 | 遷移記錄與取回方法 |

## 依賴現況（分析結論：冇程式需要 repo 內原檔）

- 全 repo 唯一提到 `PowerHistory_H4_1.dat` 的地方係 `engine/tests/test_research_period.py:44`，
  但該測試用 `write_dat()` **自己造檔**，唔讀真檔。
- `engine/research/period_probe_run.py` 用 `--dir` 參數指向外部目錄，唔硬碼 repo 路徑。

→ 刪除 repo 內原檔**唔影響任何測試或程式**。

## 取回

```bash
curl -L -O https://github.com/alvin-forex/trade-strategy-analyzer/releases/download/powerhistory-20261118/PowerHistory_50dat_20261118.tar.gz
sha256sum PowerHistory_50dat_20261118.tar.gz   # 應為 8d2041cd...
tar -xzf PowerHistory_50dat_20261118.tar.gz -C ./PowerHistory
python -m engine.research.period_probe_run --dir ./PowerHistory --tf H4 --ccy EUR
```
