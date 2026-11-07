//+------------------------------------------------------------------+
//|                                             TradeDashboard.mq4   |
//|                              Trading Dashboard for MT4           |
//|                              v1.33 - fix out-of-chart: tabs top-left + panel clamped to chart width|
//|                                    Broker summary-proof engine   |
//+------------------------------------------------------------------+
#property copyright "FF48 Alvin"
#property version   "1.63"
#property strict
#property description "TradeDashboard v1.63 (two-platform aligned)"

#import "shell32.dll"
   int ShellExecuteW(int hWnd, string Operation, string File, string Parameters, string Directory, int ShowCmd);
#import

#import "user32.dll"
   int GetAncestor(int hWnd, int gaFlags);
   int GetMenu(int hWnd);
   int GetSubMenu(int hMenu, int nPos);
   int GetMenuItemCount(int hMenu);
   int GetMenuItemID(int hMenu, int nPos);
   int GetMenuStringW(int hMenu, int uIDItem, ushort &lpString[], int nMaxCount, int uFlag);
   int PostMessageW(int hWnd, int Msg, int wParam, int lParam);
   int MessageBoxW(int hWnd, string text, string caption, int type);
#import
#import
#import

//=== INPUTS ===
//--- v1.44: Panel Label first; NewsGuard/DDGuard default OFF (enable when needed)
//=== INPUTS (v1.63: 12 groups / 70 params, two-platform aligned) ===
//--- v1.44: NewsGuard/DDGuard default OFF (enable when needed)
//--- v1.60 FIX-TD10: rename per 1230 letter 66-row table; 2 new DD-money params

input group "General"
input string InpTitleLine1              = "TradeDashboard";                          // Line 1 (max 30 chars) - no version in panel
input string InpTitleLine2              = "Flying to the moon";                      // Line 2 Subtitle (max 50 chars)
input int    InpPanelScale              = 1;                                         // Panel size multiplier (1, 2 or 3)
input int    InpDefaultView             = 0;                                         // 0=Hour (default), 1=Day, 2=Week, 3=Month

input group "Display"
input bool   InpShowDay                 = true;                                      // Show Day column in stats table
input bool   InpShowTrades              = true;                                      // Show trade count column
input bool   InpShowBuySell             = true;                                      // Buy/Sell count
input bool   InpShowWinRate             = true;                                      // Show win rate column
input bool   InpShowGainMoney           = true;                                      // Show gain in money column
input bool   InpShowGainPercent         = true;                                      // Show gain in percent column
input bool   InpShowPips                = true;                                      // Show net pips column
input bool   InpShowLots                = true;                                      // Show lots column
input bool   InpShowTotalLots           = true;                                      // Show total lots row
input bool   InpShowBalance             = true;                                      // Show balance row
input bool   InpShowMargin              = true;                                      // Show margin row
input bool   InpShowFreeMargin          = true;                                      // Show free margin row
input bool   InpShowFloatPeakProfit     = true;                                      // Max floating profit (peak)
input bool   InpShowFloatPeakLoss       = true;                                      // Max floating loss = intraday MaxDD
input bool   InpShowProfitFactor        = true;                                      // Show profit factor row
input bool   InpShowAvgPnl              = true;                                      // Show average P/L row
input bool   InpShowBestTrade           = true;                                      // Show best trade row
input bool   InpShowWorstTrade          = true;                                      // Show worst trade row
input bool   InpShowMaxDdMoney          = true;                                      // Max drawdown $
input bool   InpShowMaxDdPercent        = true;                                      // Max drawdown %
input bool   InpShowPnlChart            = false;                                     // Show cumulative P&L chart

input group "Refresh & Recording"
input int    InpRefreshSeconds          = 10;                                        // Panel refresh interval in seconds
input int    InpRecordSeconds           = 1;                                         // Min seconds between records (1=every tick)
input int    InpMaxRecords              = 12000;                                     // Records in ring buffer (max 20000)

input group "Data Filter"
input string InpReportStart             = "";                                        // Report start date YYYY.MM.DD (empty=no filter)
input string InpFilterSymbol            = "";                                        // Filter by symbol (empty=all)
input string InpFilterComment           = "";                                        // Filter by comment (empty=all)

input group "Trade Snapshot"
input bool   InpSnapshotEnable          = true;                                      // Enable local trade snapshots
input int    InpSnapshotHours           = 72;                                        // Snapshot lookback hours
input bool   InpSnapshotBackfillOnce    = false;                                     // one-shot full-history backfill, ignores SnapHours; flip back to false after the run

input group "DD Guard - Account"
input bool   InpDdgEnable               = false;                                     // default OFF - enable when needed
input double InpDdgAccountMaxPercent    = 20.0;                                      // account max drawdown % (peak-to-equity)
input double InpDdgAccountMaxMoney      = 0.0;                                       // Account max drawdown in money (0 = off)
input bool   InpDdgAccountEnable        = true;                                      // account-level DD guard (independent switch)
input bool   InpDdgCloseOnHit           = true;                                      // close positions on trigger
input int    InpDdgLockMinutes          = 60;                                        // lockout minutes after DD trigger (peak NOT lowered)
input bool   InpDdgStopAutoTrade        = true;                                      // toggle terminal AutoTrading OFF on trigger (DLL)
input bool   InpDdgAlertPopup           = false;                                     // Show alert popup on trigger
input bool   InpDdgAccountStopAutotrade = true;                                      // account-level DD stops global AutoTrading
input int    InpDdgCloseRetry           = 4;                                         // close retry attempts before giving up

input group "DD Guard - Per Symbol"
input bool   InpDdgSymbolEnable         = false;                                     // per-symbol DD guard (independent switch)
input string InpDdgSymbolList           = "";                                        // Guarded symbols, comma-separated (empty=all)
input double InpDdgSymbolMaxPercent     = 12.0;                                      // per-symbol max drawdown %
input double InpDdgSymbolMaxMoney       = 0.0;                                       // Per-symbol max drawdown in money (0 = off)
input bool   InpDdgSymbolStopAutotrade  = false;                                     // per-symbol DD stops global AutoTrading (default OFF)

input group "Symbol Guard"
input bool   InpSymbolGuardEnable       = true;                                      // Symbol Guard: monitor per-symbol trading
input int    InpSymbolGuardMode         = 0;                                         // new symbol default 0=ON 1=ALERT 2=BLOCK 3=CLOSE

input group "News Guard"
input int    InpNewsGuardMode           = 0;                                         // 0=OFF(default) 1=ALERT 2=BLOCK(new only) 3=CLOSE(new+old)
input int    InpNewsBeforeMinutes       = 30;                                        // Minutes before news event to guard
input int    InpNewsAfterMinutes        = 15;                                        // Minutes after news event to guard
input bool   InpNewsHighImpactOnly      = true;                                      // Guard high-impact news only
input string InpNewsFile                = "news_guard.csv";                          // News calendar CSV file name
input int    InpNewsServerOffsetHours   = -5;                                        // news CSV(HKT+8) -> broker server hours (Vantage=HK-5)

input group "Telegram"
input string InpTelegramChatId          = "";                                        // Telegram chat ID (set via input/.set, never hardcoded)
input string InpTelegramTokenFile       = "tg_token.txt";                            // File name holding the bot token
input bool   InpTelegramEnable          = true;                                      // Enable Telegram notifications
input int    InpTelegramMinGapMinutes   = 10;                                        // min minutes between notifications per key
input string InpTelegramWhitelistUrl    = "https://api.telegram.org";               // Whitelist this URL in firewall/proxy (copy)
input string InpTelegramBotToken        = "";                                        // Bot token direct (overrides token file; empty=use file)

input group "Backup & Recovery"
input bool   InpAutoBackup              = true;                                      // Enable daily auto backup on change
input bool   InpAutoReconnect           = true;                                      // Auto-restart terminal on stuck disconnect
input int    InpReconnectAfterMinutes   = 10;                                        // Sustained disconnect minutes before restart
input int    InpRestartCooldownHours    = 2;                                         // Min hours between restarts
input int    InpMaxRestartAttempts      = 3;                                         // Give up after N consecutive failed restarts
input string InpBackupTime              = "05:30";                                   // Daily check time, server time HH:MM
input string InpBackupFolder            = "";                                        // Custom backup root (empty=auto: UserProfile\Downloads\MT4\Profiles)

input group "Diagnostics"
//--- (reserved: no diagnostics inputs yet)


//=== GLOBALS ===
double  g_ngPeakEquity = 0;
string  g_ngLastAlert  = "";
datetime g_ngLastScan  = 0;
string  g_ngEvents[64][4];
int     g_ngEventCount = 0;
double  g_ddgPeakEquity = 0;
string  g_ddgLastAlert = "";
int     __ng_init_done = 0;
datetime g_ddgLockUntil = 0;
bool     g_tdStoppedAT = false;
bool     g_ddgAccountArmed = false;   // v1.43: account-level lock engaged awaiting manual reset (persisted v1.47 Q9)
// v1.49: runtime switches (boss 2026-10-29: "DDGUARD的開關可以在他的頁的介面做一粒開關制嗎?")
// Inputs are read-only at runtime in MT4, so the panel toggles these shadows;
// they are seeded from the input values in OnInit and persisted in GlobalVariables.
bool     g_ddgeOn   = false;          // master enable (shadow of DDG_Enable)
bool     g_ddgAccOn = true;           // account-level guard (shadow of DDG_AccOn)
bool     g_ddgSymOn = false;          // per-symbol guard (shadow of DDG_SymOn)
datetime g_ddgOffPendT = 0;           // v1.49: first press time when asking to disarm master
bool     g_ddgSymLocked[64];          // v1.43: per-symbol lockout flags (mirror of account-scoped GV, v1.47 Q9)
bool     g_sgForcedClose[64];         // v1.43: symbols force-locked CLOSE by SymbolGuard linkage
string   g_sgPendSym[64];             // v1.47 Q7: symbols awaiting second-press CLOSE confirmation
datetime g_sgPendT[64];               // v1.47 Q7: first press time (confirm window 20s)
string   g_tgToken = "";
datetime g_tgLast[8];
string   g_tgKey[8];
int      g_tgN = 0;   // v1.40: TD toggled AutoTrading off itself
bool     g_histTruncated = false;
bool     g_histEmpty = false;   // v1.51 FIX-TD2 BugB: OrdersHistoryTotal()==0

//--- v1.55 FIX-TD6 (0925 spec item 6): sync heartbeat - a frozen sync becomes
//---   visible on the panel instead of dying silently.
datetime g_syncLastOk = 0;      // last completed history sync
int      g_syncNew    = 0;      // rows added by the last sync
int      g_syncHist   = 0;      // OrdersHistoryTotal() seen by the last sync
bool     g_syncCap    = false;  // MAX_HISTORY_SCAN safety cap was hit

string PFX = "TD116_";

//--- v1.54 FIX-TD4 (0745 放行信): BINGO CLOSE BOARD state -------------------
//--- ARM is deliberately memory-only: EA reload / account switch / 60s expiry
//--- all reset it, so a stale ARM can never outlive a re-init.
int      g_bingoPage    = 0;     // v1.60: DDGuard table page (12 rows/page over g_ddSymN)
datetime g_bingoCool[28][5];     // per-row per-button 30s cooldown
datetime g_bingoCoolAll = 0;     // [CLOSE 全倉] 30s cooldown
bool     g_bingoArmed   = false; // ARM gate - whole board disabled until armed
datetime g_bingoArmT    = 0;     // ARM start time (60s window)
string   g_bingoLast    = "";    // LAST action line (board footer)
string   g_bingoResidSym= "";    // last symbol with residual after close
int      g_bingoResidN  = 0;
datetime g_bingoResidT  = 0;
int    g_view = 0;
int    g_offset = 0;
datetime g_lastFull = 0;
datetime g_lastSnap = 0;
datetime g_lastBackupCheck = 0;
int    g_backupMinute = 330;    // BackupTime as minutes-of-day (default 05:30)
datetime g_saveBtnFlashUntil = 0; // SAVE button green-flash deadline

//+------------------------------------------------------------------+
//| Parse "HH:MM" -> minutes-of-day (invalid=fallback)               |
//+------------------------------------------------------------------+
int ParseHM(string hm, int fallbackMin)
{
   string t = hm;
   StringReplace(t, " ", "");
   int p = StringFind(t, ":");
   if(p <= 0) return fallbackMin;
   int hh = (int)StringToInteger(StringSubstr(t, 0, p));
   int mm = (int)StringToInteger(StringSubstr(t, p+1));
   if(hh < 0 || hh > 23 || mm < 0 || mm > 59) return fallbackMin;
   return hh*60 + mm;
}

//--- Runtime filter (from inputs, editable via chart)
string   g_filterSymbol = "";
string   g_filterComment = "";
datetime g_reportStart = 0;

//--- Recording (equity snapshots)
//--- v1.53 FIX-TD5: pre-v1.53 shared file names (kept only as legacy names for
//---   one-time migration below). Root cause of ghost SYMBOLs: shared files let
//---   a previous account's closed-trade rows leak into the next account's panel.
string REC_FILE = "TD_records.csv";
datetime g_lastRec = 0;

// v1.43 T6: binary persistence (hydrated from td4_snap.bin like MT5)
string SNAP_BIN = "td4_snap.bin";
#define SNAP_MAGIC 0x35445054   // "TPD4"
datetime g_lastBinSave = 0;

#define MAX_REC 20000
datetime r_dt[MAX_REC];
double   r_bal[MAX_REC];
double   r_eq[MAX_REC];
double   r_marg[MAX_REC];
double   r_fmarg[MAX_REC];
double   r_float[MAX_REC];
int      r_count = 0;
int      r_head  = 0;

//--- Local Trade Snapshot
string TRADES_FILE = "TD_trades.csv";   // legacy shared name (pre-v1.53)

//--- v1.53 FIX-TD5: account-scoped file names (resolved at call time so an
//---   account switch mid-session binds to the right files instantly)
//---   TD_trades.csv  -> TD_<acct>_trades.csv   (2345 spec item 1)
//---   td4_snap.bin   -> TD_<acct>_snap.bin
//---   TD_records.csv -> TD_<acct>_records.csv
//---   TD_summary.csv -> TD_<acct>_summary.csv
string TD_F_trades()  { return(TD_AcctPfx()+"trades.csv");  }
string TD_F_snap()    { return(TD_AcctPfx()+"snap.bin");    }
string TD_F_records() { return(TD_AcctPfx()+"records.csv"); }
string TD_F_summary() { return(TD_AcctPfx()+"summary.csv"); }

int g_acct = 0;   // v1.53 FIX-TD5: account-change watchdog seed

//--- v1.53 FIX-TD5 (2345 spec item 4): one-time migration — pre-v1.53 shared
//---   files carry no account column, so rows cannot be attributed to any
//---   account: the whole file is parked as *.legacy and never auto-loaded.
//--- v1.55 FIX-TD6 (0925 spec item 3): load-then-migrate. Parking the trades
//---   file BEFORE loading its rows is what zeroed the panel on the first
//---   v1.53 start - root cause 3: TD_trades.csv.legacy held 872 trades while
//---   TD_<acct>_trades.csv was born empty and the frozen sync never filled
//---   it. Now: if the account-scoped file is missing or bare and the legacy
//---   file still holds data rows, hydrate memory from the legacy file first,
//---   park it, then immediately re-save into the account-scoped file. Legacy
//---   rows carry no account column, so current-account attribution is the
//---   best possible and is applied by construction.
void MigrateLegacyTDFiles()
{
   string src3[3]; src3[0]=TRADES_FILE; src3[1]=REC_FILE; src3[2]=SNAP_BIN;
   string dst3[3]; dst3[0]="TD_trades.csv.legacy"; dst3[1]="TD_records.csv.legacy"; dst3[2]="td4_snap.bin.legacy";
   for(int m=0; m<3; m++)
   {
      if(!FileIsExist(src3[m])) continue;
      if(FileIsExist(dst3[m])) FileDelete(dst3[m]);   // keep the latest legacy copy only

      if(m == 0 && LegacyTradesHasData() && !PerAcctTradesHasData())
      {
         int nLoaded = LoadTradesLegacy();
         if(FileMove(src3[m], 0, dst3[m], 0))
         {
            SaveTrades();
            LogEvent(StringFormat("MIGRATE load-then-park | Legacy rows: %d -> %s", nLoaded, TD_F_trades()));
            Print("TD v1.55 FIX-TD6: legacy trades hydrated (", nLoaded, " rows) into ", TD_F_trades(), ", legacy file parked");
         }
         else
            Print("TD v1.55 FIX-TD6: WARN could not park '", src3[m], "' err=", GetLastError());
         continue;
      }

      if(FileMove(src3[m], 0, dst3[m], 0))
         Print("TD v1.53 FIX-TD5: legacy shared file '", src3[m], "' parked as '", dst3[m], "' (unattributable, not auto-loaded)");
      else
         Print("TD v1.55 FIX-TD6: WARN could not park '", src3[m], "' err=", GetLastError());
   }
}

#define MAX_TRADES 12000         // v1.55 FIX-TD6 (0925 spec item 4): was 5000 - acct 28152862 passed 5463 closed trades in 6 weeks
#define MAX_HISTORY_SCAN 20000   // v1.55 FIX-TD6 (0925 spec item 2): runaway safety cap only; the `since` window is the real limiter
int      t_ticket[MAX_TRADES];
string   t_symbol[MAX_TRADES];
int      t_type[MAX_TRADES];       // OP_BUY=0, OP_SELL=1
datetime t_opentime[MAX_TRADES];
datetime t_closetime[MAX_TRADES];
double   t_openprice[MAX_TRADES];
double   t_closeprice[MAX_TRADES];
double   t_lots[MAX_TRADES];
double   t_profit[MAX_TRADES];
double   t_swap[MAX_TRADES];
double   t_commission[MAX_TRADES];
string   t_comment[MAX_TRADES];
double   t_calcPnl[MAX_TRADES];    // Independently calculated P&L
int      t_tradeCount = 0;

//--- Summary event log
string EVENT_FILE = "TD_events.log";
int      g_lastHistCount = 0;

//--- Column layout (21 columns)
#define NC 21
string g_name[NC];
int    g_wid[NC];
bool   g_vis[NC];

datetime g_cDt[30];
int      g_cN[30];
int      g_cBuy[30];
int      g_cSell[30];
int      g_cW[30];
double   g_cPnl[30];
double   g_cPips[30];
double   g_cLots[30];
double   g_cTLots[30];
double   g_cGPct[30];
double   g_cPF[30];
double   g_cAvgP[30];
double   g_cBal[30];
double   g_cFMaxPos[30];
double   g_cFMaxNeg[30];
double   g_cBest[30];
double   g_cWorst[30];
double   g_cMarg[30];
double   g_cFMarg[30];
double   g_cMaxDD[30];
double   g_cMaxDDPct[30];
int      g_cNumB = 0;

//--- Auto Backup
string BACKUP_HASH_FILE = "TD_backup_hash.txt";

//+------------------------------------------------------------------+
//| Calculate input parameter fingerprint                           |
//+------------------------------------------------------------------+
int CalcInputFingerprint()
{
   string s = IntegerToString(InpPanelScale) + "_" +
              IntegerToString(InpDefaultView) + "_" +
              IntegerToString(InpRefreshSeconds) + "_" +
              IntegerToString(InpRecordSeconds) + "_" +
              IntegerToString(InpMaxRecords) + "_" +
              IntegerToString((int)InpSnapshotEnable) + "_" +
              IntegerToString(InpSnapshotHours) + "_" +
              IntegerToString((int)InpSnapshotBackfillOnce) + "_" +
              InpReportStart + "_" +
              InpFilterSymbol + "_" +
              InpFilterComment + "_" +
              IntegerToString((int)InpShowDay) + "_" +
              IntegerToString((int)InpShowTrades) + "_" +
              IntegerToString((int)InpShowBuySell) + "_" +
              IntegerToString((int)InpShowWinRate) + "_" +
              IntegerToString((int)InpShowGainMoney) + "_" +
              IntegerToString((int)InpShowGainPercent) + "_" +
              IntegerToString((int)InpShowPips) + "_" +
              IntegerToString((int)InpShowLots) + "_" +
              IntegerToString((int)InpShowTotalLots) + "_" +
              IntegerToString((int)InpShowBalance) + "_" +
              IntegerToString((int)InpShowMargin) + "_" +
              IntegerToString((int)InpShowFreeMargin) + "_" +
              IntegerToString((int)InpShowFloatPeakProfit) + "_" +
              IntegerToString((int)InpShowFloatPeakLoss) + "_" +
              IntegerToString((int)InpShowProfitFactor) + "_" +
              IntegerToString((int)InpShowAvgPnl) + "_" +
              IntegerToString((int)InpShowBestTrade) + "_" +
              IntegerToString((int)InpShowWorstTrade) + "_" +
              IntegerToString((int)InpShowMaxDdMoney) + "_" +
              IntegerToString((int)InpShowMaxDdPercent) + "_" +
              InpTitleLine1 + "_" + InpTitleLine2 + "_" +
              IntegerToString((int)InpShowPnlChart) + "_" +
              IntegerToString((int)InpAutoBackup) + "_" +
              InpBackupTime + "_" + InpBackupFolder;
   
   int hash = 0;
   int len = StringLen(s);
   for(int i = 0; i < len; i++)
      hash += StringGetChar(s, i);
   return hash;
}

//+------------------------------------------------------------------+
//| Save fingerprint to file                                        |
//+------------------------------------------------------------------+
void SaveFingerprint(int hash)
{
   int h = FileOpen(BACKUP_HASH_FILE, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE)
   {
      FileWriteString(h, IntegerToString(hash));
      FileClose(h);
   }
}

//+------------------------------------------------------------------+
//| Load last saved fingerprint                                     |
//+------------------------------------------------------------------+
int LoadFingerprint()
{
   int h = FileOpen(BACKUP_HASH_FILE, FILE_READ | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE)
   {
      if(!FileIsEnding(h))
      {
         string s = FileReadString(h);
         FileClose(h);
         StringTrimLeft(s);
         StringTrimRight(s);
         return (int)StringToInteger(s);
      }
      FileClose(h);
   }
   return -1;  // No previous hash
}

//+------------------------------------------------------------------+
//| Get USERPROFILE via cmd echo workaround                         |
//+------------------------------------------------------------------+
string GetEnvVarEA(string varName)
{
   // v1.17: derive USERPROFILE from terminal data path first (reliable, no cmd.exe race/space bug)
   if(varName == "USERPROFILE")
   {
      string dp = TerminalInfoString(TERMINAL_DATA_PATH);
      StringReplace(dp, "/", "\\");
      for(int i = 0; i < 5; i++)
      {
         int p = StringLen(dp) - 1;
         while(p > 0 && StringGetCharacter(dp, p) != '\\') p--;
         if(p > 0) dp = StringSubstr(dp, 0, p);
      }
      if(StringFind(dp, ":\\") == 1 && StringLen(dp) >= 8)
         return dp;
   }

   string result = "";
   string tempPath = TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL4\\Files\\_env_tmp.txt";
   StringReplace(tempPath, "/", "\\");

   // v1.17: no space before '>' — classic cmd echo trap writes the space into the file
   string cmd = "/C echo %" + varName + "%> \"" + tempPath + "\"";
   ShellExecuteW(0, "open", "cmd.exe", cmd, NULL, 0);
   Sleep(500);

   int h = FileOpen("_env_tmp.txt", FILE_READ | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE)
   {
      if(!FileIsEnding(h))
         result = FileReadString(h);
      FileClose(h);
      FileDelete("_env_tmp.txt");
   }

   StringTrimLeft(result);
   StringTrimRight(result);
   // v1.17: manual whitespace strip (StringTrim insurance)
   int tL = 0, tR = StringLen(result) - 1;
   while(tL <= tR)
   {
      ushort cL = StringGetCharacter(result, tL);
      if(cL == ' ' || cL == '\t' || cL == '\r' || cL == '\n') tL++;
      else break;
   }
   while(tR >= tL)
   {
      ushort cR = StringGetCharacter(result, tR);
      if(cR == ' ' || cR == '\t' || cR == '\r' || cR == '\n') tR--;
      else break;
   }
   result = StringSubstr(result, tL, tR - tL + 1);

   if(StringLen(result) < 3)
   {
      string dp2 = TerminalInfoString(TERMINAL_DATA_PATH);
      StringReplace(dp2, "/", "\\");
      for(int j = 0; j < 5; j++)
      {
         int q = StringLen(dp2) - 1;
         while(q > 0 && StringGetCharacter(dp2, q) != '\\') q--;
         if(q > 0) dp2 = StringSubstr(dp2, 0, q);
      }
      result = dp2;
   }
   return result;
}

//+------------------------------------------------------------------+
//| v1.19: Read active profile name from profiles\lastprofile.ini   |
//+------------------------------------------------------------------+
string ReadActiveProfile()
{
   string dp = TerminalInfoString(TERMINAL_DATA_PATH);
   StringReplace(dp, "/", "\\");
   string src = dp + "\\profiles\\lastprofile.ini";
   string tempPath = dp + "\\MQL4\\Files\\_prof_tmp.txt";

   // no space before '>' — same cmd echo trap as v1.17
   string cmd = "/C type \"" + src + "\"> \"" + tempPath + "\"";
   ShellExecuteW(0, "open", "cmd.exe", cmd, NULL, 0);
   Sleep(400);

   string result = "";
   int h = FileOpen("_prof_tmp.txt", FILE_READ | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE)
   {
      if(!FileIsEnding(h))
         result = FileReadString(h);
      FileClose(h);
      FileDelete("_prof_tmp.txt");
   }
   StringTrimLeft(result);
   StringTrimRight(result);
   if(StringLen(result) < 1)
      return "Default";
   return result;
}

