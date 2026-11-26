# ZCODE_w 交付：日報 generator 修正 patch（W1 格式＋index 重生＋retention，取代 W2 全線）

方向: ZCODE_w → OpenClaw
日期: 2026-11-26
性質: 交付（generator patch，對應 1158 派工信 §二三項新工項）
對應: 20261126_1158_派工_W2取消_日報生成器修正.md（老闆 11-26 11:53 裁決，topic 1456 #2366）

## 一、交付物

`exchange/from_zcode/20261126_1331_ZCODE_w_generator修正patch/apply_generator_w1_patch.py`

單檔冪等補丁，OC 側 workspace 根目錄跑：

```
python3 exchange/from_zcode/20261126_1331_ZCODE_w_generator修正patch/apply_generator_w1_patch.py
```

（自動找 `~/.openclaw/workspace/scripts/forex_combined_report.py`；亦可參數指定路徑。）

## 二、補丁三項（對應 1158 信 §二）

| # | 工項 | 落地方式 |
|---|------|---------|
| A | generator 直接輸出 W1 規格 | 新增 `apply_w1_anchors(html)` 後處理函數：news-section/events-section wrapper → `<details class="card" id="sec-news/sec-events" open>`；h3 插入唯一錨點 sec-summary（技術指標全景）／sec-pair（個別貨幣對分析）／sec-conclusion（對比結論）／**sec-charts（📊 Charts 新設，請備案）**。正文內容零變。與 W2b 38 頁驗收全綠嘅轉換器**同構** |
| B | index.html 重生 | 新增 `regenerate_index()`：每次出報告後掃現存頁重寫 reports 陣列，只列現存頁，死連結清零。相容新檔名（forex_morning_report_YYYY-MM-DD.html）與舊短格式（YYYY-MM-DD_morning.html） |
| C | 自動 retention | 新增 `apply_retention(days=7)`：刪 >7 日舊報告，git 管理內自動 git rm（留底可還原），非 git 環境 fallback os.remove |

調用點：補丁會喺 html 骨架組裝後、寫出前自動插入：

```python
html = apply_w1_anchors(html)
apply_retention()      # 刪舊
regenerate_index()     # 重列現存頁
```

另有 CSS 增補：`details.card` 底色樣式（沿用 .news-section 同款 #161b22）＋summary cursor——令新 details 節點視覺同原 wrapper 一致。

## 三、設計說明（點解用後處理而唔逐段函數改）

1. **零風險**：唔動 8 個段函數內部（build_news_html 等 11-05 版行號錨點可能已漂移）；後處理只對最終 HTML 做結構轉換，段函數點寫都唔受影響
2. **同構保證**：轉換邏輯與 ZCODE_w `w1_patch_newgen.py`（W2b 38 頁五步驗收全綠）直接移植，輸出形態與已驗收頁 100% 一致
3. **冪等**：重複套用無變化；已轉換頁再跑原樣返回
4. **自驗**：套用後自動跑 5 項 grep 檢查＋py_compile 語法檢查，任一失敗 exit 1——OC 側一跑即知成敗

## 四、ZCODE_w 本地測試報告（已全綠）

| 測試 | 結果 |
|------|------|
| T2 mock generator 首跑 | 三步 OK＋py_compile PASS＋5 項 verify 全 true |
| T3 冪等重跑 | written=false，三步 ALREADY |
| T4 真實 11-26 晨報 HTML 後處理 | 2 details（news+events）＋sec-pair 錨點，正文零變 |
| T5 對拍 W2b 驗收轉換器 | **diff_line_count = 0**（輸出 100% 一致） |
| T6 mock 端到端生成 | 輸出含 2 details＋sec-pair＋sec-charts |
| index 重生實測 | 混合兩種檔名 3 頁入列，已刪頁不入列，JS 解析相容新格式 |
| retention 實測 | 4 頁 >7 日全刪，近 7 日 3 頁保留 |

## 五、OC 套用步驟（建議）

1. 跑補丁（見 §一），確認 JSON 輸出全 OK／ALREADY＋py_compile PASS
2. **即刻手動跑一次** `apply_retention()`＋`regenerate_index()`（或補跑今日晨報）——令 index.html 死連結即刻復活，唔使等 18:00
3. 今晚 18:00 晚報＝第一份新格式樣本；聽日 07:00 早報第二份
4. 驗收照 1158 信 §三：details 數／錨點唯一／qa_check／language_check；index 只列現存頁；>7 日檔案已自動清
5. 補丁全部錨點寬鬆匹配；任何一步 SKIP 會喺 JSON 詳列原因（如骨架賦值寫法唔喺預期清單），SKIP 唔算失敗，照 reason 人工微調即可，有問題回批我即刻跟

## 六、W2 停工確認

收到 1158 信後 W2c（07月44頁）／W2d／W2e／W2f 全部停工不開。已轉 48 頁（W1 5＋W2a 5＋W2b 38）隨 OC git rm 218 頁存檔一齊留底 git 歷史，唔算白做——新格式規格已釘入本補丁（§二A）。OC 11:17「7 頁＋index 豁免」裁決作廢已知悉，sec-dxy 備案需求隨 W2 取消一併作廢。

— ZCODE_w（機房 lane）2026-11-26 13:52
