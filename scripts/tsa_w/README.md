# scripts/tsa_w/ — ZCODE_w（機房 lane）驗證與施工腳本存檔

回應 OpenClaw 2026-10-30 12:45 回批【落差 3】：verify 腳本「口頭存在」第二次發生。
由本 commit 起，w lane 信件引用嘅腳本一律入庫於此目錄；唔入庫嘅會喺信內明示。

## 腳本清單

| 腳本 | 用途 | 來源交付 |
|---|---|---|
| `build_phase1_home.py` | 新首頁 Phase 1 組裝（地圖 SVG 注入 `<!--WORLD_G8_SVG-->`） | 1205 Phase 1 |
| `deploy_analyzer.py` | analyzer.html 部署（byte 一致＋postMessage 接收器注入） | 1205 Phase 1 |
| `verify_phase1_home.py` | Phase 1 明文態 38 項驗證 | 1205 Phase 1 |
| `verify_phase1_encrypted.py` | Phase 1 加密態 13 項驗證（閘面四色等） | 1205 Phase 1 |
| `live_verify_phase1.py` | LIVE 線上 6 項驗證 | 1205 Phase 1 |
| `audit_simplified_text.py` | 全站明文頁簡體字審計（OpenCC s2t 字級對比） | 1250 系統文字統一繁體 |
| `scan_encrypted_simplified.py` | 15 加密頁解密→明文簡體字審計 | 1250 系統文字統一繁體 |
| `fix_dbbrowser_s2t.py` | db-browser 全頁簡轉繁（產出定明文供重加密） | 1250 系統文字統一繁體 |
| `verify_dbbrowser_traditional.py` | db-browser 繁體修復瀏覽器驗證 7 項 | 1250 系統文字統一繁體 |

## 運行環境注意

腳本內 **REPO／密碼檔路徑係 w-lane 機房絕對路徑**（`/home/z/my-project/…`、
`/home/z/my-project/.keys/tsa_pw_*.txt`），只引用路徑、零密碼內容入庫。
喺其他機器重跑需改開頭常數（REPO／.keys 路徑）。依賴：python3＋
`opencc-python-reimplemented`（語言審計三支）、playwright（瀏覽器驗證三支）、
node≥18＋`scripts/staticrypt/`（加密相關）。

CI 常設門禁唔喺呢度——簡體字門禁係自足式 `tests/language_check.py`
（L23，643 檔，零依賴），與 encryption/link 门禁同級。

## 語言規矩（老闆指示 2026-10-30）

系統文字只可用**英文或繁體中文**。黑名單生成法與繁簡通用字排除清單
（台晒游群准峰吃托只里后面干系志表板冲秋松范郁）見
`tests/language_check.py` 檔頭註釋；OpenClaw 生成器模板請跟同一口徑。
