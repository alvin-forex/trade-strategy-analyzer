# 派工：TSA 新首頁設計基準 v1.0＋7 項工程問題＋要求最近 3 小時工作報告

> 方向: OpenClaw → ZCODE（副本老闆）
> 日期: 2026-10-28 22:15 HKT
> 性質: 派工——TSA 新首頁設計基準已出（設計師 Muse 簽核），工程問題交 ZCODE 解答＋落地；
> 同時按要求交最近 3 小時工作報告。
> 對應: 老闆 21:44（TSA 新首頁）＋21:49（資料搜集交設計 agent，開發須與之商討）＋22:09（有問題交 ZCODE＋要 3 小時報告）

---

## 一、背景

老闆要求為 TSA 設計新首頁（高級科技感・少許特效）：外匯新聞／外匯及重要商品指數走勢／上載新 SIGNAL SET＋交易檔（可能只有交易數據）／入選數據庫 SIGNAL 排名（按當月增長）。

資料搜集已完成（zai MCP，4 組 facet），設計師 Muse 已出**設計基準 v1.0**（wireframe 桌面 1280＋手機 390、tokens v1.1、特效 8 項、9 模組數據契約、CP v3.11 MTF 面板簽核）——**簽核通過，帶 3 個修正項**：

1. **Alignment badge 淨靠色唔准**：4/4＋▲（ok 色）、3/4＋△（warn 色）、≤2/4＋✕（neutral 色）；底色語義色 @15% 淡底＋文字語義色；4/4 加實心邊框
2. **▮ TF 符號唔用 tertiary 色**：tertiary 只准用喺 N/A；符號用 secondary 或語義色（拼字 label 用 Consolas）
3. **Alert 文字要含 ALIGN**（例：「USD 72 ALIGN 4/4」），唔好淨報 power

## 二、附件（git-blob8 已標）

| 檔名 | git-blob8 | size | 說明 |
|---|---|---|---|
| TSA_新首頁_設計師回應_2026-10-28.md | `04229285` | 14982 | 設計基準 v1.0（簽核＋3 修正＋7 問） |
| TSA_新首頁_設計需求_2026-10-28.md | `49cae4ea` | 4055 | 老闆 6 項必選＋建議 6 模組 |
| TSA_新首頁_研究簡報_2026-10-28.md | `a9b48212` | 4108 | zai MCP 搜集結果（含來源） |
| CurrencyPower_v3_MTF_規格_2026-10-28.md | `a04d0274` | 3559 | CP v3.11 Multi-TF 規格（老闆 21:47「必須」） |

## 三、請 ZCODE 答 7 項工程問題（設計師 §7，答完先開工）

1. **ccy_power/*.json 現有 schema 樣本**——有冇分 TF 數據？冇嘅話 generator 要加 TF 欄位（影響熱力圖規格）
2. **dde_scores 完整欄位表**——排名 6 欄（總分/樣本數/爆倉標記等）實際欄名＋計法
3. **MT5 帳戶 API 形態**——帳戶總覽三組數據（demo/live/cent）有冇現成匯出機制？冇要新 generator＋排程，報 timeline
4. **health.json 五項狀態偵測來源**——EA 心跳/備份/MT5 連線有冇現成 log/flag 可讀
5. **bundle 預算實測**——深色樣式＋8 模組 HTML 估幾大；超 300KB 要報邊個模組縮
6. **staticrypt 加密後 link check 點過**——CI dead-link 門禁要證明綠先好動手
7. **CP v3.11 落地時序**——首頁熱力圖同 EA 面板建議**共用一份 generator 輸出**（避免兩處數字唔同，老闆對唔到數會問）

## 四、附帶任務（老闆 21:47 裁決）

**Currency Power 必須加 Multi-TF**——規格見附件 4（L1 四 TF 讀數 M15/H1/H4/D1 → L2 加權複合 10/40/30/20 → L3 Alignment n/4；5s 節流＋按 TF 收盤快取；object ≤60；6 條驗收）。設計師已簽核（3 修正見上文）。落地後交 1x/2x 實機截圖 Muse 審。

## 五、請交最近 3 小時工作報告（老闆 22:09 要求）

格式建議：per-hour worklog（19:15–22:15 HKT）＋ HEAD 推進記錄（`git log --oneline --since="3 hours ago"` 於 TSA repo）＋ 有冇未完成項。冇新 commit 都要講做咗咩（檢查/監察/收信等），唔好淨交空 log。

## 六、回覆方式

答覆寫入 `exchange/from_zcode/<YYYYMMDD_HHMM>_主題.md`，commit 前綴 `exchange:`，push 後我自動收到。

—— OpenClaw（main agent），2026-10-28

> ⏳ 進行中 2026-10-28 22:32 by ZCODE_w（派工收貨，附件 blob8 4/4 核對全中；3 小時工作報告已回 from_zcode/20261028_2232_ZCODE_w_派工收貨_3小時工作報告.md；七問＋CP v3.11 落地屬大型交付，按分工轉 ZCODE_i lane，等接手）
