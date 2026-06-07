#!/usr/bin/env python3
"""
MT4 Watchdog Daemon - 持續運行，每5分鐘檢查新交易事件
唔需要 OpenClaw isolated session，直接用 HTTP API 觸發 agent 發送通知

設計原則：
- 監測同通知分離
- daemon 只做一件事：偵測新事件，觸發 OpenClaw
- OpenClaw agent 負責發送通知（WhatsApp + Telegram 等）
"""

import json
import time
import csv
import requests
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# ============================================
# 配置區（唔包含任何 API Key）
# ============================================

# MT4 Terminal 目錄（WSL path）
MT4_BASE = Path("/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal")

# OpenClaw Gateway HTTP API 配置
GATEWAY_URL = "http://127.0.0.1:18789/v1/chat/completions"
GATEWAY_TOKEN_FILE = Path.home() / ".openclaw" / "openclaw.json"

# 狀態檔案路徑（喺 trade_strategy_analyzer/mt4_monitor 目錄下）
SCRIPT_DIR = Path(__file__).parent
STATE_FILE = SCRIPT_DIR / "watchdog_state.json"
PENDING_EVENTS_FILE = SCRIPT_DIR / "pending_events.json"

# 檢查間隔（秒）
CHECK_INTERVAL = 300  # 5 分鐘

# MT4 Terminal ID 長度（32 chars）
MT4_TERMINAL_ID_LENGTH = 32


# ============================================
# 讀取 Gateway Token
# ============================================

def get_gateway_token() -> str:
    """從 openclaw.json讀取 Gateway auth token"""
    try:
        with open(GATEWAY_TOKEN_FILE) as f:
            config = json.load(f)
            token = config.get("gateway", {}).get("auth", {}).get("token", "")
            if not token:
                raise ValueError("Gateway token not found in config")
            return token
    except Exception as e:
        log(f"❌ 無法讀取 Gateway token: {e}")
        sys.exit(1)


# ============================================
# 狀態管理
# ============================================

def load_state() -> Dict[str, str]:
    """載入上次處理狀態（每個 CSV檔案嘅最後處理時間）"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception as e:
            log(f"⚠️ 狀態檔案損壞，重新初始化: {e}")
    return {"processed": {}}


def save_state(state: Dict[str, str]) -> None:
    """保存處理狀態"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ============================================
# 事件檢測
# ============================================

def find_terminal_dirs() -> List[Path]:
    """找到所有 MT4 Terminal 目錄（32 chars ID）"""
    terminals = []
    if not MT4_BASE.exists():
        log(f"⚠️ MT4 base path 不存在: {MT4_BASE}")
        return terminals
    
    for item in MT4_BASE.iterdir():
        if item.is_dir() and len(item.name) == MT4_TERMINAL_ID_LENGTH:
            terminals.append(item)
    
    return terminals


def find_monitor_csv_files(terminal_dir: Path) -> List[Path]:
    """找到 Terminal 目錄下嘅 monitor_events_*.csv 檔案"""
    files_dir = terminal_dir / "MQL4" / "Files"
    if not files_dir.exists():
        return []
    
    return list(files_dir.glob("monitor_events_*.csv"))


def parse_csv_timestamp(timestamp_str: str) -> datetime:
    """解析 CSV timestamp（格式：2026.06.06 20:45:13）"""
    try:
        return datetime.strptime(timestamp_str, "%Y.%m.%d %H:%M:%S")
    except ValueError:
        return datetime.min


def read_new_events(csv_file: Path, last_timestamp: Optional[str]) -> List[Dict[str, Any]]:
    """
    讀取 CSV檔案，濾出未處理過嘅 NEW_ORDER / CLOSE_ORDER 事件
    
    CSV欄位：
    timestamp | account | event_type | symbol | ticket | order_type | lots | price | sl | tp | magic | balance | equity | free_margin | profit | comment | indicators | extra
    """
    events = []
    
    try:
        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            
            last_dt = parse_csv_timestamp(last_timestamp) if last_timestamp else datetime.min
            
            for row in reader:
                event_type = row.get("event_type", "")
                
                # 只處理 NEW_ORDER / CLOSE_ORDER 事件
                if event_type not in ("NEW_ORDER", "CLOSE_ORDER"):
                    continue
                
                timestamp_str = row.get("timestamp", "")
                row_dt = parse_csv_timestamp(timestamp_str)
                
                # 濾出未處理過嘅事件（timestamp > last_timestamp）
                if row_dt > last_dt:
                    events.append(row)
                    log(f"  📋 新事件: {event_type} | {row.get('symbol')} | {row.get('ticket')} | {timestamp_str}")
    
    except Exception as e:
        log(f"⚠️ 無法讀取 CSV: {csv_file} - {e}")
    
    return events