//+------------------------------------------------------------------+
//| v1.18: Force-flush live charts to disk (File>Profiles>Save)      |
//| Dynamic menu lookup - no hardcoded command IDs                   |
//+------------------------------------------------------------------+
bool TriggerTerminalSaveProfile()
{
   int hChart = WindowHandle(Symbol(), Period());
   if(hChart == 0) { Print("[Backup] no chart hwnd"); return false; }

   int hMain = GetAncestor(hChart, 2);   // GA_ROOT = terminal main window
   if(hMain == 0) { Print("[Backup] no main hwnd"); return false; }

   int hMenu = GetMenu(hMain);
   if(hMenu == 0) { Print("[Backup] GetMenu failed"); return false; }

   int hFile = GetSubMenu(hMenu, 0);     // File menu (first item)
   if(hFile == 0) { Print("[Backup] File menu not found"); return false; }

   // find "Profiles" submenu inside File menu
   int hProf = 0;
   int nFile = GetMenuItemCount(hFile);
   for(int i = 0; i < nFile && hProf == 0; i++)
   {
      ushort buf[64];
      for(int z = 0; z < 64; z++) buf[z] = 0;
      GetMenuStringW(hFile, i, buf, 64, 0x400);        // MF_BYPOSITION
      string s = ShortArrayToString(buf);
      if(StringFind(s, "Profiles") >= 0)
         hProf = GetSubMenu(hFile, i);
   }
   if(hProf == 0) { Print("[Backup] Profiles submenu not found"); return false; }

   // find "Save" item (exact match first; skip "Save As...")
   int cmdSave = -1;
   int nProf = GetMenuItemCount(hProf);
   for(int k = 0; k < nProf; k++)
   {
      ushort b2[64];
      for(int z2 = 0; z2 < 64; z2++) b2[z2] = 0;
      GetMenuStringW(hProf, k, b2, 64, 0x400);
      string t = ShortArrayToString(b2);
      if(t == "Save") { cmdSave = GetMenuItemID(hProf, k); break; }
      if(StringFind(t, "Save") == 0 && StringFind(t, "As") < 0)
         cmdSave = GetMenuItemID(hProf, k);
   }
   if(cmdSave <= 0) { Print("[Backup] Save menu item not found"); return false; }

   // WM_COMMAND = 0x0111, fires same as clicking File>Profiles>Save
   PostMessageW(hMain, 0x0111, cmdSave, 0);
   Print("[Backup] Profile flush triggered (menu cmd ", cmdSave, ")");
   return true;
}

//+------------------------------------------------------------------+
//| Do robocopy backup (shared by auto & manual paths)              |
//+------------------------------------------------------------------+
bool DoProfileBackup()
{
   string dataPath = TerminalInfoString(TERMINAL_DATA_PATH);
   StringReplace(dataPath, "/", "\\");
   string profilesSrc = dataPath + "\\profiles";

   datetime now = TimeCurrent();
   string dateStr = StringFormat("%04d%02d%02d",
      TimeYear(now), TimeMonth(now), TimeDay(now));

   string acctNum = IntegerToString(AccountNumber());
   string serverName = AccountServer();
   // Clean server name for filename
   StringReplace(serverName, "\\", "_");
   StringReplace(serverName, "/", "_");
   StringReplace(serverName, ":", "_");
   StringReplace(serverName, "*", "_");
   StringReplace(serverName, "?", "_");
   StringReplace(serverName, "\"", "_");
   StringReplace(serverName, "<", "_");
   StringReplace(serverName, ">", "_");
   StringReplace(serverName, "|", "_");

   string destFolder;
   if(StringLen(InpBackupFolder) > 0)
      destFolder = InpBackupFolder + "\\" + acctNum + "_" + serverName + "_" + dateStr;
   else
   {
      string userProfile = GetEnvVarEA("USERPROFILE");
      destFolder = userProfile + "\\Downloads\\MT4\\Profiles\\" + acctNum + "_" + serverName + "_" + dateStr;
   }

   // v1.19: flush live chart state to disk BEFORE copying
   if(TriggerTerminalSaveProfile())
      Sleep(1500);   // give terminal UI thread time to write .chr files
   else
      Print("[Backup] WARN: flush failed, copying last-saved state only");

   // v1.19: "Save As" -> <server>_<account> snapshot profile, then keep Default in sync
   string activeProfile = ReadActiveProfile();
   string activeDir = profilesSrc + "\\" + activeProfile;
   string snapName = serverName + "_" + acctNum;   // <server>_<account>
   string snapDir = profilesSrc + "\\" + snapName;

   if(activeProfile != snapName)
   {
      string cmdSnap = "/C robocopy \"" + activeDir + "\" \"" + snapDir + "\" /MIR /NFL /NDL /NJH /NJS /NP";
      Print("[Backup] Save As profile: ", snapName);
      ShellExecuteW(0, "open", "cmd.exe", cmdSnap, NULL, 0);
      Sleep(1000);
   }
   if(activeProfile != "Default")
   {
      string defDir = profilesSrc + "\\Default";
      string cmdDef = "/C robocopy \"" + activeDir + "\" \"" + defDir + "\" /MIR /NFL /NDL /NJH /NJS /NP";
      Print("[Backup] Save As Default - sync from ", activeProfile);
      ShellExecuteW(0, "open", "cmd.exe", cmdDef, NULL, 0);
      Sleep(1000);
   }

   string cmd = "/C robocopy \"" + profilesSrc + "\" \"" + destFolder + "\" /E /NFL /NDL /NJH /NJS /NP";

   Print("[Backup] Backing up to ", destFolder);
   int result = ShellExecuteW(0, "open", "cmd.exe", cmd, NULL, 0);

   if(result > 32)
   {
      Print("[Backup] Backup initiated successfully.");
      return true;
   }
   Print("[Backup] ShellExecute failed! Error: ", result);
   return false;
}

//+------------------------------------------------------------------+
//| Manual SAVE PROFILE (button) - bypass fingerprint gate           |
//+------------------------------------------------------------------+
void ManualBackupNow()
{
   if(DoProfileBackup())
   {
      SaveFingerprint(CalcInputFingerprint());
      g_saveBtnFlashUntil = TimeLocal() + 3;
      LogEvent("SAVE PROFILE OK (manual) " + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
   }
   else
   {
      LogEvent("SAVE PROFILE FAILED (manual, ShellExecute)");
   }
   CollectData();
   RenderOnly();
}

//+------------------------------------------------------------------+
//| Check and backup profile if inputs changed                      |
//+------------------------------------------------------------------+
void CheckAndBackupProfile()
{
   if(!InpAutoBackup) return;

   // Check once per day after BackupTime (minutes-of-day, server time)
   datetime now = TimeCurrent();
   int nowMinute = TimeHour(now)*60 + TimeMinute(now);
   int today = (int)(now / 86400);
   int lastDay = 0;
   if(g_lastBackupCheck > 0)
      lastDay = (int)(g_lastBackupCheck / 86400);

   if(today == lastDay) return;  // Already checked today
   if(nowMinute < g_backupMinute) return;  // Not yet time
   
   g_lastBackupCheck = now;
   
   // Compare fingerprints
   int currentHash = CalcInputFingerprint();
   int savedHash = LoadFingerprint();
   
   if(currentHash == savedHash)
   {
      Print("[Backup] No parameter changes detected, skipping backup.");
      return;
   }
   
   // Parameters changed - do backup
   Print("[Backup] Parameter changes detected!");
   if(DoProfileBackup())
      SaveFingerprint(currentHash);
}

//+------------------------------------------------------------------+
//| OnInit                                                           |
//+------------------------------------------------------------------+
// v1.20: disconnect tracker for auto-reconnect
datetime g_discStart = 0;

int OnInit()
{
   EventSetTimer(1);   // v1.46 Q4: 1s timer so risk guards run without ticks
   // Clean up objects from previous version
   for(int oi = ObjectsTotal() - 1; oi >= 0; oi--)
   {
      string nm = ObjectName(oi);
      if(StringFind(nm, "TD110_") == 0 || StringFind(nm, "TD115_") == 0 || StringFind(nm, PFX) == 0)
         ObjectDelete(0, nm);
   }

   // Initialize view from input
   g_view = MathMax(0, MathMin(3, InpDefaultView));

   // Parse BackupTime "HH:MM" (server time) once at init; fallback 05:30
   g_backupMinute = ParseHM(InpBackupTime, 330);

   // Initialize runtime filters from inputs
   g_filterSymbol = InpFilterSymbol;
   g_filterComment = InpFilterComment;

   // Parse ReportStart
   if(InpReportStart != "")
   {
      g_reportStart = StringToTime(InpReportStart + " 00:00:00");
      if(g_reportStart < D'2020.01.01') g_reportStart = 0;
   }

   // Column definitions
   g_name[0]="Day";        g_wid[0]=89;
   g_name[1]="Trades";     g_wid[1]=48;
   g_name[2]="B/S";        g_wid[2]=58;
   g_name[3]="WR%";        g_wid[3]=42;
   g_name[4]="Gain$";      g_wid[4]=62;
   g_name[5]="Gain%";      g_wid[5]=52;
   g_name[6]="WPips";      g_wid[6]=48;
   g_name[7]="Lot";        g_wid[7]=42;
   g_name[8]="TotalLot";   g_wid[8]=58;
   g_name[9]="Balance";    g_wid[9]=68;
   g_name[10]="Margin";    g_wid[10]=62;
   g_name[11]="FreeMarg";  g_wid[11]=62;
   g_name[12]="MaxP";     g_wid[12]=55;
   g_name[13]="MaxDD";      g_wid[13]=55;
   g_name[14]="PF";        g_wid[14]=42;
   g_name[15]="AvgP&L";    g_wid[15]=58;
   g_name[16]="Best";      g_wid[16]=52;
   g_name[17]="Worst";     g_wid[17]=58;
   g_name[18]="MaxDD$";    g_wid[18]=62;
   g_name[19]="MaxDD%";    g_wid[19]=48;
   g_name[20]="Events";    g_wid[20]=42;

   // Column visibility
   g_vis[0]=InpShowDay;         g_vis[1]=InpShowTrades;      g_vis[2]=InpShowBuySell;
   g_vis[3]=InpShowWinRate;          g_vis[4]=InpShowGainMoney;        g_vis[5]=InpShowGainPercent;
   g_vis[6]=InpShowPips;       g_vis[7]=InpShowLots;         g_vis[8]=InpShowTotalLots;
   g_vis[9]=InpShowBalance;     g_vis[10]=InpShowMargin;     g_vis[11]=InpShowFreeMargin;
   g_vis[12]=InpShowFloatPeakProfit;    g_vis[13]=InpShowFloatPeakLoss;    g_vis[14]=InpShowProfitFactor;
   g_vis[15]=InpShowAvgPnl;       g_vis[16]=InpShowBestTrade;       g_vis[17]=InpShowWorstTrade;
   g_vis[18]=InpShowMaxDdMoney;      g_vis[19]=InpShowMaxDdPercent;   g_vis[20]=false;

   // v1.53 FIX-TD5 (2345 spec items 3+4): seed account watchdog, then one-time
   //   migration of pre-v1.53 shared files BEFORE any load touches them.
   g_acct = AccountNumber();
   MigrateLegacyTDFiles();

   // v1.54 FIX-TD4 (0745 spec): BINGO board starts cold - no ARM survives a
   //   restart, all per-button cooldowns cleared.
   g_bingoArmed = false;
   g_bingoPage  = 0;
   g_bingoLast  = "";
   for(int bi = 0; bi < 28; bi++)
      for(int bj = 0; bj < 5; bj++)
         g_bingoCool[bi][bj] = 0;

   LoadRecordsBin();   // v1.43 T6: hydrate from bin first
   if(r_count == 0) LoadRecords();   // fallback: legacy CSV
   LoadTrades();

   if(InpSnapshotEnable) SyncTradesFromHistory();

   RecordSnapshot();

   CollectData();
   RenderOnly();

   DumpSymbolSpecs();

   // Save initial fingerprint on startup
   SaveFingerprint(CalcInputFingerprint());
   
   Print("=== TradeDashboard v1.63 STARTED === Trades: ", t_tradeCount,
         " | Records: ", r_count,
         " | Filter: SYM='", g_filterSymbol, "' COM='", g_filterComment, "'",
         " | ReportStart: ", (g_reportStart>0 ? TimeToString(g_reportStart,TIME_DATE) : "None"));
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();   // v1.20
   SaveRecordsBin();   // v1.43 T6: flush ring buffer to bin before exit
   GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
   for(int oi = ObjectsTotal() - 1; oi >= 0; oi--)
   {
      string nm = ObjectName(oi);
      if(StringFind(nm, PFX) == 0) ObjectDelete(0, nm);
   }
}

//+------------------------------------------------------------------+
//| OnTick                                                           |
//+------------------------------------------------------------------+

//================= Symbol Guard v1.25 =================
int g_tab=0;   // v1.28: 0=Positions 1=Alerts(news+symbols) 2=DDGuard 3=Settings

//--- v1.35: remote self-test hook (agent writes MQL4/Files/TD_tabcmd.txt)
datetime g_tabCmdLast=0;
void CheckTabCmd()
{
   if(TimeLocal()-g_tabCmdLast < 2) return;   // v1.49: TimeLocal（周末不凍結）
   g_tabCmdLast=TimeCurrent();
   int h=FileOpen("TD_tabcmd.txt",FILE_READ|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE) return;
   string cmd=FileReadString(h);
   FileClose(h);
   // v1.51 FIX-TD2 (boss 2026-11-06): read-once semantics - the hook file is
   // agent-written and MUST be consumed once. A stale file (any content) used
   // to re-trigger every 2s forever: boss symptom "any TAB click bounces back
   // to DDGuard" = stale "tab=2" re-parsed on every tick/timer after throttle.
   FileDelete("TD_tabcmd.txt");
   int tp=StringFind(cmd,"tab=");
   if(tp<0) return;               // v1.51 FIX-TD2: only well-formed commands act
   int ti=(int)StringToInteger(StringSubstr(cmd,tp+4));
   string snap="";
   int sp=StringFind(cmd,"snap=");
   if(sp>=0) snap=StringSubstr(cmd,sp+5);
   if(ti>=0 && ti<4 && ti!=g_tab)
   {
      g_tab=ti;
      g_bingoArmed=false;   // v1.54 FIX-TD4: ARM 解除（切 TAB，含 agent hook）
      RenderOnly();
   }
   if(snap!="")
   {
      string f="TD_tabcheck_"+snap+".png";
      ChartScreenShot(0,f,1600,900,ALIGN_LEFT);
      Print("[TD] self-test snap ",f," tab=",g_tab);
   }
}
string  g_sgSym[64]; int g_sgSymN=0;
datetime g_sgAlertT[64];   // v1.26: last alert flash time per symbol

//--- v1.47 Q7: 4 states: 0=ON 1=ALERT 2=BLOCK(new only) 3=CLOSE(old+new)
string SG_ModeName(int m)
{
   if(m == 0) return("ON");
   if(m == 1) return("ALERT");
   if(m == 2) return("BLOCK");
   return("CLOSE");
}
//--- v1.47 Q8: temporary mode set by NewsGuard, auto-expires at window end.
//---           The user's base mode is kept in SG_ModeKey and never overwritten.
void SG_SetAuto(string sym,int m,datetime until)
{
   if(sym == "" || until <= TimeCurrent()) return;
   GlobalVariableSet(SG_AutoKey(sym), (double)(long)until);
   GlobalVariableSet(SG_AutoModeKey(sym), m);
}
void SG_ClearAuto(string sym)
{
   if(GlobalVariableCheck(SG_AutoKey(sym))) GlobalVariableDel(SG_AutoKey(sym));
   if(GlobalVariableCheck(SG_AutoModeKey(sym))) GlobalVariableDel(SG_AutoModeKey(sym));
}
//--- v1.47 Q8: effective mode = base mode raised by an active news window.
//---           Catches symbols opened AFTER the 30s NewsGuard scan.
int SG_EffMode(string sym)
{
   int m = SG_Mode(sym);
   if(InpNewsGuardMode >= 2 && NG_SymbolHot(sym))
   {
      int nm = (InpNewsGuardMode == 2) ? 2 : 3;
      if(nm > m) m = nm;
   }
   return(m);
}
int SG_Mode(string sym)
{
   if(GlobalVariableCheck(SG_AutoKey(sym)))            // v1.47 Q8: auto-expiry
   {
      datetime until = (datetime)(long)GlobalVariableGet(SG_AutoKey(sym));
      if(until > TimeCurrent()) return((int)GlobalVariableGet(SG_AutoModeKey(sym)));
      SG_ClearAuto(sym);
   }
   if(!GlobalVariableCheck(SG_ModeKey(sym))) return InpSymbolGuardMode;
   return((int)GlobalVariableGet(SG_ModeKey(sym)));
}
void SG_SetMode(string sym,int m)
{
   GlobalVariableSet(SG_ModeKey(sym), m);
}
//--- v1.47 Q7: CLOSE needs a second press within 20s before it is armed
bool SG_Pending(string sym)
{
   for(int i = 0; i < 64; i++)
   {
      if(g_sgPendSym[i] != sym) continue;
      if(TimeCurrent() - g_sgPendT[i] <= 20) return(true);
      g_sgPendSym[i] = ""; g_sgPendT[i] = 0;
      return(false);
   }
   return(false);
}
void SG_SetPending(string sym)
{
   int slot = -1;
   for(int i = 0; i < 64; i++)
   {
      if(g_sgPendSym[i] == sym) { slot = i; break; }
      if(g_sgPendSym[i] == "" && slot < 0) slot = i;
   }
   if(slot < 0) slot = 0;
   g_sgPendSym[slot] = sym;
   g_sgPendT[slot]  = TimeCurrent();
}
void SG_ClearPending(string sym)
{
   for(int i = 0; i < 64; i++)
      if(g_sgPendSym[i] == sym) { g_sgPendSym[i] = ""; g_sgPendT[i] = 0; }
}
//--- v1.47 Q7: cycle ON->ALERT->BLOCK->CLOSE->ON with confirmation on CLOSE
void SG_CycleMode(string sym)
{
   int m = (SG_Mode(sym) + 1) % 4;
   if(m == 3 && !SG_Pending(sym))
   {
      SG_SetPending(sym);
      Print("SG: ", sym, " CLOSE needs confirmation - press again within 20s");
      SendNotification("SG[" + sym + "] CLOSE pending - press again within 20s");
      return;
   }
   SG_ClearPending(sym);
   SG_SetMode(sym, m);
   Print("SG: ", sym, " -> ", SG_ModeName(m));
   if(m == 3)
   {
      int residual = DDG_CloseSymbolWithRetry(sym);
      TG_Notify("SG_CLOSE_"+sym, "🔒 SymbolGuard CLOSE — " + sym + "\n▪ Closed old + new positions" + (residual>0?"\n⚠ Residual "+IntegerToString(residual)+" still open!":" ✅") + "\n🕐 " + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES));
   }
   if(m == 2)
      TG_Notify("SG_BLOCK_"+sym, "⛔ SymbolGuard BLOCK — " + sym + "\n▪ New positions closed on sight, old ones kept");
}
void SG_CollectSymbols()
{
   g_sgSymN=0;
   for(int i=0;i<OrdersTotal() && g_sgSymN<64;i++)
   {
      if(!OrderSelect(i,SELECT_BY_POS,MODE_TRADES)) continue;
      if(OrderType()>OP_SELL) continue;
      string s=OrderSymbol();
      bool found=false;
      for(int j=0;j<g_sgSymN;j++) if(g_sgSym[j]==s){found=true;break;}
      if(!found){ g_sgSym[g_sgSymN]=s; g_sgSymN++; }
   }
   // v1.47 Q9: keep explicit per-symbol modes visible after positions are gone
   string pfx = TD_AcctPfx()+"SG_";
   for(int v = GlobalVariablesTotal()-1; v >= 0 && g_sgSymN < 64; v--)
   {
      string n = GlobalVariableName(v);
      if(StringFind(n, pfx) != 0) continue;
      string s2 = StringSubstr(n, StringLen(pfx));
      if(s2 == "" || StringFind(s2, "AUTO") == 0) continue;
      bool have=false;
      for(int j2=0;j2<g_sgSymN;j2++) if(g_sgSym[j2]==s2){have=true;break;}
      if(!have){ g_sgSym[g_sgSymN]=s2; g_sgSymN++; }
   }
}
void SymbolGuard()
{
   if(!InpSymbolGuardEnable) return;
   static datetime lastScan=0;
   if(TimeCurrent()-lastScan < 3) return;
   lastScan=TimeCurrent();

   //--- v1.47 Q7: CLOSE mode liquidates old positions of that symbol
   for(int c = 0; c < g_sgSymN; c++)
   {
      string cs = g_sgSym[c];
      if(SG_EffMode(cs) != 3) continue;
      int open = 0;
      for(int oc = OrdersTotal()-1; oc >= 0; oc--)
      {
         if(!OrderSelect(oc, SELECT_BY_POS, MODE_TRADES)) continue;
         if(OrderSymbol() != cs || OrderType() > OP_SELL) continue;
         open++;
      }
      if(open == 0) continue;
      int resid = DDG_CloseSymbolWithRetry(cs);
      Print("SG[", cs, "] CLOSE mode: closed old positions, residual=", resid);
      TG_Notify("SG_CLOSE_LOOP_"+cs, "🔒 SymbolGuard CLOSE — " + cs + "\n▪ Re-closed " + IntegerToString(open) + " position(s) (old/new)" + (resid>0?"\n⚠ Residual "+IntegerToString(resid):" ✅"));
   }

   static int knownTickets[4096]; static int knownN=0;
   for(int i=0;i<OrdersTotal();i++)
   {
      if(!OrderSelect(i,SELECT_BY_POS,MODE_TRADES)) continue;
      if(OrderType()>OP_SELL) continue;
      int tk=OrderTicket();
      bool known=false;
      for(int kk=0;kk<knownN;kk++) if(knownTickets[kk]==tk){known=true;break;}
      if(known) continue;
      if(knownN<4096){knownTickets[knownN]=tk;knownN++;}
      if(TimeCurrent()-OrderOpenTime()>120) continue;
      int mode=SG_EffMode(OrderSymbol());
      if(mode==0) continue;
      string msg;
      if(mode==1)
         msg=StringFormat("SG[%s] ALERT: new %s #%d %.2f lots",
                OrderSymbol(), (OrderType()==OP_BUY?"BUY":"SELL"), tk, OrderLots());
      else
      {
         msg=StringFormat("SG[%s] %s: %s #%d %.2f lots closed by guard",
                OrderSymbol(), (mode==2?"BLOCK":"CLOSE"), (OrderType()==OP_BUY?"BUY":"SELL"), tk, OrderLots());
         double px=(OrderType()==OP_BUY)?MarketInfo(OrderSymbol(),MODE_BID):MarketInfo(OrderSymbol(),MODE_ASK);
         if(!OrderClose(tk,OrderLots(),px,30,clrRed))
            msg=msg+" [close FAILED err "+IntegerToString(GetLastError())+"]";
      }
      Print(msg);
      SendNotification(msg);
      for(int fi=0; fi<g_sgSymN; fi++) if(g_sgSym[fi]==OrderSymbol()) { g_sgAlertT[fi]=TimeCurrent(); break; }
      if(mode>=2){ for(int k2=0;k2<knownN;k2++) if(knownTickets[k2]==tk){knownTickets[k2]=knownTickets[knownN-1];knownN--;break;} }
   }
}
void SG_Render(int x,int y,int scale)
{
   UpdTxt("SGT","GUARD:",x,y,clrWhite,7*scale);
   int bx=x+42*scale;
   for(int i=0;i<g_sgSymN && i<10;i++)
   {
      string s=g_sgSym[i];
      int m=SG_EffMode(s);   // v1.47 Q8: reflects news-window override too
      string lbl=(m==0)?s+" [ON]":(m==1)?s+" [AL]":(m==2)?s+" [BL]":s+" [CL]";
      color  bg =(m==0)?C'20,90,40':(m==1)?C'160,110,20':(m==2)?C'110,60,150':C'150,30,30';
      color  fg =(m==0)?clrLime:(m==1)?clrYellow:clrWhite;
      // v1.28: red blink also while symbol is inside a news warning window
      if(!(i<64 && g_sgAlertT[i]>0 && TimeCurrent()-g_sgAlertT[i] < 60) && NG_SymbolHot(s))
      {
         int phn=(int)(TimeCurrent()%2);
         bg = (phn==0)?clrRed:C'255,140,0';
         fg = clrWhite;
         lbl = s+" N!";
      }
      // v1.26: red warning blink for 60s after alert/close fired on this symbol
      if(i<64 && g_sgAlertT[i]>0 && TimeCurrent()-g_sgAlertT[i] < 60)
      {
         int ph=(int)((TimeCurrent()-g_sgAlertT[i])%2);
         bg = (ph==0)?clrRed:C'255,140,0';
         fg = clrWhite;
         lbl = s+" !!";
      }
      int bw=(34+StringLen(s)*6)*MathMax(1,scale/2)+34;
      UpdBtn("SG_"+IntegerToString(i), lbl, bx, y-2, bw, 14*scale, false);
      ObjectSetInteger(0,PFX+"SG_"+IntegerToString(i),OBJPROP_BGCOLOR,bg);
      ObjectSetInteger(0,PFX+"SG_"+IntegerToString(i),OBJPROP_COLOR,fg);
      bx+=bw+6;
   }
   if(g_sgSymN==0) UpdTxt("SGN","no open symbols (guard armed)",bx+6,y,clrKhaki,7*scale);
}


