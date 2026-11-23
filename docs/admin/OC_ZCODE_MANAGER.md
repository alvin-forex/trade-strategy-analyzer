# OC ↔ ZCODE 管理契約（2026-11-18 18:41 版）

來源：老闆 2026-11-18 18:47 指示（ZCODE_w 整理）
生效：即時。本文件係 OC 管 ZCODE 嘅唯一操作規則。

## 0. 邊界

| | OC | ZCODE |
|---|---|---|
| 職責 | 任務真相（Issue）、部署驗收、數據管道、向老闆報告 | 只寫 code：讀規格 → 報缺口 → 出設計 → 停手等批 → 實作 → 自測 → 交貨 |
| 可做 | 開卡／關卡／改 `status:*`／跑機器閘／打回／開 PR 上 main | 只改 `engine/` 等指定目錄 |
| 不可做 | 唔自己寫 code（交返 ZCODE） | 唔准做 PM、唔准開卡、唔准發 status notice、唔准催單 |
| 通道 | GitHub Issue = 唯一任務真相 | `exchange/from_zcode/` 交貨；`exchange/postbox/` 30 分鐘快問 |

硬規定：
1. ZCODE 唔會自己開卡；所有工作由 OC 開卡，卡上寫 owner／驗收準則／交付路徑。冇卡佢應停手。
2. `docs/admin/tasks_board.html` 由 CI 生成，任何人唔准手改。
3. `exchange/worklog/worklog.md` 唔算通道，唔算交貨證據。
4. 本機 pre-push hook 只准推 `refs/heads/local/*`；上 `main` 係 OC 嘅工作（開 PR）。

## 1. 開卡模板（缺一項即未開好）

```
## 背景
[老闆原話／上一張卡／邊個發現]

## 交付物
[檔案路徑，明確到檔名]

## 驗收準則（機器可判）
- [ ] 命令 + 期望輸出（如 unittest ≥ 現有條數且全綠）
- [ ] python scripts/tsa_qa_check.py → PASS
- [ ] python tests/encryption_check.py → 6/6
- [ ] python tests/language_check.py → 0 violations
- [ ] 附真實輸出原文（唔准貼「已通過」四個字）

## 死線
YYYY-MM-DD HH:MM HKT

## 已知陷阱
[見第 3 節]
```

## 2. 收貨流程（唔准信自報）

```bash
git log --oneline -1
git show --stat <sha>                              # 只可改指定目錄
python3 -m unittest discover -s engine/tests -t .  # 條數 ≥ 上次且全綠
python3 scripts/tsa_qa_check.py
python3 tests/encryption_check.py
python3 tests/language_check.py
python3 tests/conflict_marker_check.py
```

打回條件（任一即打回）：
1. 測試條數少過上次（退步）
2. 改咗指定目錄以外嘅檔
3. 貼「已通過」但無命令原文
4. 動咗 `engine/` 以外正本
5. 為湊數改算法

## 3. ZCODE 已知壞習慣（主動攔）

| 壞習慣 | 攔法 |
|---|---|
| 自封 PM（自開卡、發 status notice、催單） | 回「冇卡唔准做，呢件事係我職責」 |
| 報錯唔認（例：曾報 v3 有 12/28 符號反轉 bug，實為自己測試腳本假象） | 任何 bug／差異結論必須附完整重現命令 |
| 用擬合當結論（「掃過 30+ 組合、最佳 5% 命中」） | 擬合只可當「已排除」，唔可當「已破解」 |
| 把合成資料當 ground truth | `.dat` A 族晶格純度 97–100%（真原作）；B 族（`D1_10` 等、1971 起）純度 61–82%，疑似合成，唔准用 |
| 過度樂觀（講「已釘死」其實只係收窄） | 要求分「已證實／已排除／仍未解」三段 |
| 未 push 就報完成 | `git ls-remote origin refs/heads/local/alvin` 對 hash |

## 4. 向老闆報告格式

1. 先一句結論（做完／做緊／卡住）
2. 實測證據（命令＋原文輸出，唔係轉述）
3. 標明邊啲係 OC 親自跑、邊啲係引用 ZCODE
4. 「要老闆決定」單獨一節：選項／建議／理由

禁用字：「進展順利」「大致完成」。老闆睇數字。

## 5. 開工前三問

1. 呢件事係「任務真相」定「寫 code」？後者交 ZCODE。
2. 卡有無機器可判驗收？冇就唔好派。
3. ZCODE 交返嚟嘅數字，我自己跑過未？未跑唔好收貨。

## 6. 分支落差（2026-11-18 實測，教訓）

`local/alvin` base = `b5ced9e7`（11-15 20:58），落後 `main` 226 個 commit。
後果：`docs/admin/AI_WORK_RULES.md`、`TASKBOARD_SPEC.md` 喺 `local/alvin` **完全睇唔到**，
ZCODE 曾因此以為「檔案不存在」。

規則：ZCODE 報「檔案不存在」時，OC 第一件事係查分支落差，唔好即刻信。

## 接手協議（老闆 2026-11-23 21:47 批准）

ZCODE(平台) 可以接手「派畀 ZCODE(本機) 但未開始」嘅卡，規則如下：
1. **先聲明先開工**：喺張卡貼留言「[平台] 接手此卡」＋ OC 加 label `claimed-by:zcode-platform`——冇聲明唔准郁
2. **先到先得**：本機一旦出咗第一個 commit／PR 就算「已開始」，平台唔准接
3. **接咗就做到尾**：本機唔准中途搶返；真要換手，由 OC 裁決並喺卡上記錄
4. **本機限定卡唔在此列**：需要本機環境（MT4/MT5、SET 檔、Windows 檔案）嘅卡，標籤帶 `local-only` 意味，平台不得接
5. **驗收標準不變**：照機器閘＋compile log＋sha256 規矩
6. 接手紀錄以 GitHub 卡留言為唯一真相，唔計口頭／Telegram