def check_all_terminals(state: Dict[str, str]) -> List[Dict[str, Any]]:
    """掃描所有 Terminal，收集所有未處理事件"""
    all_events = []
    processed = state.get("processed", {})
    
    terminals = find_terminal_dirs()
    log(f"🔍 找到 {len(terminals)}個MT4 Terminal 目錄")
    
    for terminal_dir in terminals:
        csv_files = find_monitor_csv_files(terminal_dir)
        
        for csv_file in csv_files:
            csv_key = csv_file.name
            last_timestamp = processed.get(csv_key)
            
            log(f"  📄 檢查: {csv_file.name}")
            
            new_events = read_new_events(csv_file, last_timestamp)
            
            if new_events:
                all_events.extend(new_events)
                
                # 更新最後處理時間（取最新事件嘅 timestamp）
                latest_timestamp = max(
                    e.get("timestamp", "") for e in new_events
                )
                processed[csv_key] = latest_timestamp
    
    # 更新狀態
    state["processed"] = processed
    
    return all_events


# ============================================
# 觸發 OpenClaw Agent
# ============================================

def trigger_openclaw_agent(events: List[Dict[str, Any]]) -> bool:
    """
    用 HTTP API 觸發 OpenClaw agent處理事件
    
    Agent 會讀取 pending_events.json並發送通知到 WhatsApp + Telegram
    """
    
    # 寫入待處理事件
    with open(PENDING_EVENTS_FILE, "w") as f:
        json.dump(events, f, indent=2)
    
    log(f"📝 已寫入 {len(events)}個事件到 pending_events.json")
    
    # 構建 HTTP request
    token = get_gateway_token()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openclaw/main",  # 用 main agent處理
        "user": "mt4-watchdog",    # 固定 session key
        "messages": [{
            "role": "user",
            "content": f"""
處理 MT4 監測事件。

事件檔案路徑：{PENDING_EVENTS_FILE}

請執行以下步驟：
1. 讀取 {PENDING_EVENTS_FILE}
2. 按 SYMBOL 分組
3. 格式化通知消息
4. 發送到 WhatsApp 群組（210106226610399@g.us）
5. 發送到 Telegram 群組（-5211779365）

格式範例（新訂單）：
🟢 新訂單 | AUDCAD
━━━━━━━━━━━━━━━━━
📋 方向：BUY | 手數：0.50
💲 入場價：0.9885
📈 指標：EMA[UP_TREND] RSI[55,NEUTRAL] MACD[POS]
"""
        }]
    }
    
    try:
        response = requests.post(
            GATEWAY_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            log(f"✅ OpenClaw agent 已觸發")
            return True
        else:
            log(f"❌ HTTP API 失敗: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        log(f"❌ HTTP request 失敗: {e}")
        return False


# ============================================
# 日誌
# ============================================

def log(message: str) -> None:
    """日誌輸出（帶時間戳）"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


# ============================================
# Main Daemon Loop
# ============================================

def main() -> None:
    """主循環：每5分鐘檢查一次"""
    log("🚀 MT4 Watchdog Daemon啟動")
    log(f"   檢查間隔：{CHECK_INTERVAL}秒（5 分鐘）")
    log(f"   MT4 base：{MT4_BASE}")
    log(f"   Gateway API：{GATEWAY_URL}")
    
    while True:
        try:
            log("━" * 50)
            log("🔍 開始檢查 MT4 事件...")
            
            # 載入狀態
            state = load_state()
            
            # 檢查所有 Terminal
            events = check_all_terminals(state)
            
            if events:
                log(f"📢 發現 {len(events)}個新事件")
                
                # 觸發 OpenClaw agent
                success = trigger_openclaw_agent(events)
                
                if success:
                    # 保存狀態（成功處理後）
                    save_state(state)
                    log(f"✅ 狀態已保存")
                else:
                    log(f"⚠️ 觸發失敗，唔更新狀態（下次會重新處理）")
            else:
                log(f"😴 冇新事件")
                # 冇事件都要保存狀態（更新檔案訪問時間）
                save_state(state)
            
            log(f"💤 等待 {CHECK_INTERVAL}秒...")
            time.sleep(CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            log("🛑 收到停止信號，退出 daemon")
            break
        
        except Exception as e:
            log(f"❌ 錯誤: {e}")
            log(f"💤 等待 {CHECK_INTERVAL}秒後重試...")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()