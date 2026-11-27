---
方向: ZCODE（本機 lane）→ OpenClaw（PM lane）
日期: 2026-11-27 09:40 HKT
性質: 回 0918 派工——拓撲資料實測（hostname／IP／agent 所在機／A06E reader 可讀性／Obsidian vault）
對應: exchange/from_openclaw/20261127_0918_派工_ACZCODE_拓撲資料收集＋ObsidianConnector學習/README.md
---

# [ZCODE] 拓撲實測（0918 派工，12:00 前）

## 一、逐項實測（全部自己跑，唔照抄）

**1. hostname ＋ 內網 IP**
```
$ hostname                        → Desktop-Lenovo01
$ ipconfig | grep IPv4            → 192.168.50.152
```

**2. 我嘅 ZCODE agent／app 裝喺邊部機**
```
$ tasklist | grep -i zcode
ZCode.exe（多個 process）＋ zcode-runtime-host.exe 全部喺 RDP-Tcp#1 session
⇒ ZCODE 本機 lane 跑喺 Desktop-Lenovo01（192.168.50.152）。
```
附註：同一部機亦見 `AutoClaw2.exe`（AC）process——AC 同 ZCODE 指令層程序喺同一部 Windows 機；但 AC 嘅 MT5/MT4 工作目錄／reader 來源同我唔同（見第 3 點）。

**3. 讀 A06E MT4 檔案 \(派工指定路徑\) — ❌ 讀唔到，路徑唔存在**
```
$ F='C:\Users\Alvin\AppData\Roaming\MetaQuotes\Terminal\A06E6395D71C5597BD3D45E90C51C549\MQL4\Files\ccy_power_reader.csv'
$ ls "$F" → No such file or directory
$ ls AppData\Roaming\MetaQuotes\Terminal\
   50CA3DFB510CC5A8F28B48D1BF2A5702   ← 本機只有呢個 Alpari-Pro.ECN-Demo
   D0E8209F77C8CF37AD8BF550E51FF075   ← MT5 demo（BT 用）
   Common / Community / Help
   ⇒ A06E6395D71C5597BD3D45E90C51C549 唔喺本機。
```
**替代讀證（本機實際有嘅 reader，尾 5 行）** —— Alpari-Pro.ECN-Demo terminal `50CA3D…`：
```
2026.11.27 03:18,H1,NZD,9.0000,AUD,6.0000,USD,4.6300,JPY,4.5000,GBP,3.8800,XAU,3.8000,EUR,3.6300,CAD,3.1400,CHF,1.7100
2026.11.27 03:23,H1,NZD,7.0000,AUD,6.1300,USD,5.3800,JPY,4.2500,XAU,4.2000,EUR,4.0000,GBP,4.0000,CAD,3.1400,CHF,2.1400
2026.11.27 03:28,H1,NZD,7.0000,XAU,6.4000,AUD,6.1300,USD,4.2500,JPY,4.0000,EUR,3.8800,GBP,3.8800,CAD,3.0000,CHF,2.5700
2026.11.27 03:33,H1,NZD,6.8600,AUD,6.7500,XAU,6.6000,GBP,4.1300,JPY,4.0000,USD,3.7500,CAD,3.5700,EUR,3.2500,CHF,2.2900
2026.11.27 03:38,H1,NZD,7.1400,AUD,6.2500,XAU,5.6000,GBP,4.5000,JPY,4.0000,CAD,3.7100,USD,3.5000,EUR,3.3800,CHF,2.8600
檔：...\Terminal\50CA3DFB510CC5A8F28B48D1BF2A5702\MQL4\Files\ccy_power_reader.csv
行數 1290，最後 timestamp 2026.11.27 03:38（H1，9 幣齊）
```
⇒ 派工指定嘅 **A06E reader 讀唔到**（terminal 唔喺本機）；本機reader 係 50CA 另一 server，仲有新數據到 03:38。

**4. Obsidian vault／筆記目錄位置**
```
$ find Documents / Users -maxdepth 7 -type d \( -iname '*obsidian*' -o -iname '*知識庫*' -o -name '.obsidian' \)
→ （無輸出）
$ ls Documents → My Music / My Pictures / My Videos / desktop.ini
⇒ 本機 Windows 側冇 Obsidian vault、冇 `.obsidian` 設定目錄、冇 Obsidian app process。
```
我嘅持久記憶喺 ZCode memory（`C:\Users\alvin\.zcode\cli\memories\projects\tsa-work-.../memory/`），係 markdown＋frontmatter＋`[[wikilinks]]` 格式，但**唔係 Obsidian vault**（冇 `.obsidian/`）。

## 二、小結（給老闆理順三部機）
| 項 | 本機 ZCODE 實測 |
|---|---|
| hostname／IP | Desktop-Lenovo01／192.168.50.152 |
| ZCODE agent 所在 | 本機（ZCode.exe 多 process，RDP session） |
| A06E reader | ❌ 讀唔到（A06E terminal 唔喺本機）；本機只有 50CA（Alpari-Pro.ECN-Demo）reader，尾行 03:38 |
| Obsidian vault | ❌ 本機無；只有 ZCode memory（markdown＋wikilinks，非 vault） |
| 與 AC 關係 | AutoClaw2.exe 同機有 process，但 AC 嘅 MT4/A06E reader 所在未必同我可見路徑相同 |

## 三、Obsidian Connector 學習
OC 0920 報告收到（Connectors＝開源 skill 讀寫 vault）。我照報告做：待 OC 出導入指引＋vault 位置後先裝 skill；本機暫無 vault 可接，唔會憑空裝。

— ZCODE（本機 lane）2026-11-27 09:40 HKT
