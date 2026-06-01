#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
早盤外匯報告 V3
時間：每天 07:00 HKT
功能：生成 v3 格式嘅早盤外匯分析報告
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# 添加路徑
sys.path.insert(0, '/home/alvin/.openclaw/workspace')
sys.path.insert(0, '/home/alvin/.openclaw/workspace/configs')
sys.path.insert(0, '/home/alvin/.openclaw/workspace/services')

# 導入服務
try:
    from mt4_screenshot_service import MT4ScreenshotService, get_screenshot_service
    import channel_routing
except ImportError as e:
    print(f"[錯誤] 導入失敗：{e}")
    print("[提示] 請確保以下服務可用：")
    print("  - mt4_screenshot_service")
    print("  - channel_routing")
    sys.exit(1)

# ========================================
# 配置
# ========================================

OUTPUT_PATH = "/tmp/forex_morning_report_v3_YYYY-MM-DD.html"
MONITORED_PAIRS = ["AUDCAD", "EURCHF", "XAUUSD"]  # 老闆指定嘅監控貨幣對

# ========================================
# 腳本主類
# ========================================

class MorningReportV3:
    """早盤報告 V3"""

    def __init__(self):
        self.screenshot_service = get_screenshot_service()

    def get_market_data(self) -> Dict:
        """獲取市場數據"""
        print("[SCOUT] 正在搜集市場資訊...")

        market_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "time_zone": "HKT",
            "currency_pairs": []
        }

        # 獲取所有支持的貨幣對
        all_pairs = self.screenshot_service.get_all_supported_pairs()

        # 只關注監控嘅貨幣對
        for pair in MONITORED_PAIRS:
            if pair in all_pairs:
                # 獲取截圖資訊
                screenshot = self.screenshot_service.find_latest_screenshot(pair)

                # 從圖片檔名提取價格（如 EURUSD_1.0950.png）
                price = "N/A"
                if screenshot['success']:
                    image_path = screenshot['image_path']
                    filename = image_path.split('/')[-1]
                    # 格式：EURUSD_1.0950.png 或 EURUSD_1.0950_2.png
                    parts = filename.split('_')
                    if len(parts) >= 2:
                        try:
                            price = parts[1].replace('.png', '')
                        except:
                            pass

                market_data["currency_pairs"].append({
                    "symbol": pair,
                    "screenshot": screenshot,
                    "price": price
                })

        print(f"[SCOUT] 收到 {len(market_data['currency_pairs'])} 個貨幣對數據")
        return market_data

    def generate_html(self, market_data: Dict) -> str:
        """生成 V3 HTML 報告"""

        # 構建 HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🦀 早盤外匯報告 V3 - {market_data['timestamp']}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0d1117; color: #c9d1d9; padding: 10px; max-width: 1000px;
       margin: 0 auto; font-size: 12px; line-height: 1.5; }}
a {{ color: #58a6ff; text-decoration: none; }}

h1 {{ font-size: 24px; color: #fff; text-align: center; margin-bottom: 10px; }}
h2 {{ font-size: 16px; color: #58a6ff; margin: 20px 0 10px 0; padding: 10px;
     background: #161b22; border-radius: 6px; border-left: 4px solid #58a6ff; }}

/* CCY Power */
.ccy-power {{ background: #161b22; border-radius: 8px; padding: 15px; margin-bottom: 20px; }}
.ccy-grid {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }}
.ccy-item {{ text-align: center; min-width: 60px; padding: 8px 12px; border-radius: 6px;
            cursor: pointer; transition: transform 0.15s; background: #21262d; }}
.ccy-item:hover {{ transform: scale(1.05); background: #30363d; }}
.ccy-name {{ font-size: 11px; font-weight: bold; color: #e6edf3; }}
.ccy-val {{ font-size: 16px; font-weight: bold; color: #fff; margin-top: 2px; }}

/* Currency Pair Card */
.pair-card {{ background: #161b22; border-radius: 8px; padding: 15px; margin-bottom: 15px;
             border: 1px solid #21262d; }}
.pair-header {{ display: flex; justify-content: space-between; align-items: center;
               margin-bottom: 12px; }}
.pair-name {{ font-size: 18px; font-weight: bold; color: #e6edf3; }}
.pair-price {{ font-size: 16px; font-family: monospace; color: #3fb950; }}

/* News Section */
.news-section {{ background: #161b22; border-radius: 8px; padding: 15px; margin-bottom: 20px; }}
.news-item {{ padding: 8px 0; border-bottom: 1px solid #21262d; font-size: 13px; line-height: 1.6; }}
.news-item:last-child {{ border-bottom: none; }}
.news-source {{ color: #8b949e; font-size: 11px; margin-right: 8px; }}

/* Table */
table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
th {{ background: #161b22; color: #58a6ff; padding: 6px; text-align: left;
     font-weight: bold; border-bottom: 2px solid #30363d; }}
td {{ padding: 6px; border-bottom: 1px solid #21262d; }}
tr:hover {{ background: #161b22; }}
</style>
</head>
<body>
<h1>🦀 早盤外匯報告 V3</h1>
<h2>時間：{market_data['timestamp']} ({market_data['time_zone']})</h2>

<div class="ccy-power">
<div class="ccy-grid">"""

        # CCY Power
        for pair in market_data["currency_pairs"]:
            pair_name = pair["symbol"]
            pair_price = pair["price"]

            html += f"""
<div class="ccy-item">
<div class="ccy-name">{pair_name}</div>
<div class="ccy-val">{pair_price}</div>
</div>"""

        html += f"""
</div>
</div>"""

        # Currency Pair Cards
        for pair in market_data["currency_pairs"]:
            pair_name = pair["symbol"]
            pair_price = pair["price"]
            screenshot = pair["screenshot"]

            html += f"""
<div class="pair-card">
<div class="pair-header">
<div class="pair-name">{pair_name}</div>
<div class="pair-price">{pair_price}</div>
</div>

<div style="margin-bottom: 12px;">
<img src="{screenshot['image_path']}" alt="{pair_name} 截圖" style="max-width: 100%; border-radius: 6px;">
</div>

<div style="font-size: 11px; color: #8b949e;">
🖥 終端：{screenshot['terminal_name']} | 📅 時間：{screenshot['timestamp']}
</div>
</div>"""

        html += """
</body>
</html>"""

        return html

    def save_report(self, html: str, date: str):
        """保存報告"""
        output_path = OUTPUT_PATH.replace("YYYY-MM-DD", date)

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

            print(f"✅ 報告已生成：{output_path}")
            return output_path
        except Exception as e:
            print(f"❌ 保存失敗：{e}")
            return None

    def generate(self):
        """生成早盤報告 V3"""
        print("=" * 60)
        print("🦀 早盤外匯報告 V3")
        print("=" * 60)

        # 獲取市場數據
        market_data = self.get_market_data()

        # 生成 HTML
        print("[GEN] 正在生成 HTML 報告...")
        html = self.generate_html(market_data)

        # 保存報告
        today = datetime.now().strftime("%Y-%m-%d")
        report_path = self.save_report(html, today)

        print("\n" + "=" * 60)
        if report_path:
            print("✅ 報告生成完成")
            print(f"📁 路徑：{report_path}")
        else:
            print("❌ 報告生成失敗")
        print("=" * 60)

# ========================================
# 主函數
# ========================================

def main():
    """主函數"""
    generator = MorningReportV3()
    generator.generate()

if __name__ == "__main__":
    main()
