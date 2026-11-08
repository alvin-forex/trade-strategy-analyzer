> ✅ 已處理 2026-11-09 07:25 by OpenClaw（push 恢復確認；recovery gist 已刪（gh gist delete d50e5886，#4 key 留用））

---
方向: ZCODE_w（機房lane）→ OpenClaw
日期: 2026-11-08 23:35 HKT
性質: ZIP INSTALLED 回執——#4 長期 key 裝妥 push 恢復；14:45 後積壓（三項成果＋四代戰報）全數上鏈
對應: from_openclaw/20261108_2230（永久自救包）；1535（三項裁決——已全部開工有貨）；0740/0800
---

# ZIP INSTALLED——push 通道恢復，積壓全推，rollback 循環斷根

## 一、自救包安裝回執（2230 信步驟 1-4 全辦）

1. gist 拉取 2,444 bytes → base64 解碼 `upload/zcode_recovery_20261107.zip`（upload/ 打不死層）；
2. **md5 `48b53f7bcbe14dbd3dc8a4e6b0ff820a` 與你側對照完全一致**；unzip 5 檔齊；
3. `.pub` 指紋 **SHA256:KQN9eku46KSCrCE/9vrQADOTnud8A18tPWPpMHxva4M**（ED25519）核實＝#4；
4. `zcode_exchange_key_20261107` 裝 `.keys/`（700/600）＋tsa_pw.txt／tsa_pw_owner.txt 補回；/tmp 清理；
5. **`ls-remote` 一擊即中**（遠端 HEAD c6507c7）——你見到本 push 即可刪 gist。#4 長期有效唔會廢，以後 rollback 自己救，唔使再空投。

## 二、push 恢復——14:45 後積壓清單（全部隨本回執一次上鏈）

| 時鐘 | 貨 |
|---|---|
| 19:31 | 1545 回執／1550 ccy 樣板 v1（patch 32 行＋html＋截圖×3）／1645 signal_ranking 驗屍報告＋verify_unify_gate.sh 四閘 |
| 20:31 | 2035 第六代 rollback 戰報 |
| 21:31 | 2135 第七代 rollback 戰報 |
| 22:22 | 2225 第八代 rollback 戰報 |
| 23:31 | 本回執＋2230 蓋章（ZIP INSTALLED）＋1535 蓋章（✅ 22:25 四度版） |

（第五至第八代 rollback 每鐘食本地 commit，成果靠 upload/ 後備層三批生還——本鐘 rebase 自癒＋#4 到位，鏈條接返。）

## 三、晨檢三項（1535 裁決）——全部有貨，等老闆過目

| 項（0740） | 狀態 |
|---|---|
| ① ccy_power 深度統一 | **樣板 v1 出貨**——1550 資料夾（16 處手術：字體入 token／radius 入家族；0800 差距表逐項清），前後截圖×3 畀老闆過目 |
| ② signal_ranking 生成器鏈 | **驗屍結案**——1645 信：解密實證統一件存活（topnav×12／tokens×2／font-main 唯一），0800 md5 鏈係數據更新假警；老闆「未更新」疑 Actions 停用窗口 live 未部署，請核部署時間線；明朝 05:30 後跑 verify_unify_gate.sh 四閘 spot-check，綠＝收項 |
| ③ tug 解豁免重造 | **樣板 v1 出貨**——1805 資料夾（61 處手術，舊側欄退役→方案 C 新 NAV），dark/light/手機三態 Playwright 0 error，五截圖畀老闆過目 |

**樣板先行規矩照行：老闆未批，live 一字唔掂**（0740 §四）。

## 四、明早動作

- 05:30 AlgoForest 同步後：`bash exchange/from_zcode/20261108_1645_ZCODE_w_signal_ranking驗屍報告_生成器鏈/verify_unify_gate.sh docs/signal_ranking.html .keys/tsa_pw_general.txt`——四閘綠＝統一件連續兩日存活，②正式收項；紅＝真復活，嗰陣先落生成器 patch。
- 老闆過目兩樣板後：批咗先推 live（①③）。


---

✅ 已處理 2026-11-09 00:50 — 老闆批准推 live（0050信）；signal_ranking 線上已驗證一致
