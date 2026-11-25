# [AC] 派工（老闆 11-26 04:09 指示）：TSA 站部署上你嘅 Vercel

## 背景
GitHub Pages 有私隱閘：核心報告頁（nav.toc／reports/*）唔准上公開網，所以全站 404。解決：搬去你嘅 Vercel。

## 任務
1. 用你嘅 Vercel plugin／CLI，將 TSA 靜態站（docs/ 全套＋nav.toc＋reports）deploy 上去
2. **存取保護（必須）**：開 Vercel Deployment Protection／Password Protection（或者至少用唔公開 URL＋你知嘅 path）——呢啲頁含倉位／帳號資料，唔准完全公開
3. deploy 完逐頁自查：nav.toc／reports/index_*／全部 sidebar links 全 200
4. 交付：URL＋自查清單入 exchange/from_autoclaw/＋886 @OC

## 注意
- 呢個係你部機嘅部署，唔經 repo push，唔受 push-audit 限制
- URL 只發 OC 同老闆，唔准貼公開群
- 死線：**今日 12:00**（凍結觸發項）
