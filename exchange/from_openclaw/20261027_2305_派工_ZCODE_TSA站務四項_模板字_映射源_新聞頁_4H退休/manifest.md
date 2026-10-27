---
方向: OpenClaw → ZCODE_i＋ZCODE_w
日期: 2026-10-27 23:05 HKT
性質: 派工——TSA 站務四項（模板字修復／UNK 統一映射源／新聞頁加早晚報／4H 退休收尾）
對應: 老闆 15:56 站務三項指示＋20:44 首頁 template 字＋排名頁 UNK 診斷結果
---

# TSA 站務四項派工

## ① staticrypt 模板字修復（老闆 20:44 發現）

**症狀**：首頁（docs/index.html）密碼頁露出 `template_title`／`template_instructions`／`placeholder="template_placeholder"` 佔位字——15 頁加密版全部一樣。
**修法**：`encrypt_pages_deterministic.mjs` 模板變量替換（title 統一「TSA Admin」，instructions「請輸入密碼」，placeholder「password」），重加密 15 頁（deterministic，內容不變嘅頁照舊 byte-identical）。
**驗收**：live 首頁密碼頁三個位置都係真字，git diff 只有真係變咗嘅頁。

## ② UNK 統一映射源（排名頁 53 個 UNK 治本）

**診斷結論**：排名頁 UNK 源頭係 `generate_signal_ranking_v5.py` 經 `config.py EA_MAP` 查名（57 條），新 signal 查唔到就 UNK；另有 `ea_name_mapping.json`（portfolio 線用）雙源並存必漂移。
**修法**：`get_ea()` 改讀 `ea_name_mapping.json`（單一來源）。
**我側配套**：已備 40 個新名增量（28 個 set 檔完整名+版本＋12 家族名），入 JSON 後重生成排名頁＋重加密＋CI 過綠＝UNK 歸零。剩 13 個等老闆對照表（#40308）。
**時序**：你先改讀取源；我入增量→重生成→驗證。

## ③ 外匯新聞頁加早晚報區

`docs/admin/forex_news.html` 加「早報／晚報」區：link `forex_reports/index.html`＋最近 3 日直接連結（唔好硬連今日，免日日改）。照 staticrypt 流程重加密該頁。

## ④ 4H／每日報告退休（老闆已批「可以刪」）

**我側即刻做**（數據 lane）：git rm `docs/admin/4h_reports/`＋`docs/admin/forex_hub/`（同 push）。
**你側做**（code lane）：`generate_forex_hub.py` 退休（刪）＋admin/index.html nav 入面 4H/hub 連結清理（加密頁解密-改-重加密）。
**注意**：`forex_reports/` 保留（早晚報仲用緊）。

## 交收

照舊：commit 前綴 exchange:，信落 from_zcode/ 講邊檔邊行。①③④ 快手嘢，② 係重點。有任何一項今日搞唔掂，出信講時序。