// v1.27: hide main-table objects when on other tabs
void HideMainTable()
{
   string ids[] = {"TTL","SUB","AC1","AC2","S_P","S_R","FLBL","FS_EDIT","CLBL2","FC_EDIT","SAVELBL",
                   "CLBL","CZERO","SGT","SGN","FT","TABCZ","HISTW","S_ALL","EMPTYW"};   // v1.50 FIX-TD: +HISTW; v1.52 FIX-TD3: +S_ALL/EMPTYW
   for(int i2=0;i2<ArraySize(ids);i2++) ObjectDelete(0,PFX+ids[i2]);
   for(int c2=0;c2<NC;c2++) { ObjectDelete(0,PFX+"H"+IntegerToString(c2)); ObjectDelete(0,PFX+"V_"+(c2==0?"H":c2==1?"D":c2==2?"W":"M")); }
   for(int r2=0;r2<10;r2++)
   {
      ObjectDelete(0,PFX+"CBAR_"+IntegerToString(r2));
      for(int c3=0;c3<NC;c3++) ObjectDelete(0,PFX+"D"+IntegerToString(r2)+"_"+IntegerToString(c3));
   }
   ObjectDelete(0,PFX+"NAV_L"); ObjectDelete(0,PFX+"NAV_R"); ObjectDelete(0,PFX+"SAVE"); ObjectDelete(0,PFX+"DV");
   for(int g2=0;g2<10;g2++) ObjectDelete(0,PFX+"SG_"+IntegerToString(g2));
   for(int g3=0;g3<8;g3++) { ObjectDelete(0,PFX+"TSG_"+IntegerToString(g3)); ObjectDelete(0,PFX+"TSY"+IntegerToString(g3)); }
   for(int g4=0;g4<14;g4++) ObjectDelete(0,PFX+"TN"+IntegerToString(g4));
   // v1.50 FIX-TD (ghost fix, boss 2026-11-05): prefix sweeps instead of fixed
   // enums - dynamic row counts and $-suffixed names (DDC$k) leaked; adds the
   // DDG families never listed before: DDP/DDM rows, TPC2-5 headers, DDGT_*,
   // DDRESET(+LBL). Prefix match is ObjectsDeleteAll, not exact ObjectDelete.
   ObjectsDeleteAll(0, PFX+"DDC"); ObjectsDeleteAll(0, PFX+"DDN");
   ObjectsDeleteAll(0, PFX+"DDB"); ObjectsDeleteAll(0, PFX+"DDF");
   ObjectsDeleteAll(0, PFX+"DDP"); ObjectsDeleteAll(0, PFX+"DDM");
   ObjectsDeleteAll(0, PFX+"TPH"); ObjectsDeleteAll(0, PFX+"TPC");
   ObjectsDeleteAll(0, PFX+"DDGT"); ObjectsDeleteAll(0, PFX+"DDRESET");
   // v1.54 FIX-TD4 (0745 item 4): BINGO CLOSE BOARD family - without this the
   // board ghosts across TAB switches (v1.50 lesson, boss repro).
   ObjectsDeleteAll(0, PFX+"BG");
   string tids[]={"TNX","TA0","TAX","TAM","TD0","TD1","TD2","TD3","TD4","TDB","TDF","TS0","TS1","TS2","TS3","TS4"};
   for(int g5=0;g5<ArraySize(tids);g5++) ObjectDelete(0,PFX+tids[g5]);
}

// v1.27: tab content renderers
void TabRender_Alerts(int x,int y,int scale,int w)
{
   datetime now=TimeCurrent();
   UpdTxtBold("TN0","UPCOMING NEWS -> affected open symbols",x,y,clrDeepSkyBlue,10*scale);
   int ln=1;
   for(int i=0;i<g_ngEventCount && ln<9;i++)
   {
      datetime ev=NG_EvTimeHKT(g_ngEvents[i][0]);
      datetime nw=NG_NowHKT();
      if(ev+InpNewsAfterMinutes*60 < nw) continue;
      bool hot=(nw >= ev-InpNewsBeforeMinutes*60 && nw <= ev+InpNewsAfterMinutes*60);
      string syms="";
      for(int j=0;j<g_sgSymN;j++)
         if(NG_SymbolAffected(g_sgSym[j], g_ngEvents[i][1])) syms=syms+g_sgSym[j]+" ";
      color c=hot?clrRed:clrWhite;
      UpdTxt("TN"+IntegerToString(ln), StringFormat("%s %s %s -> %s%s",
         g_ngEvents[i][0],g_ngEvents[i][1],g_ngEvents[i][2],(syms==""?"-":syms),(hot?"  << NOW":(ev-now<3600?"  soon":""))),
         x, y+ln*14*scale, c, 9*scale);
      ln++;
   }
   if(ln==1) UpdTxt("TNX","(no upcoming events loaded)",x,y+12*scale,clrKhaki,9*scale);
   int sy=y+ln*14*scale+6;
   UpdTxtBold("TA0","SYMBOL STATUS  (red = news window | click = ON/ALERT/BLOCK/CLOSE)",x,sy,clrDeepSkyBlue,10*scale);
   for(int k=0;k<g_sgSymN && k<8;k++)
   {
      string s2=g_sgSym[k];
      bool hot2=NG_SymbolHot(s2);
      int m2=SG_EffMode(s2);
      color stc=hot2?clrRed:clrLime;
      UpdTxt("TSY"+IntegerToString(k), StringFormat("%s  %s",s2,(hot2?"NEWS RISK":"clear")), x, sy+14*scale+k*16*scale, stc, 9*scale);
      string lbl=(m2==0)?"[ON]":(m2==1)?"[ALERT]":(m2==2)?"[BLOCK]":"[CLOSE]";
      color  bg=(m2==0)?C'20,90,40':(m2==1)?C'160,110,20':(m2==2)?C'110,60,150':C'150,30,30';
      color  fg=(m2==0)?clrLime:(m2==1)?clrYellow:clrWhite;
      int bw=40*MathMax(1,scale/2)+52;
      UpdBtn("TSG_"+IntegerToString(k), lbl, x+w-bw-10, sy+12*scale+k*16*scale, bw, 13*scale, false);
      ObjectSetInteger(0,PFX+"TSG_"+IntegerToString(k),OBJPROP_BGCOLOR,bg);
      ObjectSetInteger(0,PFX+"TSG_"+IntegerToString(k),OBJPROP_COLOR,fg);
   }
   if(g_sgSymN==0) UpdTxt("TAX","(no open symbols)",x,sy+14*scale,clrKhaki,9*scale);
   UpdTxt("TAM",StringFormat("NG mode=%s | window %dm/%dm | push on entry",(InpNewsGuardMode==0?"OFF":InpNewsGuardMode==1?"ALERT":InpNewsGuardMode==2?"BLOCK":"CLOSE"),InpNewsBeforeMinutes,InpNewsAfterMinutes), x, sy+15*scale+MathMax(MathMin(g_sgSymN,8),1)*15*scale, clrWhite, 9*scale);
}// v1.29: per-symbol DD from closed-trade history (t_ arrays)
string g_ddSyms[32]; bool g_ddSel[32]; int g_ddSymN=0;
double g_ddSymDD[32];      // max DD in $
double g_ddSymDDPct[32];   // max DD as % of cumulative peak
double g_ddSymCum[32];     // current cumulative pnl
void DD_BuildSymbols()
{
   ArrayInitialize(g_ddUsed,false);
   g_ddSymN=0;
   ArrayInitialize(g_ddSymDD,0); ArrayInitialize(g_ddSymDDPct,0); ArrayInitialize(g_ddSymCum,0);
   for(int i=0;i<t_tradeCount;i++)
   {
      // v1.30: any trade record (open or closed) counts
      string sym=t_symbol[i];
      bool f1=false;
      for(int j=0;j<g_ddSymN;j++) if(g_ddSyms[j]==sym){f1=true;break;}
      if(!f1 && g_ddSymN<32){ g_ddSyms[g_ddSymN]=sym; g_ddSymN++; }
   }
   // also live positions not yet in t_ list
   for(int p4=0;p4<OrdersTotal();p4++)
   {
      if(!OrderSelect(p4,SELECT_BY_POS,MODE_TRADES)) continue;
      if(OrderType()>OP_SELL) continue;
      string sym2=OrderSymbol();
      bool f2=false;
      for(int j2=0;j2<g_ddSymN;j2++) if(g_ddSyms[j2]==sym2){f2=true;break;}
      if(!f2 && g_ddSymN<32){ g_ddSyms[g_ddSymN]=sym2; g_ddSymN++; }
   }
   // walk trades in close-time order per symbol, track cumulative peak/trough
   // v1.60 FIX (1400 §四-1): % denominator is now DDG_Base() balance — the same
   //   base as the DD-now column — NOT the realized-P/L curve peak, which is
   //   tiny on losing symbols and produced 1080%/4819% absurdities.
   double mbase = DDG_Base();
   for(int j=0;j<g_ddSymN;j++)
   {
      string sym=g_ddSyms[j];
      double cum=0, peak=0, maxdd=0;
      // selection sort by closetime among this symbol's trades (simple pass)
      for(int pass=0; pass<t_tradeCount; pass++)
      {
         datetime bestT=0; int bestI=-1;
         for(int i=0;i<t_tradeCount;i++)
         {
            if(t_symbol[i]!=sym) continue;
            // v1.30: open trades included, ordered after all closed ones
            datetime ct=(t_closetime[i]==0)?TimeCurrent()+1:t_closetime[i];
            if(bestI>=0 && ct<=bestT) continue;
            if(ct>bestT && !TD_TradeConsumed(sym,i,j)) { bestT=ct; bestI=i; }
         }
         if(bestI<0) break;
         double pnl=(t_closetime[bestI]==0)?t_calcPnl[bestI]:(t_profit[bestI]+t_swap[bestI]+t_commission[bestI]);
         cum += pnl;
         TD_MarkConsumed(sym,bestI,j);
         if(cum>peak) peak=cum;
         if(peak-cum>maxdd) maxdd=peak-cum;
      }
      g_ddSymCum[j]=cum; g_ddSymDD[j]=maxdd;
      g_ddSymDDPct[j]=(mbase>0)?maxdd/mbase*100:0.0;   // v1.60: peak=0 branch gone too
   }
}
// helper consumed-marks for the ordering pass (per symbol build)
bool g_ddUsed[MAX_TRADES];   // v1.55 FIX-TD6 (0925 spec item 4): was literal 5000 - must track MAX_TRADES or the DDG build crashes past 5000 trades
bool TD_TradeConsumed(string sym,int i,int j){ return g_ddUsed[i]; }
void TD_MarkConsumed(string sym,int i,int j){ g_ddUsed[i]=true; }

void TabRender_DDG(int x,int y,int scale,int w)
{
   double eq=AccountEquity();
   double base=DDG_Base();     // v1.47 Q6: same Balance denominator as the guards
   double dd=MathMax(0.0,(g_ddgPeakEquity>0)?(g_ddgPeakEquity-eq)/base*100:0);   // v1.60 (1400 §四-2): clamp, never negative
   color dc=(dd>=InpDdgAccountMaxPercent)?clrRed:(dd>=InpDdgAccountMaxPercent*0.7?clrYellow:clrLime);
   UpdTxtBold("TD0","DDGuard - Account Drawdown",x,y,clrDeepSkyBlue,10*scale);
   // v1.60 (1230 §3.3): both limits in the status line
   UpdTxt("TD1",StringFormat("Peak $%.2f | Eq $%.2f | DD %.2f%% (limit %.1f%% / $%.2f)",g_ddgPeakEquity,eq,dd,InpDdgAccountMaxPercent,InpDdgAccountMaxMoney),x,y+16*scale,clrWhite,9*scale);
   UpdTxt("TD4",StringFormat("SymMaxDD: %.1f%% | Lock: %dmin | base = balance",InpDdgSymbolMaxPercent,InpDdgLockMinutes),x,y+31*scale,clrKhaki,9*scale);

   //--- v1.48: runtime switches (boss 2026-10-29). MT4 inputs are read-only at
   //--- runtime, so the panel toggles the g_ddg* shadows, persisted via
   //--- GlobalVariables in DDG_SaveState(). Disarming the master needs a second
   //--- press within 10s so a mis-click cannot silently disable the risk guard.
   int swY = y + 46*scale;
   bool offPend = (g_ddgOffPendT > 0 && TimeCurrent() - g_ddgOffPendT <= 10);
   string mastTxt = g_ddgeOn ? "DDG: ON" : (offPend ? "DDG: ON -> OFF?" : "DDG: OFF");
   UpdBtn("DDGT_ON", mastTxt, x, swY, 92*scale, 16*scale, g_ddgeOn);
   if(!g_ddgeOn) ObjectSetInteger(0,PFX+"DDGT_ON",OBJPROP_BGCOLOR, offPend?clrOrangeRed:C'90,40,40');
   UpdBtn("DDGT_ACC", g_ddgAccOn ? "Acc: ON" : "Acc: OFF", x+96*scale, swY, 62*scale, 16*scale, (g_ddgeOn && g_ddgAccOn));
   UpdBtn("DDGT_SYM", g_ddgSymOn ? "Sym: ON" : "Sym: OFF", x+162*scale, swY, 62*scale, 16*scale, (g_ddgeOn && g_ddgSymOn));
   if(!g_ddgeOn) UpdTxt("TAM6","! guards inactive (master OFF)",x+228*scale,swY+4*scale,clrOrangeRed,9*scale);
   else HideObj("TAM6");

   int bw=w-20;
   UpdRect("TDB", x, y+66*scale, bw, 10*scale, C'40,50,80', C'40,50,80');
   double pct=MathMin(1.0, dd/InpDdgAccountMaxPercent);
   color bc=(pct>=1.0)?clrRed:(pct>=0.7?clrYellow:clrLime);
   UpdRect("TDF", x, y+66*scale, (int)(bw*pct), 10*scale, bc, bc);

   //--- v1.37: aligned column table, one row per traded symbol ---
   //--- v1.60 (1400 §三, boss 13:29): CLOSE buttons INLINE — five buttons per
   //--- row right of MaxDD$; the independent CLOSE BOARD block is gone (its
   //--- 3 columns duplicated this table); ARM + pager live in the table
   //--- header, LAST in the tail. BGB_ semantics unchanged.
   //--- v1.63 (1915 §一/§二, boss 19:04): five-button column RIGHT-ALIGNED to
   //---   the panel edge; ARM renamed UNLOCK/LOCK (1925); [CLOSE ALL] moved to
   //---   the header beside UNLOCK, pure-ASCII label (MQL button font mangles CJK).
   int ty = y + 86*scale;
   double bal = DDG_Base();   // v1.47 Q6: explicit balance base
   int c1 = x + 8*scale;          // symbol
   int c2 = x + 100*scale;        // Float $
   int c3 = x + 175*scale;        // DD now %
   int c4 = x + 250*scale;        // MaxDD %
   int c5 = x + 320*scale;        // MaxDD $
   int bx0 = x + w - 6*scale - 250*scale;   // v1.63 (1915 §一): button column right-aligned to the panel edge
   int rows = 12;                 // v1.60: rows per page (was the k<12 cap)
   int pages = (g_ddSymN + rows - 1) / rows;
   if(pages < 1) pages = 1;
   if(g_bingoPage >= pages) g_bingoPage = pages - 1;
   if(g_bingoPage < 0) g_bingoPage = 0;
   int row0 = g_bingoPage * rows;
   UpdTxtBold("TPH", "SYMBOL",        c1, ty, clrDeepSkyBlue, 9*scale);
   UpdTxtBold("TPC2","Float $",       c2, ty, clrDeepSkyBlue, 9*scale);
   UpdTxtBold("TPC3","DD now %",      c3, ty, clrDeepSkyBlue, 9*scale);
   UpdTxtBold("TPC4","MaxDD %",       c4, ty, clrDeepSkyBlue, 9*scale);
   UpdTxtBold("TPC5","MaxDD $",       c5, ty, clrDeepSkyBlue, 9*scale);
   // v1.63 (1925): ARM renamed — UNLOCK when locked (opens the 60s window);
   //   LOCK + countdown when armed (press = immediate manual re-lock).
   // v1.63 (1915 §二): [CLOSE ALL] moved from the tail into the header, right
   //   of the UNLOCK button (boss: "放在ARM鍵旁"); ASCII-only label.
   string armTxt = g_bingoArmed ? StringFormat("LOCK %ds", 60 - (int)(TimeCurrent() - g_bingoArmT)) : "UNLOCK";
   UpdBtn("BGA", armTxt, bx0, ty - 2*scale, 64*scale, 13*scale, g_bingoArmed);
   if(g_bingoArmed) ObjectSetInteger(0, PFX+"BGA", OBJPROP_BGCOLOR, clrOrange);
   bool allOn = (g_bingoArmed && TimeCurrent() - g_bingoCoolAll >= 30);   // v1.63: moved up from the tail (BGC now in the header)
   UpdBtn("BGC", "[ CLOSE ALL ]", bx0 + 68*scale, ty - 2*scale, 90*scale, 13*scale, allOn);
   if(allOn)
   {
      ObjectSetInteger(0, PFX+"BGC", OBJPROP_BGCOLOR, clrOrangeRed);
      ObjectSetInteger(0, PFX+"BGC", OBJPROP_COLOR, clrWhite);
   }
   UpdTxt("BGP", StringFormat("%d/%d", g_bingoPage + 1, pages), x + w - 96*scale, ty, clrWhite, 9*scale);
   UpdBtn("BGP_L", "[<]", x + w - 64*scale, ty - 2*scale, 28*scale, 13*scale, (g_bingoPage > 0));
   UpdBtn("BGP_R", "[>]", x + w - 32*scale, ty - 2*scale, 28*scale, 13*scale, (g_bingoPage < pages - 1));
   for(int k=row0; k<row0+rows && k<g_ddSymN; k++)
   {
      int i2 = k - row0;               // v1.60: visible row index (object suffix)
      int ry2=ty+16*scale+i2*15*scale;
      // live floating P/L for this symbol
      double fl=0;
      for(int p3=OrdersTotal()-1;p3>=0;p3--)
      {
         if(!OrderSelect(p3, SELECT_BY_POS, MODE_TRADES)) continue;
         if(OrderType()>OP_SELL) continue;
         if(OrderSymbol()!=g_ddSyms[k]) continue;
         fl += OrderProfit()+OrderSwap()+OrderCommission();
      }
      double ddNow = -fl/bal*100.0;               // floating loss as % of balance
      color cFl  = (fl>=0)?clrLime:clrTomato;
      color cDn  = (ddNow>=InpDdgSymbolMaxPercent)?clrRed:(ddNow>=InpDdgSymbolMaxPercent*0.7?clrYellow:clrWhite);
      color cMx  = (g_ddSymDDPct[k]>=InpDdgSymbolMaxPercent)?clrRed:(g_ddSymDDPct[k]>=InpDdgSymbolMaxPercent*0.7?clrYellow:clrKhaki);
      UpdTxt("DDN"+IntegerToString(i2), g_ddSyms[k], c1, ry2, clrWhite, 9*scale);
      UpdTxt("DDF"+IntegerToString(i2), StringFormat("%+.2f", fl), c2, ry2, cFl, 9*scale);
      UpdTxt("DDP"+IntegerToString(i2), StringFormat("%.2f%%", MathMax(0.0,ddNow)), c3, ry2, cDn, 9*scale);   // v1.60 clamp display
      UpdTxt("DDM"+IntegerToString(i2), StringFormat("%.2f%%", g_ddSymDDPct[k]), c4, ry2, cMx, 9*scale);
      UpdTxt("DDC$"+IntegerToString(i2), StringFormat("%.2f", g_ddSymDD[k]), c5, ry2, cMx, 9*scale);
      // v1.60 (1400 §三): inline [BUY][SELL][WIN][LOSE][ALL] for this row's symbol.
      // Identical semantics to the v1.54 board buttons — moved + narrowed only.
      for(int b = 0; b < 5; b++)
      {
         bool cool = (TimeCurrent() - g_bingoCool[i2][b] < 30);
         string bl = BINGO_BtnName(b);
         if(cool) bl = StringFormat("%ds", 30 - (int)(TimeCurrent() - g_bingoCool[i2][b]));
         string onm = PFX+"BGB_"+IntegerToString(i2)+"_"+IntegerToString(b);
         UpdBtn("BGB_"+IntegerToString(i2)+"_"+IntegerToString(b), bl, bx0 + b*50*scale, ry2 - 1, 46*scale, 13*scale, (g_bingoArmed && !cool));
         if(g_bingoArmed && !cool)
         {
            ObjectSetInteger(0, onm, OBJPROP_BGCOLOR, clrOrangeRed);   // 橙紅、即按即執行
            ObjectSetInteger(0, onm, OBJPROP_COLOR, clrWhite);
         }
      }
   }
   // v1.60: hide stale row objects on shorter pages (page 2+ tails)
   for(int i3=0; i3<rows; i3++)
   {
      if(row0 + i3 < g_ddSymN) continue;
      HideObj("DDN"+IntegerToString(i3)); HideObj("DDF"+IntegerToString(i3)); HideObj("DDP"+IntegerToString(i3));
      HideObj("DDM"+IntegerToString(i3)); HideObj("DDC$"+IntegerToString(i3));
      for(int b3=0; b3<5; b3++) HideObj("BGB_"+IntegerToString(i3)+"_"+IntegerToString(b3));
   }
   int shown = MathMin(g_ddSymN - row0, rows); if(shown < 0) shown = 0;
   if(g_ddSymN==0) UpdTxt("TAX2","(no traded symbols yet)",x+8*scale,ty+16*scale,clrKhaki,9*scale);
   // v1.63 (1915 §二): table tail — LAST only ([CLOSE ALL] moved to the header)
   int ly = ty + 18*scale + shown*15*scale;
   UpdTxt("BGL", (g_bingoLast == "" ? "LAST: -" : g_bingoLast), x, ly, clrKhaki, 9*scale);
   UpdTxt("TAM2","DD now = live floating loss / balance | MaxDD = historical peak decline | base = balance | Gain = formula-recomputed from prices", x, ly + 16*scale, clrKhaki, 8*scale);
   // v1.43 T3: manual confirm / reset-peak button (shows when lock engaged or AT stopped)
   int by = ly + 32*scale;
   bool needConfirm = (g_ddgAccountArmed || g_tdStoppedAT || TimeCurrent() < g_ddgLockUntil);
   if(needConfirm)
   {
      UpdTxtBold("DDRESETLBL","⚠️ RISK LOCKED — verify manually, then press [Confirm / Reset Peak]",x,by,clrOrangeRed,9*scale);
      UpdBtn("DDRESET","[ Confirm / Reset Peak ]",x+w-230*scale,by+16*scale,220*scale,16*scale,true);
   }
   else UpdBtn("DDRESET","[ Reset Peak ]",x+w-230*scale,by+16*scale,220*scale,16*scale,false);
   // v1.60 (1400 §三): independent CLOSE BOARD removed — buttons inline above.
   // v1.63 (1915 §二): UNLOCK/LOCK + [CLOSE ALL] + pager in the header, LAST at the tail.
   // v1.37: tickbox/bar chart removed (was confusing, no info value)
}
void TabRender_Set(int x,int y,int scale,int w)
{
   UpdTxtBold("TS0","Settings Quick View (change via EA inputs)",x,y,clrDeepSkyBlue,10*scale);
   UpdTxt("TS1",StringFormat("Refresh: %ds   Record: %ds   Scale: %d   Chart: %s",InpRefreshSeconds,InpRecordSeconds,InpPanelScale,(InpShowPnlChart?"ON":"OFF")),x,y+16*scale,clrWhite,9*scale);
   UpdTxt("TS2",StringFormat("SymbolGuard: %s   DefaultMode: %s",(InpSymbolGuardEnable?"ON":"OFF"),SG_ModeName(InpSymbolGuardMode)),x,y+30*scale,clrWhite,9*scale);
   UpdTxt("TS3",StringFormat("Snapshot: %s   AutoBackup: %s @ %s",(InpSnapshotEnable?"ON":"OFF"),(InpAutoBackup?"ON":"OFF"),InpBackupTime),x,y+44*scale,clrWhite,9*scale);
   UpdTxt("TS4","Tip: click tabs to switch. Guard tab = per-symbol ON/ALERT/BLOCK/CLOSE (CLOSE needs 2nd press).",x,y+59*scale,clrWhite,9*scale);
}

//================= v1.54 FIX-TD4: BINGO CLOSE BOARD (0745 放行信) =========
// 覆蓋 0745 信全部硬約束：
//   - 品種來源只准即時掃 OrdersTotal()，禁 g_ddSyms[]（跨帳戶幽靈 SYMBOL）
//   - 平倉只准 OrderSelect(SELECT_BY_POS, MODE_TRADES) 即時重掃，禁 t_ 陣列
//   - ARM 60s 倒數未 ARM 全板禁用灰；到期自動失效；切 TAB／帳號變更解除
//   - 每按鈕獨立 30s 冷卻；橙紅色；即按即執行無延遲；殘留顯示 RESID n
//   - 底部 LAST 行；[CLOSE 全倉] 含刪除全部 pending
string BINGO_BtnName(int b)
{
   if(b == 0) return("BUY");
   if(b == 1) return("SELL");
   if(b == 2) return("WIN");
   if(b == 3) return("LOSE");
   return("ALL");
}

//--- v1.60 (1400 §三): BINGO_RowsPerPage removed — the inline table uses a
//--- fixed 12 rows/page over g_ddSymN (cap 32 => max 3 pages).

//--- v1.60 (1400 §三): BINGO_Collect removed — the row list is the DDGuard
//--- table itself (g_ddSyms); per-row floating is already the Float$ column;
//--- the 0745 live-rescan rule still governs every close via BINGO_CountMatch.

