# scripts/ 腳本索引（TSA 遷移 P6 標記，2026-11-23）

> 本索引照 `docs/admin/TSA_ARCHITECTURE_AUDIT.md` §2 判準整理：CI 引用／排程接線／數據鏈近 7 日產物 → 活的；檔名帶日期尾碼＋只出現在歷史 commit（11-04–11-06 導航／配色／修復波次）→ 已退役。審計基數 84（活 12＋一次性 72，11 月中盤點）；其後新增加按同判準歸類，下表為現況實錄。

## 活的（14）——生成鏈／QA 閘／排程接線，照常維護

| 腳本 |
|---|
| `build_board.py` |
| `ccy_power_history_api.py` |
| `date_range_review.py` |
| `extract_signal_data.py` |
| `generate_health_json.py` |
| `prep_ranking_data.py` |
| `run_scheduled_reviews.py` |
| `signal_anomaly_detector.py` |
| `signal_ea_timeline.py` |
| `signal_lot_mapping_upgrade.py` |
| `signal_walk_forward.py` |
| `tasks_board_gen.py` |
| `tsa_qa_check.py` |
| `update_ccy_power.py` |

## 已退役（83）——歷史波次遺留，唔好重跑

> 以下腳本均為 11-04–11-06 導航／配色／修復波次（`w5*`／`w6_*`／`w8_*`／`p0_*`／`p1a_*`／`reg187_*`／`tbnav_*`／`wfinal_*` 等）及同判準歸類檔：任務完結即退役。**唔刪（歷史可追溯），唔好重跑**——重跑會對現行頁面套用過時波次補丁（§2.2 處理建議）。

| 腳本 |
|---|
| `algoforest_downloader.py` |
| `algoforest_scraper.py` |
| `analyze_signal_entry.py` |
| `api_server.py` |
| `apply_w3_forex_patch_20261105.py` |
| `audit_remember_reencrypt.sh` |
| `backup_dbs.sh` |
| `batch_csv_downloader.py` |
| `batch_set_browser.py` |
| `batch_set_downloader.py` |
| `batch_set_wsl.py` |
| `build_volatility_html.py` |
| `cdp_helper.py` |
| `deploy_ghpages.sh` |
| `e2e_timing_check.py` |
| `ea_grouping_fix.py` |
| `encrypt_admin_pages.sh` |
| `export_hst.py` |
| `fix_links_unify.py` |
| `fix_nav.py` |
| `fix_remember_4pages_20261031.sh` |
| `forex_data_freshness.py` |
| `g1_g2_ui_fix_20261106.py` |
| `g5_residual_white_fix_20261106.py` |
| `gen_set_js.py` |
| `generate_enhanced_portfolios.py` |
| `generate_portfolio_reports.py` |
| `generate_portfolio_v2_reports.py` |
| `generate_portfolios.py` |
| `history_manager.py` |
| `live_verify_admin_fix.sh` |
| `migrate_to_sqlite.py` |
| `p0_tokens_batch_20261104.py` |
| `p0_wave3_martin_20261105.py` |
| `p1a_detailed_batch_20261105.py` |
| `p2_w2_semantic_20261105.py` |
| `portfolio_builder.py` |
| `portfolio_generator.py` |
| `portfolio_unified.py` |
| `portfolio_v2_analyzer.py` |
| `reg187_forex_batch_20261105.py` |
| `remember_layer_reencrypt_20261104.sh` |
| `save_set_files.py` |
| `set_parser.py` |
| `sync_gh_pages.sh` |
| `tb_flagship_20261105.py` |
| `tbnav_a_20261106.py` |
| `tsa_db_snapshot.sh` |
| `unify_report_heads.py` |
| `unify_sidebar.py` |
| `unify_sidebar_all.py` |
| `v2_snapshot.py` |
| `verify_admin_index_fix.py` |
| `verify_td_v153.py` |
| `verify_td_v154.py` |
| `verify_td_v155.py` |
| `verify_unify_gate_v2.sh` |
| `version_tracker.py` |
| `w33_fixab_patch_20261105.py` |
| `w4_reviews_20261105.py` |
| `w5_survey_20261105.py` |
| `w5a_martin_v4_20261105.py` |
| `w5b_ccy_20261105.py` |
| `w5c_signal_deep_20261105.py` |
| `w5d_index_nav_20261105.py` |
| `w5e_signal_light_20261105.py` |
| `w5f_nav_20261105.py` |
| `w5g_portfolio_nav_20261105.py` |
| `w5h_ccypower_nav_20261105.py` |
| `w5i_admin_nav_20261105.py` |
| `w6_label_fix_20261105.py` |
| `w6_label_fix_shots_20261105.py` |
| `w6_map_v2_20261105.py` |
| `w7_homepage_modules_20261105.py` |
| `w7b_home_links_ea_20261105.py` |
| `w8_dark_fix_apply_20261105.py` |
| `w8_dark_fix_shots_20261105.py` |
| `w8_darkbg_scan2_20261105.py` |
| `watchdog_retry.sh` |
| `wfinal_batch0_classify.py` |
| `wfinal_batch0_root_v3.sh` |
| `wfinal_batch0_wave2.sh` |
| `wfinal_batch0_wave2_classify.py` |
