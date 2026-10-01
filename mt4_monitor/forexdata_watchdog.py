#!/usr/bin/env python3
"""
forex_data 自動 watchdog
- 每 5 分鐘檢查 T1 嘅 forex_data.csv 新鮮度（exporter 每小時 :01 寫入）
- 陳舊 > 70 分鐘 → 自動重啟 MT4-T1（只殺 "Vantage International MT4 - 2" 嗰個 terminal.exe）
- 重啟後 8 分鐘覆核寫入有冇恢復，通知 Telegram（經 Gateway localhost API 免 token 跑通知版？唔 — 直接用 bot token send）
狀態/日誌：同目錄 forexdata_watchdog.log / .state.json
"""
import json, subprocess, time, os
from pathlib import Path
from datetime import datetime

CSV = Path("/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/MQL4/Files/forex_data.csv")
MT4_EXE = r"C:\Program Files (x86)\Vantage International MT4 - 2\terminal.exe"
LOG = Path(__file__).parent / "forexdata_watchdog.log"
STATE = Path(__file__).parent / "forexdata_watchdog.state.json"
STALE_MIN = 70          # mtime 舊過呢個數 = 塞
CHECK_SEC = 300         # 5 分鐘一次
RECHECK_SEC = 480       # 重啟後 8 分鐘覆核
COOLDOWN_MIN = 40       # 兩次重啟之間最少隔（防 loop）

PS = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f: f.write(line + "\n")

def load_state():
    try: return json.loads(STATE.read_text())
    except Exception: return {}

def save_state(s): STATE.write_text(json.dumps(s))

def notify(text):
    # 經 WSL 直接 call bot API（token 由 config 讀，唔寫入任何 log）
    try:
        cfg = json.loads((Path.home()/".openclaw/openclaw.json").read_text())
        tok = cfg["channels"]["telegram"]["accounts"]["main"]["botToken"]
        subprocess.run(["curl","-s","-m","10","-X","POST",
            f"https://api.telegram.org/bot{tok}/sendMessage",
            "-d","chat_id=920593269","-d",f"text={text}"], capture_output=True)
    except Exception as e:
        log(f"notify fail: {e}")

def csv_age_min():
    try: return (time.time() - CSV.stat().st_mtime) / 60
    except FileNotFoundError: return 9999

def restart_t1():
    # 淨殺 MT4-2 嗰個 process（用 ExecutablePath 鎖定，唔會錯殺其他 MT4）
    r = subprocess.run([PS, "-Command",
        "Get-CimInstance Win32_Process -Filter \"name='terminal.exe'\" | "
        f"Where-Object {{$_.ExecutablePath -like '*MT4 - 2*'}} | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Output ('killed ' + $_.ProcessId) }"],
        capture_output=True, text=True, timeout=60)
    log("kill: " + r.stdout.strip())
    time.sleep(5)
    r2 = subprocess.run([PS, "-Command",
        f"Start-Process '{MT4_EXE}'; Write-Output started"],
        capture_output=True, text=True, timeout=60)
    log("start: " + r2.stdout.strip())

def main():
    log("=== forexdata watchdog 啟動 ===")
    while True:
        try:
            st = load_state()
            age = csv_age_min()
            now = time.time()
            last_rs = st.get("last_restart", 0)
            pending = st.get("pending_recheck", 0)

            if pending and now >= pending:
                age2 = csv_age_min()
                if age2 < STALE_MIN:
                    log(f"覆核 OK：age {age2:.0f}min 已恢復")
                    notify(f"✅ forex_data 已恢復（age {age2:.0f}min）— watchdog 自動修復成功")
                else:
                    log(f"覆核仍塞：age {age2:.0f}min")
                    notify(f"⚠️ forex_data 重啟後仍塞（age {age2:.0f}min）— 需要人手睇吓")
                st["pending_recheck"] = 0; save_state(st)
            elif age > STALE_MIN:
                if (now - last_rs) / 60 >= COOLDOWN_MIN:
                    log(f"偵測塞流：age {age:.0f}min > {STALE_MIN}min → 重啟 MT4-T1")
                    notify(f"🚨 forex_data 塞（age {age:.0f}min）— watchdog 自動重啟 MT4-T1 中")
                    restart_t1()
                    st["last_restart"] = now
                    st["pending_recheck"] = now + RECHECK_SEC
                    save_state(st)
                else:
                    log(f"塞但 cooldown 中（重啟於 {(now-last_rs)/60:.0f}min 前）")
            else:
                if int(age) % 15 == 0 or age < 6:
                    log(f"OK age {age:.0f}min")
        except Exception as e:
            log(f"ERROR {e}")
        time.sleep(CHECK_SEC)

if __name__ == "__main__":
    main()