//--- count open positions matching a BINGO mode (live rescan)
int BINGO_CountMatch(int mode, string sym)
{
   int n = 0;
   for(int p = OrdersTotal()-1; p >= 0; p--)
   {
      if(!OrderSelect(p, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderType() > OP_SELL) continue;
      if(mode != 5 && OrderSymbol() != sym) continue;
      if(mode == 0 && OrderType() != OP_BUY) continue;
      if(mode == 1 && OrderType() != OP_SELL) continue;
      double pf = OrderProfit() + OrderSwap() + OrderCommission();
      if(mode == 2 && pf <= 0) continue;                // WIN = floating profit
      if(mode == 3 && pf >= 0) continue;                // LOSE = floating loss
      n++;
   }
   return(n);
}

//--- v1.60 (1400 §三): BINGO_Render removed — the independent CLOSE BOARD is
//--- gone; its ARM/pager/LAST/CLOSE-全倉 pieces render inside TabRender_DDG.

//--- ARM toggle: 60s window starts here; whole board gates on this flag
void BINGO_ArmToggle()
{
   if(!g_bingoArmed)
   {
      g_bingoArmed = true;
      g_bingoArmT = TimeCurrent();
      LogEvent("BINGO: UNLOCK on (60s window)");
   }
   else
   {
      g_bingoArmed = false;
      LogEvent("BINGO: LOCK (manual)");
   }
}

//--- per-symbol row button: 0=BUY 1=SELL 2=WIN 3=LOSE 4=SYM-ALL(keeps pending)
//--- v1.60 (1400 §三): row = DDGuard table visible row on the current page;
//--- symbol comes from g_ddSyms[page*12+row] (that row's symbol). Close path
//--- unchanged — 0745 hard rule: LIVE rescan at press time, never caches.
void BINGO_Press(int row, int b)
{
   if(row < 0 || row >= 12 || b < 0 || b >= 5) return;
   if(!g_bingoArmed) return;                                            // 未 ARM 全板禁用
   if(TimeCurrent() > g_bingoArmT + 60) { g_bingoArmed = false; return; } // 到期自動失效
   if(TimeCurrent() - g_bingoCool[row][b] < 30) return;                 // 每按鈕獨立冷卻 30s
   int idx = g_bingoPage * 12 + row;                                    // v1.60: table row
   if(idx >= g_ddSymN || idx >= 32) return;
   string sym = g_ddSyms[idx];
   int closed = BINGO_CountMatch(b, sym);
   if(closed == 0) return;                                              // 該範圍無單，唔燒冷卻
   double balBefore = AccountBalance();
   int residual = DDG_CloseMatch(b, sym);
   double realized = AccountBalance() - balBefore;
   g_bingoCool[row][b] = TimeCurrent();
   if(residual > 0) { g_bingoResidSym = sym; g_bingoResidN = residual; g_bingoResidT = TimeCurrent(); }
   else if(sym == g_bingoResidSym) { g_bingoResidSym = ""; g_bingoResidN = 0; }
   // v1.60 (1400 §三): RESID moved from the board row into the LAST line
   //   (0745 hard rule: residual must be visible on the panel).
   g_bingoLast = StringFormat("LAST: %s %s %d張 %+.2f @%s", BINGO_BtnName(b), sym, closed, realized, TimeToString(TimeCurrent(), TIME_MINUTES))
             + (residual > 0 ? StringFormat(" ⚠RESID %d!", residual) : "");
   LogEvent(StringFormat("BINGO %s %s: closed %d, residual %d, realized $%.2f", BINGO_BtnName(b), sym, closed, residual, realized));
   TG_Notify("TD_BINGO_" + sym + "_" + IntegerToString(b), "🎯 BINGO " + BINGO_BtnName(b) + " — " + sym + "\n▪ Closed: " + IntegerToString(closed) + " position(s)\n▪ Realized: $" + DoubleToString(realized, 2) + (residual > 0 ? "\n⚠ Residual: " + IntegerToString(residual) + " still open!" : "\n▪ Residual: 0 ✅") + "\n🕐 " + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + " server");
   RenderOnly();
}

//--- global [CLOSE 全倉]: all symbols all positions + delete ALL pending
void BINGO_CloseAll()
{
   if(!g_bingoArmed) return;
   if(TimeCurrent() > g_bingoArmT + 60) { g_bingoArmed = false; return; }
   if(TimeCurrent() - g_bingoCoolAll < 30) return;
   int closed = BINGO_CountMatch(5, "");
   if(closed == 0) return;
   double balBefore = AccountBalance();
   int residual = DDG_CloseMatch(5, "");
   double realized = AccountBalance() - balBefore;
   g_bingoCoolAll = TimeCurrent();
   g_bingoLast = StringFormat("LAST: CLOSE全倉 %d張 %+.2f @%s", closed, realized, TimeToString(TimeCurrent(), TIME_MINUTES))
             + (residual > 0 ? StringFormat(" ⚠RESID %d!", residual) : "");   // v1.60: RESID in LAST
   LogEvent(StringFormat("BINGO CLOSEALL: closed %d, residual %d, realized $%.2f", closed, residual, realized));
   TG_Notify("TD_CLOSEALL", "🎯 TD CLOSE ALL\n▪ Closed: " + IntegerToString(closed) + " position(s)\n▪ Realized: $" + DoubleToString(realized, 2) + (residual > 0 ? "\n⚠ Residual: " + IntegerToString(residual) + " still open — manual check!" : "\n▪ Residual: 0 ✅") + "\n🕐 " + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + " server");
   RenderOnly();
}

//--- per-second upkeep from OnTimer: ARM countdown text, cooldown expiry,
//--- RESID timeout; renders ONLY when something on the board is live.
void BINGO_Tick()
{
   if(g_tab != 2) return;
   if(g_bingoArmed && TimeCurrent() > g_bingoArmT + 60)
   {
      g_bingoArmed = false;                    // ARM 到期自動失效
      RenderOnly();
      return;
   }
   bool busy = g_bingoArmed;
   if(!busy)
      for(int i = 0; i < 28 && !busy; i++)
         for(int b = 0; b < 5; b++)
            if(TimeCurrent() - g_bingoCool[i][b] < 30) { busy = true; break; }
   if(!busy && TimeCurrent() - g_bingoCoolAll < 30) busy = true;
   if(!busy && g_bingoResidN > 0 && TimeCurrent() - g_bingoResidT < 60) busy = true;
   if(busy) RenderOnly();
}

void OnTick()
{
   CheckTabCmd();   // v1.35: agent self-test hook
   NGDDG_Init();
   NG_Guard();
   DDG_Guard();
   DDG_ATStatusCheck();   // v1.43 T3: observe-only, never auto-restore AT
   SymbolGuard();
   NG_WindowPush();
   GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
   RecordSnapshot();
   SG_CollectSymbols();
   
   // Daily auto backup check (runs once per day after BackupTime)
   CheckAndBackupProfile();

   if(InpSnapshotEnable && TimeCurrent() - g_lastSnap >= 300)
   {
      SyncTradesFromHistory();
      g_lastSnap = TimeCurrent();
   }

   if(TimeCurrent() - g_lastFull >= InpRefreshSeconds)
   {
      CollectData();
      DD_BuildSymbols();
      RenderOnly();
      g_lastFull = TimeCurrent();
   }
}

//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| v1.20: FX market should be open? (PC clock, assumes HKT timezone) |
//| FX week: Mon ~04:00-05:00 HKT open -> Sat ~04:00-05:00 HKT close |
//| Buffers: no trigger Sunday, Monday from 06:00, Saturday to 04:00 |
//+------------------------------------------------------------------+
bool MarketShouldBeOpenLocal(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   int w = dt.day_of_week;          // 0=Sun 1=Mon ... 6=Sat
   if(w == 0) return false;         // Sunday: closed (buffer)
   if(w == 1) return dt.hour >= 6;  // Monday: from 06:00 HKT
   if(w >= 2 && w <= 5) return true;// Tue-Fri full day
   if(w == 6) return dt.hour < 4;   // Saturday: before 04:00
   return false;
}

//+------------------------------------------------------------------+
//| v1.20: Write restart script + launch it (kills own terminal,     |
//| restarts exe; MT4 re-logins with saved account credentials)      |
//+------------------------------------------------------------------+
void TriggerTerminalRestart()
{
   string exe = TerminalInfoString(TERMINAL_PATH);
   StringReplace(exe, "/", "\\");
   if(StringLen(exe) < 5) { Print("[RC] no terminal path"); return; }

   int h = FileOpen("TD_restart.cmd", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) { Print("[RC] cannot write TD_restart.cmd"); return; }
   FileWriteString(h, "@echo off\r\n");
   FileWriteString(h, "setlocal\r\n");
   FileWriteString(h, "set \"EXE=" + exe + "\"\r\n");
   FileWriteString(h, "set \"PIDF=%TEMP%\\td_pid.txt\"\r\n");
   FileWriteString(h, "wmic process where \"ExecutablePath='%EXE%'\" get ProcessId /value > \"%PIDF%\" 2>nul\r\n");
   FileWriteString(h, "set PID=\r\n");
   FileWriteString(h, "for /f \"tokens=2 delims==\" %%P in ('findstr /b \"ProcessId\" \"%PIDF%\"') do set PID=%%P\r\n");
   FileWriteString(h, "if defined PID taskkill /F /PID %PID% >nul 2>&1\r\n");
   FileWriteString(h, "ping -n 4 127.0.0.1 >nul\r\n");
   FileWriteString(h, "start \"\" \"%EXE%\"\r\n");
   FileWriteString(h, "del \"%PIDF%\" >nul 2>&1\r\n");
   FileClose(h);

   string dp = TerminalInfoString(TERMINAL_DATA_PATH);
   StringReplace(dp, "/", "\\");
   string full = dp + "\\MQL4\\Files\\TD_restart.cmd";
   ShellExecuteW(0, "open", "cmd.exe", "/C \"" + full + "\"", NULL, 0);
   Print("[RC] terminal restart triggered: ", exe);
}

//+------------------------------------------------------------------+
//| v1.20: OnTimer - auto-reconnect watchdog                         |
//+------------------------------------------------------------------+
void OnTimer()
{
   // v1.53 FIX-TD5 (2345 spec item 3): account switch mid-session — wipe
   //   in-memory state and reload everything from THIS account's files.
   if(AccountNumber() != g_acct && AccountNumber() > 0)
   {
      g_acct = AccountNumber();
      t_tradeCount = 0;
      r_count = 0;
      r_head = 0;
      LoadRecordsBin();                 // hydrate from TD_<acct>_snap.bin
      if(r_count == 0) LoadRecords();   // fallback legacy per-account CSV
      LoadTrades();                     // TD_<acct>_trades.csv
      DDG_LoadState();                  // account-scoped risk state (v1.47 Q9 keys)
      g_bingoArmed = false;             // v1.54 FIX-TD4: ARM 解除（帳號變更）
      LogEvent("ACCT SWITCH: reloaded TD files for account " + IntegerToString(g_acct));
      Print("TD v1.53 FIX-TD5: account switch -> ", g_acct, ", state reloaded");
   }

   CheckTabCmd();   // v1.35: agent self-test hook (also when no ticks)
   BINGO_Tick();    // v1.54 FIX-TD4: ARM countdown / cooldown expiry refresh

   //--- v1.60 (1230 item 1, MT5 parity): 5-min history sync + refresh from the
   //--- timer, so quiet sessions / weekends with ZERO ticks still keep the trade
   //--- store and the panel fresh. OnTick does the same on ticks; the shared
   //--- g_lastSnap / g_lastFull stamps make the two paths idempotent.
   if(InpSnapshotEnable && TimeCurrent() - g_lastSnap >= 300)
   {
      SyncTradesFromHistory();
      g_lastSnap = TimeCurrent();
   }
   if(TimeCurrent() - g_lastFull >= InpRefreshSeconds)
   {
      CollectData();
      DD_BuildSymbols();
      RenderOnly();
      g_lastFull = TimeCurrent();
   }

   //--- v1.46 Q4: risk guards every 1s, independent of market ticks
   NGDDG_Init();
   NG_Guard();
   DDG_Guard();
   DDG_ATStatusCheck();
   SymbolGuard();
   NG_WindowPush();
   GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
   RecordSnapshot();
   SG_CollectSymbols();
   CheckAndBackupProfile();

   if(!InpAutoReconnect) return;

   if(IsConnected())
   {
      double okCnt = GlobalVariableGet("TD_RC_count");
      if(okCnt >= 1)
      {
         LogEvent("RECONNECT OK: restored after " + IntegerToString((int)okCnt) + " restart attempt(s)");
         GlobalVariableSet("TD_RC_count", 0);
         GlobalVariableSet("TD_RC_gaveup", 0);
      }
      g_discStart = 0;
      return;
   }

   datetime nowL = TimeLocal();
   if(g_discStart == 0) { g_discStart = nowL; return; }
   if(nowL - g_discStart < InpReconnectAfterMinutes * 60) return;   // not sustained yet
   if(!MarketShouldBeOpenLocal(nowL)) return;                // weekend/overnight

   // v1.21: give up after N consecutive failed restarts
   // (password changed / account locked - manual intervention needed)
   double cnt = GlobalVariableGet("TD_RC_count");
   if(cnt >= InpMaxRestartAttempts)
   {
      if(GlobalVariableGet("TD_RC_gaveup") < 1)
      {
         GlobalVariableSet("TD_RC_gaveup", 1);
         LogEvent("RECONNECT GAVE UP: " + IntegerToString((int)cnt) +
                  " restarts failed - MANUAL LOGIN REQUIRED (check password/account)");
      }
      return;
   }

   // cooldown across restarts via terminal Global Variables
   double gv = GlobalVariableGet("TD_RC_last");
   if(gv > 0 && nowL - (datetime)gv < InpRestartCooldownHours * 3600) return;
   GlobalVariableSet("TD_RC_last", (double)nowL);
   GlobalVariableSet("TD_RC_count", cnt + 1);

   LogEvent("RECONNECT RESTART #" + IntegerToString((int)cnt + 1) + "/" +
            IntegerToString(InpMaxRestartAttempts) + ": disconnected " +
            IntegerToString((int)((nowL - g_discStart) / 60)) + " min, restarting terminal");
   TriggerTerminalRestart();
}

//| OnChartEvent                                                     |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id == CHARTEVENT_OBJECT_CLICK)
   {
      string s = sparam;
      bool changed = false;

      if(StringFind(s, PFX+"DDC") == 0)
      {
         int di = (int)StringToInteger(StringSubstr(s, StringLen(PFX)+3));
         if(di >= 0 && di < g_ddSymN && di < 14)
            g_ddSel[di] = !g_ddSel[di];
         changed = true;
      }
      else if(StringFind(s, PFX+"TSG_") == 0)
      {
         int ai = (int)StringToInteger(StringSubstr(s, StringLen(PFX)+4));
         if(ai >= 0 && ai < g_sgSymN && ai < 8)
            SG_CycleMode(g_sgSym[ai]);   // v1.47 Q7: 4 states + CLOSE confirm
         changed = true;
      }
      else if(StringFind(s, PFX+"TAB") == 0)
      {
         int ti = (int)StringToInteger(StringSubstr(s, StringLen(PFX)+3));
         if(ti >= 0 && ti < 4)
         {
            if(ti != g_tab) g_bingoArmed = false;   // v1.54 FIX-TD4: ARM 解除（切 TAB）
            g_tab = ti;
         }
         changed = true;
      }
      else if(s == PFX+"V_H")       { g_view=0; g_offset=0; changed=true; }
      else if(s == PFX+"V_D")  { g_view=1; g_offset=0; changed=true; }
      else if(s == PFX+"V_W")  { g_view=2; g_offset=0; changed=true; }
      else if(s == PFX+"V_M")  { g_view=3; g_offset=0; changed=true; }
      else if(s == PFX+"NAV_L"){ g_offset--; changed=true; }
      else if(s == PFX+"NAV_R"){ if(g_offset<0) g_offset++; changed=true; }
      else if(s == PFX+"DDRESET") { DDG_ResetPeakConfirm(); changed=true; }
      //--- v1.48: DDGuard runtime switches (panel toggles, persisted via GV) ---
      else if(s == PFX+"DDGT_ON")
      {
         if(g_ddgeOn)
         {
            // arming is safe, disarming is not -> require a second press in 10s
            if(g_ddgOffPendT > 0 && TimeCurrent() - g_ddgOffPendT <= 10)
            {
               g_ddgeOn = false; g_ddgOffPendT = 0;
               Print("DDGuard v1.48: MASTER OFF (panel)");
            }
            else g_ddgOffPendT = TimeCurrent();
         }
         else { g_ddgeOn = true; g_ddgOffPendT = 0; Print("DDGuard v1.48: MASTER ON (panel)"); }
         DDG_SaveState(); changed = true;
      }
      else if(s == PFX+"DDGT_ACC")
      {
         g_ddgAccOn = !g_ddgAccOn;
         if(!g_ddgeOn && g_ddgAccOn) g_ddgeOn = true;
         Print("DDGuard v1.48: account guard ", (g_ddgAccOn?"ON":"OFF"), " (panel)");
         DDG_SaveState(); changed = true;
      }
      else if(s == PFX+"DDGT_SYM")
      {
         g_ddgSymOn = !g_ddgSymOn;
         if(!g_ddgeOn && g_ddgSymOn) g_ddgeOn = true;
         Print("DDGuard v1.48: symbol guard ", (g_ddgSymOn?"ON":"OFF"), " (panel)");
         DDG_SaveState(); changed = true;
      }
      //--- v1.54 FIX-TD4: BINGO CLOSE BOARD buttons -------------------------
      else if(StringFind(s, PFX+"BGB_") == 0)
      {
         string bgRest = StringSubstr(s, StringLen(PFX) + 4);
         int us = StringFind(bgRest, "_");
         if(us > 0)
            BINGO_Press((int)StringToInteger(StringSubstr(bgRest, 0, us)),
                        (int)StringToInteger(StringSubstr(bgRest, us + 1)));
         changed = true;
      }
      else if(s == PFX+"BGA")   { BINGO_ArmToggle(); changed = true; }
      else if(s == PFX+"BGC")   { BINGO_CloseAll();  changed = true; }
      else if(s == PFX+"BGP_L") { g_bingoPage--; if(g_bingoPage < 0) g_bingoPage = 0; changed = true; }
      else if(s == PFX+"BGP_R") { g_bingoPage++; changed = true; }
      else if(s == PFX+"SAVE") { ManualBackupNow(); changed=false; }
      else if(StringFind(s, PFX+"SG_") == 0)
      {
         int gi = (int)StringToInteger(StringSubstr(s, StringLen(PFX)+3));
         if(gi >= 0 && gi < g_sgSymN && gi < 10)
         {
            string sym2 = g_sgSym[gi];
            SG_CycleMode(sym2);   // v1.47 Q7: 4 states + CLOSE confirm
            if(gi<64) g_sgAlertT[gi]=0;   // pressing acknowledges alert
         }
         changed = true;
      }
      else
      {
         for(int c = 0; c < NC; c++)
         {
            if(s == PFX+"C"+IntegerToString(c))
            {
               g_vis[c] = !g_vis[c];
               changed = true;
               break;
            }
         }
      }

      if(changed)
      {
         CollectData();
         RenderOnly();
         g_lastFull = TimeCurrent();
      }
   }
   else if(id == CHARTEVENT_OBJECT_ENDEDIT)
   {
      string s = sparam;
      bool changed = false;

      if(s == PFX+"FS_EDIT")
      {
         g_filterSymbol = ObjectGetString(0, PFX+"FS_EDIT", OBJPROP_TEXT);
         changed = true;
      }
      else if(s == PFX+"FC_EDIT")
      {
         g_filterComment = ObjectGetString(0, PFX+"FC_EDIT", OBJPROP_TEXT);
         changed = true;
      }

      if(changed)
      {
         CollectData();
         RenderOnly();
         g_lastFull = TimeCurrent();
      }
   }
}

//+------------------------------------------------------------------+
//| Filter helper                                                    |
//+------------------------------------------------------------------+
bool PassesFilter(int idx)
{
   if(g_filterSymbol != "" && t_symbol[idx] != g_filterSymbol) return false;
   if(g_filterComment != "" && StringFind(t_comment[idx], g_filterComment) < 0) return false;
   return true;
}

//+------------------------------------------------------------------+
//| Local Trade Snapshot System                                      |
//+------------------------------------------------------------------+
int FindTrade(int ticket)
{
   for(int i = 0; i < t_tradeCount; i++)
   {
      if(t_ticket[i] == ticket) return i;
   }
   return -1;
}

double CalcTradePnl(string symbol, int type, double openPrice, double closePrice,
                    double volume, double swap, double commission)
{
   double pt = MarketInfo(symbol, MODE_POINT);
   if(pt < 0.0000001) pt = 0.0001;

   double contractSize = MarketInfo(symbol, MODE_LOTSIZE);
   if(contractSize < 1) contractSize = 100000;

   double tickValue = MarketInfo(symbol, MODE_TICKVALUE);
   double tickSize  = MarketInfo(symbol, MODE_TICKSIZE);
   double priceDiff;

   if(type == OP_BUY)
      priceDiff = closePrice - openPrice;
   else
      priceDiff = openPrice - closePrice;

   double pureProfit;
   if(tickValue > 0 && tickSize > 0)
   {
      pureProfit = (priceDiff / tickSize) * tickValue * volume;
   }
   else
   {
      pureProfit = priceDiff * contractSize * volume;
   }

   return pureProfit + swap + commission;
}

void SyncTradesFromHistory()
{
   //--- v1.55 FIX-TD6 addendum (608dbe5): BackfillOnce ignores SnapHours and
   //---   scans the whole history once (since=0) - the frozen-window gap
   //---   between freeze day and 72h ago would otherwise stay missing forever.
   datetime since;
   if(InpSnapshotBackfillOnce) since = 0;
   else since = TimeCurrent() - InpSnapshotHours * 3600;
   int newCount = 0;
   int lostCount = 0;

   //--- v1.55 FIX-TD6 (0925 spec items 1+2): scan NEWEST-first, no 2000 cap.
   //---   MT4 history index 0 = oldest; the old oldest-first scan froze at
   //---   index 1999 once history passed 2000 rows - this account crossed the
   //---   line on 10-21 and every newer close was never scanned again, so the
   //---   sync silently died (last ok 2026.10.21 17:36). Walking down from
   //---   the newest row, the first row older than `since` ends the scan -
   //---   the window is the natural limiter; MAX_HISTORY_SCAN is only a
   //---   runaway safety cap.
   int histTotal = OrdersHistoryTotal();
   int scanned   = 0;
   bool capHit   = false;

   bool seen[MAX_TRADES];
   ArrayInitialize(seen, false);

   for(int i = histTotal - 1; i >= 0; i--)
   {
      if(scanned >= MAX_HISTORY_SCAN) { capHit = true; break; }
      scanned++;
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY)) continue;
      if(OrderType() > OP_SELL) continue;
      if(OrderCloseTime() == 0) continue;
      if(OrderCloseTime() < since) break;   // ascending close times: everything below is older

      int ticket = OrderTicket();
      int idx = FindTrade(ticket);

      if(idx >= 0)
      {
         seen[idx] = true;
         t_symbol[idx]     = OrderSymbol();
         t_type[idx]       = OrderType();
         t_opentime[idx]   = OrderOpenTime();
         t_closetime[idx]  = OrderCloseTime();
         t_openprice[idx]  = OrderOpenPrice();
         t_closeprice[idx] = OrderClosePrice();
         t_lots[idx]       = OrderLots();
         t_profit[idx]     = OrderProfit();
         t_swap[idx]       = OrderSwap();
         t_commission[idx] = OrderCommission();
         t_comment[idx]    = OrderComment();
         t_calcPnl[idx]    = CalcTradePnl(OrderSymbol(), OrderType(),
                                         OrderOpenPrice(), OrderClosePrice(),
                                         OrderLots(), OrderSwap(), OrderCommission());
      }
      else
      {
         if(t_tradeCount >= MAX_TRADES) continue;

         t_ticket[t_tradeCount]     = ticket;
         t_symbol[t_tradeCount]     = OrderSymbol();
         t_type[t_tradeCount]       = OrderType();
         t_opentime[t_tradeCount]   = OrderOpenTime();
         t_closetime[t_tradeCount]  = OrderCloseTime();
         t_openprice[t_tradeCount]  = OrderOpenPrice();
         t_closeprice[t_tradeCount] = OrderClosePrice();
         t_lots[t_tradeCount]       = OrderLots();
         t_profit[t_tradeCount]     = OrderProfit();
         t_swap[t_tradeCount]       = OrderSwap();
         t_commission[t_tradeCount] = OrderCommission();
         t_comment[t_tradeCount]    = OrderComment();
         t_calcPnl[t_tradeCount]    = CalcTradePnl(OrderSymbol(), OrderType(),
                                                   OrderOpenPrice(), OrderClosePrice(),
                                                   OrderLots(), OrderSwap(), OrderCommission());
         t_tradeCount++;
         newCount++;
      }
   }

   for(int j = 0; j < t_tradeCount; j++)
   {
      if(!seen[j] && t_closetime[j] >= since)
      {
         lostCount++;
      }
   }

   if(newCount > 0 || lostCount > 0)
   {
      LogEvent(StringFormat("SYNC %s | New: %d | Lost(trade): %d | Total: %d",
               TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
               newCount, lostCount, t_tradeCount));
   }

   //--- v1.55 FIX-TD6 (0925 spec item 6): feed the panel heartbeat line
   g_syncLastOk = TimeCurrent();
   g_syncNew    = newCount;
   g_syncHist   = histTotal;
   g_syncCap    = capHit;
   if(capHit)
      LogEvent(StringFormat("SYNC CAP HIT | scanned %d of hist %d - raise MAX_HISTORY_SCAN", scanned, histTotal));

   //--- v1.55 FIX-TD6 addendum (608dbe5): one-shot backfill result line
   if(InpSnapshotBackfillOnce)
      LogEvent(StringFormat("BACKFILL DONE n=%d", t_tradeCount));

   SaveTrades();
}

