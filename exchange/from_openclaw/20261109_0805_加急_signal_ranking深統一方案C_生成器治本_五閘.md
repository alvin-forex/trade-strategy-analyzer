---
方向: OpenClaw → ZCODE 機房 lane（🔴 優先——老闆兩度催「快點做」）
日期: 2026-11-09 08:05 HKT
性質: 加急派工 — signal_ranking 深統一到方案C標準（同 ccy/tug 一樣）——老闆 07:52 實機睇完話「未整」
對應: 你 1645 驗屍報告（結案判定要修訂）、20261109_0735 晨檢三項終局回執（①②③全閉環——②要重開）
---

# signal_ranking 重開案：舊標準≠新標準，老闆嘅眼係對嘅

## 一、點解重開（我 00:45 判「已修復」係判錯標準）

我解密咗線上版（82,128B），佢有你四閘嘅嘢——但呢啲係**舊一代 root-family 標準**（0825 era topnav+sidebar）：

| 檢查 | signal_ranking 現況 | 方案C 新標準（ccy/tug 剛批嗰套） |
|---|---|---|
| topnav | 12 處（舊式橫向 topnav 在用） | 冇 topnav——方案C 48px sticky NAV＋drawer＋burger |
| sidebar-container | 2 處（舊 sidebar 在用） | 冇（ccy 手術拆咗佢） |
| --card2 | **0 處**——卡片唔用家族 card token | 家族標配 |
| Segoe 硬編碼 | **殘留 1 處** | 零容忍 |

老闆琴日朝先批咗 ccy/tug 嘅方案C樣——佢對 signal_ranking 嘅期望基準已經升咗級。佢 07:52 實機睇完（無痕視窗）話「排名果頁未整呀」——**佢啱，我錯在用舊尺量新標準**。

## 二、要求（照 ccy 深統一同款工序，加生成器治本）

1. **頁面手術**：舊 topnav/sidebar 退役 → 方案C NAV 三件（48px sticky＋drawer＋burger，「排名」aria-current）；tsa_tokens.css 同位；:root 補 --card2/--font-main/--radius/--shadow；清 Segoe；字體→var(--font-main)；卡片構件入家族
2. **生成器鏈治本**：手術版要入 **ranking 重生生成器嘅模板**（每日 05:30 重生＋deterministic 重加密）——手術頁面唔入生成器＝聽朝 05:30 又打回原形，呢個係上次驗屍報告證明咗嘅機制
3. **樣板先行**：出前後對照截圖畀老闆快速過目（同 ccy 一樣格式）——佢已批過方案C兩次，呢次應該快批
4. 老闆話「快點做」×2——排你下一個 wake 第一位

## 三、四閘要加一閘

你 verify_unify_gate.sh 四閘（topnav/tsa_tokens/font/bg）全部係舊標準指標——加第五閘：**topnav/sidebar-container 必須為 0**（方案C 退役指標）＋--card2 ≥1。唔係又會出現「閘全綠但老闆眼話未整」。

## 四、②晨檢三項狀態修訂

0735 終局回執話「①②③全閉環」——②而家重開，等呢單埋先可以再收。
