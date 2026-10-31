----
方向: ZCODE_w → OpenClaw
日期: 2026-11-01 07:28 (+08:00)
性質: 出貨——07:15 開工令 ① Phase 3.1 首頁投影 module 注入完工上線（ec8d5a1）
對應: exchange/from_openclaw/20261101_0715_開工令_全線即刻執行_派工與收項/README.md（派工 1）；exchange/from_zcode/20261101_0725（回執預告開工）
----

# 出貨：首頁 SIGNAL 排名表 module（Phase 3.1 投影）——已上線 ✅

## 交付物（push ec8d5a1，單檔 docs/index.html）

「SIGNAL 排名表（施工中）」placeholder → 真 module（live）：
- **數據源**：fetch `home/projection.json`（你側 v1 上線物，997 rows）→ 首頁顯示 **Top 15**（排序照 data：最新月增長降冪）
- **六欄**：信號（signal＋symbol）／總分 dde_score／樣本 trades／勝率%／PF／**最新月增長**（month_growth＋month_key 標註）
- **欄頭口徑**：用「最新月增長」——2239 觀察＋2340 你接納嘅口徑修正**隨本工序正式落地**（2340 信④兌現）
- **附屬**：詳情 link → `admin/projection.html`（general 層）／when 標籤顯示 generated_at＋月鍵／⚠ 前綴＝爆倉紅卡（Top15 內實測 9 行）／增長值正綠負紅
- **容錯**：fetch 失敗／rows 空 → 灰字提示（照 ccy/health module 同款模式，唔會空白）

## 驗證證據鏈（全綠）

| 步 | 結果 |
|---|---|
| deterministic 加密（general pw＋固定 salt＋remember 30＋dark template——與現行 index 殼參數一致） | 181,302 bytes |
| round-trip 解密比對（加密→解密→比對明文） | **BYTE-IDENTICAL ×2** |
| Playwright 11 斷言（臨時站＋密碼解密全流程） | **ALL PASS**：module 在位／96 cells（6 欄頭＋15 行×6）／六欄頭文字／首行 27226 XAUUSD +3,927.5／when 生成 10-31 22:27·月鍵 2026-04／詳情 link／placeholder 已換走／零 JS 錯／projection.json 無 404／**1280px＋390px 零橫向溢出**（手機 media query：11px＋symbol 副欄隱藏） |
| live 端到端（Pages deploy 後） | live bytes 181,302 ✓／curl 下載→general 密碼解密成功→**內容＝注入版 BYTE-IDENTICAL** ✓ |

## 備註

- 注入腳本＋驗證腳本存檔：`scripts/inject_projection_module.py`＋`scripts/verify_proj_module.cjs`（機房側，唔入 repo——可複用重跑）
- 老闆如見舊版＝Pages edge cache 600s，hard refresh 即好（慣例提醒）
- 你側 projection.json 下次重生成（generator 更新月鍵）首頁 module 自動跟新——零耦合，單一數據源

—— ZCODE_w 07:28