void SaveTrades()
{
   //--- v1.55 FIX-TD6 (0925 spec item 5): silent-wipe guard. A sync that
   //---   legitimately holds 0 in-memory trades must never overwrite an
   //---   account-scoped file that still carries data rows - the frozen sync
   //---   kept rewriting from the stale array, and the boss's manually rebuilt
   //---   file would have been wiped by the first tick after a reload.
   if(t_tradeCount == 0 && PerAcctTradesHasData())
   {
      LogEvent("SAVE SKIPPED: 0 trades in memory, file non-empty (v1.55 guard, kept in v1.60)");
      Print("TD v1.55 FIX-TD6: SAVE SKIPPED - 0 trades in memory, non-empty ", TD_F_trades(), " left untouched");
      return;
   }

   int fh = FileOpen(TD_F_trades(), FILE_WRITE|FILE_CSV|FILE_ANSI, ',');   // v1.53 FIX-TD5: TD_<acct>_trades.csv
   if(fh == INVALID_HANDLE) return;

   FileWrite(fh, "Ticket", "Account", "Symbol", "Type", "OpenTime", "CloseTime",
             "OpenPrice", "ClosePrice", "Volume", "Profit", "Swap",
             "Commission", "CalcPnl", "Comment");

   for(int i = 0; i < t_tradeCount; i++)
   {
      FileWrite(fh,
         t_ticket[i],
         IntegerToString(AccountNumber()),   // v1.53 FIX-TD5: per-row account (2nd line of defense)
         t_symbol[i],
         (t_type[i]==OP_BUY ? "BUY" : "SELL"),
         (int)t_opentime[i],
         (int)t_closetime[i],
         DoubleToString(t_openprice[i], 5),
         DoubleToString(t_closeprice[i], 5),
         DoubleToString(t_lots[i], 2),
         DoubleToString(t_profit[i], 2),
         DoubleToString(t_swap[i], 2),
         DoubleToString(t_commission[i], 2),
         DoubleToString(t_calcPnl[i], 2),
         t_comment[i]
      );
   }
   FileClose(fh);
}

void LoadTrades()
{
   t_tradeCount = 0;

   int fh = FileOpen(TD_F_trades(), FILE_READ|FILE_CSV|FILE_ANSI, ',');   // v1.53 FIX-TD5: TD_<acct>_trades.csv
   if(fh == INVALID_HANDLE) return;

   for(int h = 0; h < 14; h++) FileReadString(fh);   // v1.53 FIX-TD5: header now 14 cols (Ticket,Account,...)

   while(!FileIsEnding(fh) && t_tradeCount < MAX_TRADES)
   {
      string sTicket = FileReadString(fh);
      if(sTicket == "") break;

      int tkt        = (int)StringToInteger(sTicket);
      string sAcct   = FileReadString(fh);   // v1.53 FIX-TD5: per-row account
      string sym     = FileReadString(fh);
      string sType   = FileReadString(fh);
      datetime ot    = (datetime)StringToInteger(FileReadString(fh));
      datetime ct    = (datetime)StringToInteger(FileReadString(fh));
      double op      = StringToDouble(FileReadString(fh));
      double cp      = StringToDouble(FileReadString(fh));
      double lots    = StringToDouble(FileReadString(fh));
      double prof    = StringToDouble(FileReadString(fh));
      double swp     = StringToDouble(FileReadString(fh));
      double comm    = StringToDouble(FileReadString(fh));
      double calcP   = StringToDouble(FileReadString(fh));
      string cmt     = FileReadString(fh);

      // v1.53 FIX-TD5 (2345 spec item 2): 2nd line of defense — rows whose
      //   Account column mismatches this account are skipped, never rendered.
      //   Empty value tolerated (manually crafted file); a 13-col legacy row
      //   would shift sAcct onto the Symbol value, which also fails the match
      //   and is skipped — safe by construction.
      if(sAcct != "" && sAcct != IntegerToString(AccountNumber())) continue;

      // Apply ReportStart filter when loading
      if(g_reportStart > 0 && ct < g_reportStart) continue;

      t_ticket[t_tradeCount]     = tkt;
      t_symbol[t_tradeCount]     = sym;
      t_type[t_tradeCount]       = (sType == "BUY") ? OP_BUY : OP_SELL;
      t_opentime[t_tradeCount]   = ot;
      t_closetime[t_tradeCount]  = ct;
      t_openprice[t_tradeCount]  = op;
      t_closeprice[t_tradeCount] = cp;
      t_lots[t_tradeCount]       = lots;
      t_profit[t_tradeCount]     = prof;
      t_swap[t_tradeCount]       = swp;
      t_commission[t_tradeCount] = comm;
      t_calcPnl[t_tradeCount]    = calcP;
      t_comment[t_tradeCount]    = cmt;
      t_tradeCount++;
   }
   FileClose(fh);
   Print("TD trades loaded: ", t_tradeCount);
}

//--- v1.55 FIX-TD6 (0925 spec item 3): 13-column pre-v1.53 loader (no Account
//---   column). Rows are attributed to the current account by construction.
//---   Returns the number of rows loaded into memory.
int LoadTradesLegacy()
{
   t_tradeCount = 0;

   int fh = FileOpen(TRADES_FILE, FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) return(0);

   for(int h = 0; h < 13; h++) FileReadString(fh);   // legacy 13-col header

   while(!FileIsEnding(fh) && t_tradeCount < MAX_TRADES)
   {
      string sTicket = FileReadString(fh);
      if(sTicket == "") break;

      int tkt        = (int)StringToInteger(sTicket);
      string sym     = FileReadString(fh);
      string sType   = FileReadString(fh);
      datetime ot    = (datetime)StringToInteger(FileReadString(fh));
      datetime ct    = (datetime)StringToInteger(FileReadString(fh));
      double op      = StringToDouble(FileReadString(fh));
      double cp      = StringToDouble(FileReadString(fh));
      double lots    = StringToDouble(FileReadString(fh));
      double prof    = StringToDouble(FileReadString(fh));
      double swp     = StringToDouble(FileReadString(fh));
      double comm    = StringToDouble(FileReadString(fh));
      double calcP   = StringToDouble(FileReadString(fh));
      string cmt     = FileReadString(fh);

      // Apply ReportStart filter when loading (same rule as LoadTrades)
      if(g_reportStart > 0 && ct < g_reportStart) continue;

      t_ticket[t_tradeCount]     = tkt;
      t_symbol[t_tradeCount]     = sym;
      t_type[t_tradeCount]       = (sType == "BUY") ? OP_BUY : OP_SELL;
      t_opentime[t_tradeCount]   = ot;
      t_closetime[t_tradeCount]  = ct;
      t_openprice[t_tradeCount]  = op;
      t_closeprice[t_tradeCount] = cp;
      t_lots[t_tradeCount]       = lots;
      t_profit[t_tradeCount]     = prof;
      t_swap[t_tradeCount]       = swp;
      t_commission[t_tradeCount] = comm;
      t_calcPnl[t_tradeCount]    = calcP;
      t_comment[t_tradeCount]    = cmt;
      t_tradeCount++;
   }
   FileClose(fh);
   Print("TD v1.55 FIX-TD6: legacy trades loaded: ", t_tradeCount);
   return(t_tradeCount);
}

//--- v1.55 FIX-TD6: true when the legacy shared trades file exists and still
//---   holds at least one data row beyond the 13-col header.
bool LegacyTradesHasData()
{
   if(!FileIsExist(TRADES_FILE)) return(false);
   int fh = FileOpen(TRADES_FILE, FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) return(false);
   for(int h = 0; h < 13; h++) FileReadString(fh);
   bool hasData = !FileIsEnding(fh);
   FileClose(fh);
   return(hasData);
}

//--- v1.55 FIX-TD6: true when the account-scoped trades file exists and holds
//---   at least one data row beyond the 14-col header (mirrors LoadTrades).
bool PerAcctTradesHasData()
{
   if(!FileIsExist(TD_F_trades())) return(false);
   int fh = FileOpen(TD_F_trades(), FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) return(false);
   for(int h = 0; h < 14; h++) FileReadString(fh);
   bool hasData = !FileIsEnding(fh);
   FileClose(fh);
   return(hasData);
}

void LogEvent(string msg)
{
   int fh = FileOpen(EVENT_FILE, FILE_WRITE|FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) return;
   FileSeek(fh, 0, SEEK_END);
   FileWrite(fh, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS), msg);
   FileClose(fh);
}

//+------------------------------------------------------------------+
//| Recording functions (equity snapshots)                           |
//+------------------------------------------------------------------+
double GetCurFloat()
{
   double f = 0;
   for(int k=0; k<OrdersTotal(); k++)
   {
      if(!OrderSelect(k, SELECT_BY_POS, MODE_TRADES)) continue;
      f += OrderProfit()+OrderSwap()+OrderCommission();
   }
   return f;
}

void RecordSnapshot()
{
   datetime now = TimeCurrent();
   if(now - g_lastRec < MathMax(1, InpRecordSeconds)) return;
   g_lastRec = now;

   double bal = AccountBalance();
   double eq  = AccountEquity();
   double mg  = AccountMargin();
   double fm  = AccountFreeMargin();
   double fl  = GetCurFloat();

   r_dt[r_head]    = now;
   r_bal[r_head]   = bal;
   r_eq[r_head]    = eq;
   r_marg[r_head]  = mg;
   r_fmarg[r_head] = fm;
   r_float[r_head] = fl;
   r_head++;
   if(r_head >= MAX_REC) r_head = 0;
   if(r_count < MAX_REC) r_count++;

   int fh = FileOpen(TD_F_records(), FILE_WRITE|FILE_READ|FILE_CSV|FILE_ANSI, ',');   // v1.53 FIX-TD5
   if(fh != INVALID_HANDLE)
   {
      FileSeek(fh, 0, SEEK_END);
      FileWrite(fh, (int)now, TimeToString(now, TIME_DATE|TIME_SECONDS),
         DoubleToString(bal, 2), DoubleToString(eq, 2),
         DoubleToString(mg, 2), DoubleToString(fm, 2),
         DoubleToString(fl, 2));
      FileClose(fh);
   }

   // v1.43 T6: throttle binary flush to once per 30s (mirror MT5)
   if(TimeCurrent() - g_lastBinSave >= 30)
   {
      SaveRecordsBin();
      g_lastBinSave = TimeCurrent();
   }
}

//+------------------------------------------------------------------+
//| v1.43 T6: binary serialization — [magic][count][count x           |
//| (dt,bal,eq,marg,fmarg,float)]  mirror MT5 td5_snap.bin           |
//+------------------------------------------------------------------+
void SaveRecordsBin()
{
   int fh = FileOpen(TD_F_snap(), FILE_WRITE|FILE_BIN);   // v1.53 FIX-TD5: TD_<acct>_snap.bin
   if(fh == INVALID_HANDLE) return;
   FileWriteInteger(fh, SNAP_MAGIC, INT_VALUE);
   FileWriteInteger(fh, r_count, INT_VALUE);
   for(int i = 0; i < r_count; i++)
   {
      int idx = (r_head - r_count + i + MAX_REC) % MAX_REC;
      FileWriteInteger(fh, (int)r_dt[idx], LONG_VALUE);
      FileWriteDouble(fh, r_bal[idx]);
      FileWriteDouble(fh, r_eq[idx]);
      FileWriteDouble(fh, r_marg[idx]);
      FileWriteDouble(fh, r_fmarg[idx]);
      FileWriteDouble(fh, r_float[idx]);
   }
   FileClose(fh);
}

//+------------------------------------------------------------------+
//| v1.43 T6: hydrate from td4_snap.bin; fall back to legacy CSV     |
//+------------------------------------------------------------------+
void LoadRecordsBin()
{
   int fh = FileOpen(TD_F_snap(), FILE_READ|FILE_BIN);   // v1.53 FIX-TD5: TD_<acct>_snap.bin
   if(fh == INVALID_HANDLE) return;

   int magic = FileReadInteger(fh, INT_VALUE);
   if(magic != SNAP_MAGIC) { FileClose(fh); Print("TD snap bin: bad magic, ignored"); return; }

   int cnt = FileReadInteger(fh, INT_VALUE);
   if(cnt < 0 || cnt > MAX_REC) { FileClose(fh); return; }

   int cap = MathMin(cnt, MathMin(InpMaxRecords, MAX_REC));
   int skip = cnt - cap;   // drop oldest if file has more than we keep

   r_count = 0;
   r_head = 0;
   for(int i = 0; i < cnt && !FileIsEnding(fh); i++)
   {
      datetime dt = (datetime)FileReadInteger(fh, LONG_VALUE);
      double bal  = FileReadDouble(fh);
      double eq   = FileReadDouble(fh);
      double mg   = FileReadDouble(fh);
      double fm   = FileReadDouble(fh);
      double fl   = FileReadDouble(fh);

      if(i < skip) continue;
      if(g_reportStart > 0 && dt < g_reportStart) continue;

      r_dt[r_head]    = dt;
      r_bal[r_head]   = bal;
      r_eq[r_head]    = eq;
      r_marg[r_head]  = mg;
      r_fmarg[r_head] = fm;
      r_float[r_head] = fl;
      r_head++;
      if(r_head >= MAX_REC) r_head = 0;
      r_count++;
   }
   FileClose(fh);
   Print("TD records hydrated from bin: ", r_count);
}

void LoadRecords()
{
   r_count = 0;
   r_head = 0;

   int fh = FileOpen(TD_F_records(), FILE_READ|FILE_CSV|FILE_ANSI, ',');   // v1.53 FIX-TD5
   if(fh == INVALID_HANDLE) return;

   int cap = MathMin(InpMaxRecords, MAX_REC);

   while(!FileIsEnding(fh) && r_count < cap)
   {
      string s0 = FileReadString(fh);
      if(s0 == "") break;

      datetime recDt = (datetime)StringToInteger(s0);

      // Apply ReportStart filter
      if(g_reportStart > 0 && recDt < g_reportStart)
      {
         FileReadString(fh); // skip time string
         FileReadString(fh); // skip bal
         FileReadString(fh); // skip eq
         FileReadString(fh); // skip marg
         FileReadString(fh); // skip fmarg
         FileReadString(fh); // skip float
         continue;
      }

      r_dt[r_head]    = recDt;
      FileReadString(fh);
      r_bal[r_head]   = StringToDouble(FileReadString(fh));
      r_eq[r_head]    = StringToDouble(FileReadString(fh));
      r_marg[r_head]  = StringToDouble(FileReadString(fh));
      r_fmarg[r_head] = StringToDouble(FileReadString(fh));
      r_float[r_head] = StringToDouble(FileReadString(fh));
      r_head++;
      if(r_head >= MAX_REC) r_head = 0;
      r_count++;
   }
   FileClose(fh);
   Print("TD records loaded: ", r_count);
}

//+------------------------------------------------------------------+
//| Query functions                                                  |
//+------------------------------------------------------------------+
double GetRecMargin(datetime from, datetime to)
{
   double mx = 0;
   for(int i = 0; i < r_count; i++)
   {
      int idx = (r_head - r_count + i + MAX_REC) % MAX_REC;
      if(r_dt[idx] >= from && r_dt[idx] < to)
         if(r_marg[idx] > mx) mx = r_marg[idx];
   }
   return mx;
}

double GetRecFreeMargin(datetime from, datetime to)
{
   double mn = 999999999;
   bool found = false;
   for(int i = 0; i < r_count; i++)
   {
      int idx = (r_head - r_count + i + MAX_REC) % MAX_REC;
      if(r_dt[idx] >= from && r_dt[idx] < to)
      {
         if(r_fmarg[idx] < mn) mn = r_fmarg[idx];
         found = true;
      }
   }
   return found ? mn : 0;
}

double GetRecFloatMaxPos(datetime from, datetime to)
{
   double maxPos = 0;
   for(int i = 0; i < r_count; i++)
   {
      int idx = (r_head - r_count + i + MAX_REC) % MAX_REC;
      if(r_dt[idx] >= from && r_dt[idx] < to)
      {
         if(r_float[idx] > maxPos) maxPos = r_float[idx];
      }
   }
   return maxPos;
}

double GetRecFloatMaxNeg(datetime from, datetime to)
{
   double maxNeg = 0;
   for(int i = 0; i < r_count; i++)
   {
      int idx = (r_head - r_count + i + MAX_REC) % MAX_REC;
      if(r_dt[idx] >= from && r_dt[idx] < to)
      {
         if(r_float[idx] < maxNeg) maxNeg = r_float[idx];
      }
   }
   return maxNeg;
}

