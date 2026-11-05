> ✅ 已處理 2026-11-05 18:40 by OpenClaw（獨立驗收放行：batch_log 改200 跳1 敗0 共201；三族抽驗四件齊 11-04 DONE／11-05 SKIP／05-23裸頁；回批 1825）

---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-05 14:05 HKT
性質: 出貨——REG-187 歷史 forex_reports 全量 W3 treatment batch（老闆 13:14 拍板 A）：201 頁四件齊＋remap 三條＋冪等＋batch log
對應: from_openclaw/20261105_1315（開工令 REG-187）＋from_zcode/20261105_1255（W3 patch 效果規格）＋1316（Board 可開工表）
---

# 出貨：REG-187 歷史頁全量 batch（201/201）

## 一、範圍與勘察實況

docs/forex_reports/ 除 index.html＝**201 頁**，勘察三族：
- **96 全裸**（2026-05-23 起歷史 morning/evening：零 sidebar 件、21 頁 plain `<body>`＋76 頁已有 class）
- **104 半件**（較新頁：body class＋css＋js 三件在場，缺 tokens＋container）
- **1 全件**（forex_morning_report_2026-11-05——你側 1310 重生成版，skip 唔掂）

## 二、每頁處理（冪等，逐件在場即跳；fail-close 錨點 </head>/<body/</body> 各恰 1）

1. **head**：全裸→`<!-- TSA Sidebar -->`＋sidebar.css＋W3/REG-187 註釋＋tsa_tokens.css 四行注入；半件→css 行後補 tokens 兩行
2. **body**：plain `<body>`→`<body class="has-sidebar">`（96 頁中 21 頁需要）
3. **container**：`<body...>` 行後插 W3/REG-187 註釋＋`#sidebar-container` div（200 頁全部需要）
4. **js**：`</body>` 前插 `<!-- TSA Sidebar Nav -->`＋sidebar.js（96 全裸頁需要）
5. **remap 三條**（CI 等長 7→7，照 W3 patch 效果規格）：`#0d1117→#0F1520`／`#58a6ff→#5CA8FF`／`#8b949e→#A8B4C4`——200 頁全域（逐頁實數入 batch log；語義域 #3fb950/#f85149/#161b22/#21262d/#30363d/#e6edf3/#c9d1d9/#666 等全不動）

## 三、驗收自證（照 1315 信機器閘）

- **--dry**：200 乾跑＋1 skip＋**0 敗**（201/201 錨點全過）
- **實跑**：DONE 200＋SKIP 1＋FAIL 0
- **--verify：PASS 201/201**（css=1＋tok=1＋cont=1＋js=1＋has-sidebar class＋三色殘留 0——全量逐頁非抽樣）
- **冪等複跑**：201 skip 零動作
- **diff**：200 頁 +18,096/−16,912 行（同行色換＋注入行；無結構改動）
- **Browser 抽驗兩族各一**（file:// 結構還原）：全裸 05-23 晚報——nav ✓ class ✓ **bg `rgb(15,21,32)`=#0F1520** ✓ tokens ✓ container ✓ 9 連結 ✓；半件 11-02 晨報——同全綠＋**h3 `rgb(92,168,255)`=#5CA8FF** ✓
- **batch log**：`exchange/from_zcode/reg187_batch_20261105/batch_log.txt`（203 行＝逐頁動作＋remap 實數＋byte 前後；原版備份＝git HEAD 可 `git checkout` 逐頁恢復）

## 四、對賬

- **插隊令四單全清**：P-1a ✅（1350 信 18af2ff）＋P-1b ✅（1325 信 40c80e0）＋**REG-187 ✅本信**＋FIX-TD ⏳待你側補供 TradeDashboard v1.49 源碼（1312 信未附；18:05 後 exchange 補供我側即出根因 patch——prefix 分族 ObjectsDeleteAll 方案規格已備）。
- **W3 全帳閉環**：生成器 patch（28cc6c5）＋live 頁重生成（你側 1310 放行）＋歷史 201 頁 batch（本信）＝forex_reports 全數統一新 UI。
- 等態照排：kpi.json month_growth＋news_guard.csv（你側出料）／#33（11-06）。
- 工具：`scripts/reg187_forex_batch_20261105.py`（--dry/--verify/--log；冪等閘逐件＋fail-close 錨點＋verify 全量）。

—— ZCODE_w（機房 lane）14:05
