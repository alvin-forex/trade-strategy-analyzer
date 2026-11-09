# signal_ranking 方案C深統一樣板 v1 — manifest

- 日期：2026-11-09 08:35 HKT
- 派工：from_openclaw/20261109_0805（加急——老闆 07:52 實機「排名果頁未整呀」）
- 身份：ZCODE_w（機房 lane）

## 交付物

| 檔 | 說明 |
|---|---|
| signal_ranking_方案C深統一樣板_v1.html | 手術版明文正本（82,673 bytes，md5 3ade50a9ff3b8b11c07c88a1659171bd；before 3b0cdda5dc0a36497d9e5cd49b013ae5） |
| signal_ranking_方案C深統一_v1.patch | before→after 統一 diff（75 行） |
| verify_unify_gate_v2.sh | 方案C五閘＋附加（取代 v1 四閘——舊閘1 topnav≥1 已修訂 topnav=0） |
| sr_前_before_線上現狀.png | before（舊 topnav＋無 NAV 標準態） |
| sr_後_after_樣板v1_dark.png / _light.png | after dark／light 桌面（1440×900） |
| sr_後_手機_dark.png / _手機_drawer_dark.png | 手機 390×844＋drawer 開啟態 |
| sr_後_頭部特寫_dark.png | NAV 48px sticky 頭部特寫 |

## 手術內容（6 步次數鎖定全中，腳本 scripts/sr_unify_surgery_20261109.py）

1. 刪舊 topnav CSS 6 條（.topnav 系列）
2. 插方案C NAV CSS（48px sticky＋drawer＋burger，照 ccy_power 正本同款）
3. 刪 sidebar.css link（舊 sidebar 退役）
4. 換舊 NAV HTML（sidebar-container＋topnav 塊）→ 方案C 三件（六連結根路徑，「排名」aria-current；theme-toggle 實體鈕照 ccy 正本唔入 NAV，toggleTheme＋localStorage 邏輯保留防禦式）
5. info-tip 次層面板 → var(--card2)（家族標配 1 處；tokens 正本 dark #1C2638／light #E2E8F0）
6. drawer JS 插 </body> 前（照 ccy 659，含 bar/drawer 清單一致性 console 閘）

## 五閘實績

- 樣板明文：topnav=0／sidebar-container=0／tsa_tokens=2／font-main=1／card2=1／Arial=0——**全綠**
- v2 工具對現版 live：GATE-RED 3/6（正中 0805 §一三缺陷）——分辨力實證
- Playwright：console error 僅 file:// 相對路徑假象（tsa_tokens.css 於 /tmp 無正本；部署 docs/ 根正常），無腳本錯誤，drawer/bar 清單一致性閘靜默通過

## 老闆過目後動作（批咗先做，樣板先行 0740 §四）

1. patch apply → 解密手術 docs/signal_ranking.html → deterministic 重加密 → push（Pages 部署）
2. **生成器治本**：手術構件注入 ranking 重生生成器模板（scripts/home/build_ranking.py 鏈）——唔入生成器＝聽朝 05:30 打回原形（1645 驗屍證明嘅機制）
3. verify_unify_gate_v2.sh 收錄正式工具位＋0531 鐘後改跑五閘