void GetRecMaxDD(datetime from, datetime to, double &ddAmt, double &ddPct)
{
   ddAmt = 0;
   ddPct = 0;
   double peak = -999999999;
   for(int i = 0; i < r_count; i++)
   {
      int idx = (r_head - r_count + i + MAX_REC) % MAX_REC;
      if(r_dt[idx] >= from && r_dt[idx] < to)
      {
         if(r_eq[idx] > peak) peak = r_eq[idx];
         double dd = peak - r_eq[idx];
         if(dd > ddAmt)
         {
            ddAmt = dd;
            ddPct = (peak > 0.01) ? dd / peak * 100.0 : 0;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| v1.43 spec #15: REALIZED max drawdown — closed-trade PnL curve    |
//| peak-to-trough inside the window, starting from window balance.   |
//| Distinct from GetRecMaxDD (intraday floating, ring-buffer based). |
//+------------------------------------------------------------------+
void GetRealizedMaxDD(datetime from, datetime to, double startBal, double &ddAmt, double &ddPct)
{
   datetime ctArr[MAX_TRADES] = {0}; double pnlArr[MAX_TRADES] = {0};   // v1.55 FIX-TD6 (0925 spec item 4): was literal 5000 - realized MaxDD silently truncated at 5000 rows
   int n = 0;
   for(int i = 0; i < t_tradeCount && n < MAX_TRADES; i++)
   {
      if(t_closetime[i] == 0 || t_closetime[i] < from || t_closetime[i] >= to) continue;
      if(!PassesFilter(i)) continue;
      ctArr[n] = t_closetime[i]; pnlArr[n] = t_calcPnl[i]; n++;
   }
   // insertion sort by close time (trades not guaranteed chronological)
   for(int a = 1; a < n; a++)
   {
      datetime kt = ctArr[a]; double kp = pnlArr[a];
      int b = a - 1;
      while(b >= 0 && ctArr[b] > kt){ ctArr[b+1] = ctArr[b]; pnlArr[b+1] = pnlArr[b]; b--; }
      ctArr[b+1] = kt; pnlArr[b+1] = kp;
   }
   ddAmt = 0; ddPct = 0;
   if(n == 0) return;
   double bal = startBal, peak = startBal;
   for(int k = 0; k < n; k++)
   {
      bal += pnlArr[k];
      if(bal > peak) peak = bal;
      double dd = peak - bal;
      if(dd > ddAmt){ ddAmt = dd; ddPct = (peak > 0.01) ? dd/peak*100.0 : 0; }
   }
}

//+------------------------------------------------------------------+
//| Dump Summary CSV                                                 |
//+------------------------------------------------------------------+
void DumpSummaryCSV()
{
   int fh = FileOpen(TD_F_summary(), FILE_WRITE|FILE_CSV|FILE_ANSI, ',');   // v1.53 FIX-TD5: TD_<acct>_summary.csv
   if(fh == INVALID_HANDLE) return;

   FileWrite(fh, "View","Period","Trades","Buy","Sell","WR%","Gain$","Gain%",
             "WPips","Lot","TotalLot","Balance","Margin","FreeMarg",
             "MaxP","MaxDD$","MaxDD%",
             "PF","AvgP&L","Best","Worst");

   string viewNames[4]; viewNames[0]="Time"; viewNames[1]="Date"; viewNames[2]="Week"; viewNames[3]="Month";

   datetime now = TimeCurrent();

   for(int v = 0; v < 4; v++)
   {
      // v1.22: same bucket logic as screen (aligned + offset-aware)
      datetime bnd[32];
      int nB = 0;
      BuildBuckets(v, g_offset, now, bnd, nB);

      double runLots = 0;
      double prevBal = CalcWindowStartBalance(bnd[0]);

      for(int b = 0; b < nB; b++)
      {
         datetime bS = bnd[b];
         datetime bE = bnd[b+1];
         if(bS >= now) break;
         if(bE > now) bE = now;

         int bn=0, bw=0, bBuy=0, bSell=0;
         double bpnl=0, bpips=0, blots=0;
         double gW=0, gL=0;
         double bestT=0, worstT=0;
         bool first=true;

         for(int i = 0; i < t_tradeCount; i++)
         {
            datetime ct = t_closetime[i];
            if(ct == 0 || ct < bS || ct >= bE) continue;
            if(!PassesFilter(i)) continue;

            bn++;
            double p = t_calcPnl[i];
            bpnl += p;
            blots += t_lots[i];

            if(t_type[i] == OP_BUY) bBuy++; else bSell++;
            if(p > 0) { bw++; gW += p; } else gL += MathAbs(p);

            if(first) { bestT = p; worstT = p; first = false; }
            else { if(p > bestT) bestT = p; if(p < worstT) worstT = p; }

            string sym = t_symbol[i];
            double pt = MarketInfo(sym, MODE_POINT);
            if(pt < 0.0000001) pt = 0.0001;
            int digits = (int)MarketInfo(sym, MODE_DIGITS);
            double pv = (digits == 5 || digits == 3) ? pt*10 : pt;
            if(pv < 0.0000001) pv = 0.0001;

            double pips = (t_closeprice[i] - t_openprice[i]) / pv;
            if(t_type[i] == OP_SELL) pips = -pips;
            bpips += pips;
         }

         if(bn > 0)
         {
            runLots += blots;
            double bwr = 100.0 * bw / bn;
            double gpct = (prevBal > 0.01) ? bpnl/prevBal*100.0 : 0;
            double pf = (gL > 0.01) ? gW/gL : (gW > 0 ? 99.99 : 0.0);   // spec: all-win => 99.99
            double avgp = bpnl / bn;

            double ddAmt, ddPct;
            GetRealizedMaxDD(bS, bE, prevBal, ddAmt, ddPct);
            double recMarg = GetRecMargin(bS, bE);
            double recFMarg = GetRecFreeMargin(bS, bE);
            double recFPos = GetRecFloatMaxPos(bS, bE);

            string periodStr = (v==0) ? TimeToString(bS, TIME_MINUTES)
                                      : TimeToString(bS, TIME_DATE);

            FileWrite(fh,
               viewNames[v],
               periodStr,
               bn, bBuy, bSell,
               DoubleToString(bwr, 1),
               DoubleToString(bpnl, 2),
               DoubleToString(gpct, 2),
               DoubleToString(bpips, 0),
               DoubleToString(blots, 2),
               DoubleToString(runLots, 2),
               DoubleToString(prevBal + bpnl, 2),
               DoubleToString(recMarg, 2),
               DoubleToString(recFMarg, 2),
               DoubleToString(recFPos, 2),
               DoubleToString(ddAmt, 2),
               DoubleToString(ddPct, 2),
               DoubleToString(pf, 2),
               DoubleToString(avgp, 2),
               DoubleToString(bestT, 2),
               DoubleToString(worstT, 2)
            );

            prevBal += bpnl;
         }
      }
   }

   FileClose(fh);
}

//+------------------------------------------------------------------+
//| DumpSymbolSpecs                                                  |
//+------------------------------------------------------------------+
void DumpSymbolSpecs()
{
   string symbols[] = {"XAUUSD", "XAUUSD.", "BTCUSD", "NAS100", "NAS100.r",
                       "HK50", "HK50.r", "JPN225", "JPN225ft",
                       "GER40", "GER40.r", "UK100", "UK100.r",
                       "EU50", "EU50.r", "SP500", "SP500.r", "DJ30", "DJ30.r"};

   int fh = FileOpen("symbol_specs.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) return;

   FileWrite(fh, "Symbol", "Digits", "Point", "ContractSize", "TickSize", "TickValue",
             "Spread", "Bid", "Ask");

   for(int s = 0; s < ArraySize(symbols); s++)
   {
      string sym = symbols[s];
      double pt = MarketInfo(sym, MODE_POINT);
      int dg = (int)MarketInfo(sym, MODE_DIGITS);
      double cs = MarketInfo(sym, MODE_LOTSIZE);
      double ts = MarketInfo(sym, MODE_TICKSIZE);
      double tv = MarketInfo(sym, MODE_TICKVALUE);
      double sp = MarketInfo(sym, MODE_SPREAD);
      double bid = MarketInfo(sym, MODE_BID);
      double ask = MarketInfo(sym, MODE_ASK);

      if(bid > 0 || ask > 0)
      {
         FileWrite(fh, sym, dg,
            DoubleToString(pt, 8),
            DoubleToString(cs, 2),
            DoubleToString(ts, 8),
            DoubleToString(tv, 8),
            DoubleToString(sp, 0),
            DoubleToString(bid, dg),
            DoubleToString(ask, dg));
      }
   }
   FileClose(fh);
}

//+------------------------------------------------------------------+
//| v1.22 IsoWeekNumber - proper ISO week for Monday-aligned buckets |
//+------------------------------------------------------------------+
int IsoWeekNumber(datetime t)
{
   MqlDateTime tm; TimeToStruct(t, tm);
   int dow = (tm.day_of_week==0) ? 7 : tm.day_of_week;   // Mon=1..Sun=7
   datetime thu = t + (4 - dow)*86400;                   // Thursday rule
   MqlDateTime tt; TimeToStruct(thu, tt);
   return (tt.day_of_year + 6) / 7;
}

//+------------------------------------------------------------------+
//| v1.22 BuildBuckets - calendar-aligned buckets, whole-window pages|
//| view: 0=Hour 1=Day 2=Week 3=Month                                |
//| Fills bnd[0..nB] (nB buckets, bucket i = [bnd[i], bnd[i+1]))     |
//+------------------------------------------------------------------+
void BuildBuckets(const int view, const int pageOff, const datetime now, datetime &bnd[], int &nB)
{
   MqlDateTime tm; TimeToStruct(now, tm);
   tm.hour=0; tm.min=0; tm.sec=0;
   datetime today0 = StructToTime(tm);
   nB = 0;

   if(view==0)            // Hour: from today 00:00, page = 24h
   {
      datetime s = today0 + pageOff*86400;
      for(int i=0; i<=24; i++) bnd[i] = s + i*3600;
      nB = 24;
   }
   else if(view==1)       // Day: from this week's Monday, page = 7 days
   {
      int d2m = (tm.day_of_week==0) ? 6 : (tm.day_of_week-1);
      datetime s = today0 - d2m*86400 + pageOff*7*86400;
      for(int i=0; i<=7; i++) bnd[i] = s + i*86400;
      nB = 7;
   }
   else if(view==2)       // Week: Monday-aligned 7-day weeks, page = 6 weeks
   {
      int d2m = (tm.day_of_week==0) ? 6 : (tm.day_of_week-1);
      datetime s = today0 - d2m*86400 - 5*604800 + pageOff*6*604800;
      for(int i=0; i<=6; i++) bnd[i] = s + i*604800;
      nB = 6;
   }
   else                   // Month: calendar months, page = 12 months
   {
      int cur = tm.year*12 + (tm.mon-1);
      int st  = cur + pageOff*12 - 11;
      for(int i=0; i<=12; i++)
      {
         int a = st + i;
         MqlDateTime b = tm;
         b.year = a/12;
         b.mon  = a%12 + 1;
         b.day  = 1;
         bnd[i] = StructToTime(b);
      }
      nB = 12;
   }

   // Clamp: drop whole buckets older than 1yr / ReportStart
   datetime minDt = now - 31536000;
   if(g_reportStart > 0 && g_reportStart > minDt) minDt = g_reportStart;
   int drop = 0;
   while((nB - drop) > 1 && bnd[drop+1] <= minDt) drop++;
   if(drop > 0)
   {
      for(int i=0; i <= (nB - drop); i++) bnd[i] = bnd[i+drop];
      nB -= drop;
   }
   if(bnd[0] < minDt) bnd[0] = minDt;
}

//+------------------------------------------------------------------+
//| v1.22 CalcWindowStartBalance - balance at window start           |
//| record-based if available, else current minus post-window PnL     |
//+------------------------------------------------------------------+
double CalcWindowStartBalance(const datetime startDt)
{
   double prevBal;
   if(r_count > 0)
   {
      int closestIdx = -1;
      datetime minDiff = 31536000;
      for(int i = 0; i < r_count; i++)
      {
         int idx = (r_head - r_count + i + MAX_REC) % MAX_REC;
         datetime diff = MathAbs(r_dt[idx] - startDt);
         if(diff < minDiff)
         {
            minDiff = diff;
            closestIdx = idx;
         }
      }
      if(closestIdx >= 0)
      {
         if(r_dt[closestIdx] <= startDt) {
            prevBal = r_bal[closestIdx];
            for(int i = 0; i < t_tradeCount; i++)
            {
               if(t_closetime[i] == 0) continue;
               if(t_closetime[i] <= r_dt[closestIdx] || t_closetime[i] >= startDt) continue;
               if(!PassesFilter(i)) continue;
               prevBal += t_calcPnl[i];
            }
         }
         else {
            prevBal = r_bal[closestIdx];
            for(int i = 0; i < t_tradeCount; i++)
            {
               if(t_closetime[i] == 0) continue;
               if(t_closetime[i] < startDt || t_closetime[i] >= r_dt[closestIdx]) continue;
               if(!PassesFilter(i)) continue;
               prevBal -= t_calcPnl[i];
            }
         }
      }
      else
      {
         prevBal = AccountBalance();
         double totalPnl = 0;
         for(int i = 0; i < t_tradeCount; i++)
         {
            if(t_closetime[i] == 0 || t_closetime[i] < startDt) continue;
            if(!PassesFilter(i)) continue;
            totalPnl += t_calcPnl[i];
         }
         prevBal -= totalPnl;
      }
   }
   else
   {
      prevBal = AccountBalance();
      double totalPnl = 0;
      for(int i = 0; i < t_tradeCount; i++)
      {
         if(t_closetime[i] == 0 || t_closetime[i] < startDt) continue;
         if(!PassesFilter(i)) continue;
         totalPnl += t_calcPnl[i];
      }
      prevBal -= totalPnl;
   }
   return prevBal;
}

//+------------------------------------------------------------------+
//| CollectData                                                      |
//+------------------------------------------------------------------+
void CollectData()
{
   datetime now = TimeCurrent();

   // v1.22: calendar-aligned buckets + whole-window paging
   datetime bnd[32];
   int nB = 0;
   BuildBuckets(g_view, g_offset, now, bnd, nB);

   g_cNumB = 0;
   double runLots = 0;
   double prevBal = CalcWindowStartBalance(bnd[0]);

   for(int b = 0; b < nB; b++)
   {
      datetime bS = bnd[b];
      datetime bE = bnd[b+1];
      if(bS >= now) break;
      if(bE > now) bE = now;

      int bn=0, bw=0, bBuy=0, bSell=0;
      double bpnl=0, bpips=0, blots=0;
      double gW=0, gL=0;
      double bestT=0, worstT=0;
      bool first=true;

      for(int i = 0; i < t_tradeCount; i++)
      {
         datetime ct = t_closetime[i];
         if(ct == 0 || ct < bS || ct >= bE) continue;
         if(!PassesFilter(i)) continue;

         bn++;
         double p = t_calcPnl[i];
         bpnl += p;
         blots += t_lots[i];

         if(t_type[i] == OP_BUY) bBuy++; else bSell++;

         if(p > 0) { bw++; gW += p; } else gL += MathAbs(p);

         if(first) { bestT = p; worstT = p; first = false; }
         else { if(p > bestT) bestT = p; if(p < worstT) worstT = p; }

         string sym = t_symbol[i];
         double pt = MarketInfo(sym, MODE_POINT);
         if(pt < 0.0000001) pt = 0.0001;
         int digits = (int)MarketInfo(sym, MODE_DIGITS);
         double pv = (digits == 5 || digits == 3) ? pt*10 : pt;
         if(pv < 0.0000001) pv = 0.0001;

         double pips = (t_closeprice[i] - t_openprice[i]) / pv;
         if(t_type[i] == OP_SELL) pips = -pips;
         bpips += pips;
      }

      // v1.48: always materialise the bucket. Previously a zero-trade hour/day
      // was skipped entirely, so the H/D tabs showed an almost empty table and
      // looked broken (boss 2026-10-29). A zero row is information: "no closed
      // trades in this window", and it keeps the time axis continuous.
      if(true)
      {
         g_cDt[g_cNumB]    = bS;
         g_cN[g_cNumB]     = bn;
         g_cBuy[g_cNumB]   = bBuy;
         g_cSell[g_cNumB]  = bSell;
         g_cW[g_cNumB]     = bw;
         g_cPnl[g_cNumB]   = bpnl;
         g_cPips[g_cNumB]  = bpips;
         g_cLots[g_cNumB]  = blots;
         runLots += blots;
         g_cTLots[g_cNumB] = runLots;
         g_cGPct[g_cNumB]  = (prevBal > 0.01) ? bpnl/prevBal*100.0 : 0;
         g_cPF[g_cNumB]    = (gL > 0.01) ? gW/gL : (gW > 0 ? 99.0 : 0);
         g_cAvgP[g_cNumB]  = (bn > 0) ? bpnl/bn : 0;
         prevBal += bpnl;
         g_cBal[g_cNumB]   = prevBal;
         g_cBest[g_cNumB]  = bestT;
         g_cWorst[g_cNumB] = worstT;

         g_cMarg[g_cNumB]  = GetRecMargin(bS, bE);
         g_cFMarg[g_cNumB] = GetRecFreeMargin(bS, bE);
         g_cFMaxPos[g_cNumB] = GetRecFloatMaxPos(bS, bE);
         g_cFMaxNeg[g_cNumB] = GetRecFloatMaxNeg(bS, bE);

         double ddAmt, ddPct;
         GetRealizedMaxDD(bS, bE, prevBal, ddAmt, ddPct);
         g_cMaxDD[g_cNumB]    = ddAmt;
         g_cMaxDDPct[g_cNumB] = ddPct;

         g_cNumB++;
      }
   }

   // Update latest bucket with real-time values
   if(g_cNumB > 0 && g_offset == 0)
   {
      double curFl = GetCurFloat();
      if(curFl > g_cFMaxPos[g_cNumB-1]) g_cFMaxPos[g_cNumB-1] = curFl;
      if(curFl < g_cFMaxNeg[g_cNumB-1]) g_cFMaxNeg[g_cNumB-1] = curFl;

      g_cMarg[g_cNumB-1]  = AccountMargin();
      g_cFMarg[g_cNumB-1] = AccountFreeMargin();
   }

   DumpSummaryCSV();
}

//+------------------------------------------------------------------+
//| HideChartBars                                                    |
//+------------------------------------------------------------------+
void HideChartBars()
{
   for(int i = 0; i < 30; i++)
      HideObj("CBAR_"+IntegerToString(i));
   HideObj("CZERO");
   HideObj("CLBL");
}

//+------------------------------------------------------------------+
//| DrawChartArea — draw cumulative P&L bars                         |
//+------------------------------------------------------------------+
void DrawChartArea(int px, int py, int w, int h, int scale)
{
   HideChartBars();

   if(g_cNumB < 1) return;

   UpdTxt("CLBL", "Cumulative P&L", px+5, py, clrWhite, 7*scale);

   // Calculate cumulative P&L per bucket
   double cumArr[30];
   ArrayInitialize(cumArr, 0);
   double cumPnl = 0;
   double minP = 0, maxP = 0;

   for(int i = 0; i < g_cNumB; i++)
   {
      cumPnl += g_cPnl[i];
      cumArr[i] = cumPnl;
      if(i == 0) { minP = cumPnl; maxP = cumPnl; }
      else {
         if(cumPnl < minP) minP = cumPnl;
         if(cumPnl > maxP) maxP = cumPnl;
      }
   }

   if(minP > 0) minP = 0;
   if(maxP < 0) maxP = 0;

   double range = maxP - minP;
   if(range < 0.01) range = 1;

   int innerY = py + 12 * scale;
   int innerH = h - 14 * scale;
   if(innerH < 10) innerH = 10;

   int zeroY = innerY + innerH - (int)((0 - minP) / range * innerH);

   // Zero line
   UpdRect("CZERO", px+2, zeroY, w-4, 1, C'60,70,100', C'60,70,100');

   // Bars
   int availW = w - 8;
   int barW = availW / g_cNumB;
   if(barW < 3) barW = 3;

   for(int i = 0; i < g_cNumB; i++)
   {
      int barX = px + 4 + i * barW;
      double val = cumArr[i];
      int barH = (int)(MathAbs(val) / range * innerH);
      if(barH < 1) barH = 1;

      int barY;
      if(val >= 0)
         barY = zeroY - barH;
      else
         barY = zeroY;

      color bColor = (val >= 0) ? C'30,200,100' : C'220,70,70';
      UpdRect("CBAR_"+IntegerToString(i), barX, barY, barW-1, barH, bColor, bColor);
   }
}

//+------------------------------------------------------------------+
//| RenderOnly                                                       |
//+------------------------------------------------------------------+
double TD_NZ0(double x) { return (MathAbs(x)<0.005) ? 0.0 : x; }   // v1.52 FIX-TD3: -0.00 display fix

void RenderOnly()
{
   int scale = MathMax(1, MathMin(3, InpPanelScale));
   int px = 10;
   int py = 18;
   int padR = 15;

   string vn[4]; vn[0]="Hour"; vn[1]="Day"; vn[2]="Week"; vn[3]="Month";
   string viewLabel = (g_offset==0) ? vn[g_view]+" (Latest)" : StringFormat("%s %+d", vn[g_view], g_offset);

   double tPnl=0;
   int tN=0, tW=0;
   for(int i=0; i<g_cNumB; i++)
   {
      tPnl+=g_cPnl[i];
      tN+=g_cN[i]; tW+=g_cW[i];
   }
   double tWR=(tN>0) ? 100.0*tW/tN : 0;

   // v1.52 FIX-TD3: all-time stats from local snapshot (view/filter independent,
   // same accounting as buckets: pnl = t_calcPnl, win = calcPnl > 0; matches CSV audit gate)
   int aN=0, aBuy=0, aSell=0, aW=0;
   double aPnl=0;
   datetime aLast=0;
   for(int ai=0; ai<t_tradeCount; ai++)
   {
      aN++; aPnl+=t_calcPnl[ai];
      if(t_type[ai]==OP_BUY) aBuy++; else aSell++;
      if(t_calcPnl[ai]>0) aW++;
      if(t_closetime[ai]>aLast) aLast=t_closetime[ai];
   }
   double aWR=(aN>0) ? 100.0*aW/aN : 0;

   int colX[NC];
   ArrayInitialize(colX, 0);
   int curX=px+10;
   for(int c=0; c<NC; c++)
   {
      colX[c]=curX;
      if(g_vis[c]) curX+=g_wid[c]*scale;
   }
   int tableW=curX-px-10+padR;
   int panelW=tableW+30;
   if(panelW<380) panelW=380;
   // v1.60 (1400 §三): Guard tab hosts the inline button column (5x50*scale
   // right of MaxDD$ at x+320) — widen THIS tab only; other tabs unchanged.
   if(g_tab == 2 && panelW < 620*scale) panelW = 620*scale;
   int chartWpx=(int)ChartGetInteger(0,CHART_WIDTH_IN_PIXELS,0);
   if(chartWpx>100 && panelW>chartWpx-20) panelW=chartWpx-20;   // v1.33 clamp

   int fTitle=11*scale, fNorm=9*scale, fSm=8*scale, fTiny=7*scale;
   int rowH=14*scale, headerH=124*scale, btnH=18*scale;

   int maxRows=MathMin(10, g_cNumB);
   if(maxRows<1) maxRows=1;

   int chartH=InpShowPnlChart ? 60*scale : 0;
   int panelH=headerH+chartH+18+maxRows*rowH+40;
   // v1.39: non-Positions tabs need their own height (symbol table can exceed main table rows)
   int tabNeedH = 0;
   if(g_tab != 0)
   {
      tabNeedH = (14 + 17) + 8;                 // header block above content
      if(g_tab == 2)      // DDGuard: account block + col header + 12 rows + tail + DDRESET
      {
         // v1.60 (1400 §三): inline buttons — fixed 12 rows/page; tail = LAST 16
         // + TAM2 note + DDRESET 16 + button 16; old CLOSE BOARD height removed.
         tabNeedH = tabNeedH + 86*scale + 16*scale + 12*15*scale
                  + 16 + 16 + 16 + 16 + 32*scale + 12;
      }
      else if(g_tab == 1) // Alerts: news up to 8 lines *14 + symbol block 8 rows *16 + footer
         tabNeedH = tabNeedH + 8*14*scale + 8*16*scale + 40*scale + 12;
      else                // Set: 4 lines
         tabNeedH = tabNeedH + 70*scale + 12;
      if(tabNeedH > panelH) panelH = tabNeedH;
   }
   // v1.54 FIX-TD4 (0745 item 6): vertical clamp - panel must never fall off
   // the chart bottom; the DDGuard table pages 12 rows/page to fit.
   int chartHpxV = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);
   if(chartHpxV > 100 && panelH > chartHpxV - 30) panelH = chartHpxV - 30;

   // v1.60 (1325): panel base renamed BG->PANELBG so the BG* prefix is
   //   exclusively the CLOSE-board family; ObjectsDeleteAll(0,PFX+"BG")
   //   in HideMainTable/tab-switch becomes the exact family cleanup.
   UpdRect("PANELBG", px, py, panelW, panelH, C'16,21,46', C'40,50,80');

   //--- v1.27: TAB bar ---
   string tabNames[4]; tabNames[0]="Positions"; tabNames[1]="Alerts"; tabNames[2]="DDGuard"; tabNames[3]="Set";
   int tbW=64*scale, tbH=14*scale;
   int tbx=px+panelW-4-(tbW+3)*4, tby=py+2;   // v1.34: tabs top-RIGHT, right-aligned
   for(int t=0;t<4;t++)
   {
      UpdBtn("TAB"+IntegerToString(t), tabNames[t], tbx, tby, tbW, tbH, (g_tab==t));
      if(g_tab==t)
      {
         ObjectSetInteger(0,PFX+"TAB"+IntegerToString(t),OBJPROP_BGCOLOR,C'30,60,140');
         ObjectSetInteger(0,PFX+"TAB"+IntegerToString(t),OBJPROP_COLOR,clrWhite);
      }
      tbx+=tbW+3;
   }
   int tabY=tby+tbH+3;

   //--- v1.27: non-Positions tabs draw own panel and skip main table ---
   if(g_tab != 0)
   {
      int czY=tabY+4, czH=panelH-(czY-py)-8;
      // v1.32: hide main-table objects FIRST, then draw tab content
      // (v1.31 bug: HideMainTable ran AFTER rendering and deleted the fresh tab content)
      // v1.34: TABCZ backdrop must ALSO be drawn AFTER HideMainTable(),
      //        because HideMainTable() deletes TABCZ (it is in its cleanup list)
      HideMainTable();
      TD_ClearTabContent();
      UpdRect("TABCZ", px+6, czY, panelW-12, czH, C'12,16,36', C'40,50,80');
      if(g_tab==1)      { SG_CollectSymbols(); TabRender_Alerts(px+14, czY+6, scale, panelW-28); }
      else if(g_tab==2) { DD_BuildSymbols(); TabRender_DDG(px+14, czY+6, scale, panelW-28); }
      else              TabRender_Set(px+14, czY+6, scale, panelW-28);
      ChartRedraw();
      return;
   }
   TD_ClearTabContent();   // v1.35: prefix cleanup (overlap fix)

   //--- Left side: 5 lines, uniform 16px spacing, all left-aligned at px+4
   int lh = 16*scale;
   int ttlY=py+2+14*scale+4;
   UpdTxtBold("TTL", InpTitleLine1, px+4, ttlY, clrLime, 13*scale);
   if(g_histEmpty) UpdTxt("HISTW", StringFormat("!! TERMINAL HISTORY EMPTY (0 orders) - right-click History -> All History; panel on local snapshot %d trades, last close %s",
      t_tradeCount, (aLast>0 ? TimeToString(aLast, TIME_DATE|TIME_MINUTES) : "n/a")),
      px+170*scale, ttlY, clrOrangeRed, 8*scale);   // v1.52 FIX-TD3: snapshot vs terminal timestamps visible
   else if(g_histTruncated) UpdTxt("HISTW", "HIST truncated! Switch to All History", px+170*scale, ttlY, clrOrangeRed, 8*scale);
   else
   {
      ObjectDelete(0,PFX+"HISTW");
      //--- v1.55 FIX-TD6 (0925 spec item 6): sync heartbeat line - a frozen
      //---   sync is now visible at a glance instead of dying silently.
      UpdTxt("SYNCLN", StringFormat("SYNC: last ok %s / new %d / hist %d%s",
         (g_syncLastOk > 0 ? TimeToString(g_syncLastOk, TIME_MINUTES) : "never"),
         g_syncNew, g_syncHist, (g_syncCap ? " / CAP HIT" : "")),
         px+170*scale, ttlY, (g_syncCap ? clrOrangeRed : clrSilver), 8*scale);
   }
   UpdTxtBold("SUB", InpTitleLine2, px+4, ttlY+lh, clrLime, 10*scale);
   int acY = ttlY+lh*2;
   UpdTxt("AC1", StringFormat("AC: %d  |  Balance: $%.2f  |  Equity: $%.2f",
      AccountNumber(), TD_NZ0(AccountBalance()), AccountEquity()),
      px+4, acY, clrWhite, fNorm);
   UpdTxt("AC2", StringFormat("Free Margin: $%.2f  |  Margin: $%.2f  |  Snap: %d trades",
      AccountFreeMargin(), AccountMargin(), t_tradeCount),
      px+4, acY+lh, clrWhite, fNorm);
   int spY = acY+lh*2;
   color pClr=(tPnl>=0) ? clrLimeGreen : clrTomato;
   // v1.52 FIX-TD3: row 1 = current view window (WR shows n/a when window has no closed trades)
   UpdTxt("S_P", StringFormat("VIEW: %s | %d %s | P&L: $%+.2f | WR: %s",
      viewLabel, tN, (tN==1 ? "trade" : "trades"), tPnl, (tN>0 ? DoubleToStr(tWR,1)+"%" : "n/a")),
      px+4, spY, pClr, fNorm);
   // v1.52 FIX-TD3: row 2 = all-time snapshot line, kills the "Snap 70 but P&L 0.00" contradiction
   color aClr=(aPnl>=0) ? clrLimeGreen : clrTomato;
   UpdTxt("S_ALL", StringFormat("ALL: %d trades | P&L: $%+.2f | WR: %.1f%% | B%d/S%d | Last close: %s",
      aN, aPnl, aWR, aBuy, aSell, (aLast>0 ? TimeToString(aLast, TIME_DATE|TIME_MINUTES) : "n/a")),
      px+4, spY+lh, aClr, fNorm);

   //--- Right side: H/D/W/M buttons + Symbol/Comment filter
   int btnY=acY;
   int btnW=48*scale;
   int bx=px+tableW-235*scale;
   UpdBtn("V_H","H",  bx,           btnY, btnW, btnH, (g_view==0));
   UpdBtn("V_D","D",  bx+48*scale,  btnY, btnW, btnH, (g_view==1));
   UpdBtn("V_W","W",  bx+96*scale,  btnY, btnW, btnH, (g_view==2));
   UpdBtn("V_M","M",  bx+144*scale, btnY, btnW, btnH, (g_view==3));
   UpdBtn("NAV_L","<", bx+192*scale, btnY, 18*scale, btnH, false);
   UpdBtn("NAV_R",">", bx+210*scale, btnY, 18*scale, btnH, false);

   int fY = btnY + btnH + 4*scale;
   UpdTxt("FLBL", "Symbol:", bx, fY, clrWhite, fSm);
   EnsureEdit("FS_EDIT", g_filterSymbol, bx+42*scale, fY-2, 90*scale, 16*scale);
   UpdTxt("CLBL2", "Comment:", bx+140*scale, fY, clrWhite, fSm);
   EnsureEdit("FC_EDIT", g_filterComment, bx+190*scale, fY-2, 70*scale, 16*scale);

   //--- SAVE PROFILE button (row below Symbol/Comment filter) v1.16
   int sY2 = fY + 18*scale;
   bool saveFlash = (TimeLocal() < g_saveBtnFlashUntil);
   UpdBtn("SAVE","SAVE", bx, sY2, 56*scale, btnH, saveFlash);
   if(saveFlash)
   {
      ObjectSetInteger(0, PFX+"SAVE", OBJPROP_BGCOLOR, clrLime);
      ObjectSetInteger(0, PFX+"SAVE", OBJPROP_COLOR, clrBlack);
   }
   UpdTxt("SAVELBL", "MT4 PROFILE", bx+62*scale, sY2+2, clrKhaki, fSm);

   int yPos=py+headerH;

   // Chart area
   if(InpShowPnlChart)
   {
      DrawChartArea(px+10, yPos, panelW-20, chartH, scale);
      yPos+=chartH;
   }
   else
   {
      HideChartBars();
   }

   UpdRect("DV", px+10, yPos, panelW-20, 1, C'40,50,80', C'40,50,80');
   yPos+=4;

   // Column headers
   for(int c=0; c<NC; c++)
   {
      string nm="H"+IntegerToString(c);
      if(g_vis[c]) UpdTxt(nm, g_name[c], colX[c], yPos, clrWhite, fSm);
      else HideObj(nm);
   }
   yPos+=16*scale;

   // v1.52 FIX-TD3: explicit empty-window notice (boss 2026-11-06 A06E: silent all-zero grid reads as wrong math)
   if(tN==0)
   {
      UpdTxt("EMPTYW", StringFormat("(no closed trades in this window - last close %s)",
         (aLast>0 ? TimeToString(aLast, TIME_DATE|TIME_MINUTES) : "n/a")),
         colX[0], yPos, clrKhaki, fSm);
      yPos+=rowH;
   }
   else HideObj("EMPTYW");

   // Data rows
   for(int r=0; r<10; r++)
   {
      int idx=g_cNumB-1-r;
      int ry=yPos+r*rowH;
      string pp="D"+IntegerToString(r);

      if(idx < 0)
      {
         for(int c=0; c<NC; c++) HideObj(pp+"_"+IntegerToString(c));
         continue;
      }

      double bwr=(g_cN[idx]>0) ? 100.0*g_cW[idx]/g_cN[idx] : 0;
      color cPnl=(g_cPnl[idx]>=0)?clrLimeGreen:clrTomato;
      color cWR=(bwr>=50)?clrLimeGreen:clrTomato;
      color cGP=(g_cGPct[idx]>=0)?clrLimeGreen:clrTomato;
      color cAvg=(g_cAvgP[idx]>=0)?clrLimeGreen:clrTomato;
      color cB=(g_cBest[idx]>=0)?clrLimeGreen:clrTomato;
      color cW=(g_cWorst[idx]>=0)?clrLimeGreen:clrTomato;
      color cFMP=(g_cFMaxPos[idx]>0)?clrLimeGreen:clrWhite;
      color cFMN=(g_cFMaxNeg[idx]<0)?clrTomato:clrWhite;
      color cDD=(g_cMaxDD[idx]>0)?clrTomato:clrWhite;
      color cDDP=(g_cMaxDDPct[idx]>0)?clrTomato:clrWhite;

      string tStr;
      if(g_view==0) tStr=TimeToString(g_cDt[idx],TIME_MINUTES);
      else if(g_view==1) tStr=TimeToString(g_cDt[idx],TIME_DATE);
      else if(g_view==2) {
         tStr="W"+IntegerToString(IsoWeekNumber(g_cDt[idx]))+" ("+TimeToString(g_cDt[idx],TIME_DATE)+")";
      }
      else {
         MqlDateTime tm;
         TimeToStruct(g_cDt[idx], tm);
         string months[]={"Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"};
         tStr=months[tm.mon-1]+" "+IntegerToString(tm.year);
      }

      string bsStr = StringFormat("%d/%d", g_cBuy[idx], g_cSell[idx]);

      UpdCell(pp+"_0",  tStr, colX[0], ry, clrWhite, fSm, g_vis[0]);
      UpdCell(pp+"_1",  IntegerToString(g_cN[idx]), colX[1], ry, clrWhite, fSm, g_vis[1]);
      UpdCell(pp+"_2",  bsStr, colX[2], ry, clrDeepSkyBlue, fSm, g_vis[2]);
      UpdCell(pp+"_3",  DoubleToStr(bwr,0)+"%", colX[3], ry, cWR, fSm, g_vis[3]);
      UpdCell(pp+"_4",  "$"+DoubleToStr(TD_NZ0(g_cPnl[idx]),2), colX[4], ry, cPnl, fSm, g_vis[4]);
      UpdCell(pp+"_5",  StringFormat("%.2f%%",g_cGPct[idx]), colX[5], ry, cGP, fSm, g_vis[5]);
      UpdCell(pp+"_6",  DoubleToStr(g_cPips[idx],0), colX[6], ry, clrWhite, fSm, g_vis[6]);
      UpdCell(pp+"_7",  DoubleToStr(g_cLots[idx],2), colX[7], ry, clrWhite, fSm, g_vis[7]);
      UpdCell(pp+"_8",  DoubleToStr(g_cTLots[idx],2), colX[8], ry, clrWhite, fSm, g_vis[8]);
      UpdCell(pp+"_9",  "$"+DoubleToStr(TD_NZ0(g_cBal[idx]),2), colX[9], ry, clrWhite, fSm, g_vis[9]);
      UpdCell(pp+"_10", (g_cMarg[idx]>0?"$"+DoubleToStr(g_cMarg[idx],2):"-"), colX[10], ry, clrWhite, fSm, g_vis[10]);
      UpdCell(pp+"_11", (g_cFMarg[idx]>0?"$"+DoubleToStr(g_cFMarg[idx],2):"-"), colX[11], ry, clrWhite, fSm, g_vis[11]);
      UpdCell(pp+"_12", (g_cFMaxPos[idx]>0?"$"+DoubleToStr(g_cFMaxPos[idx],2):"-"), colX[12], ry, cFMP, fSm, g_vis[12]);
      UpdCell(pp+"_13", (g_cFMaxNeg[idx]<0?"$"+DoubleToStr(g_cFMaxNeg[idx],2):"-"), colX[13], ry, cFMN, fSm, g_vis[13]);
      UpdCell(pp+"_14", DoubleToStr(g_cPF[idx],2), colX[14], ry, clrWhite, fSm, g_vis[14]);
      UpdCell(pp+"_15", "$"+DoubleToStr(g_cAvgP[idx],2), colX[15], ry, cAvg, fSm, g_vis[15]);
      UpdCell(pp+"_16", "$"+DoubleToStr(g_cBest[idx],2), colX[16], ry, cB, fSm, g_vis[16]);
      UpdCell(pp+"_17", "$"+DoubleToStr(g_cWorst[idx],2), colX[17], ry, cW, fSm, g_vis[17]);
      UpdCell(pp+"_18", (g_cMaxDD[idx]>0?"$"+DoubleToStr(g_cMaxDD[idx],2):"$0.00"), colX[18], ry, cDD, fSm, g_vis[18]);
      UpdCell(pp+"_19", (g_cMaxDDPct[idx]>0?DoubleToStr(g_cMaxDDPct[idx],1)+"%":"0.0%"), colX[19], ry, cDDP, fSm, g_vis[19]);
   }

   yPos+=maxRows*rowH+5;

   // Footer
   string filterInfo = "";
   if(g_filterSymbol != "" || g_filterComment != "")
      filterInfo = "  |  Filter: " + g_filterSymbol + " / " + g_filterComment;
   if(g_reportStart > 0)
      filterInfo += "  |  From: " + TimeToString(g_reportStart, TIME_DATE);

   UpdTxt("FT", "Updated: "+TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS)+
      "  |  Refresh: "+IntegerToString(InpRefreshSeconds)+"s"+
      "  |  Rec: "+IntegerToString(InpRecordSeconds)+"s ("+IntegerToString(r_count)+" recs)"+
      "  |  Trades: "+IntegerToString(t_tradeCount)+filterInfo,
      px+10, yPos, clrWhite, fTiny);

   yPos+=14*scale;
   SG_Render(px+10, yPos, scale);

   ChartRedraw();
}

//+------------------------------------------------------------------+
//| Object helpers                                                   |
//+------------------------------------------------------------------+
void HideObj(string nm)
{
   string o=PFX+nm;
   if(ObjectFind(0,o)>=0)
      ObjectSetInteger(0,o,OBJPROP_TIMEFRAMES,OBJ_NO_PERIODS);
}

void UpdCell(string nm, string txt, int x, int y, color clr, int sz, bool show)
{
   if(!show) { HideObj(nm); return; }
   string o=PFX+nm;
   if(ObjectFind(0,o)<0) ObjectCreate(0,o,OBJ_LABEL,0,0,0);
   ObjectSetInteger(0,o,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,o,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,o,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,o,OBJPROP_FONTSIZE,sz);
   ObjectSetInteger(0,o,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,o,OBJPROP_SELECTABLE,false);
   ObjectSetString(0,o,OBJPROP_TEXT,txt);
   ObjectSetString(0,o,OBJPROP_FONT,"Arial");
   ObjectSetInteger(0,o,OBJPROP_TIMEFRAMES,OBJ_ALL_PERIODS);
}

void UpdRect(string nm, int x, int y, int w, int h, color bg, color bd)
{
   string o=PFX+nm;
   if(ObjectFind(0,o)<0) ObjectCreate(0,o,OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,o,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,o,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,o,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,o,OBJPROP_XSIZE,w);
   ObjectSetInteger(0,o,OBJPROP_YSIZE,h);
   ObjectSetInteger(0,o,OBJPROP_BGCOLOR,bg);
   ObjectSetInteger(0,o,OBJPROP_COLOR,bd);
   ObjectSetInteger(0,o,OBJPROP_BORDER_TYPE,BORDER_FLAT);
   ObjectSetInteger(0,o,OBJPROP_WIDTH,1);
   ObjectSetInteger(0,o,OBJPROP_BACK,false);
   ObjectSetInteger(0,o,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,o,OBJPROP_TIMEFRAMES,OBJ_ALL_PERIODS);
}

void UpdTxt(string nm, string txt, int x, int y, color clr, int sz)
{
   string o=PFX+nm;
   if(ObjectFind(0,o)<0) ObjectCreate(0,o,OBJ_LABEL,0,0,0);
   ObjectSetInteger(0,o,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,o,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,o,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,o,OBJPROP_FONTSIZE,sz);
   ObjectSetInteger(0,o,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,o,OBJPROP_SELECTABLE,false);
   ObjectSetString(0,o,OBJPROP_TEXT,txt);
   ObjectSetString(0,o,OBJPROP_FONT,"Arial");
   ObjectSetInteger(0,o,OBJPROP_TIMEFRAMES,OBJ_ALL_PERIODS);
}

void UpdTxtBold(string nm, string txt, int x, int y, color clr, int sz)
{
   string o=PFX+nm;
   if(ObjectFind(0,o)<0) ObjectCreate(0,o,OBJ_LABEL,0,0,0);
   ObjectSetInteger(0,o,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,o,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,o,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,o,OBJPROP_FONTSIZE,sz);
   ObjectSetInteger(0,o,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,o,OBJPROP_SELECTABLE,false);
   ObjectSetString(0,o,OBJPROP_TEXT,txt);
   ObjectSetString(0,o,OBJPROP_FONT,"Arial Bold");
   ObjectSetInteger(0,o,OBJPROP_TIMEFRAMES,OBJ_ALL_PERIODS);
}

void UpdBtn(string nm, string txt, int x, int y, int w, int h, bool active)
{
   string o=PFX+nm;
   if(ObjectFind(0,o)<0) ObjectCreate(0,o,OBJ_BUTTON,0,0,0);
   ObjectSetInteger(0,o,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,o,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,o,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,o,OBJPROP_XSIZE,w);
   ObjectSetInteger(0,o,OBJPROP_YSIZE,h);
   ObjectSetInteger(0,o,OBJPROP_BGCOLOR,active?clrDeepSkyBlue:C'26,39,69');
   ObjectSetInteger(0,o,OBJPROP_COLOR,active?clrBlack:clrWhite);
   ObjectSetInteger(0,o,OBJPROP_STATE,active);
   ObjectSetInteger(0,o,OBJPROP_BORDER_TYPE,BORDER_FLAT);
   ObjectSetString(0,o,OBJPROP_TEXT,txt);
   ObjectSetString(0,o,OBJPROP_FONT,"Arial");
   ObjectSetInteger(0,o,OBJPROP_FONTSIZE,9);
   ObjectSetInteger(0,o,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,o,OBJPROP_TIMEFRAMES,OBJ_ALL_PERIODS);
}

void EnsureEdit(string nm, string txt, int x, int y, int w, int h)
{
   string o=PFX+nm;
   if(ObjectFind(0,o)<0) ObjectCreate(0,o,OBJ_EDIT,0,0,0);
   ObjectSetInteger(0,o,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,o,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,o,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,o,OBJPROP_XSIZE,w);
   ObjectSetInteger(0,o,OBJPROP_YSIZE,h);
   ObjectSetInteger(0,o,OBJPROP_FONTSIZE,8);
   ObjectSetInteger(0,o,OBJPROP_COLOR,clrWhite);
   ObjectSetInteger(0,o,OBJPROP_BGCOLOR,C'26,39,69');
   ObjectSetInteger(0,o,OBJPROP_BORDER_TYPE,BORDER_FLAT);
   ObjectSetInteger(0,o,OBJPROP_SELECTABLE,false);
   ObjectSetString(0,o,OBJPROP_FONT,"Arial");
   ObjectSetInteger(0,o,OBJPROP_TIMEFRAMES,OBJ_ALL_PERIODS);
}
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| v1.23 NewsGuard + DDGuard module                                  |
//+------------------------------------------------------------------+
void NGDDG_Init()
{
   if(__ng_init_done) return;
   __ng_init_done = 1;
   TD_CheckHistoryDepth();
   // v1.63 (2010 §三): InpTelegramBotToken non-empty overrides the token file
   if(InpTelegramBotToken != "")
   {
      g_tgToken = InpTelegramBotToken;
      StringTrimLeft(g_tgToken); StringTrimRight(g_tgToken);
   }
   else
   {
      int th = FileOpen(InpTelegramTokenFile, FILE_READ|FILE_TXT|FILE_ANSI);
      if(th != INVALID_HANDLE){ g_tgToken = FileReadString(th); StringTrimLeft(g_tgToken); StringTrimRight(g_tgToken); FileClose(th); }
   }
   // v1.43 T5: strip any stray CR/LF from token file (prevents HTTP 400 in URL)
   StringReplace(g_tgToken, "\r", "");
   StringReplace(g_tgToken, "\n", "");
   // clean stale flags
   for(int v = GlobalVariablesTotal()-1; v >= 0; v--)
   {
      string n = GlobalVariableName(v);
      if(StringFind(n, "NEWSGUARD_") == 0) GlobalVariableDel(n);
   }
   // restore DDG peak equity
   if(GlobalVariableCheck(DDG_PeakKey()))
      g_ddgPeakEquity = GlobalVariableGet(DDG_PeakKey());
   DDG_LoadState();   // v1.47 Q9: restore armed / lock-until / AT-stopped
   // v1.48: seed the runtime switches from the chart inputs; LoadState above
   // already overrode them when a saved GV exists (panel toggle survives restart).
   if(!GlobalVariableCheck(DDG_OnKey()))    g_ddgeOn   = InpDdgEnable;    // default OFF
   if(!GlobalVariableCheck(DDG_AccKey()))   g_ddgAccOn = InpDdgAccountEnable;
   if(!GlobalVariableCheck(DDG_SymOnKey())) g_ddgSymOn = InpDdgSymbolEnable;
}


//+------------------------------------------------------------------+
//| OnChartEvent                                                     |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Filter helper                                                    |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Local Trade Snapshot System                                      |
//+------------------------------------------------------------------+






//+------------------------------------------------------------------+
//| Recording functions (equity snapshots)                           |
//+------------------------------------------------------------------+



//+------------------------------------------------------------------+
//| Query functions                                                  |
//+------------------------------------------------------------------+





//+------------------------------------------------------------------+
//| Dump Summary CSV                                                 |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| DumpSymbolSpecs                                                  |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| CollectData                                                      |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| HideChartBars                                                    |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| DrawChartArea — draw cumulative P&L bars                         |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| RenderOnly                                                       |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Object helpers                                                   |
//+------------------------------------------------------------------+






//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//=== v1.15 GLOBALS ===

//+------------------------------------------------------------------+
//| NewsGuard: news CSV loader                                      |
//| Format: YYYY.MM.DD HH:MM,CCY,NAME,IMPACT(HIGH/MED/LOW)           |
//| v1.43 T7: CSV time is HKT(+8); hot-window tests always use       |
//| TimeGMT()+8h and never the broker server offset (DST-safe).       |
//+------------------------------------------------------------------+
datetime NG_EvTime(string t){ return(StringToTime(t) + InpNewsServerOffsetHours*3600); }   // display/fallback only
datetime NG_EvTimeHKT(string t){ return(StringToTime(t)); }                             // CSV raw time is HKT
datetime NG_NowHKT(){ return(TimeGMT() + 8*3600); }                                     // now in HKT
//--- v1.47 Q9: every persistent key is account-scoped so two accounts sharing
//---           one terminal never inherit each other's risk locks or SG modes.
string   TD_AcctPfx(){ return("TD_"+IntegerToString(AccountNumber())+"_"); }
string   DDG_PeakKey(){ return(TD_AcctPfx()+"DDG_PEAK"); }
string   DDG_OnKey(){ return(TD_AcctPfx()+"DDG_ON"); }
string   DDG_AccKey(){ return(TD_AcctPfx()+"DDG_ACC"); }
string   DDG_SymOnKey(){ return(TD_AcctPfx()+"DDG_SYM"); }
string   DDG_ArmedKey(){ return(TD_AcctPfx()+"DDG_ARMED"); }
string   DDG_LockKey(){ return(TD_AcctPfx()+"DDG_LOCKUNTIL"); }
string   DDG_ATKey(){ return(TD_AcctPfx()+"DDG_ATSTOP"); }
string   DDG_SymLockKey(string s){ return(TD_AcctPfx()+"DDG_SYMLOCK_"+s); }
string   SG_ModeKey(string s){ return(TD_AcctPfx()+"SG_"+s); }
string   SG_AutoKey(string s){ return(TD_AcctPfx()+"SG_AUTO_"+s); }
string   SG_AutoModeKey(string s){ return(TD_AcctPfx()+"SG_AUTOMODE_"+s); }

//--- v1.47 Q6: single DD denominator. Balance is used by the account guard,
//--- the per-symbol guard and the DDGuard tab so all three agree. Balance is
//--- not inflated by floating profit (an equity base would widen the limit).
double   DDG_Base(){ double b = AccountBalance(); if(b <= 0) b = AccountEquity(); if(b <= 0) b = 1.0; return(b); }

//--- v1.47 Q9: risk-lock state survives a terminal restart (GlobalVariables)
void     DDG_SaveState()
{
   GlobalVariableSet(DDG_ArmedKey(), g_ddgAccountArmed ? 1 : 0);
   GlobalVariableSet(DDG_LockKey(), (double)(long)g_ddgLockUntil);
   GlobalVariableSet(DDG_ATKey(), g_tdStoppedAT ? 1 : 0);
   GlobalVariableSet(DDG_OnKey(), g_ddgeOn ? 1 : 0);        // v1.48
   GlobalVariableSet(DDG_AccKey(), g_ddgAccOn ? 1 : 0);     // v1.48
   GlobalVariableSet(DDG_SymOnKey(), g_ddgSymOn ? 1 : 0);   // v1.48
}
void     DDG_LoadState()
{
   if(GlobalVariableCheck(DDG_ArmedKey())) g_ddgAccountArmed = (GlobalVariableGet(DDG_ArmedKey()) > 0.5);
   if(GlobalVariableCheck(DDG_LockKey()))  g_ddgLockUntil   = (datetime)(long)GlobalVariableGet(DDG_LockKey());
   if(GlobalVariableCheck(DDG_ATKey()))    g_tdStoppedAT    = (GlobalVariableGet(DDG_ATKey()) > 0.5);
   // v1.48: restored switches win over the input defaults, so a panel toggle
   // survives a terminal restart. No GV yet = first run, keep the input values.
   if(GlobalVariableCheck(DDG_OnKey()))    g_ddgeOn   = (GlobalVariableGet(DDG_OnKey()) > 0.5);
   if(GlobalVariableCheck(DDG_AccKey()))   g_ddgAccOn = (GlobalVariableGet(DDG_AccKey()) > 0.5);
   if(GlobalVariableCheck(DDG_SymOnKey())) g_ddgSymOn = (GlobalVariableGet(DDG_SymOnKey()) > 0.5);
   if(g_ddgLockUntil > 0 && TimeCurrent() > g_ddgLockUntil) g_ddgLockUntil = 0;
}
bool     DDG_SymLocked(string s)
{
   if(s == "") return(false);
   if(!GlobalVariableCheck(DDG_SymLockKey(s))) return(false);
   return(GlobalVariableGet(DDG_SymLockKey(s)) > 0.5);
}
void     DDG_SetSymLock(string s, bool on)
{
   if(s == "") return;
   GlobalVariableSet(DDG_SymLockKey(s), on ? 1 : 0);
}
void     TD_CheckHistoryDepth()
{
   g_histTruncated = false;
   g_histEmpty = false;   // v1.51 FIX-TD2 BugB
   if(OrdersHistoryTotal() == 0)
   {
      // v1.51 FIX-TD2 BugB (boss 2026-11-06): stats all-zero while
      // TD_summary.csv has real numbers = panel reads terminal history
      // tab, which is EMPTY (MT4 has no API to change the history-tab
      // filter). Loud warning instead of silent zeros.
      g_histEmpty = true;
      Print("TD: ACCOUNT HISTORY EMPTY (OrdersHistoryTotal==0) - right-click Account History tab and choose All History");
      return;
   }
   if(InpReportStart == "") return;
   datetime rs = StringToTime(InpReportStart);
   if(rs <= 0) return;
   datetime earliest = 0;
   for(int i = OrdersHistoryTotal()-1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY)) continue;
      datetime ct = OrderCloseTime();
      if(ct <= 0) continue;
      if(earliest == 0 || ct < earliest) earliest = ct;
   }
   if(earliest == 0 || earliest > rs + 86400)
   {
      g_histTruncated = true;
      Print("TD: history truncated (earliest=", TimeToString(earliest), " vs ReportStart=", InpReportStart, ") - set Account History to All History");
   }
}
void     TD_ClearTabContent()
{
   ObjectsDeleteAll(0, PFX+"TABCZ");
   ObjectsDeleteAll(0, PFX+"TN");  ObjectsDeleteAll(0, PFX+"TA0");
   ObjectsDeleteAll(0, PFX+"TAM"); ObjectsDeleteAll(0, PFX+"TAX");
   ObjectsDeleteAll(0, PFX+"TSY"); ObjectsDeleteAll(0, PFX+"TSG");
   for(int k=0;k<5;k++){ ObjectsDeleteAll(0, PFX+"TD"+IntegerToString(k)); ObjectsDeleteAll(0, PFX+"TS"+IntegerToString(k)); }
   ObjectsDeleteAll(0, PFX+"TDB"); ObjectsDeleteAll(0, PFX+"TDF");
   ObjectsDeleteAll(0, PFX+"TPH"); ObjectsDeleteAll(0, PFX+"DDC");
   ObjectsDeleteAll(0, PFX+"DDN"); ObjectsDeleteAll(0, PFX+"DDB");
   // v1.50 FIX-TD (ghost fix, boss 2026-11-05): complete the families - DDG row
   // columns DDF/DDP/DDM, column headers TPC2-5, buttons DDGT_*, reset DDRESET*.
   // Without these, redrawing Positions after visiting DDGuard stacks old DD
   // text over the position table (exact boss repro: POS -> DDG -> POS).
   ObjectsDeleteAll(0, PFX+"DDF"); ObjectsDeleteAll(0, PFX+"DDP");
   ObjectsDeleteAll(0, PFX+"DDM"); ObjectsDeleteAll(0, PFX+"TPC");
   ObjectsDeleteAll(0, PFX+"DDGT"); ObjectsDeleteAll(0, PFX+"DDRESET");
   ObjectsDeleteAll(0, PFX+"BG");   // v1.54 FIX-TD4: BINGO CLOSE BOARD family
}

void NG_LoadNews()
{
   g_ngEventCount = 0;
   int h = FileOpen(InpNewsFile, FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(h == INVALID_HANDLE) return;
   while(!FileIsEnding(h) && g_ngEventCount < 64)
   {
      string t = FileReadString(h);
      string c = FileReadString(h);
      string n = FileReadString(h);
      string im= FileReadString(h);
      if(t == "" || c == "") continue;
      datetime dt = StringToTime(t);
      if(dt <= 0) continue;
      if(InpNewsHighImpactOnly && im != "HIGH") continue;
      g_ngEvents[g_ngEventCount][0] = t;
      g_ngEvents[g_ngEventCount][1] = c;
      g_ngEvents[g_ngEventCount][2] = n;
      g_ngEvents[g_ngEventCount][3] = im;
      g_ngEventCount++;
   }
   FileClose(h);
}

//+------------------------------------------------------------------+
// v1.28: is this symbol inside any upcoming-news warning window?
bool NG_SymbolHot(string sym)
{
   datetime now=NG_NowHKT();
   for(int i=0;i<g_ngEventCount;i++)
   {
      datetime ev=NG_EvTimeHKT(g_ngEvents[i][0]);
      if(ev==0) continue;
      if(now >= ev-InpNewsBeforeMinutes*60 && now <= ev+InpNewsAfterMinutes*60)
         if(NG_SymbolAffected(sym, g_ngEvents[i][1])) return true;
   }
   return false;
}
// v1.28: push once per event when it enters the warning window
bool g_ngFired[64];
void NG_WindowPush()
{
   datetime now=NG_NowHKT();
   for(int i=0;i<g_ngEventCount && i<64;i++)
   {
      datetime ev=NG_EvTimeHKT(g_ngEvents[i][0]);
      if(ev==0) continue;
      if(now >= ev-InpNewsBeforeMinutes*60 && now <= ev+InpNewsAfterMinutes*60 && !g_ngFired[i])
      {
         g_ngFired[i]=true;
         string syms="";
         for(int j=0;j<g_sgSymN;j++)
            if(NG_SymbolAffected(g_sgSym[j], g_ngEvents[i][1]))
               syms=syms+g_sgSym[j]+(SG_Mode(g_sgSym[j])==3?"[CL]":SG_Mode(g_sgSym[j])==2?"[BL]":SG_Mode(g_sgSym[j])==1?"[AL]":"[ON]")+" ";
         string msg=StringFormat("ALERT: %s %s in %d min | affected: %s",
            g_ngEvents[i][1], g_ngEvents[i][2], (int)((ev-now)/60), (syms==""?"(no open symbols)":syms));
         Print(msg); SendNotification(msg);
      }
   }
}

bool NG_SymbolAffected(string sym, string ccy)
{
   string s = sym;
   StringToUpper(s);
   return (StringFind(s, ccy) >= 0);   // direct substring match on the 6-letter pair
}

//+------------------------------------------------------------------+
//| NewsGuard main loop (called from OnTick/OnTimer, 30s scan)        |
//+------------------------------------------------------------------+
void NG_Guard()
{
   if(InpNewsGuardMode == 0) return;
   if(TimeCurrent() - g_ngLastScan < 30) return;
   g_ngLastScan = TimeCurrent();
   NG_LoadNews();

   for(int i = 0; i < g_ngEventCount; i++)
   {
      datetime evT = NG_EvTimeHKT(g_ngEvents[i][0]);
      string   ccy = g_ngEvents[i][1];
      datetime now = NG_NowHKT();
      if(now <  evT - InpNewsBeforeMinutes*60) continue;   // before the window
      if(now >  evT + InpNewsAfterMinutes*60)  continue;   // after the window

      string msg = StringFormat("🛡 NewsGuard: %s %s @ %s (-%dm/+%dm) mode=%s",
                   ccy, g_ngEvents[i][2], TimeToString(evT, TIME_MINUTES), InpNewsBeforeMinutes, InpNewsAfterMinutes,
                   (InpNewsGuardMode==1?"ALERT":InpNewsGuardMode==2?"BLOCK":"CLOSE"));
      if(msg != g_ngLastAlert)
      {
         Print(msg);
         if(IsTradeAllowed()) SendNotification(msg);
         g_ngLastAlert = msg;
      }
      GlobalVariableSet("NEWSGUARD_" + ccy, 1);
      TG_Notify("NG_"+ccy, "🛡 NewsGuard WINDOW OPEN\n━━━━━━━━━━━━━━\n📢 " + g_ngEvents[i][2] + "\n💵 " + ccy + "\n⏳ Window: " + TimeToString(NG_EvTimeHKT(g_ngEvents[i][0])-InpNewsBeforeMinutes*60, TIME_MINUTES) + "–" + TimeToString(NG_EvTimeHKT(g_ngEvents[i][0])+InpNewsAfterMinutes*60, TIME_MINUTES) + " HKT\n⚡ Mode: " + (InpNewsGuardMode==3?"CLOSE (old+new)":InpNewsGuardMode==2?"BLOCK (new only)":"ALERT") + "\n🕐 " + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + " server");

      //--- v1.47 Q8: 2=BLOCK and 3=CLOSE arm SymbolGuard for the window.
      //--- BLOCK closes new entries only; CLOSE also liquidates old positions.
      //--- Auto-expiry at window end restores the user's per-symbol base mode,
      //--- so a grid EA cannot reopen -> get closed -> reopen forever.
      if(InpNewsGuardMode >= 2)
      {
         int autoMode = (InpNewsGuardMode == 2) ? 2 : 3;
         datetime until = evT + InpNewsAfterMinutes*60;
         for(int a = 0; a < g_sgSymN; a++)
            if(NG_SymbolAffected(g_sgSym[a], ccy))
               SG_SetAuto(g_sgSym[a], autoMode, until);
         if(NG_SymbolAffected(Symbol(), ccy))
            SG_SetAuto(Symbol(), autoMode, until);
         //--- fallback when SymbolGuard itself is disabled: CLOSE mode closes here
         if(!InpSymbolGuardEnable && InpNewsGuardMode == 3)
         {
            for(int p = OrdersTotal() - 1; p >= 0; p--)
            {
               if(!OrderSelect(p, SELECT_BY_POS, MODE_TRADES)) continue;
               if(OrderType() > OP_SELL) continue;
               if(!NG_SymbolAffected(OrderSymbol(), ccy)) continue;
               if(IsTradeContextBusy()) continue;
               double px = (OrderType()==OP_BUY) ? MarketInfo(OrderSymbol(), MODE_BID)
                                                 : MarketInfo(OrderSymbol(), MODE_ASK);
               if(!OrderClose(OrderTicket(), OrderLots(), px, 30, clrRed))
                  Print("NewsGuard close fail #", OrderTicket(), " err=", GetLastError());
            }
         }
      }
   }
   // clear expired flags
   for(int i2 = 0; i2 < g_ngEventCount; i2++)
   {
      datetime evT2 = NG_EvTimeHKT(g_ngEvents[i2][0]);
      string   c2   = g_ngEvents[i2][1];
      if(NG_NowHKT() > evT2 + InpNewsAfterMinutes*60)
         GlobalVariableSet("NEWSGUARD_" + c2, 0);
   }
}

//+------------------------------------------------------------------+
//| NewsGuard panel row (called at the end of RenderOnly)             |
//+------------------------------------------------------------------+
void NG_RenderFooter(int x, int y)
{
   string o = "TDNG_FOOT";
   if(ObjectFind(0,o) < 0) ObjectCreate(0,o,OBJ_LABEL,0,0,0);
   ObjectSetInteger(0,o,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,o,OBJPROP_YDISTANCE,y);
   string mode = (InpNewsGuardMode==3 ? "CLOSE" : InpNewsGuardMode==2 ? "BLOCK" : InpNewsGuardMode==1 ? "ALERT" : "OFF");
   string next = "";
   int best = 24*3600;
   for(int i=0;i<g_ngEventCount;i++)
   {
      int dl = (int)(NG_EvTimeHKT(g_ngEvents[i][0]) - NG_NowHKT());
      if(dl > 0 && dl < best){ best = dl; next = g_ngEvents[i][1]+" "+g_ngEvents[i][2]; }
   }
   string txt = StringFormat("🛡 News[%s] ", mode);
   if(next != "") txt += StringFormat("Next: %s (%dh%02dm)  %s",
       next, best/3600, (best%3600)/60, g_ngEventCount);
   else txt += "No high-impact events in 48h";
   ObjectSetString(0,o,OBJPROP_TEXT, txt);
   ObjectSetInteger(0,o,OBJPROP_COLOR, InpNewsGuardMode>=2 ? clrOrangeRed : clrWhite);
   ObjectSetInteger(0,o,OBJPROP_FONTSIZE, 9);
   ObjectSetString(0,o,OBJPROP_FONT,"Arial");
}

//+------------------------------------------------------------------+
//| DD Guard: account / per-symbol drawdown protection                |
//+------------------------------------------------------------------+
//--- v1.45 Q2: Telegram via MT4 built-in WebRequest (no wininet DLL) ---
//---            NOTE: add https://api.telegram.org to WebRequest whitelist
//---            (Tools -> Options -> Expert Advisors -> Allow WebRequest)
string TG_URLEncode(string s)
{
   char b[]; int n = StringToCharArray(s, b, 0, WHOLE_ARRAY, CP_UTF8);
   string o = "";
   for(int i=0; i<n-1; i++)
   {
      uchar c = (uchar)b[i];
      if((c>='0'&&c<='9')||(c>='A'&&c<='Z')||(c>='a'&&c<='z')||c=='-'||c=='.'||c=='_'||c=='~'){ o += CharToString((uchar)b[i]); }
      else if(c==0x20) o += "+";
      else o += StringFormat("%%%02X", c);
   }
   return(o);
}
bool TG_SendRaw(string text)
{
   // v1.45 Q2: MT4 built-in WebRequest - no wininet DLL needed
   // NOTE: add https://api.telegram.org to WebRequest whitelist first
   if(!InpTelegramEnable || g_tgToken == "") { SendNotification(StringSubstr(text,0,200)); return(false); }
   string url = "https://api.telegram.org/bot" + g_tgToken + "/sendMessage";
   // form-encoded body: chat_id + UTF-8 URL-encoded text
   string data = "chat_id=" + TG_URLEncode(InpTelegramChatId) + "&text=" + TG_URLEncode(text);
   char post[]; int plen = StringToCharArray(data, post, 0, WHOLE_ARRAY, CP_UTF8); plen--;
   string hdr = "Content-Type: application/x-www-form-urlencoded\r\n";
   char resp[]; string respHdr;
   ResetLastError();
   int code = WebRequest("POST", url, hdr, 3000, post, resp, respHdr);
   if(code == -1)
   {
      // v1.45 Q2: WebRequest failed (whitelist missing / no network) -> fallback phone push
      Print("TD: WebRequest failed err=", GetLastError(),
            " - add api.telegram.org to MT4 WebRequest whitelist (Tools->Options->EA)");
      SendNotification(StringSubstr(text,0,200));
      return(false);
   }
   if(code != 200) { Print("TD: Telegram HTTP ", code); return(false); }
   string body = CharArrayToString(resp, 0, WHOLE_ARRAY, CP_UTF8);
   // v1.45 Q2: verify Telegram responded with ok:true
   return(StringFind(body, "\"ok\":true") >= 0);
}
void TG_Notify(string key, string text)
{
   datetime now = TimeCurrent();
   for(int i=0;i<g_tgN;i++)
      if(g_tgKey[i]==key){ if(now - g_tgLast[i] < InpTelegramMinGapMinutes*60) return; g_tgLast[i]=now; TG_SendRaw(text); return; }
   if(g_tgN < 8){ g_tgKey[g_tgN]=key; g_tgLast[g_tgN]=now; g_tgN++; }
   TG_SendRaw(text);
}

//--- v1.40 DLL: toggle terminal AutoTrading button (MT4 cmd id 33020)
bool TD_TerminalHandle(int &root)
{
   int h = (int)ChartGetInteger(0, CHART_WINDOW_HANDLE, 0);
   if(h <= 0) return(false);
   root = GetAncestor(h, 2);   // GA_ROOT
   return(root > 0);
}
void TD_ToggleAutoTrade()
{
   int root;
   if(!TD_TerminalHandle(root)) return;
   PostMessageW(root, 0x0111, 33020, 0);   // WM_COMMAND, autotrade toggle
}
//+------------------------------------------------------------------+
//| v1.43 T8: deposit/withdrawal-aware peak adjustment               |
//+------------------------------------------------------------------+
datetime g_lastBalScan = 0;
double   g_balBase     = 0;
void DDG_ScanBalanceOps()
{
   if(!g_ddgeOn) return;
   datetime now = TimeCurrent();
   if(now - g_lastBalScan < 60) return;
   g_lastBalScan = now;
   double base = AccountBalance();
   double sum  = 0;
   bool   found = false;
   for(int i = OrdersHistoryTotal()-1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY)) continue;
      if(OrderCloseTime() < g_lastBalScan - 120) break;
      if(OrderType() != 6) continue;
      sum += OrderProfit();
      found = true;
   }
   if(!found) return;
   if(g_balBase <= 0) { g_balBase = base - sum; return; }
   double delta = sum;
   if(delta != 0)
   {
      g_ddgPeakEquity = MathMax(AccountEquity(), g_ddgPeakEquity + delta);
      GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
      Print("TD v1.43: balance op detected $" + DoubleToString(delta,2) + " — peak adjusted to $" + DoubleToString(g_ddgPeakEquity,2));
   }
   g_balBase = base;
}

