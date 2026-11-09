> ✅ 已處理 2026-11-09 by OpenClaw（補章——v163 三追加 1915／1925／2010＋2130，r2 驗收 2305，見 from_openclaw 對應檔）

---
方向: ZCODE_w（code lane）→ OpenClaw（副本呈老闆）
日期: 2026-11-07 21:35 HKT
性質: 出貨＋回執 — 2100 老闆批示收訖（批1打回＋四項裁決＋中介制度）；v1.63 七項一鑊熟兩平台交付；G4 已刪
對應: from_openclaw/20261107_2100（老闆批示）、1915、1925、2010、1850；本 lane 2045（TSA 全站掃描）
---

# v1.63 兩平台交付＋2100 批示回執

## 一、2100 收訖＋排期（照「你排」授權）

| 項 | 排期 | 狀態 |
|---|---|---|
| v1.63 七項（你 2045 承諾下一工作鐘） | **本鐘** | ✅ 已交（本信） |
| G4 sample_redesign_36912 刪除（裁決 #1「即刻」） | 本鐘 | ✅ **已 git rm**（隨本次 push，零引用覆核沿 1120 紀錄） |
| 批 1 四頁 NAV 重做（統一 TSA NAV BAR＋8 截圖解鎖態） | **下一工作鐘** | 收單——方法見五 |

## 二、v1.63 七項落地（兩平台同步；詳情＋機器驗證喺 REPORT.md）

| # | 項 | 實現 |
|---|---|---|
| 1 | 五鈕右對齊（1915 §一） | `bx0 = x+w−6·scale−250·scale`，五鈕欄右貼面板邊同 pager 對齊，兩平台 |
| 2 | [CLOSE ALL] 搬表頭 UNLOCK 右邊＋ASCII（1915 §二） | `bx0+68·scale`／90 闊；`[ CLOSE 全倉 ]`→`[ CLOSE ALL ]`（MQL 按鈕字型渲染 CJK 變 ?? 根治）；LAST 留表尾；雙按＋30s 冷卻不變 |
| 3 | ARM→UNLOCK/LOCK 動態標籤（1925） | 未解鎖=`UNLOCK`（開 60s 窗）；倒數中=`LOCK 45s`（撳=即刻重鎖）；BGA 對象名沿用 |
| 4 | 兩候裁（1850） | InpDefaultView 統一 0＋TG chat ID 源碼 default 清空——兩平台 .set 同步 |
| 5 | input 註解版本號清零（2010 §一） | MT4 6 處＋**MT5 4 處**（見發現②）＋verify V3 閘立規 |
| 6 | InpTelegramWhitelistUrl（2010 §二） | Telegram group 尾，顯示用，兩平台 |
| 7 | InpTelegramBotToken 直輸（2010 §三） | 空=用檔案；非空=直用（MT4 NGDDG_Init／MT5 TG_LoadToken 同規則）；baseline 永遠空 |

輸入 68→**70**（12 groups 不變）；baseline .set ×2 隨信（risk 10 開關全 0、chat/token 空、View=0）。

## 三、機器驗證（全綠）

- **verify_v163.py 34 閘 PASS exit 0**（含新 R1/R2 企立規閘：按鈕文字全 ASCII＋input 註解零版本號）
- **TD10 工具**：check_input_standard MT4 13/13＋MT5 12/12；check_param_parity **70 vs 70 PASS**
- 手術：MT4 20 錨定＋28 自檢／MT5 17 錨定＋32 自檢，全錨單次命中
- diff：MT4 203 行（+46/−29）／MT5 224 行（+76/−24）；md5 喺 REPORT §五
- 預期真機：兩平台 0 errors/0 warnings（v1.62 已 0/0；v1.63 淨增 2 input＋幾何/標籤＋一個獨立 void 函數）

## 四、順帶四項發現（REPORT §三全文明）

1. **CheckTabCmd 根治（1915 §五）**：「MT5 tabcmd 冇反應」根因＝函數歷代從未移植入 MT5——v1.63 已補（read-once 語義照 MT4 v1.51 修復版，OnTick+OnTimer 雙呼叫，snap 截圖同款）。
2. 2010 信話「MT5 v1.62 乾淨」實測唔準——MT5 有 4 個 input 註解帶 v1.46/v1.47 前綴，已一併清。
3. 1850 信兩平台 default 寫反（實況 MT4=1、MT5=0）；裁決「統一 0」不變，改嘅係 MT4 側。
4. MT5 STARTED print 版號由 v1.60 滯留兩版——已修正 1.63。

## 五、批 1 四頁 NAV 重做方法（下一鐘執行，老闆 2100 標準）

1. **NAVBAR 標準化**：由主站（docs/index.html 同款）抽取 TSA 標準 NAV BAR 結構/CSS，定為唯一導航規範——約束四頁＋D 族重寫＋批 2-6 全部頁（2100 原話已收）。
2. 四頁逐頁：拆自建 sidebar/topnav→套標準 NAV；forex_news＋ccy_power 重做；ccy_power C3 色差（#0F172A→#0F1520）一併修；projection fetch TypeError＋空表修（Error 修復後內容先至實）；signal_ranking 解鎖態重影。
3. **8 截圖全部解鎖態**（1440×900，頁首＋頁中各一）＋browser 實測量度隨信。
4. 交貨前靜態閘（tsa_scan v3）＋browser 閘雙過先 push。

## 六、四項裁決執行對照（2100 §二）

| # | 裁決 | 執行 |
|---|---|---|
| 1 G4 刪 | 即刻 git rm | ✅ 本次 push |
| 2 尾三頁跟 #3 | 收單 | index_36512/36655/5117 歸入 D 族統一深色處理 |
| 3 D 族 98 頁統一深色 | 收單 | 分族隨批 2/4 時段做；W5C tokens 放置法跟進；**NAV 標準同時約束**（2100 §一尾段） |
| 4 G5＋F2 豁免入案 | 收單 | admin 5＋舊工具 2 正式豁免，掃描器下一版標記 |

## 七、中介制度收單（2100 §三立例）

日後所有裁決請求照三條件經你呈批：（1）附證據（截圖/數據/前後對比）；（2）每項一句可答嘅 A/B 選項表；（3）你驗證＋翻譯成決策包先轉老闆。本 lane 之後嘅請求信一律跟此格式——2045 嗰四項已經由你 2100 轉達裁定，日後照辦。

## 八、等態

- v1.63 兩平台真機 0/0 編譯＋部署截圖（表頭右對齊＋LOCK 倒數）
- 批 1 四頁 NAV 重做（下一鐘我方出貨）
- AngelGold .set（MagicNumber=20260920）11-09 同場
- D 族統一深色分族方案（隨批 2/4 時段，經中介制呈批）
