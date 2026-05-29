"""
MT4 Multi-Account Monitor — Python Service
PRD v1.1 — Phase 1 MVP

FastAPI service that:
1. Receives HTTP POST from MT4 AccountMonitor EA
2. Stores data in SQLite (WAL mode)
3. Pushes notifications to Telegram
4. Serves web dashboard
"""

__version__ = "1.0.0"

import os
import json
import time
import csv
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import OrderedDict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
import uvicorn

# --- Configuration ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "account_monitor.db"
TEMPLATES_DIR = BASE_DIR / "templates"

API_PORT = int(os.getenv("MT4_MONITOR_API_PORT", "8788"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID", "920593269")

# Quiet hours
QUIET_START = os.getenv("MT4_MONITOR_QUIET_HOURS_START", "00:00")
QUIET_END = os.getenv("MT4_MONITOR_QUIET_HOURS_END", "07:00")

# Thresholds
LARGE_MOVE_THRESHOLD = float(os.getenv("MT4_MONITOR_LARGE_MOVE_THRESHOLD", "100"))
LARGE_PNL_THRESHOLD = float(os.getenv("MT4_MONITOR_LARGE_PNL_THRESHOLD", "100"))
MARGIN_WARN_THRESHOLD = float(os.getenv("MT4_MONITOR_MARGIN_WARN", "150"))
MARGIN_CRIT_THRESHOLD = float(os.getenv("MT4_MONITOR_MARGIN_CRIT", "120"))
HTTP_TIMEOUT = int(os.getenv("MT4_MONITOR_HTTP_TIMEOUT", "300"))  # 5 min

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mt4_monitor")


# --- Data Classes ---
@dataclass
class AccountState:
    account_id: str
    label: str
    login: int
    broker: str
    server: str
    name: str
    currency: str
    leverage: int
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    profit: float
    open_positions: int
    pending_orders: int
    positions: list = field(default_factory=list)
    pending: list = field(default_factory=list)
    timestamp: str = ""
    first_run: bool = False
    received_at: float = 0.0

    def __post_init__(self):
        self.received_at = time.time()


@dataclass
class TradeHistory:
    account_id: str
    trades: list = field(default_factory=list)
    full_sync: bool = False
    sync_days: int = 0
    timestamp: str = ""
    received_at: float = 0.0

    def __post_init__(self):
        self.received_at = time.time()


@dataclass
class Notification:
    priority: int  # 0=Critical, 1=High, 2=Normal
    message: str
    account_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    event_type: str = ""


# --- In-Memory Cache ---
class StateCache:
    """Fast in-memory cache for current account states."""
    
    def __init__(self):
        self._accounts: OrderedDict[str, AccountState] = OrderedDict()
        self._history: dict[str, list] = {}  # account_id -> last N trades
        self._last_events: dict[str, float] = {}  # dedup key -> timestamp
    
    def update_account(self, state: AccountState):
        self._accounts[state.account_id] = state
    
    def get_account(self, account_id: str) -> Optional[AccountState]:
        return self._accounts.get(account_id)
    
    def get_all_accounts(self) -> dict[str, AccountState]:
        return dict(self._accounts)
    
    def add_history(self, history: TradeHistory):
        if history.account_id not in self._history:
            self._history[history.account_id] = []
        # Keep last 100 trades per account
        existing_tickets = {t.get("ticket") for t in self._history[history.account_id]}
        for trade in history.trades:
            if trade.get("ticket") not in existing_tickets:
                self._history[history.account_id].append(trade)
        self._history[history.account_id] = self._history[history.account_id][-100:]
    
    def get_history(self, account_id: str) -> list:
        return self._history.get(account_id, [])
    
    def check_event_dedup(self, key: str, window_seconds: float = 60) -> bool:
        """Return True if this is a duplicate event within window."""
        now = time.time()
        if key in self._last_events:
            if now - self._last_events[key] < window_seconds:
                return True
        self._last_events[key] = now
        return False


cache = StateCache()


# --- SQLite Database ---
class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._create_tables()
        logger.info(f"Database initialized: {path}")
    
    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS account_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                account_id TEXT NOT NULL,
                label TEXT,
                login INTEGER,
                broker TEXT,
                balance REAL,
                equity REAL,
                margin REAL,
                free_margin REAL,
                margin_level REAL,
                profit REAL,
                open_positions INTEGER,
                received_at REAL
            );
            
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ticket INTEGER NOT NULL,
                symbol TEXT,
                type TEXT,
                lots REAL,
                open_price REAL,
                current_price REAL,
                sl REAL,
                tp REAL,
                profit REAL,
                swap REAL,
                commission REAL,
                open_time TEXT,
                magic INTEGER,
                comment TEXT,
                pips REAL
            );
            
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket INTEGER NOT NULL,
                account_id TEXT NOT NULL,
                symbol TEXT,
                type TEXT,
                lots REAL,
                open_price REAL,
                close_price REAL,
                open_time TEXT,
                close_time TEXT,
                profit REAL,
                swap REAL,
                commission REAL,
                magic INTEGER,
                comment TEXT,
                received_at REAL,
                UNIQUE(ticket, account_id)
            );
            
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                account_id TEXT,
                event_type TEXT,
                priority INTEGER,
                message TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_states_account ON account_states(account_id);
            CREATE INDEX IF NOT EXISTS idx_positions_ticket ON positions(ticket, account_id);
            CREATE INDEX IF NOT EXISTS idx_history_ticket ON trade_history(ticket, account_id);
            CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp);
        """)
        self.conn.commit()
    
    def save_state(self, state: AccountState):
        now = time.time()
        with self.conn:
            self.conn.execute("""
                INSERT INTO account_states 
                (timestamp, account_id, label, login, broker, balance, equity, 
                 margin, free_margin, margin_level, profit, open_positions, received_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (state.timestamp, state.account_id, state.label, state.login,
                  state.broker, state.balance, state.equity, state.margin,
                  state.free_margin, state.margin_level, state.profit,
                  state.open_positions, now))
            
            # Save positions (delete old, insert new)
            self.conn.execute(
                "DELETE FROM positions WHERE account_id = ? AND timestamp < ?",
                (state.account_id, state.timestamp)
            )
            for pos in state.positions:
                self.conn.execute("""
                    INSERT INTO positions 
                    (timestamp, account_id, ticket, symbol, type, lots, open_price,
                     current_price, sl, tp, profit, swap, commission, open_time,
                     magic, comment, pips)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (state.timestamp, state.account_id,
                      pos.get("ticket"), pos.get("symbol"), pos.get("type"),
                      pos.get("lots"), pos.get("open_price"), pos.get("current_price"),
                      pos.get("sl"), pos.get("tp"), pos.get("profit"),
                      pos.get("swap"), pos.get("commission"), pos.get("open_time"),
                      pos.get("magic"), pos.get("comment"), pos.get("pips")))
    
    def save_history(self, history: TradeHistory):
        with self.conn:
            for trade in history.trades:
                self.conn.execute("""
                    INSERT OR IGNORE INTO trade_history 
                    (ticket, account_id, symbol, type, lots, open_price, close_price,
                     open_time, close_time, profit, swap, commission, magic, comment, received_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (trade.get("ticket"), history.account_id,
                      trade.get("symbol"), trade.get("type"), trade.get("lots"),
                      trade.get("open_price"), trade.get("close_price"),
                      trade.get("open_time"), trade.get("close_time"),
                      trade.get("profit"), trade.get("swap"), trade.get("commission"),
                      trade.get("magic"), trade.get("comment"), time.time()))
    
    def save_event(self, event: Notification):
        with self.conn:
            self.conn.execute("""
                INSERT INTO events (timestamp, account_id, event_type, priority, message)
                VALUES (?,?,?,?,?)
            """, (event.created_at.isoformat(), event.account_id,
                  event.event_type, event.priority, event.message))
    
    def cleanup(self):
        """Remove old data based on retention policy."""
        cutoff_7d = (datetime.now() - timedelta(days=7)).isoformat()
        cutoff_90d = (datetime.now() - timedelta(days=90)).isoformat()
        
        with self.conn:
            # 7-day: raw states and positions
            self.conn.execute("DELETE FROM account_states WHERE timestamp < ?", (cutoff_7d,))
            self.conn.execute("DELETE FROM positions WHERE timestamp < ?", (cutoff_7d,))
            logger.info("Cleaned up data older than 7 days")


# Initialize database
db = Database(DB_PATH)


# --- Event Detector ---
class EventDetector:
    """Detect events from state changes."""
    
    def __init__(self):
        self._prev_positions: dict[str, set] = {}  # account_id -> set of tickets
        self._prev_balance: dict[str, float] = {}
    
    def detect(self, state: AccountState) -> list[Notification]:
        events = []
        account_id = state.account_id
        label = state.label
        
        # Current position tickets
        current_tickets = {p.get("ticket") for p in state.positions}
        prev_tickets = self._prev_positions.get(account_id, set())
        
        # New positions
        new_tickets = current_tickets - prev_tickets
        for ticket in new_tickets:
            pos = next((p for p in state.positions if p.get("ticket") == ticket), None)
            if pos:
                # Skip dedup
                dedup_key = f"open_{account_id}_{ticket}"
                if not cache.check_event_dedup(dedup_key, 120):
                    msg = (
                        f"🟢 新開倉 — {label}\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"📊 {pos['symbol']} | {pos['type']} {pos['lots']} lot\n"
                        f"💰 開倉價: {pos['open_price']}\n"
                        f"🛡️ SL: {pos.get('sl', 0)} | TP: {pos.get('tp', 0)}\n"
                        f"🤖 Magic: #{pos.get('magic', 0)}\n"
                        f"⏰ {state.timestamp}"
                    )
                    events.append(Notification(
                        priority=2, message=msg, account_id=account_id,
                        event_type="position_open"
                    ))
        
        # Closed positions
        closed_tickets = prev_tickets - current_tickets
        for ticket in closed_tickets:
            dedup_key = f"close_{account_id}_{ticket}"
            if not cache.check_event_dedup(dedup_key, 120):
                # Check if large close
                priority = 2
                msg_prefix = "🔴 平倉"
                
                msg = (
                    f"{msg_prefix} — {label}\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🎫 Ticket: #{ticket}\n"
                    f"⏰ {state.timestamp}"
                )
                events.append(Notification(
                    priority=priority, message=msg, account_id=account_id,
                    event_type="position_close"
                ))
        
        # Margin warnings
        if state.margin_level > 0:
            if state.margin_level < MARGIN_CRIT_THRESHOLD:
                dedup_key = f"margin_crit_{account_id}"
                if not cache.check_event_dedup(dedup_key, 300):  # 5 min dedup
                    msg = (
                        f"🚨 保證金危險 — {label}\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"⚠️ Margin Level: {state.margin_level:.1f}%\n"
                        f"💰 Equity: {state.equity:.2f}\n"
                        f"📊 Free Margin: {state.free_margin:.2f}\n"
                        f"⏰ {state.timestamp}"
                    )
                    events.append(Notification(
                        priority=0, message=msg, account_id=account_id,
                        event_type="margin_critical"
                    ))
            elif state.margin_level < MARGIN_WARN_THRESHOLD:
                dedup_key = f"margin_warn_{account_id}"
                if not cache.check_event_dedup(dedup_key, 300):
                    msg = (
                        f"⚠️ 保證金警告 — {label}\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"⚠️ Margin Level: {state.margin_level:.1f}%\n"
                        f"💰 Equity: {state.equity:.2f}\n"
                        f"⏰ {state.timestamp}"
                    )
                    events.append(Notification(
                        priority=1, message=msg, account_id=account_id,
                        event_type="margin_warning"
                    ))
        
        # Large PnL change
        for pos in state.positions:
            if abs(pos.get("profit", 0)) > LARGE_PNL_THRESHOLD:
                dedup_key = f"large_pnl_{account_id}_{pos.get('ticket')}"
                if not cache.check_event_dedup(dedup_key, 600):  # 10 min dedup
                    direction = "📈" if pos["profit"] > 0 else "📉"
                    msg = (
                        f"{direction} 大額浮動 — {label}\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"📊 {pos['symbol']} | {pos['type']}\n"
                        f"💰 浮動盈虧: {pos['profit']:.2f} {state.currency}\n"
                        f"⏰ {state.timestamp}"
                    )
                    events.append(Notification(
                        priority=1, message=msg, account_id=account_id,
                        event_type="large_pnl"
                    ))
        
        # Balance change
        prev_balance = self._prev_balance.get(account_id)
        if prev_balance is not None and abs(state.balance - prev_balance) > 1:
            diff = state.balance - prev_balance
            if not cache.check_event_dedup(f"balance_{account_id}", 60):
                direction = "📈" if diff > 0 else "📉"
                msg = (
                    f"{direction} 餘額變動 — {label}\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"💰 {prev_balance:.2f} → {state.balance:.2f} ({diff:+.2f})\n"
                    f"⏰ {state.timestamp}"
                )
                events.append(Notification(
                    priority=2, message=msg, account_id=account_id,
                    event_type="balance_change"
                ))
        
        # Update state
        self._prev_positions[account_id] = current_tickets
        self._prev_balance[account_id] = state.balance
        
        return events


detector = EventDetector()


# --- Telegram Notification ---
class TelegramNotifier:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.user_id = TELEGRAM_USER_ID
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._sent_times: list[float] = []
    
    def is_configured(self) -> bool:
        return bool(self.bot_token)
    
    def is_quiet_hours(self) -> bool:
        now = datetime.now()
        try:
            start_h, start_m = map(int, QUIET_START.split(":"))
            end_h, end_m = map(int, QUIET_END.split(":"))
            start_min = start_h * 60 + start_m
            end_min = end_h * 60 + end_m
            now_min = now.hour * 60 + now.minute
            
            if start_min <= end_min:
                return start_min <= now_min < end_min
            else:  # crosses midnight
                return now_min >= start_min or now_min < end_min
        except Exception:
            return False
    
    async def enqueue(self, notification: Notification):
        await self._queue.put((notification.priority, id(notification), notification))
    
    async def start_worker(self):
        if self._running:
            return
        self._running = True
        asyncio.create_task(self._worker())
    
    async def _worker(self):
        while self._running:
            try:
                _, _, notif = await asyncio.wait_for(
                    self._queue.get(), timeout=5.0
                )
                
                # Check quiet hours — only send Critical
                if self.is_quiet_hours() and notif.priority > 0:
                    logger.info(f"Suppressed (quiet hours): {notif.event_type}")
                    continue
                
                # Rate limit: 1 msg/sec, 20 msg/min
                await self._wait_for_rate_limit()
                
                # Send via OpenClaw message tool or direct API
                await self._send(notif.message)
                
                # Save event
                db.save_event(notif)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Telegram worker error: {e}")
                await asyncio.sleep(5)
    
    async def _wait_for_rate_limit(self):
        now = time.time()
        # Burst limit: 20 per 60s
        while len(self._sent_times) >= 20:
            if now - self._sent_times[0] > 60:
                self._sent_times.pop(0)
            else:
                await asyncio.sleep(1.0)
                now = time.time()
        # Rate limit: 1 msg/sec
        if self._sent_times:
            elapsed = now - self._sent_times[-1]
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
        self._sent_times.append(time.time())
    
    async def _send(self, message: str):
        if not self.is_configured():
            logger.info(f"[Telegram not configured] {message[:80]}...")
            return
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.user_id,
            "text": message,
            "parse_mode": "HTML"
        }
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=payload, timeout=10)
                if resp.status_code == 429:
                    retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
                    logger.warning(f"Telegram rate limited, retry after {retry_after}s")
                    await asyncio.sleep(retry_after)
                elif resp.status_code != 200:
                    logger.error(f"Telegram error: {resp.status_code} {resp.text[:200]}")
            except Exception as e:
                logger.error(f"Telegram send error: {e}")