//+------------------------------------------------------------------+
//| v1.43 T2: close-all with retry-until-zero                        |
//+------------------------------------------------------------------+
int DDG_CloseAllWithRetry()
{
   int retries = MathMax(1, InpDdgCloseRetry);
   int residual = 9999;
   for(int r = 0; r < retries; r++)
   {
      for(int p = OrdersTotal()-1; p >= 0; p--)
      {
         if(!OrderSelect(p, SELECT_BY_POS, MODE_TRADES)) continue;
         if(OrderType() <= OP_SELL) continue;
         if(!OrderDelete(OrderTicket()))
            Print("DDGuard pending-del fail #", OrderTicket(), " err=", GetLastError());
      }
      for(int p = OrdersTotal()-1; p >= 0; p--)
      {
         if(!OrderSelect(p, SELECT_BY_POS, MODE_TRADES)) continue;
         if(OrderType() > OP_SELL) continue;
         double px = (OrderType()==OP_BUY) ? MarketInfo(OrderSymbol(),MODE_BID)
                                           : MarketInfo(OrderSymbol(),MODE_ASK);
         if(!OrderClose(OrderTicket(), OrderLots(), px, 30, clrRed))
            Print("DDGuard close fail #", OrderTicket(), " err=", GetLastError());
      }
      RefreshRates();
      Sleep(150);
      residual = 0;
      for(int p = OrdersTotal()-1; p >= 0; p--)
      {
         if(!OrderSelect(p, SELECT_BY_POS, MODE_TRADES)) continue;
         if(OrderType() > OP_SELL) continue;
         residual++;
      }
      if(residual == 0) break;
   }
   return residual;
}

