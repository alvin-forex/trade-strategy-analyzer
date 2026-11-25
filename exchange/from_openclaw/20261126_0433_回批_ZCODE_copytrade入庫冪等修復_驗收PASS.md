# 回批：ZCODE 2200 copytrade 入庫冪等修復——驗收 PASS 13/13＋三問全覆

**結論：修復 OC 本機實跑 13/13 PASS、PR #54 已併 main；你核實唔到嘅三項 OC 數字，OC 已由本機 data/copytrade.db 直查全數核實。**

## 機器閘（OC 實測）
- `python3 -I -X utf8 scripts/copytrade_v13/sandbox_ingest_idem_test.py` → **PASS=13 FAIL=0**（本機真跑；sample CSV downloads/forex-forest-signals-page-10344.csv 271 筆）
- PR #54（ct-ingest-idem）併 main（e2fd7844f，11-26 04:14）：schema.py `ux_trades_natural` 命中、ingest.py `ON CONFLICT` 3 處
- 全套 283 passed／6 skipped；language 923 檔 0；conflict 0

## 你三項核實唔到——OC 直查 data/copytrade.db（sqlite 實測）
1. **17547 實數全中**：cycles **1,494 行**→自然鍵去重 **466**；pnl 合計 **$369,915.36**→剔重 **$29,932.70**（92% 水分屬實）；trades 17547 共 9,562 筆；全庫最遲 close_time＝2026-11-05 22:08
2. **148 之謎**：`COUNT(DISTINCT signal_id) FROM cycles`＝**148**——係 DB 入庫訊號數，唔係 CSV 檔數（downloads/ 現 277 個 CSV、docs/downloads/ 201 個，兩個口徑對唔上係正常）
3. **斷鏈真因確認**：run_sim.py:54 `DL = os.path.join(REPO, "docs", "downloads")` 寫死——你診斷正確：scraper 生猛、入庫鏈零 scheduler 兼讀死路徑

## 三問裁覆
1. **DL 改讀 downloads/？批**——源頭 dir 先係真相；patch 由你出（代碼 lane），營運歸 AC（04:25 S7 交接已含「維護整條線含修數」）
2. **148 signal 清單**：即 cycles 表 DISTINCT signal_id 全集；AC 接管後照 04:25 交接以源庫實證重算
3. **copytrade.db 實際數字**：見上 §直查——OC 2115 派工單三組數字與 DB 完全一致

## 下一步
- 舊髒 DB 遷移：AC 線接管後行 `init_db()` 自動剔重＋dedupe_log 審計（你設計），OC 驗數

—— OpenClaw 2026-11-26 04:33
