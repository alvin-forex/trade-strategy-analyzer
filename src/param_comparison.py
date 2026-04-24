#!/usr/bin/env python3
"""
Parameter Comparison Report - 策略參數 vs 說明書預設值對比
"""

import os
from datetime import datetime
from typing import Dict, Any, List


def generate_param_comparison(
    ea_name: str,
    signal_id: str,
    actual_params: Dict[str, Any],
    default_params: Dict[str, str],
    param_descriptions: Dict[str, str],
    output_path: str
):
    """生成參數對比報告"""
    
    rows = ""
    changes = 0
    for key, default_val in default_params.items():
        actual_val = str(actual_params.get(key, '—'))
        is_changed = actual_val != default_val and actual_val != '—'
        if is_changed:
            changes += 1
        
        desc = param_descriptions.get(key, '')
        icon = '🔴' if is_changed else '✅'
        bg = '#fff3cd' if is_changed else '#d4edda'
        
        rows += f"""
        <tr style="background:{bg}">
            <td>{icon}</td>
            <td><code>{key}</code></td>
            <td>{desc}</td>
            <td>{default_val}</td>
            <td style="font-weight:bold">{actual_val}</td>
        </tr>"""
    
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{ea_name} 參數對比</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, sans-serif; background: #f5f7fa; color: #333; padding: 16px; }}
.container {{ max-width: 1000px; margin: 0 auto; }}
h1 {{ font-size: 1.4em; color: #1a1a2e; margin-bottom: 4px; }}
h2 {{ font-size: 1.1em; color: #16213e; margin: 20px 0 10px; border-bottom: 2px solid #0f3460; padding-bottom: 4px; }}
.subtitle {{ color: #666; font-size: 0.85em; margin-bottom: 16px; }}
.summary {{ background: white; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.summary .stat {{ display: inline-block; margin-right: 24px; }}
.summary .stat .value {{ font-size: 1.2em; font-weight: bold; }}
table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 16px; }}
th {{ background: #0f3460; color: white; padding: 10px; text-align: left; font-size: 0.8em; }}
td {{ padding: 8px 10px; border-bottom: 1px solid #eee; font-size: 0.85em; }}
.insight {{ background: #e3f2fd; border-left: 4px solid #0f3460; padding: 12px 16px; margin: 12px 0; border-radius: 0 8px 8px 0; font-size: 0.9em; }}
</style>
</head>
<body>
<div class="container">
<h1>🔧 {ea_name} 參數對比報告</h1>
<p class="subtitle">信號頁 {signal_id} | 生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

<div class="summary">
    <div class="stat"><div class="value">{len(default_params)}</div><div>總參數</div></div>
    <div class="stat"><div class="value" style="color:#dc3545">{changes}</div><div>已修改</div></div>
    <div class="stat"><div class="value" style="color:#28a745">{len(default_params)-changes}</div><div>保持預設</div></div>
</div>

<h2>📊 參數明細</h2>
<table>
<tr><th></th><th>參數</th><th>說明</th><th>預設值</th><th>實際值</th></tr>
{rows}
</table>

</div>
</body>
</html>"""
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"參數對比報告：{output_path}")