//+------------------------------------------------------------------+
//| v1.54 FIX-TD4 (0745 item 1): unified close body                  |
//| int DDG_CloseMatch(int mode, string sym)                         |
//|   mode 0=BUY 1=SELL 2=WIN 3=LOSE 4=SYM-ALL (keeps pending)       |
//|   mode 5=GLOBAL (all symbols, all positions + delete ALL pending)|
//|   mode 6=legacy alias: sym positions + THIS symbol's pending     |
//|         deleted - keeps DDG_CloseSymbolWithRetry bit-for-bit     |
//| One shared retry-until-zero loop (RefreshRates + Sleep(150)),    |
//| live rescans OrdersTotal() only, never touches t_* arrays.       |
//| WIN/LOSE split on net floating P&L (profit+swap+commission).     |
//+------------------------------------------------------------------+
int DDG_CloseMatch(int mode, string sym)
{
   bool global   = (mode == 5);
   bool delPend  = (mode == 5 || mode == 6);
   int retries = MathMax(1, InpDdgCloseRetry);
   int residual = 9999;
   for(int r = 0; r < retries; r++)
   {
      if(delPend)
      {
         for(int p = OrdersTotal()-1; p >= 0; p--)
         {
            if(!OrderSelect(p, SELECT_BY_POS, MODE_TRADES)) continue;
            if(OrderType() <= OP_SELL) continue;
            if(!global && OrderSymbol() != sym) continue;
            if(!OrderDelete(OrderTicket()))
               Print("DDG close-match pending-del fail #", OrderTicket(), " err=", GetLastError());
         }
      }
      for(int p2 = OrdersTotal()-1; p2 >= 0; p2--)
      {
         if(!OrderSelect(p2, SELECT_BY_POS, MODE_TRADES)) continue;
         if(OrderType() > OP_SELL) continue;
         if(!global && OrderSymbol() != sym) continue;
         if(mode == 0 && OrderType() != OP_BUY) continue;
         if(mode == 1 && OrderType() != OP_SELL) continue;
         double pf = OrderProfit() + OrderSwap() + OrderCommission();
         if(mode == 2 && pf <= 0) continue;   // WIN = floating profit
         if(mode == 3 && pf >= 0) continue;   // LOSE = floating loss
         double px = (OrderType()==OP_BUY) ? MarketInfo(OrderSymbol(),MODE_BID)
                                           : MarketInfo(OrderSymbol(),MODE_ASK);
         if(!OrderClose(OrderTicket(), OrderLots(), px, 30, clrRed))
            Print("DDG close-match fail #", OrderTicket(), " err=", GetLastError());
      }
      RefreshRates();
      Sleep(150);
      residual = 0;
      for(int p3 = OrdersTotal()-1; p3 >= 0; p3--)
      {
         if(!OrderSelect(p3, SELECT_BY_POS, MODE_TRADES)) continue;
         if(OrderType() > OP_SELL) continue;
         if(!global && OrderSymbol() != sym) continue;
         if(mode == 0 && OrderType() != OP_BUY) continue;
         if(mode == 1 && OrderType() != OP_SELL) continue;
         double pf3 = OrderProfit() + OrderSwap() + OrderCommission();
         if(mode == 2 && pf3 <= 0) continue;
         if(mode == 3 && pf3 >= 0) continue;
         residual++;
      }
      if(residual == 0) break;
   }
   return residual;
}

//+------------------------------------------------------------------+
//| v1.43 T2: close one symbol with retry-until-zero                 |
//| v1.54 FIX-TD4: legacy alias over DDG_CloseMatch(6, sym);         |
//| behaviour unchanged - still deletes THIS symbol's pending.       |
//+------------------------------------------------------------------+
int DDG_CloseSymbolWithRetry(string sym)
{
   return(DDG_CloseMatch(6, sym));
}

//+------------------------------------------------------------------+
//| v1.43 T3: stop AT — guarded toggle, DLL-safe                     |
//+------------------------------------------------------------------+
void DDG_StopAT()
{
   if(!TerminalInfoInteger(TERMINAL_DLLS_ALLOWED)) { Print("TD: DLL not allowed — cannot toggle AutoTrading"); return; }
   bool atOn = (TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0);
   if(!atOn) { g_tdStoppedAT = true; DDG_SaveState(); return; }
   TD_ToggleAutoTrade();
   Sleep(250);
   if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) == 0) { g_tdStoppedAT = true; DDG_SaveState(); }
}

//+------------------------------------------------------------------+
//| v1.43 T3: restore AT — only if WE stopped it and still off       |
//+------------------------------------------------------------------+
void DDG_RestoreAT()
{
   if(!g_tdStoppedAT) return;
   if(!TerminalInfoInteger(TERMINAL_DLLS_ALLOWED)) { Print("TD: DLL not allowed — cannot restore AutoTrading"); return; }
   if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0) { g_tdStoppedAT = false; return; }
   TD_ToggleAutoTrade();
   Sleep(250);
   if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0) { g_tdStoppedAT = false; DDG_SaveState(); }
}

//+------------------------------------------------------------------+
//| v1.43 T3: AT status check — observe-only, never auto-restores.   |
//| Tracks whether WE stopped AT; if user manually reopened, clears  |
//| our lock flag so we don't fight the human.                       |
//+------------------------------------------------------------------+
void DDG_ATStatusCheck()
{
   bool atOn = (TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0);
   if(atOn && g_tdStoppedAT)
   {
      g_tdStoppedAT = false;   // user (or something) already reopened — release our ownership
      DDG_SaveState();
   }
   // if not DLL-allowed we can't verify via button, rely on TERMINAL_TRADE_ALLOWED only
}

//+------------------------------------------------------------------+
//| v1.43 T3: manual [Reset Peak / Confirm Resume] button handler    |
//+------------------------------------------------------------------+
void DDG_ResetPeakConfirm()
{
   g_ddgPeakEquity = AccountEquity();
   GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
   g_ddgLockUntil = 0;
   g_ddgAccountArmed = false;
   for(int k = 0; k < 64; k++) { g_ddgSymLocked[k] = false; g_sgForcedClose[k] = false; }
   // v1.47 Q9: clear every persisted per-symbol lock for this account
   string pfx = TD_AcctPfx()+"DDG_SYMLOCK_";
   for(int v = GlobalVariablesTotal()-1; v >= 0; v--)
      if(StringFind(GlobalVariableName(v), pfx) == 0) GlobalVariableDel(GlobalVariableName(v));
   DDG_RestoreAT();
   DDG_SaveState();   // v1.47 Q9: persist the cleared state too
   TG_Notify("DDG_RESET", "✅ Risk lock cleared manually: Peak reset to $" + DoubleToString(g_ddgPeakEquity,2) + ", AlgoTrading restored (" + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + " server)");
   Print("TD v1.47: manual reset peak -> ", DoubleToString(g_ddgPeakEquity,2));
}

//+------------------------------------------------------------------+
//| v1.43 T4: force a symbol's SymbolGuard into CLOSE                |
//+------------------------------------------------------------------+
void SG_ForceClose(string sym)
{
   for(int k = 0; k < g_sgSymN; k++)
      if(g_sgSym[k] == sym) { g_sgForcedClose[k] = true; }
   GlobalVariableSet(SG_ModeKey(sym), 3);   // v1.47: account-scoped CLOSE
}

//+------------------------------------------------------------------+
//| DDGuard main check (v1.43 rewrite)                               |
//+------------------------------------------------------------------+
void DDG_Guard()
{
   //--- v1.60 FIX (1400 §四-2): the peak ratchet runs UNCONDITIONALLY, before
   //--- the master gate. Tracking must never depend on the guard switch: with
   //--- DDG OFF the old code froze the peak ($0.00 or a stale value) and the
   //--- panel showed DD -97.51% nonsense. GV persisted only when the mark
   //--- actually advances (cheap, and restart-safe).
   double eq  = AccountEquity();
   if(eq > g_ddgPeakEquity)
   {
      g_ddgPeakEquity = eq;
      GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
   }
   if(!g_ddgeOn) return;
   DDG_ScanBalanceOps();
   double base = DDG_Base();                 // v1.47 Q6: single balance denominator
   if(g_ddgPeakEquity <= 0) return;
   if(TimeCurrent() < g_ddgLockUntil) return;
   if(g_ddgAccountArmed) return;

   //--- v1.60 (1230 §3.3): account DD in money, OR-triggered with the % limit.
   //--- Display clamped >= 0: eq >= peak must read 0.00% DD, never negative.
   double ddPct   = MathMax(0.0, (g_ddgPeakEquity - eq) / base * 100.0);   // v1.47 Q6 denominator
   double ddMoney = MathMax(0.0, g_ddgPeakEquity - eq);
   bool hitPct   = (InpDdgAccountMaxPercent > 0 && ddPct   >= InpDdgAccountMaxPercent);
   bool hitMoney = (InpDdgAccountMaxMoney   > 0 && ddMoney >= InpDdgAccountMaxMoney);
   if(g_ddgAccOn && (hitPct || hitMoney))
   {
      string trig = hitPct ? StringFormat("DD %.1f%% >= limit %.1f%%", ddPct, InpDdgAccountMaxPercent)
                            : StringFormat("DD $%.2f >= limit $%.2f", ddMoney, InpDdgAccountMaxMoney);
      string msg = StringFormat("🚨 DDGuard: ACCOUNT %s — %s",
                   trig, InpDdgCloseOnHit ? "CLOSE ALL!" : "block new entries");
      if(msg != g_ddgLastAlert)
      {
         Print(msg); SendNotification(msg); g_ddgLastAlert = msg;
      }
      if(InpDdgCloseOnHit)
      {
         int residual = DDG_CloseAllWithRetry();
         g_ddgLockUntil = TimeCurrent() + InpDdgLockMinutes*60;
         g_ddgAccountArmed = true;
         if(InpDdgAccountStopAutotrade) DDG_StopAT();
         DDG_SaveState();                       // v1.47 Q9: survive terminal restart
         if(residual > 0)
            TG_Notify("DDG_ACC_RESID", "🚨 [URGENT] Close incomplete! " + IntegerToString(residual) + " position(s) still open — manual intervention required!");
         TG_Notify("DDG_ACC", "🚨 DDGuard TRIGGERED — ACCOUNT LEVEL\n━━━━━━━━━━━━━━\n🏦 AC: " + IntegerToString(AccountNumber()) + "\n📉 DD: " + DoubleToString(ddPct,2) + "% / $" + DoubleToString(ddMoney,2) + " (limits " + DoubleToString(InpDdgAccountMaxPercent,1) + "% / $" + DoubleToString(InpDdgAccountMaxMoney,2) + ")\n💰 Peak: $" + DoubleToString(g_ddgPeakEquity,2) + "\n💸 Equity: $" + DoubleToString(AccountEquity(),2) + "\n⚡ Action: close all" + (residual>0?" (residual "+IntegerToString(residual)+" open!)":" ✅") + " + AutoTrade " + (InpDdgAccountStopAutotrade?"STOPPED":"not stopped") + "\n⏱ Awaiting manual confirm [Reset Peak]\n🕐 " + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + " server");
         if(InpDdgAlertPopup){ int rh; if(TD_TerminalHandle(rh)) MessageBoxW(rh, msg, "DDGuard", 0x30); }
      }
      return;
   }

   if(g_ddgSymOn && (InpDdgSymbolMaxPercent > 0 || InpDdgSymbolMaxMoney > 0))   // v1.60 §3.3: OR money limit
   {
      string syms = InpDdgSymbolList;
      if(syms == "") syms = Symbol();
      string parts[20]; int n = StringSplit(syms, ',', parts);
      for(int s = 0; s < n; s++)
      {
         string sym = parts[s];
         StringTrimLeft(sym); StringTrimRight(sym);
         if(sym == "") continue;
         bool symLocked = DDG_SymLocked(sym);        // v1.47 Q9: persisted per-symbol lock
         if(symLocked) continue;
         double floating = 0;
         for(int p2 = OrdersTotal()-1; p2 >= 0; p2--)
         {
            if(!OrderSelect(p2, SELECT_BY_POS, MODE_TRADES)) continue;
            if(OrderType() > OP_SELL) continue;
            if(OrderSymbol() != sym) continue;
            floating += OrderProfit() + OrderSwap() + OrderCommission();
         }
         //--- v1.60 (1230 §3.3): per-symbol OR-trigger — % of balance OR money.
         bool symHitPct   = (InpDdgSymbolMaxPercent > 0 && -floating >= base * InpDdgSymbolMaxPercent / 100.0);
         bool symHitMoney = (InpDdgSymbolMaxMoney   > 0 && -floating >= InpDdgSymbolMaxMoney);
         if(symHitPct || symHitMoney)   // v1.47 Q6: pct arm was AcctEquity-based
         {
            string strig = symHitPct ? StringFormat("%.1f%% limit", InpDdgSymbolMaxPercent)
                                      : StringFormat("$%.2f limit", InpDdgSymbolMaxMoney);
            string m2 = StringFormat("🚨 DDGuard: %s floating %.0f hit %s — %s",
                        sym, floating, strig, InpDdgCloseOnHit?"close":"block new entries");
            Print(m2); SendNotification(m2);
            if(InpDdgCloseOnHit)
            {
               int residual2 = DDG_CloseSymbolWithRetry(sym);
               SG_ForceClose(sym);
               DDG_SetSymLock(sym, true);                  // v1.47 Q9: persist lock
               g_ddgLockUntil = TimeCurrent() + InpDdgLockMinutes*60;
               DDG_SaveState();
               if(InpDdgSymbolStopAutotrade) DDG_StopAT();
               if(residual2 > 0)
                  TG_Notify("DDG_SYM_RESID_" + sym, "🚨 [URGENT] " + sym + " close incomplete! " + IntegerToString(residual2) + " position(s) still open — manual intervention required!");
               TG_Notify("DDG_"+sym, "⚠️ DDGuard TRIGGERED — SYMBOL LEVEL\n━━━━━━━━━━━━━━\n.Symbol: " + sym + "\n📉 Floating: $" + DoubleToString(floating,2) + " (hit " + (symHitPct ? DoubleToString(InpDdgSymbolMaxPercent,1) + "% limit" : "$" + DoubleToString(InpDdgSymbolMaxMoney,2) + " limit") + "\n⚡ Action: close symbol" + (residual2>0?" (residual "+IntegerToString(residual2)+" open!)":" ✅") + " + SymbolGuard CLOSE locked" + (InpDdgSymbolStopAutotrade?" + AutoTrade STOPPED":"") + "\n⏱ Awaiting manual confirm\n🕐 " + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + " server");
               if(InpDdgAlertPopup){ int rh2; if(TD_TerminalHandle(rh2)) MessageBoxW(rh2, m2, "DDGuard", 0x30); }
            }
         }
      }
   }
}
//+------------------------------------------------------------------+
//| v1.36 CHANGELOG (2026-10-14 boss review)                          |
//| 1. Alerts/DDGuard/Set tabs: body text 7-8*scale -> 9*scale        |
//|    (unified with main panel size)                                 |
//| 2. Tab headers (TN0/TA0/TD0/TS0/TPH): UpdTxtBold + 10*scale       |
//| 3. All gray/silver text -> clrWhite/clrKhaki (contrast fix)       |
//| 4. NG footer font 8 -> 9, gray -> white                           |
//+------------------------------------------------------------------+
