"""
MT4 Account Monitor API Server
接收多個 MT4 EA 嘅帳戶數據，提供 dashboard 同 API

安裝：pip install fastapi uvicorn
運行：python server.py
訪問：http://你的IP:8788/dashboard
"""

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import json
import os
from datetime import datetime
from collections import OrderedDict

# ============ 配置 ============
API_KEY = "mt4_monitor_2026"  # API 密鑰，EA 同 server 要一致
PORT = 8788
DATA_FILE = "accounts_data.json"  # 數據持久化檔案

# ============ FastAPI ============
app = FastAPI(title="MT4 Account Monitor API", version="1.0")

# 帳戶數據（記憶體 + 檔案持久化）
accounts_db = {}

def load_data():
    """從檔案載入數據"""
    global accounts_db
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                accounts_db = json.load(f)
            print(f"✅ Loaded {len(accounts_db)} accounts from {DATA_FILE}")
        except:
            accounts_db = {}

def save_data():
    """保存數據到檔案"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(accounts_db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Save error: {e}")

# ============ API 端點 ============

@app.post("/api/account/state")
async def receive_state(request: Request):
    """接收 EA 傳嚟嘅帳戶狀態"""
    # 驗證 API Key
    auth = request.headers.get("X-API-Key", "")
    if auth != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    data = await request.json()
    account_id = data.get("account_id", "unknown")
    
    # 更新數據
    data["received_at"] = datetime.now().isoformat()
    accounts_db[account_id] = data
    save_data()
    
    print(f"📊 Updated: {data.get('label', account_id)} | "
          f"Balance: {data.get('balance', 0)} | "
          f"Equity: {data.get('equity', 0)} | "
          f"Positions: {data.get('open_positions', 0)}")
    
    return {"status": "ok", "account": account_id}

@app.post("/api/account/history")
async def receive_history(request: Request):
    """接收 EA 傳嚟嘅交易歷史"""
    auth = request.headers.get("X-API-Key", "")
    if auth != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    data = await request.json()
    account_id = data.get("account_id", "unknown")
    
    # 歷史數據分開存
    history_key = f"{account_id}_history"
    accounts_db[history_key] = data
    save_data()
    
    trades = data.get("trades", [])
    print(f"📜 History: {account_id} | {len(trades)} trades")
    
    return {"status": "ok", "trades_received": len(trades)}

@app.get("/api/status")
async def get_status():
    """返回所有帳戶狀態"""
    # 只返回 state 數據（唔包括 history）
    state_accounts = {k: v for k, v in accounts_db.items() if "_history" not in k}
    
    summary = {
        "total_accounts": len(state_accounts),
        "total_balance": sum(a.get("balance", 0) for a in state_accounts.values()),
        "total_equity": sum(a.get("equity", 0) for a in state_accounts.values()),
        "total_profit": sum(a.get("profit", 0) for a in state_accounts.values()),
        "total_positions": sum(a.get("open_positions", 0) for a in state_accounts.values()),
    }
    
    return {
        "accounts": list(state_accounts.values()),
        "summary": summary,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/account/{account_id}")
async def get_account(account_id: str):
    """返回單個帳戶詳情"""
    if account_id in accounts_db:
        return accounts_db[account_id]
    raise HTTPException(status_code=404, detail="Account not found")

# ============ Dashboard ============

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Web Dashboard"""
    state_accounts = {k: v for k, v in accounts_db.items() if "_history" not in k}
    
    # 計算總計
    total_balance = sum(a.get("balance", 0) for a in state_accounts.values())
    total_equity = sum(a.get("equity", 0) for a in state_accounts.values())
    total_profit = sum(a.get("profit", 0) for a in state_accounts.values())
    total_positions = sum(a.get("open_positions", 0) for a in state_accounts.values())
    
    # 生成帳戶卡片
    cards_html = ""
    for acc_id, acc in state_accounts.items():
        label = acc.get("label", acc_id)
        broker = acc.get("broker", "")
        login = acc.get("login", "")
        balance = acc.get("balance", 0)
        equity = acc.get("equity", 0)
        profit = acc.get("profit", 0)
        margin_level = acc.get("margin_level", 0)
        positions = acc.get("open_positions", 0)
        currency = acc.get("currency", "USD")
        leverage = acc.get("leverage", 0)
        ts = acc.get("timestamp", "")
        received = acc.get("received_at", "")
        
        profit_color = "#4caf50" if profit >= 0 else "#f44336"
        profit_sign = "+" if profit >= 0 else ""
        
        # 持倉詳情
        positions_html = ""
        for pos in acc.get("positions", []):
            pos_profit = pos.get("profit", 0)
            pos_color = "#4caf50" if pos_profit >= 0 else "#f44336"
            positions_html += f"""
            <tr>
                <td>{pos.get('symbol','')}</td>
                <td>{pos.get('type','')}</td>
                <td>{pos.get('lots',0):.2f}</td>
                <td>{pos.get('profit',0):+.2f}</td>
                <td>{pos.get('pips',0):+.1f}</td>
            </tr>"""
        
        positions_section = ""
        if positions > 0:
            positions_section = f"""
            <div class="positions">
                <h4>📋 持倉 ({positions})</h4>
                <table>
                    <tr><th>貨幣對</th><th>方向</th><th>手數</th><th>盈虧</th><th>點數</th></tr>
                    {positions_html}
                </table>
            </div>"""
        
        cards_html += f"""
        <div class="card">
            <div class="card-header">
                <span class="label">{label}</span>
                <span class="broker">{broker} #{login}</span>
            </div>
            <div class="card-body">
                <div class="metrics">
                    <div class="metric">
                        <span class="metric-label">餘額</span>
                        <span class="metric-value">{balance:,.2f} {currency}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">淨值</span>
                        <span class="metric-value">{equity:,.2f} {currency}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">浮動盈虧</span>
                        <span class="metric-value" style="color:{profit_color}">{profit_sign}{profit:,.2f} {currency}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">保證金水平</span>
                        <span class="metric-value">{margin_level:.1f}%</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">槓桿</span>
                        <span class="metric-value">1:{leverage}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">持倉</span>
                        <span class="metric-value">{positions}</span>
                    </div>
                </div>
                {positions_section}
            </div>
            <div class="card-footer">
                最後更新: {ts} | 伺服器收到: {received}
            </div>
        </div>"""
    
    if not state_accounts:
        cards_html = '<div class="empty">📭 尚未收到任何帳戶數據<br><small>請確認 MT4 EA 正在運行並指向正確的 API 地址</small></div>'
    
    return f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🦀 MT4 多帳戶監控</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
        h1 {{ text-align: center; color: #FFD700; margin-bottom: 5px; font-size: 24px; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 20px; font-size: 14px; }}
        .summary {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
        .summary-item {{ background: #161b22; padding: 15px 25px; border-radius: 10px; text-align: center; min-width: 150px; border: 1px solid #30363d; }}
        .summary-item .label {{ color: #888; font-size: 12px; }}
        .summary-item .value {{ color: #FFD700; font-size: 22px; font-weight: bold; margin-top: 5px; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(450px, 1fr)); gap: 20px; max-width: 1400px; margin: 0 auto; }}
        .card {{ background: #161b22; border-radius: 12px; border: 1px solid #30363d; overflow: hidden; }}
        .card-header {{ padding: 15px 20px; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; }}
        .card-header .label {{ color: #FFD700; font-weight: bold; font-size: 16px; }}
        .card-header .broker {{ color: #888; font-size: 12px; }}
        .card-body {{ padding: 20px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }}
        .metric {{ text-align: center; }}
        .metric-label {{ display: block; color: #888; font-size: 11px; margin-bottom: 3px; }}
        .metric-value {{ display: block; color: #c9d1d9; font-size: 16px; font-weight: 600; }}
        .positions {{ margin-top: 15px; }}
        .positions h4 {{ color: #58a6ff; margin-bottom: 8px; font-size: 14px; }}
        .positions table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        .positions th {{ color: #888; text-align: left; padding: 5px 8px; border-bottom: 1px solid #30363d; }}
        .positions td {{ padding: 5px 8px; }}
        .card-footer {{ padding: 10px 20px; background: #0d1117; color: #555; font-size: 11px; text-align: center; }}
        .empty {{ text-align: center; color: #888; padding: 60px 20px; font-size: 18px; }}
        .refresh {{ text-align: center; margin-top: 20px; color: #555; font-size: 12px; }}
        @media (max-width: 500px) {{ .metrics {{ grid-template-columns: repeat(2, 1fr); }} .cards {{ grid-template-columns: 1fr; }} }}
    </style>
    <script>setTimeout(() => location.reload(), 30000);</script>
</head>
<body>
    <h1>🦀 MT4 多帳戶監控</h1>
    <div class="subtitle">Account Monitor Dashboard • 自動刷新 30s</div>
    
    <div class="summary">
        <div class="summary-item">
            <div class="label">帳戶數量</div>
            <div class="value">{len(state_accounts)}</div>
        </div>
        <div class="summary-item">
            <div class="label">總餘額</div>
            <div class="value">${total_balance:,.2f}</div>
        </div>
        <div class="summary-item">
            <div class="label">總淨值</div>
            <div class="value">${total_equity:,.2f}</div>
        </div>
        <div class="summary-item">
            <div class="label">總浮動盈虧</div>
            <div class="value" style="color:{"#4caf50" if total_profit >= 0 else "#f44336"}">${"+" if total_profit >= 0 else ""}{total_profit:,.2f}</div>
        </div>
        <div class="summary-item">
            <div class="label">總持倉</div>
            <div class="value">{total_positions}</div>
        </div>
    </div>
    
    <div class="cards">
        {cards_html}
    </div>
    
    <div class="refresh">最後刷新: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
</body>
</html>"""

# ============ 啟動 ============

@app.on_event("startup")
async def startup():
    load_data()
    print(f"🦀 MT4 Account Monitor API started on port {PORT}")
    print(f"📊 Dashboard: http://localhost:{PORT}/dashboard")
    print(f"📡 API: http://localhost:{PORT}/api/status")
    print(f"🔑 API Key: {API_KEY}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
