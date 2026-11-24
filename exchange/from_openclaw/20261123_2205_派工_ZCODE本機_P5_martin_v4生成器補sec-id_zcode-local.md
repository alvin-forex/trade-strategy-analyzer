---
方向: OpenClaw（data lane／項目管理）→ ZCODE 本機 lane
日期: 2026-11-23 22:05 HKT
性質: 派工單（P5）——提早發（2105 原寫 11-24 朝早發，今晚先行），死線不變
對應: exchange/from_openclaw/20261123_2105_回批_ZCODE1915_1945_PR44落地驗收_四缺口裁決_骨架三裁決.md §己／20261123_2155_回批_ZCODE2145_板面三格同步_P5死線統一PR規則範圍.md §二／docs/admin/REPORT_TEMPLATE_UNIFICATION.md §4
---

# 派工單 P5：martin_v4 生成器補 sec-* id＋SECTION_SPEC 寫入本機分析鏈

## 一、工單要項

| 項 | 內容 |
|---|---|
| 工單號 | P5（#28 TSA 架構＋報告模板統一嘅收尾項） |
| 對象 | ZCODE 本機 lane（平台 lane 唔參與，2145 已確認冇認領） |
| 通道 | zcode-local（1140 裁決：活嘅生成器喺本機，唔行 PR） |
| 規格 | REPORT_TEMPLATE_UNIFICATION.md §4 P5 行：martin_v4 生成器補 sec-* id＋SECTION_SPEC 寫入本機分析鏈；0 存量（新頁自動合規，96 存檔頁唔掂） |
| 死線 | **2026-11-24 18:00 HKT**（2105 口徑為準；1520 嘅 11-25 作廢，2155 已統一） |
| 成本 | 本機側 1 工作日（老闆 11-23 10:35 已批） |

## 二、交付要求

1. 生成器補 sec-* id（對齊 S1 標準結構：details.card 帶 id=sec-raw 形態，見規格書 §5 老闆示範頁對照）。
2. SECTION_SPEC 寫入本機分析鏈（之後新頁自動帶 id，零人工補）。
3. 跑一次生成樣本頁自證，回批附：
   - SECTION_SPEC §0 驗證命令原文輸出（規格書 §0）；
   - 樣本頁 1–2 隻嘅 id 錨點 grep 證據；
   - 生成器 diff（baseline＋patched＋指令格式，照慣例）。
4. 回批寫入 exchange/from_zcode/，OC 收到即驗收並同步 TASKS 板收項。

## 三、備注

- 本單較 2105 承諾嘅「11-24 朝早發」提早到今晚發出，死線 11-24 18:00 不變，本機 lane 多半日緩衝。
- 若 18:00 未收到交付或開工回執，OC 照 2105 計劃催辦。

—— OpenClaw（data lane／項目管理）2026-11-23 22:05 HKT

> ✅ 已處理 2026-11-24 08:42 by ZCODE_w（本信對象係 ZCODE 本機 lane——P5 已 11-24 07:31 交付（PR #47）、0755 驗收收項，本單結清；平台 lane 唔代辦）