notifier = TelegramNotifier()


# --- FastAPI App ---
app = FastAPI(title="MT4 Multi-Account Monitor", version=__version__)


@app.on_event("startup")
async def startup():
    await notifier.start_worker()
    logger.info("MT4 Monitor service started")


@app.get("/")
async def root():
    return {"status": "ok", "version": __version__}


@app.get("/api/status")
async def api_status():
    """Get all account statuses."""
    accounts = cache.get_all_accounts()
    result = []
    for acct_id, state in accounts.items():
        result.append({
            "account_id": acct_id,
            "label": state.label,
            "broker": state.broker,
            "login": state.login,
            "balance": state.balance,
            "equity": state.equity,
            "profit": state.profit,
            "margin_level": state.margin_level,
            "open_positions": state.open_positions,
            "currency": state.currency,
            "timestamp": state.timestamp,
            "age_seconds": int(time.time() - state.received_at),
        })
    
    # Check for stale accounts (> HTTP_TIMEOUT)
    total_balance = sum(a.balance for a in accounts.values())
    total_equity = sum(a.equity for a in accounts.values())
    total_profit = sum(a.profit for a in accounts.values())
    
    return {
        "accounts": result,
        "summary": {
            "total_accounts": len(result),
            "total_balance": round(total_balance, 2),
            "total_equity": round(total_equity, 2),
            "total_profit": round(total_profit, 2),
            "total_positions": sum(a.open_positions for a in accounts.values()),
        },
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/account/state")
async def receive_state(request: Request):
    """Receive account state from MT4 EA."""
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    # Parse state
    try:
        state = AccountState(
            account_id=data.get("account_id", ""),
            label=data.get("label", ""),
            login=data.get("login", 0),
            broker=data.get("broker", ""),
            server=data.get("server", ""),
            name=data.get("name", ""),
            currency=data.get("currency", "USD"),
            leverage=data.get("leverage", 0),
            balance=float(data.get("balance", 0)),
            equity=float(data.get("equity", 0)),
            margin=float(data.get("margin", 0)),
            free_margin=float(data.get("free_margin", 0)),
            margin_level=float(data.get("margin_level", 0)),
            profit=float(data.get("profit", 0)),
            open_positions=int(data.get("open_positions", 0)),
            pending_orders=int(data.get("pending_orders", 0)),
            positions=data.get("positions", []),
            pending=data.get("pending", []),
            timestamp=data.get("timestamp", ""),
            first_run=data.get("first_run", False),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {e}")
    
    # Update cache
    cache.update_account(state)
    
    # Save to DB
    db.save_state(state)
    
    # Detect events
    events = detector.detect(state)
    for event in events:
        await notifier.enqueue(event)
    
    logger.info(
        f"State received: {state.label} | "
        f"Balance: {state.balance:.2f} | Equity: {state.equity:.2f} | "
        f"Positions: {state.open_positions} | Events: {len(events)}"
    )
    
    return {"status": "ok", "events": len(events)}


@app.post("/api/account/history")
async def receive_history(request: Request):
    """Receive trade history from MT4 EA."""
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    history = TradeHistory(
        account_id=data.get("account_id", ""),
        trades=data.get("trades", []),
        full_sync=data.get("full_sync", False),
        sync_days=data.get("sync_days", 0),
        timestamp=data.get("timestamp", ""),
    )
    
    # Update cache
    cache.add_history(history)
    
    # Save to DB
    db.save_history(history)
    
    logger.info(
        f"History received: {history.account_id} | "
        f"Trades: {len(history.trades)} | "
        f"Full sync: {history.full_sync}"
    )
    
    return {"status": "ok", "trades_received": len(history.trades)}


@app.get("/api/positions")
async def api_positions():
    """Get all open positions across accounts."""
    accounts = cache.get_all_accounts()
    positions = []
    for acct_id, state in accounts.items():
        for pos in state.positions:
            positions.append({
                **pos,
                "account_id": acct_id,
                "account_label": state.label,
                "currency": state.currency,
            })
    return {"positions": positions, "count": len(positions)}


@app.get("/api/history/{account_id}")
async def api_history(account_id: str, limit: int = 50):
    """Get trade history for an account."""
    trades = cache.get_history(account_id)[-limit:]
    return {"account_id": account_id, "trades": trades, "count": len(trades)}


@app.get("/api/events")
async def api_events(limit: int = 50):
    """Get recent events."""
    rows = db.conn.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return {"events": [dict(zip([d[0] for d in db.conn.execute("SELECT * FROM events LIMIT 0").description], row)) for row in rows]}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Simple dashboard HTML."""
    accounts = cache.get_all_accounts()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MT4 多帳戶監控</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a2e; color: #eee; padding: 20px;
        }}
        .header {{ text-align: center; margin-bottom: 24px; }}
        .header h1 {{ font-size: 24px; color: #0f3460; background: #e94560; padding: 12px; border-radius: 8px; }}
        .header .time {{ color: #888; font-size: 14px; margin-top: 8px; }}
        
        .summary {{ 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px; margin-bottom: 24px;
        }}
        .summary-card {{
            background: #16213e; border-radius: 12px; padding: 20px; text-align: center;
        }}
        .summary-card .value {{ font-size: 28px; font-weight: bold; margin-top: 8px; }}
        .summary-card .label {{ font-size: 12px; color: #888; text-transform: uppercase; }}
        .positive {{ color: #4caf50; }}
        .negative {{ color: #f44336; }}
        .neutral {{ color: #2196f3; }}
        
        .accounts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .account-card {{
            background: #16213e; border-radius: 12px; padding: 20px;
            border-left: 4px solid #e94560;
        }}
        .account-card h3 {{ margin-bottom: 12px; font-size: 16px; }}
        .account-row {{ display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px; }}
        .account-row .key {{ color: #888; }}
        
        .positions {{ background: #16213e; border-radius: 12px; padding: 20px; }}
        .positions h3 {{ margin-bottom: 16px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th {{ text-align: left; padding: 8px; border-bottom: 2px solid #0f3460; color: #888; }}
        td {{ padding: 8px; border-bottom: 1px solid #0f3460; }}
        tr:nth-child(even) {{ background: rgba(255,255,255,0.03); }}
        
        .stale {{ opacity: 0.5; }}
        .stale::after {{ content: ' ⚠️'; }}
        
        .refresh {{ position: fixed; bottom: 20px; right: 20px; background: #e94560; color: white;
            border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; }}
    </style>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <div class="header">
        <h1>📊 MT4 多帳戶監控</h1>
        <div class="time">最後更新: {now} | 每 30 秒自動刷新</div>
    </div>
"""
    
    if not accounts:
        html += '<div style="text-align:center;color:#888;padding:40px;">等待 MT4 EA 連接...</div>'
    else:
        # Summary cards
        total_balance = sum(a.balance for a in accounts.values())
        total_equity = sum(a.equity for a in accounts.values())
        total_profit = sum(a.profit for a in accounts.values())
        total_positions = sum(a.open_positions for a in accounts.values())
        
        profit_class = "positive" if total_profit >= 0 else "negative"
        
        html += f"""
    <div class="summary">
        <div class="summary-card">
            <div class="label">總資產</div>
            <div class="value neutral">${total_equity:,.2f}</div>
        </div>
        <div class="summary-card">
            <div class="label">總餘額</div>
            <div class="value">${total_balance:,.2f}</div>
        </div>
        <div class="summary-card">
            <div class="label">浮動盈虧</div>
            <div class="value {profit_class}">{total_profit:+,.2f}</div>
        </div>
        <div class="summary-card">
            <div class="label">總持倉數</div>
            <div class="value">{total_positions}</div>
        </div>
    </div>
"""
        
        # Account cards
        html += '<div class="accounts">'
        for acct_id, state in accounts.items():
            age = int(time.time() - state.received_at)
            stale = age > HTTP_TIMEOUT
            profit_class = "positive" if state.profit >= 0 else "negative"
            margin_color = "#f44336" if (state.margin_level > 0 and state.margin_level < MARGIN_WARN_THRESHOLD) else "#4caf50"
            
            html += f"""
        <div class="account-card {'stale' if stale else ''}">
            <h3>🏦 {state.label}</h3>
            <div class="account-row"><span class="key">Broker</span><span>{state.broker}</span></div>
            <div class="account-row"><span class="key">Login</span><span>#{state.login}</span></div>
            <div class="account-row"><span class="key">Balance</span><span>${state.balance:,.2f}</span></div>
            <div class="account-row"><span class="key">Equity</span><span>${state.equity:,.2f}</span></div>
            <div class="account-row"><span class="key">浮動盈虧</span><span class="{profit_class}">{state.profit:+,.2f}</span></div>
            <div class="account-row"><span class="key">Margin Level</span><span style="color:{margin_color}">{state.margin_level:.1f}%</span></div>
            <div class="account-row"><span class="key">持倉數</span><span>{state.open_positions}</span></div>
            <div class="account-row"><span class="key">更新</span><span>{state.timestamp}</span></div>
        </div>
"""
        html += '</div>'
        
        # Positions table
        html += '<div class="positions"><h3>📊 活躍持倉</h3><table>'
        html += '<tr><th>Account</th><th>Symbol</th><th>Type</th><th>Lots</th><th>Open</th><th>Current</th><th>P/L</th><th>Pips</th></tr>'
        
        for acct_id, state in accounts.items():
            for pos in state.positions:
                pl_class = "positive" if pos.get("profit", 0) >= 0 else "negative"
                html += f"""<tr>
                    <td>{state.label}</td>
                    <td>{pos.get('symbol')}</td>
                    <td>{pos.get('type')}</td>
                    <td>{pos.get('lots')}</td>
                    <td>{pos.get('open_price')}</td>
                    <td>{pos.get('current_price')}</td>
                    <td class="{pl_class}">{pos.get('profit', 0):+,.2f}</td>
                    <td>{pos.get('pips', 0):+.1f}</td>
                </tr>"""
        
        html += '</table></div>'
    
    html += """
    <button class="refresh" onclick="location.reload()">🔄 刷新</button>
</body>
</html>"""
    
    return html


# --- Disconnect Monitor ---
async def check_disconnects():
    """Check for stale accounts (no data for > HTTP_TIMEOUT seconds)."""
    while True:
        await asyncio.sleep(60)
        accounts = cache.get_all_accounts()
        for acct_id, state in accounts.items():
            age = time.time() - state.received_at
            if age > HTTP_TIMEOUT:
                dedup_key = f"disconnect_{acct_id}"
                if not cache.check_event_dedup(dedup_key, 600):  # 10 min dedup
                    msg = (
                        f"🔌 MT4 斷線偵測\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"🏦 {state.label}\n"
                        f"⏰ 最後更新: {int(age)}秒前\n"
                        f"⚠️ 超過 {HTTP_TIMEOUT} 秒未收到數據"
                    )
                    await notifier.enqueue(Notification(
                        priority=0, message=msg, account_id=acct_id,
                        event_type="disconnect"
                    ))


@app.on_event("startup")
async def start_disconnect_monitor():
    asyncio.create_task(check_disconnects())


# --- Entry Point ---
def main():
    logger.info(f"Starting MT4 Monitor on port {API_PORT}")
    logger.info(f"Telegram: {'configured' if notifier.is_configured() else 'NOT configured (set TELEGRAM_BOT_TOKEN)'}")
    logger.info(f"Quiet hours: {QUIET_START} - {QUIET_END}")
    uvicorn.run(app, host="127.0.0.1", port=API_PORT, log_level="info")


if __name__ == "__main__":
    main()
