# RUNBOOK：Vercel TSA 私有站部署（ZCODE_w 平台側，賬戶綁定後照此五步）

日期: 2026-11-26
執行: ZCODE_w（1402 老闆裁決：Vercel 部署→ZCODE（平台）今日內接手）
前置: 附件齊——`vercel.json`／`RULES_page_routing_20261126.md`／`verify_vercel_links.py`

## 步驟 0：前置條件（本鐘實測現狀）

- 平台 Vercel 插件已裝，**賬戶未綁**（MCP 實測 teams=0）——請老闆喺插件頁綁定 Vercel 賬戶，或提供 `VERCEL_TOKEN` 環境變數（token 唔入 repo 唔入信）
- sandbox 有 node／npx；vercel CLI 隨用隨裝（`npx vercel@latest`）

## 步驟 1：部署（rsync 白名單複製，排除 downloads/）

```bash
STAGE=/tmp/tsa_vercel_site
rsync -a --exclude 'downloads/' docs/ $STAGE/
cp exchange/from_zcode/20261126_1435_ZCODE_w_Vercel接手準備件/vercel.json $STAGE/vercel.json
cd $STAGE && npx vercel@latest deploy --prod --yes
```

- 靜態站無 build（framework=null）；761MB−63MB≈698MB 首推需數分鐘
- 唔經 repo push；產物唔 commit

## 步驟 2：存取保護（必須，0410 §2）

Dashboard → 專案 Settings → Deployment Protection：
1. **Vercel Authentication**: `Only Team Members`（或 Password Protection，Pro 計劃）
2. **Password Protection** ON（密碼交 OC＋老闆，唔入 repo 唔入 exchange 信）
3. Auto-assign Custom Production Domains → OFF（唔綁公開 domain）
4. 開完用**隱身窗無 token 訪問**確認彈保護牆先算數

## 步驟 3：逐頁自查（0410 §3）

```bash
python3 verify_vercel_links.py https://<deployment-url>            # index 全量 481＋admin 全量＋data 抽樣＋報告連結抽樣
python3 verify_vercel_links.py https://<deployment-url> --sample 60  # 快測模式
```

任何非 200 → 逐條列 fail_list，全部 200＋`"PASS": true` 先算過閘。

## 步驟 4：交付

- 交付信入 `exchange/from_zcode/`（URL 只寫信內，886 @OC；唔貼公開群）
- 板面卡留言＋worklog

## 步驟 5：流水線接入（0412 五步，腳本死線 11-27 18:00）

- 分流照 `RULES_page_routing_20261126.md`；每晚 22:00 板面停更提醒檢查範圍納入「發佈閘失敗未修」
- 驗證閘：本腳本 cron 化，404／非 200 → 通知 topic 904＋24 小時內必修

## 附：GitHub Pages 私隱閘失效（本鐘發現，與 Vercel 任務直接相關）

14:40 實測公開網 **reports/*（明文信號深析）＋根層 ccy_ranking.html 全部 HTTP 200 可達**（700KB 全文）；真 404 機制本身正常（不存在頁真 404）。0410 背景所講「核心頁唔准公開」嘅閘而家唔閘——已另信上報 OC／老闆，修復唔喺 Vercel RUNBOOK 範圍。
