# AI 工作規則（所有 lane 通用）

1. 開工前必須有卡，冇卡唔准做。
2. 開工：卡轉 In Progress，寫 owner ＋開始時間。
3. 完工：轉 Review，貼證據（commit hash／測試輸出／截圖）。
4. 人間簽核後才轉 Done，AI 唔准自己簽自己。
5. 卡住：轉 Blocked，寫明「等邊個／等乜」。
6. 每張卡必填：lane、owner、優先級(P0/P1/P2)、驗收準則、依賴連結。
7. 同一 lane 同時最多 2 張 In Progress。
8. 每次狀態變更寫一行 log：時間｜由誰｜舊→新｜原因。
9. 事實來源係 GitHub Issue；board 由 CI 生成，唔准手改 HTML。
10. 唔准跨 lane 改嘢；要人幫就開卡。
11. 唔准喺卡或 commit 寫密碼／token。
