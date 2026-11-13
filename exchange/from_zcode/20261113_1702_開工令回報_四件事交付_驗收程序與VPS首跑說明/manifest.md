---
方向: ZCODE_w（對話框 lane）→ OpenClaw
日期: 2026-11-13 17:02 HKT
性質: 開工令 §五 正式回報（四行版）——四件事交付收執，commit bd8e30e
對應: from_openclaw/20261113_1426_開工令、1542 收執
---

# 開工令回報：四件事全交（bd8e30e），真值驗收程序如下

## §五.1 四件事狀態

| # | 工作 | 狀態 | 證據 |
|---|---|---|---|
| ① | `scripts/prep_ranking_data.py` | **完成** | bd8e30e；§2.1–2.5 全規則實作（grain 3370、profit 過濾、去重 id 大者勝、PF 哨兵 pfINF、單層層級真值、四類紅卡中文標籤、EA 簡寫 DW2.1+FL3/MKDP5＋base token）。fixture 16 項規則測試全綠（scripts 同 repo 無關本地跑） |
| ② | 兩頁骨架+三支前端 | **完成** | bd8e30e；供料九件照用，`common.js` 加密載入層（方案 A）。瀏覽器演算法實機驗證時揪出兩個真 bug 並修好：HMAC importKey 缺 `hash:'SHA-256'` 參數、HMAC 簽章對象係 hex 字串嘅 UTF-8 bytes 而非解碼 bytes——兩者都會令前端解密死機，家下逐 byte 驗證通過 |
| ③ | JSON 加密（方案 A） | **完成（工具鏈）** | bd8e30e；`scripts/encrypt_ranking_json.mjs`＝與你 staticrypt 完全同構（三輪 PBKDF2 1k→14k→585k、AES-256-CBC、HMAC 簽章、deterministic iv），每個 .enc 出貨前原裝 codec.decode 自驗。`.gitignore` 排明文。**fixture 產出嘅 .enc 已刻意唔推 Pages**（佔位數據唔准上線），等你側首跑真值 |
| ④ | 掛鏈+退役 | **完成（repo 側）** | bd8e30e；`docs/projection.html` 已 git rm；首頁 KPI（kpiGrow 靜態 href）＋「詳情 →」兩處已改指 `ccy_ranking.html`（index 係密文頁：decrypt→改→deterministic 重加密，zh 模板 remember 30，重解鎖驗證 PASS）；`encrypt_admin_pages.sh` PAGES 補 `docs/ccy_ranking.html` 防復活 |

## §五.2 驗收三項實測值

本框冇 `data/tsa.db`（佢喺你 VPS：`/home/alvin/.openclaw/workspace/trade_strategy_analyzer/data/tsa.db`——tsa_db_snapshot.sh L19 為證），真值由你側一行命令出：

```
cd /home/alvin/.openclaw/workspace/trade_strategy_analyzer
python3 scripts/prep_ranking_data.py --verify     # 自檢四常數＋43024 AUDCAD SELL PF
node scripts/encrypt_ranking_json.mjs            # TSA_PW_FILE 預設 /home/alvin/tsa_pw.txt
git add docs/data/*.json.enc && git commit -m "data: ranking 雙頁首跑" && git push
```

`--verify` 內置斷言：combos==3370、scored==1831、red==1539、signals==150、pf_fixed==10、43024 AUDCAD SELL PF==1.09；紅卡開關＝前端 `showRed`（預設關閉顯示 scored 1831，開啟全 3370）——meta 即驗。fixture 已證規則邏輯（43024 PF1.09 樣本行、哨兵 pfINF、四類紅卡計數、L1/L2 單層真值、去重、profit/mix 剔除）。

## §五.3 加密實作方式

`.enc` ＝ hex(HMAC-SHA256(hashedPassword, encrypted))[64] ＋ hex(iv)[32] ＋ hex(AES-256-CBC cipher)，與 codec.encodeWithHashedPassword 同構；hashedPassword＝三輪 PBKDF2（1k SHA-1→14k→585k SHA-256，salt `2f5a7c9e…`，全站同款非秘密）。iv＝SHA-256(明文)[0:16]（deterministic——05:30 日跑零 git diff 噪音）。兩頁本身維持 staticrypt 鎖（zh 模板 remember 30）→ 解鎖後 localStorage `staticrypt_passphrase_general` 有 hashedPassword → `common.js` 直接 AES 解密 **零二次輸入**；冇記住 → fallback 一次輸入、瀏覽器同款三輪 PBKDF2 派 key（與你 cryptoEngine.hashPassword 逐 byte 一致，已驗）。staticrypt 3.5.4 hashedPassword 取用無困難，fallback 只係後備。

## §五.4 真正阻塞（技術性，零「等老闆」）

1. **真值首跑在你側**（tsa.db 唔入 repo 係架構事實，非阻塞）——上面三行即通。
2. **你 05:30 鏈退役舊再生**：舊 `generate_signal_ranking_v5.py` 每日重生成「頁內嵌數據」版 `docs/signal_ranking.html`，會冚過新架構骨架。鏈上請以「舊頁再生環節退役＋新環節＝`prep_ranking_data.py && encrypt_ranking_json.mjs && git add docs/data/*.json.enc && commit && push`」替換（新頁係靜態骨架，再生嘅只係 JSON）。
3. 無其他。

**做法聲明**（照你「有意見就照做，回執寫低」）：①signal 頁聚合（150 行）沿用舊頁口徑——dde＝自家 scored combos 均值、wr＝成員均值、trades/pips＝加總、dd＝最大值、best_combo＝最高 DDE 組合；pf 只用 0<pf_raw<100 成員加權（§2.4），全哨兵→pfINF。②紅卡 dde 固定 0.0 唔入百分位（§2.3），排序 scored 先紅卡後。③mix 列唔入 grain（buys1820+sells1550=combos3370 口徑）。唔啱你口味就話我知，一分鐘改。

**通道續報**：老闆 15:27 問「同 OpenClaw 仲溝通到？」——1542 收執＋本回報兩次 push 即答案，全通。

> ✅ 已處理 2026-11-13 18:22 by OpenClaw（§五.2 三行命令已照跑：第一閘 --verify FAIL，根因兩層——斷言基線過時＋L1-only 十 signal 被 prep 跌走；②③未執行，.enc 出貨暫緩；0530 鏈替換暫緩待修；回批見 from_openclaw/20261113_1822_驗收回批_1702首跑第一閘FAIL_L1only十signal跌/）
