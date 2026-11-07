//+------------------------------------------------------------------+
//|                                             TradeDashboard5.mq5  |
//|        MT5 port of TradeDashboard v1.39 (broker summary-proof)   |
//|        v1.10 - full feature port: 21-col table, 4 tabs,          |
//|               NewsGuard / DDGuard / SymbolGuard, snap bin        |
//+------------------------------------------------------------------+
#property copyright "FF48 Alvin"
#property version   "1.63"
#property description "TradeDashboard v1.63 (MT5 build, inline CLOSE board port)"

#include <Trade/Trade.mqh>

//--- v1.11 DLL imports (require Allow DLL imports)
//--- v1.15 Q2: wininet removed - Telegram now via MT5 built-in WebRequest()
//---            DLL kept only for AlgoTrading toggle (user32.dll)
#import "shell32.dll"
   int ShellExecuteW(long hWnd, string lpOperation, string lpFile, string lpParameters, string lpDirectory, int nShowCmd);
#import
#import "user32.dll"
   int PostMessageW(long hWnd, uint Msg, long wParam, long lParam);
   long GetAncestor(long hWnd, uint gaFlags);
   int MessageBoxW(long hWnd, string text, string caption, uint type);
   int GetMenu(long hWnd);
   int GetSubMenu(int hMenu, int nPos);
   int GetMenuItemCount(int hMenu);
   int GetMenuItemID(int hMenu, int uItem);
   int GetMenuStringW(int hMenu, int uItem, ushort &lpString[], int nMaxCount, int uFlag);
#import
CTrade trade;

//=== INPUTS ===
//--- v1.44: Panel Label first; NewsGuard/DDGuard default OFF (enable when needed)
//=== INPUTS (v1.63: 12 groups / 70 params, two-platform aligned) ===
//--- v1.44: NewsGuard/DDGuard default OFF (enable when needed)
//--- v1.60 FIX-TD10: rename per 1230 letter 66-row table; 2 new DD-money params

sinput string Spacer01                  = "";                                        // ────────────────────────────────
input group "General"
input string InpTitleLine1              = "TradeDashboard";                          // Line 1 (max 30 chars) - no version in panel
input string InpTitleLine2              = "Flying to the moon";                      // Line 2 Subtitle
input int    InpPanelScale              = 1;                                         // Panel size multiplier (1, 2 or 3)
input int    InpDefaultView             = 0;                                         // 0=Hour, 1=Day, 2=Week, 3=Month

sinput string Spacer02                  = "";                                        // ────────────────────────────────
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

sinput string Spacer03                  = "";                                        // ────────────────────────────────
input group "Refresh & Recording"
input int    InpRefreshSeconds          = 10;                                        // Panel refresh interval in seconds
input int    InpRecordSeconds           = 1;                                         // Min seconds between records (1=every tick)
input int    InpMaxRecords              = 12000;                                     // Records in ring buffer (max 20000)

sinput string Spacer04                  = "";                                        // ────────────────────────────────
input group "Data Filter"
input string InpReportStart             = "";                                        // Report start date YYYY.MM.DD (empty = from beginning)
input string InpFilterSymbol            = "";                                        // Filter by symbol (empty = all)
input string InpFilterComment           = "";                                        // Filter by comment (empty = all)

sinput string Spacer05                  = "";                                        // ────────────────────────────────
input group "Trade Snapshot"
input bool   InpSnapshotEnable          = true;                                      // Enable local trade snapshots
input int    InpSnapshotHours           = 72;                                        // Snapshot lookback hours
input bool   InpSnapshotBackfillOnce    = false;                                     // One-shot full-history backfill, flip back after run

sinput string Spacer06                  = "";                                        // ────────────────────────────────
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

sinput string Spacer07                  = "";                                        // ────────────────────────────────
input group "DD Guard - Per Symbol"
input bool   InpDdgSymbolEnable         = false;                                     // per-symbol DD guard (independent switch)
input string InpDdgSymbolList           = "";                                        // Guarded symbols, comma-separated (empty = all)
input double InpDdgSymbolMaxPercent     = 12.0;                                      // per-symbol max drawdown %
input double InpDdgSymbolMaxMoney       = 0.0;                                       // Per-symbol max drawdown in money (0 = off)
input bool   InpDdgSymbolStopAutotrade  = false;                                     // per-symbol DD stops global AutoTrading (default OFF)

sinput string Spacer08                  = "";                                        // ────────────────────────────────
input group "Symbol Guard"
input bool   InpSymbolGuardEnable       = true;                                      // Symbol Guard: monitor per-symbol trading
input int    InpSymbolGuardMode         = 0;                                         // new symbol default 0=ON 1=ALERT 2=BLOCK 3=CLOSE

sinput string Spacer09                  = "";                                        // ────────────────────────────────
input group "News Guard"
input int    InpNewsGuardMode           = 0;                                         // 0=OFF(default) 1=ALERT 2=BLOCK(new only) 3=CLOSE(new+old)
input int    InpNewsBeforeMinutes       = 30;                                        // Minutes before news event to guard
input int    InpNewsAfterMinutes        = 15;                                        // Minutes after news event to guard
input bool   InpNewsHighImpactOnly      = true;                                      // Guard high-impact news only
input string InpNewsFile                = "news_guard.csv";                          // News calendar CSV file name
input int    InpNewsServerOffsetHours   = -5;                                        // news CSV(HKT+8) -> broker server hours

sinput string Spacer10                  = "";                                        // ────────────────────────────────
input group "Telegram"
input string InpTelegramChatId          = "";                                        // Telegram chat ID (empty = no Telegram target; set via input/.set)
input string InpTelegramTokenFile       = "tg_token.txt";                            // File name holding the bot token
input bool   InpTelegramEnable          = true;                                      // Enable Telegram notifications
input int    InpTelegramMinGapMinutes   = 10;                                        // min minutes between notifications per key
input string InpTelegramWhitelistUrl    = "https://api.telegram.org";               // Whitelist this URL in firewall/proxy (copy)
input string InpTelegramBotToken        = "";                                        // Bot token direct (overrides token file; empty=use file)

sinput string Spacer11                  = "";                                        // ────────────────────────────────
input group "Backup & Recovery"
input bool   InpAutoBackup              = true;                                      // Enable daily auto backup on change
input bool   InpAutoReconnect           = true;                                      // Auto-restart terminal on stuck disconnect
input int    InpReconnectAfterMinutes   = 10;                                        // Sustained disconnect minutes before restart
input int    InpRestartCooldownHours    = 2;                                         // Min hours between restarts
input int    InpMaxRestartAttempts      = 3;                                         // Give up after N consecutive failed restarts
input string InpBackupTime              = "05:30";                                   // Daily check time, server time HH:MM
input string InpBackupFolder            = "";                                        // Custom backup root (empty = auto data path)

sinput string Spacer12                  = "";                                        // ────────────────────────────────
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
datetime g_lastBalScan = 0;   // v1.14 T8: deposit/withdrawal scan
bool     g_balBaseSet   = false;
double   g_balBase      = 0;bool g_tdStoppedAT = false;
bool     g_ddgAccountArmed = false;   // v1.14: account-level lock awaiting manual reset (persisted v1.47 Q9)
bool     g_ddgSymLocked[64];          // v1.14: per-symbol lockout mirror (account-scoped GV, v1.47 Q9)
bool     g_sgForcedClose[64];         // v1.14: symbols force-locked CLOSE by SymbolGuard linkage
string   g_sgPendSym[64];             // v1.47 Q7: symbols awaiting second-press CLOSE confirmation
datetime g_sgPendT[64];               // v1.47 Q7: first press time (confirm window 20s)
string g_tgToken = "";
datetime g_tgLast[8];
string g_tgKey[8];
int g_tgN = 0;
bool     g_histTruncated = false;

#define PFX "TD5_"
int    g_tab  = 0;   // 0=Positions 1=Alerts 2=DDGuard 3=Set
int    g_view = 0;
int    g_offset = 0;
datetime g_lastFull = 0;
datetime g_lastSnap = 0;
datetime g_saveBtnFlashUntil = 0; // SAVE button green-flash deadline
//--- v1.60 (1230 §3.2): auto-backup / auto-reconnect support (MT4 parity)
int      g_backupMinute    = 330;  // parsed from InpBackupTime at OnInit
datetime g_lastBackupCheck = 0;
datetime g_discStart       = 0;    // v1.20: disconnect tracker for auto-reconnect
string   BACKUP_HASH_FILE  = "TD_backup_hash.txt";

//--- Runtime filter (from inputs, editable via chart)
string   g_filterSymbol = "";
string   g_filterComment = "";
datetime g_reportStart = 0;

//--- Recording (equity snapshots) - ring buffer + binary persistence
datetime g_lastRec = 0;
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
//--- v1.51 TD6: per-account file names (two accounts on one terminal must not
//---            share trade/snapshot/event files - that is what produced the
//---            ghost-symbol panel on MT4 v1.52 and earlier).
string AccountTag(){ return("TD_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "_"); }
string SnapFile()  { return(AccountTag() + "snap.bin"); }
string TradesFile(){ return(AccountTag() + "trades.csv"); }
string EventFile() { return(AccountTag() + "events.log"); }
#define SNAP_MAGIC 0x35445054   // "TPD5"

//--- Local Trade Snapshot
#define MAX_TRADES 12000
long     t_ticket[MAX_TRADES];
string   t_symbol[MAX_TRADES];
int      t_type[MAX_TRADES];       // 0=BUY 1=SELL
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
long     g_acct = 0;              // v1.51 TD6: account watchdog

//--- Summary event log -> EventFile() (per account)

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

string DDG_PeakKey(){ return("TD5_"+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"_PEAK"); }
//--- v1.47 Q9: every persistent key is account-scoped so two accounts sharing
//---           one terminal never inherit each other's risk locks or SG modes.
string TD_AcctPfx(){ return("TD5_"+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"_"); }
string DDG_ArmedKey(){ return(TD_AcctPfx()+"DDG_ARMED"); }
string DDG_LockKey(){ return(TD_AcctPfx()+"DDG_LOCKUNTIL"); }
string DDG_ATKey(){ return(TD_AcctPfx()+"DDG_ATSTOP"); }
string DDG_SymLockKey(string s){ return(TD_AcctPfx()+"DDG_SYMLOCK_"+s); }
string SG_ModeKey(string s){ return(TD_AcctPfx()+"SG_"+s); }
string SG_AutoKey(string s){ return(TD_AcctPfx()+"SG_AUTO_"+s); }
string SG_AutoModeKey(string s){ return(TD_AcctPfx()+"SG_AUTOMODE_"+s); }

//--- v1.47 Q6: single DD denominator. Balance is used by the account guard,
//--- the per-symbol guard and the DDGuard tab so all three agree. Balance is
//--- not inflated by floating profit (an equity base would widen the limit).
double DDG_Base(){ double b = AcctBalance(); if(b <= 0) b = AcctEquity(); if(b <= 0) b = 1.0; return(b); }

//--- v1.47 Q9: risk-lock state survives a terminal restart (GlobalVariables)
void DDG_SaveState()
{
   GlobalVariableSet(DDG_ArmedKey(), g_ddgAccountArmed ? 1 : 0);
   GlobalVariableSet(DDG_LockKey(), (double)(long)g_ddgLockUntil);
   GlobalVariableSet(DDG_ATKey(), g_tdStoppedAT ? 1 : 0);
}
void DDG_LoadState()
{
   if(GlobalVariableCheck(DDG_ArmedKey())) g_ddgAccountArmed = (GlobalVariableGet(DDG_ArmedKey()) > 0.5);
   if(GlobalVariableCheck(DDG_LockKey()))  g_ddgLockUntil   = (datetime)(long)GlobalVariableGet(DDG_LockKey());
   if(GlobalVariableCheck(DDG_ATKey()))    g_tdStoppedAT    = (GlobalVariableGet(DDG_ATKey()) > 0.5);
   if(g_ddgLockUntil > 0 && TimeCurrent() > g_ddgLockUntil) g_ddgLockUntil = 0;
}
bool DDG_SymLocked(string s)
{
   if(s == "") return(false);
   if(!GlobalVariableCheck(DDG_SymLockKey(s))) return(false);
   return(GlobalVariableGet(DDG_SymLockKey(s)) > 0.5);
}
void DDG_SetSymLock(string s, bool on)
{
   if(s == "") return;
   GlobalVariableSet(DDG_SymLockKey(s), on ? 1 : 0);
}
// v1.14 T7: CSV time is HKT(+8); hot-window checks use TimeGMT()+8h
datetime NG_EvTime(string t){ return(StringToTime(t) + (datetime)(InpNewsServerOffsetHours*3600)); }   // display/fallback only
datetime NG_EvTimeHKT(string t){ return(StringToTime(t)); }   // CSV raw time == HKT
datetime NG_NowHKT(){ return(TimeGMT() + 8*3600); }

//+------------------------------------------------------------------+
//| Account helpers                                                  |
//+------------------------------------------------------------------+
double AcctBalance()  { return AccountInfoDouble(ACCOUNT_BALANCE); }
double AcctEquity()   { return AccountInfoDouble(ACCOUNT_EQUITY); }
double AcctMargin()   { return AccountInfoDouble(ACCOUNT_MARGIN); }
double AcctFreeMarg() { return AccountInfoDouble(ACCOUNT_MARGIN_FREE); }

//+------------------------------------------------------------------+
//| Symbol info helpers (MT5)                                        |
//+------------------------------------------------------------------+
double SymPoint(string sym)
{
   double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
   if(pt <= 0) pt = 0.0001;
   return pt;
}
int SymDigits(string sym)
{
   return (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
}

//--- v1.60 (1230 §3.4): CalcTradePnl() removed - it had ZERO callers in
//---   the MT5 build (dead code). Gain keeps using the broker-true
//---   DEAL_PROFIT + DEAL_SWAP + DEAL_COMMISSION recorded at sync time.

//+------------------------------------------------------------------+
//| OnInit                                                           |
//+------------------------------------------------------------------+
int OnInit()
{
   EventSetTimer(1);    // v1.46 Q4: 1s timer so risk guards run without ticks
   trade.SetDeviationInPoints(30);
   TG_LoadToken();      // v1.15 Q2: load TG token at startup (was only in NewsGuard)

   // v1.61 (0745 spec MT5 port): BINGO board starts cold - no ARM survives a
   //   restart, all per-button cooldowns cleared.
   g_bingoArmed = false;
   g_bingoPage  = 0;
   g_bingoLast  = "";
   for(int bi = 0; bi < 12; bi++)
      for(int bj = 0; bj < 5; bj++)
         g_bingoCool[bi][bj] = 0;

   // Clean up objects from previous version
   ObjectsDeleteAll(0, PFX);

   g_view = MathMax(0, MathMin(3, InpDefaultView));
   g_tab = 0;
   g_offset = 0;

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

   //--- v1.51 TD6: park pre-1.51 shared files BEFORE any load touches them
   MigrateLegacySharedFiles();
   g_acct = AccountInfoInteger(ACCOUNT_LOGIN);

   LoadRecords();       // hydrate binary snapshot ring buffer
   LoadTrades();        // hydrate local trade snapshot CSV
   g_backupMinute = ParseHM(InpBackupTime, 330);   // v1.60 (1230 §3.2)

   //--- v1.60 FIX (1245 review): pre-v1.60 stores were built with the
   //---   OVERWRITE upsert and no deal dedup, so merging the new `+=`
   //---   aggregation on top of them would double-count every historical
   //---   OUT deal. First v1.60 run with no seen-set file = one-shot
   //---   rebuild from full history; the seen set is then persisted so
   //---   the migration never repeats.
   LoadSeenSet();
   int legacyCount = t_tradeCount;
   bool migrating  = (!g_seenLoaded && legacyCount > 0);
   if(migrating)
   {
      t_tradeCount = 0;   // fresh rebuild from history
      LogEvent("V1.60 MIGRATION: rebuilding store from full history (netting aggregation fix)");
   }

   //--- v1.60 (1230 §3.2): BackfillOnce runs the (always full-history)
   //---   sync at init even when snapshots are off; flip the input back
   //---   after the run, as on MT4.
   if(InpSnapshotEnable || InpSnapshotBackfillOnce)
      SyncTradesFromHistory();
   if(InpSnapshotBackfillOnce)
      LogEvent(StringFormat("BACKFILL DONE n=%d", t_tradeCount));

   if(migrating)
   {
      if(t_tradeCount == 0)
      {
         // history unavailable - keep the legacy store (SaveTrades
         // no-shrink guard already skipped the overwrite), retry next init
         LoadTrades();
         g_seenDealN = 0; g_seenDirty = false; g_seenLoaded = false;
         LogEvent("V1.60 MIGRATION DEFERRED: empty history scan, legacy store kept");
      }
      else
      {
         LogEvent(StringFormat("V1.60 MIGRATION DONE: %d trades rebuilt (was %d)",
                  t_tradeCount, legacyCount));
         g_seenDirty = true;   // belt-and-braces; the sync tail already saved
         SaveSeenSet();
      }
   }

   RecordSnapshot();

   CollectData();
   RenderOnly();

   Print("=== TradeDashboard v1.63 (MT5) STARTED === Trades: ", t_tradeCount,
         " | Records: ", r_count,
         " | Filter: SYM='", g_filterSymbol, "' COM='", g_filterComment, "'",
         " | ReportStart: ", (g_reportStart>0 ? TimeToString(g_reportStart,TIME_DATE) : "None"));
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| v1.60 (1230 §3.2): MT4-parity profile backup & auto-restart       |
//| Ported from TradeDashboard_v1.60_final.mq4 (MT4 :344-708, :529-   |
//| 580, :1538-1580). hwnd types are `long` per the MT5 import block, |
//| chart hwnd comes from CHART_WINDOW_HANDLE, cmd temp files live in |
//| MQL5\Files, and the restart launches terminal64.exe (TERMINAL_PATH|
//| already points at it on MT5).                                     |
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
      hash += (int)StringGetCharacter(s, i);
   return hash;
}

void SaveFingerprint(int hash)
{
   int h = FileOpen(BACKUP_HASH_FILE, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE)
   {
      FileWriteString(h, IntegerToString(hash));
      FileClose(h);
   }
}

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

string GetEnvVarEA(string varName)
{
   // v1.17 (MT4): derive USERPROFILE from terminal data path first (no cmd race)
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
   string tempPath = TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL5\\Files\\_env_tmp.txt";
   StringReplace(tempPath, "/", "\\");

   // no space before '>' - classic cmd echo trap writes the space into the file
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

string ReadActiveProfile()
{
   string dp = TerminalInfoString(TERMINAL_DATA_PATH);
   StringReplace(dp, "/", "\\");
   string src = dp + "\\profiles\\lastprofile.ini";
   string tempPath = dp + "\\MQL5\\Files\\_prof_tmp.txt";

   // no space before '>' - same cmd echo trap as v1.17
   string cmd = "/C type \"" + src + "\"> \"" + tempPath + "\"";
   ShellExecuteW(0, "open", "cmd.exe", cmd, NULL, 0);
   Sleep(500);

   string prof = "Default";
   int h = FileOpen("_prof_tmp.txt", FILE_READ | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE)
   {
      if(!FileIsEnding(h))
      {
         string s = FileReadString(h);
         StringTrimLeft(s);
         StringTrimRight(s);
         if(StringLen(s) > 0) prof = s;
      }
      FileClose(h);
      FileDelete("_prof_tmp.txt");
   }
   return prof;
}

bool TriggerTerminalSaveProfile()
{
   long hChart = ChartGetInteger(0, CHART_WINDOW_HANDLE);
   if(hChart == 0) { Print("[Backup] no chart hwnd"); return false; }

   long hMain = GetAncestor(hChart, 2);   // GA_ROOT = terminal main window
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
      string t2 = ShortArrayToString(b2);
      if(t2 == "Save") { cmdSave = GetMenuItemID(hProf, k); break; }
      if(StringFind(t2, "Save") == 0 && StringFind(t2, "As") < 0)
         cmdSave = GetMenuItemID(hProf, k);
   }
   if(cmdSave <= 0) { Print("[Backup] Save menu item not found"); return false; }

   // WM_COMMAND = 0x0111, fires same as clicking File>Profiles>Save
   PostMessageW(hMain, 0x0111, cmdSave, 0);
   Print("[Backup] Profile flush triggered (menu cmd ", cmdSave, ")");
   return true;
}

bool DoProfileBackup()
{
   string dataPath = TerminalInfoString(TERMINAL_DATA_PATH);
   StringReplace(dataPath, "/", "\\");
   string profilesSrc = dataPath + "\\profiles";

   datetime now = TimeCurrent();
   MqlDateTime mdt;
   TimeToStruct(now, mdt);
   string dateStr = StringFormat("%04d%02d%02d", mdt.year, mdt.mon, mdt.day);

   string acctNum = IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN));
   string serverName = AccountInfoString(ACCOUNT_SERVER);
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
      destFolder = userProfile + "\\Downloads\\MT5\\Profiles\\" + acctNum + "_" + serverName + "_" + dateStr;
   }

   // v1.19 (MT4): flush live chart state to disk BEFORE copying
   if(TriggerTerminalSaveProfile())
      Sleep(1500);   // give terminal UI thread time to write .chr files
   else
      Print("[Backup] WARN: flush failed, copying last-saved state only");

   // v1.19 (MT4): "Save As" -> <server>_<account> snapshot profile, keep Default in sync
   string activeProfile = ReadActiveProfile();
   string activeDir = profilesSrc + "\\" + activeProfile;
   string snapName = serverName + "_" + acctNum;
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

void CheckAndBackupProfile()
{
   if(!InpAutoBackup) return;

   // Check once per day after BackupTime (minutes-of-day, server time)
   datetime now = TimeCurrent();
   MqlDateTime mdt2;
   TimeToStruct(now, mdt2);
   int nowMinute = mdt2.hour*60 + mdt2.min;
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
//| v1.20 (MT4): FX market should be open? (PC clock, HKT timezone)   |
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
//| v1.20 (MT4): restart script - kills own terminal, relaunches exe  |
//| (MT5: TERMINAL_PATH is terminal64.exe; re-login uses saved creds) |
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
   string full = dp + "\\MQL5\\Files\\TD_restart.cmd";
   ShellExecuteW(0, "open", "cmd.exe", "/C \"" + full + "\"", NULL, 0);
   Print("[RC] terminal restart triggered: ", exe);
}

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   SaveSeenSet();      // v1.60 FIX (1245): flush seen-deal tickets before shutdown
   SaveRecordsBin();
   GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
   ObjectsDeleteAll(0, PFX);
}

//+------------------------------------------------------------------+
//| OnTick                                                           |
//+------------------------------------------------------------------+
//--- v1.63 (1915 §五): remote self-test hook ported from MT4 v1.35 — the
//---   agent writes MQL5/Files/TD_tabcmd.txt ("tab=N" and/or "snap=name");
//---   read-once semantics (MT4 v1.51 FIX-TD2): the hook file is ALWAYS
//---   deleted after read, only well-formed "tab=" acts. This hook was absent
//---   from every MT5 build — the root cause of the "MT5 tabcmd no reaction"
//---   ticket (1915 §五).
datetime g_tabCmdLast=0;
void CheckTabCmd()
{
   if(TimeLocal()-g_tabCmdLast < 2) return;   // v1.49: TimeLocal (weekend-safe)
   g_tabCmdLast=TimeCurrent();
   int h=FileOpen("TD_tabcmd.txt",FILE_READ|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE) return;
   string cmd=FileReadString(h);
   FileClose(h);
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
      Print("[TD5] self-test snap ",f," tab=",g_tab);
   }
}
void OnTick()
{
   CheckTabCmd();   // v1.63 (1915 §五): agent self-test hook (MT4 v1.35 parity)
   NGDDG_Init();
   NG_Guard();
   DDG_Guard();
   DDG_ATStatusCheck();   // v1.14 T3: observe-only, never auto-restore AT
   SymbolGuard();
   NG_WindowPush();
   GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
   RecordSnapshot();
   SG_CollectSymbols();

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
//| OnTimer - keep recording + refresh alive when no ticks           |
//+------------------------------------------------------------------+
void OnTimer()
{
   //--- v1.51 TD6: account switch mid-session -> wipe and reload this account's files
   long acctNow = AccountInfoInteger(ACCOUNT_LOGIN);
   if(acctNow != g_acct && acctNow > 0)
   {
      g_acct = acctNow;
      t_tradeCount = 0;
      r_count = 0;
      r_head = 0;
      LoadRecords();
      LoadTrades();
      LoadSeenSet();   // v1.60 FIX (1245): per-account seen set follows the switch
      // v1.60 FIX (1245): same first-run rule as OnInit - a populated store
      //   without a seen-set file must be REBUILT, never merged into.
      if(!g_seenLoaded && t_tradeCount > 0)
      {
         LogEvent("V1.60 MIGRATION (account switch): rebuilding store from full history");
         t_tradeCount = 0;
         SyncTradesFromHistory();
         if(t_tradeCount == 0)
         {
            LoadTrades();
            g_seenDealN = 0; g_seenDirty = false; g_seenLoaded = false;
            LogEvent("V1.60 MIGRATION DEFERRED (account switch): legacy store kept");
         }
      }
      LogEvent("ACCT SWITCH: reloaded TD files for account " + IntegerToString(acctNow));
      Print("TD5 v1.61: account switch -> ", acctNow, ", state reloaded");
      // v1.61 (0745): 帳號變更解除 ARM — cold board on account switch
      g_bingoArmed = false;
      g_bingoPage  = 0;
   }

   //--- v1.51 TD6: sync here too. OnTick never fires on a closed market, so the
   //---   MT5 build used to stop syncing every weekend while the MT4 build did not.
   if(InpSnapshotEnable && TimeCurrent() - g_lastSnap >= 300)
   {
      SyncTradesFromHistory();
      g_lastSnap = TimeCurrent();
   }

   NGDDG_Init();
   //--- v1.46 Q4: risk guards every 1s, independent of market ticks
   NG_Guard();
   DDG_Guard();
   DDG_ATStatusCheck();
   SymbolGuard();
   NG_WindowPush();
   CheckTabCmd();   // v1.63 (1915 §五): agent self-test hook (also when no ticks)
   BINGO_Tick();    // v1.61: ARM countdown / cooldown expiry refresh (g_tab==2 only)
   GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
   SG_CollectSymbols();
   RecordSnapshot();
   if(TimeCurrent() - g_lastFull >= InpRefreshSeconds)
   {
      CollectData();
      DD_BuildSymbols();
      RenderOnly();
      g_lastFull = TimeCurrent();
   }

   //--- v1.60 (1230 §3.2, MT4 parity): daily profile backup on input change
   CheckAndBackupProfile();

   //--- v1.60 (1230 §3.2, MT4 parity): auto-reconnect watchdog - sustained
   //---   disconnect restarts terminal64.exe; cooldown + give-up live in
   //---   terminal Global Variables so they survive the restart itself.
   if(!InpAutoReconnect) return;

   if((bool)TerminalInfoInteger(TERMINAL_CONNECTED))
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

   // v1.21 (MT4): give up after N consecutive failed restarts
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

//+------------------------------------------------------------------+
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
         if(ti >= 0 && ti < 4) g_tab = ti;
         changed = true;
      }
      else if(s == PFX+"V_H")       { g_view=0; g_offset=0; changed=true; }
      else if(s == PFX+"V_D")  { g_view=1; g_offset=0; changed=true; }
      else if(s == PFX+"V_W")  { g_view=2; g_offset=0; changed=true; }
      else if(s == PFX+"V_M")  { g_view=3; g_offset=0; changed=true; }
      else if(s == PFX+"NAV_L"){ g_offset--; changed=true; }
      else if(s == PFX+"NAV_R"){ if(g_offset<0) g_offset++; changed=true; }
      else if(s == PFX+"SAVE") { ManualSaveNow(); changed=false; }
      else if(s == PFX+"DDRESET") { DDG_ResetPeakConfirm(); changed=true; }
      //--- v1.61 (1400 §三 MT5 port): BINGO CLOSE BOARD buttons ---------------
      else if(StringFind(s, PFX+"BGB_") == 0)
      {
         string bgRest = StringSubstr(s, StringLen(PFX)+4);
         int us = StringFind(bgRest, "_");
         if(us > 0)
            BINGO_Press((int)StringToInteger(StringSubstr(bgRest, 0, us)), (int)StringToInteger(StringSubstr(bgRest, us+1)));
         changed = true;
      }
      else if(s == PFX+"BGA")   { BINGO_ArmToggle(); changed = true; }
      else if(s == PFX+"BGC")   { BINGO_CloseAll();  changed = true; }
      else if(s == PFX+"BGP_L") { g_bingoPage--; if(g_bingoPage < 0) g_bingoPage = 0; changed = true; }
      else if(s == PFX+"BGP_R") { g_bingoPage++; changed = true; }
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
//| SAVE profile (writes snapshot state + logs)                      |
//+------------------------------------------------------------------+
void ManualSaveNow()
{
   SaveTrades();
   SaveRecordsBin();
   GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
   g_saveBtnFlashUntil = TimeLocal() + 3;
   LogEvent("SAVE PROFILE OK (manual) " + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
   CollectData();
   RenderOnly();
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
//| v1.60 FIX (1245 review): seen OUT-deal ticket set                |
//| Persisted per account (TD_<acct>_seen.bin) so restarts and       |
//| re-syncs never double-add the `+=` netting aggregation below.    |
//| Deals arrive in (roughly) ascending order, so the sorted insert  |
//| is append-mostly and binary search keeps lookups cheap.          |
//+------------------------------------------------------------------+
ulong  g_seenDeal[];
int    g_seenDealN  = 0;
bool   g_seenDirty  = false;
bool   g_seenLoaded = false;

string SeenFile() { return(AccountTag() + "seen.bin"); }

bool DealSeen(ulong ticket)
{
   int lo = 0, hi = g_seenDealN - 1;          // ascending binary search
   while(lo <= hi)
   {
      int mid = (lo + hi) / 2;
      if(g_seenDeal[mid] == ticket) return true;
      if(g_seenDeal[mid] < ticket) lo = mid + 1; else hi = mid - 1;
   }
   return false;
}

void MarkDealSeen(ulong ticket)
{
   if(DealSeen(ticket)) return;
   int n = ArraySize(g_seenDeal);
   if(g_seenDealN >= n) ArrayResize(g_seenDeal, MathMax(256, n * 2));
   int pos = 0;
   while(pos < g_seenDealN && g_seenDeal[pos] < ticket) pos++;
   for(int i = g_seenDealN; i > pos; i--) g_seenDeal[i] = g_seenDeal[i - 1];
   g_seenDeal[pos] = ticket;
   g_seenDealN++;
   g_seenDirty = true;
}

void LoadSeenSet()
{
   g_seenDealN = 0; g_seenDirty = false; g_seenLoaded = false;
   ArrayResize(g_seenDeal, 0);
   if(!FileIsExist(SeenFile())) return;   // first run / pre-v1.60 store
   int fh = FileOpen(SeenFile(), FILE_READ|FILE_BIN);
   if(fh == INVALID_HANDLE) return;
   int rd = (int)FileReadArray(fh, g_seenDeal, 0, WHOLE_ARRAY);  // v1.62: uint->int explicit cast (warning 43)
   FileClose(fh);
   if(rd > 0) g_seenDealN = rd;
   g_seenLoaded = true;
}

void SaveSeenSet()
{
   if(!g_seenDirty || g_seenDealN == 0) return;
   int fh = FileOpen(SeenFile(), FILE_WRITE|FILE_BIN);
   if(fh == INVALID_HANDLE) return;
   FileWriteArray(fh, g_seenDeal, 0, g_seenDealN);
   FileClose(fh);
   g_seenDirty = false;
   g_seenLoaded = true;
}

//+------------------------------------------------------------------+
//| Local Trade Snapshot System                                      |
//+------------------------------------------------------------------+
int FindTrade(long ticket)
{
   for(int i = 0; i < t_tradeCount; i++)
   {
      if(t_ticket[i] == ticket) return i;
   }
   return -1;
}

void SyncTradesFromHistory()
{
   //+------------------------------------------------------------------+
   //| v1.51 TD6: ACCUMULATING sync (was: wipe-and-rebuild 72h)         |
   //|                                                                  |
   //| Before: t_tradeCount=0 then HistorySelect(now-SnapHours, now) -> |
   //|   every 5-minute sync DELETED all trades older than 72h, so the  |
   //|   Week/Month tabs could never show more than 3 days of history   |
   //|   and TD5_trades.csv shrank instead of growing.                   |
   //|                                                                  |
   //| Now: scan the whole terminal history once, merge into the local   |
   //|   store (upsert by position id), never drop existing rows.        |
   //|   The store only grows, so W/M and MaxDD have real data.          |
   //+------------------------------------------------------------------+
   int newCount = 0;
   int updCount = 0;

   HistorySelect(0, TimeCurrent()+86400);
   int nd = HistoryDealsTotal();

   for(int i = 0; i < nd; i++)
   {
      ulong dt = HistoryDealGetTicket(i);
      if(dt == 0) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(dt, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;
      long dtype = HistoryDealGetInteger(dt, DEAL_TYPE);
      if(dtype != DEAL_TYPE_BUY && dtype != DEAL_TYPE_SELL) continue;
      string sym = HistoryDealGetString(dt, DEAL_SYMBOL);
      if(sym == "") continue;
      datetime ct = (datetime)HistoryDealGetInteger(dt, DEAL_TIME);
      if(ct == 0) continue;

      //--- v1.60 FIX (1245 review, netting): one OUT deal counts exactly
      //---   once, EVER. Without this the `+=` aggregation below would
      //---   re-add every historical deal on each restart/re-sync.
      if(DealSeen(dt)) continue;
      MarkDealSeen(dt);

      long posId = HistoryDealGetInteger(dt, DEAL_POSITION_ID);
      if(posId <= 0) posId = (long)dt;
      int idx = FindTrade(posId);
      if(idx >= 0 && MathAbs((long)t_closetime[idx] - (long)ct) > 48*3600)
      {
         posId = (long)dt;
         idx = FindTrade(posId);
      }

      double dProfit = HistoryDealGetDouble(dt, DEAL_PROFIT);
      double dSwap   = HistoryDealGetDouble(dt, DEAL_SWAP);
      double dComm   = HistoryDealGetDouble(dt, DEAL_COMMISSION);
      double dVol    = HistoryDealGetDouble(dt, DEAL_VOLUME);
      double dOpenPr = 0, dClosePr = HistoryDealGetDouble(dt, DEAL_PRICE);
      datetime dOpenTm = ct;

      if(idx >= 0)
      {
         //--- v1.60 FIX (1245 review, netting): partial closes AGGREGATE
         //---   into the same record (baseline :625-631 semantics). The
         //---   v1.51 `=` overwrite kept only the LAST partial close, so a
         //---   netting position closed in 3 OUT deals retained just deal
         //---   #3 - Week/Month/MaxDD silently understated. Idempotency is
         //---   NOT "delta recompute" (only true for a single OUT deal);
         //---   it is the deal-ticket dedup set above.
         t_lots[idx]       += dVol;
         t_profit[idx]     += dProfit;
         t_swap[idx]       += dSwap;
         t_commission[idx] += dComm;
         t_closeprice[idx]  = dClosePr;
         t_closetime[idx]   = ct;
         t_calcPnl[idx]     = t_profit[idx] + t_swap[idx] + t_commission[idx];
         updCount++;
         continue;
      }

      if(t_tradeCount >= MAX_TRADES) continue;

      long etype = dtype;
      for(int e = 0; e < nd; e++)
      {
         ulong ed = HistoryDealGetTicket(e);
         if(ed == 0 || ed == dt) continue;
         if(HistoryDealGetInteger(ed, DEAL_POSITION_ID) != posId) continue;
         ENUM_DEAL_ENTRY ee = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(ed, DEAL_ENTRY);
         if(ee == DEAL_ENTRY_IN)
         {
            dOpenPr = HistoryDealGetDouble(ed, DEAL_PRICE);
            dOpenTm = (datetime)HistoryDealGetInteger(ed, DEAL_TIME);
            etype   = HistoryDealGetInteger(ed, DEAL_TYPE);
            dComm  += HistoryDealGetDouble(ed, DEAL_COMMISSION);
            break;
         }
      }

      t_ticket[t_tradeCount]     = posId;
      t_symbol[t_tradeCount]     = sym;
      t_type[t_tradeCount]       = (etype == DEAL_TYPE_BUY) ? 0 : 1;
      t_opentime[t_tradeCount]   = dOpenTm;
      t_closetime[t_tradeCount]  = ct;
      t_openprice[t_tradeCount]  = dOpenPr;
      t_closeprice[t_tradeCount] = dClosePr;
      t_lots[t_tradeCount]       = dVol;
      t_profit[t_tradeCount]     = dProfit;
      t_swap[t_tradeCount]       = dSwap;
      t_commission[t_tradeCount] = dComm;
      t_comment[t_tradeCount]    = HistoryDealGetString(dt, DEAL_COMMENT);
      t_calcPnl[t_tradeCount]    = dProfit + dSwap + dComm;
      t_tradeCount++;
      newCount++;
   }

   if(newCount > 0 || updCount > 0)
   {
      SortTradesByClose();
      LogEvent(StringFormat("SYNC %s | New: %d | Upd: %d | Total: %d | ND: %d",
               TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
               newCount, updCount, t_tradeCount, nd));
   }

   // v1.60 FIX (1245): seen set AFTER the store - a crash in between
   //   double-counts once (visible in SYNC log, fixable by deleting the
   //   seen file to re-migrate); the reverse order would permanently
   //   SKIP deals whose store rows were lost. Recoverable > silent loss.
   SaveTrades();
   SaveSeenSet();
}

//--- keep the store ordered oldest -> newest so LoadTrades and the
//--- MaxDD walker see a stable sequence regardless of deal order
void SortTradesByClose()
{
   for(int i = 1; i < t_tradeCount; i++)
   {
      datetime kc = t_closetime[i];
      if(kc == 0) continue;
      int j = i - 1;
      while(j >= 0 && (t_closetime[j] == 0 || t_closetime[j] > kc))
      {
         t_ticket[j+1]     = t_ticket[j];
         t_symbol[j+1]     = t_symbol[j];
         t_type[j+1]       = t_type[j];
         t_opentime[j+1]   = t_opentime[j];
         t_closetime[j+1]  = t_closetime[j];
         t_openprice[j+1]  = t_openprice[j];
         t_closeprice[j+1] = t_closeprice[j];
         t_lots[j+1]       = t_lots[j];
         t_profit[j+1]     = t_profit[j];
         t_swap[j+1]       = t_swap[j];
         t_commission[j+1] = t_commission[j];
         t_comment[j+1]    = t_comment[j];
         t_calcPnl[j+1]    = t_calcPnl[j];
         j--;
      }
      t_ticket[j+1]     = t_ticket[i];
      t_symbol[j+1]     = t_symbol[i];
      t_type[j+1]       = t_type[i];
      t_opentime[j+1]   = t_opentime[i];
      t_closetime[j+1]  = t_closetime[i];
      t_openprice[j+1]  = t_openprice[i];
      t_closeprice[j+1] = t_closeprice[i];
      t_lots[j+1]       = t_lots[i];
      t_profit[j+1]     = t_profit[i];
      t_swap[j+1]       = t_swap[i];
      t_commission[j+1] = t_commission[i];
      t_comment[j+1]    = t_comment[i];
      t_calcPnl[j+1]    = t_calcPnl[i];
   }
}

void SaveTrades()
{
   //--- v1.51 TD6 safety: never overwrite a populated store with an empty
   //---   in-memory list. A dead sync used to wipe the CSV down to its header,
   //---   which is exactly how the MT4 panel lost 5,463 trades on 2026-11-07.
   string fname = TradesFile();
   if(t_tradeCount == 0 && FileIsExist(fname))
   {
      LogEvent("SAVE SKIPPED: 0 trades in memory, existing file kept");
      return;
   }

   int fh = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) return;

   FileWrite(fh, "Ticket", "Account", "Symbol", "Type", "OpenTime", "CloseTime",
             "OpenPrice", "ClosePrice", "Volume", "Profit", "Swap",
             "Commission", "CalcPnl", "Comment");

   for(int i = 0; i < t_tradeCount; i++)
   {
      FileWrite(fh,
         t_ticket[i],
         IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)),
         t_symbol[i],
         (t_type[i]==0 ? "BUY" : "SELL"),
         (long)t_opentime[i],
         (long)t_closetime[i],
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

   int fh = FileOpen(TradesFile(), FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) return;

   for(int h = 0; h < 14; h++) FileReadString(fh);   // v1.51: 14 cols (Account added)

   while(!FileIsEnding(fh) && t_tradeCount < MAX_TRADES)
   {
      string sTicket = FileReadString(fh);
      if(sTicket == "") break;

      long tkt        = StringToInteger(sTicket);
      string sAcct    = FileReadString(fh);            // v1.51 TD6: per-row account
      string sym      = FileReadString(fh);
      string sType    = FileReadString(fh);
      datetime ot     = (datetime)StringToInteger(FileReadString(fh));
      datetime ct     = (datetime)StringToInteger(FileReadString(fh));
      double op       = StringToDouble(FileReadString(fh));
      double cp       = StringToDouble(FileReadString(fh));
      double lots     = StringToDouble(FileReadString(fh));
      double prof     = StringToDouble(FileReadString(fh));
      double swp      = StringToDouble(FileReadString(fh));
      double comm     = StringToDouble(FileReadString(fh));
      double calcP    = StringToDouble(FileReadString(fh));
      string cmt      = FileReadString(fh);

      //--- 2nd line of defence: rows belonging to another account are skipped
      if(sAcct != "" && sAcct != IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))) continue;

      if(g_reportStart > 0 && ct < g_reportStart) continue;

      t_ticket[t_tradeCount]     = tkt;
      t_symbol[t_tradeCount]     = sym;
      t_type[t_tradeCount]       = (sType == "BUY") ? 0 : 1;
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
   Print("TD5 trades loaded: ", t_tradeCount, " from ", TradesFile());
}

//--- v1.51 TD6: one-time migration of the pre-1.51 shared (account-less) files.
//---   They cannot be attributed to an account, so they are parked as *.legacy
//---   and never auto-loaded; a fresh accumulating sync rebuilds per account.
void MigrateLegacySharedFiles()
{
   string src[3]; src[0]="TD5_trades.csv"; src[1]="td5_snap.bin"; src[2]="TD5_events.log";
   for(int i=0; i<3; i++)
   {
      if(!FileIsExist(src[i])) continue;
      string dst = src[i] + ".legacy";
      if(FileIsExist(dst)) FileDelete(dst);
      if(FileMove(src[i], 0, dst, 0))
         Print("TD5 v1.51 TD6: legacy shared file '", src[i], "' parked as '", dst, "'");
      else
         Print("TD5 v1.51 TD6: WARN could not park '", src[i], "' err=", GetLastError());
   }
}

void LogEvent(string msg)
{
   int fh = FileOpen(EventFile(), FILE_WRITE|FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) return;
   FileSeek(fh, 0, SEEK_END);
   FileWrite(fh, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS), msg);
   FileClose(fh);
}

//+------------------------------------------------------------------+
//| Recording functions (equity snapshots)                           |
//| MT5: tick-level AccountEquity snapshot ring buffer + binary      |
//| persistence to MQL5\Files\td5_snap.bin                            |
//+------------------------------------------------------------------+
double GetCurFloat()
{
   double f = 0;
   for(int k=0; k<PositionsTotal(); k++)
   {
      ulong tk = PositionGetTicket(k);
      if(tk == 0) continue;
      f += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   }
   return f;
}

void RecordSnapshot()
{
   datetime now = TimeCurrent();
   if(now - g_lastRec < MathMax(1, InpRecordSeconds)) return;
   // v1.50: monotonic time guard - TimeCurrent() can briefly report a stale
   // value (weekend/rollover tick); writing it poisons the ring buffer with
   // an old timestamp + current balance, corrupting Week/Month baselines
   if(r_count > 0)
   {
      int newest = (r_head - 1 + MAX_REC) % MAX_REC;
      if(now < r_dt[newest] - 60)
      {
         Print("TD5 v1.50: skip out-of-order snapshot t=", TimeToString(now),
               " (newest=", TimeToString(r_dt[newest]), ")");
         return;
      }
   }
   g_lastRec = now;

   double bal = AcctBalance();
   double eq  = AcctEquity();
   double mg  = AcctMargin();
   double fm  = AcctFreeMarg();
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

   // throttle binary flush to once per 30s
   if(TimeCurrent() - g_lastBinSave >= 30)
   {
      SaveRecordsBin();
      g_lastBinSave = TimeCurrent();
   }
}

//--- binary serialization: [magic][count][count x (dt,bal,eq,marg,fmarg,float)]
void SaveRecordsBin()
{
   int fh = FileOpen(SnapFile(), FILE_WRITE|FILE_BIN);
   if(fh == INVALID_HANDLE) return;
   FileWriteInteger(fh, SNAP_MAGIC, INT_VALUE);
   FileWriteInteger(fh, r_count, INT_VALUE);
   for(int i = 0; i < r_count; i++)
   {
      int idx = (r_head - r_count + i + MAX_REC) % MAX_REC;
      FileWriteLong(fh, (long)r_dt[idx]);
      FileWriteDouble(fh, r_bal[idx]);
      FileWriteDouble(fh, r_eq[idx]);
      FileWriteDouble(fh, r_marg[idx]);
      FileWriteDouble(fh, r_fmarg[idx]);
      FileWriteDouble(fh, r_float[idx]);
   }
   FileClose(fh);
}

//--- OnInit hydration: deserialize td5_snap.bin back into ring buffer
void LoadRecords()
{
   r_count = 0;
   r_head = 0;

   int fh = FileOpen(SnapFile(), FILE_READ|FILE_BIN);
   if(fh == INVALID_HANDLE) return;

   int magic = FileReadInteger(fh, INT_VALUE);
   if(magic != SNAP_MAGIC) { FileClose(fh); Print("TD5 snap bin: bad magic, ignored"); return; }

   int cnt = FileReadInteger(fh, INT_VALUE);
   if(cnt < 0 || cnt > MAX_REC) { FileClose(fh); return; }

   int cap = MathMin(cnt, MathMin(InpMaxRecords, MAX_REC));
   int skip = cnt - cap;   // if file has more than we keep, drop oldest

   for(int i = 0; i < cnt && !FileIsEnding(fh); i++)
   {
      datetime dt = (datetime)FileReadLong(fh);
      double bal  = FileReadDouble(fh);
      double eq   = FileReadDouble(fh);
      double mg   = FileReadDouble(fh);
      double fm   = FileReadDouble(fh);
      double fl   = FileReadDouble(fh);

      if(i < skip) continue;

      // Apply ReportStart filter
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
   Print("TD5 snap bin hydrated: ", r_count, " records");
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
//| v1.14 spec #15: REALIZED max drawdown — closed-trade PnL curve    |
//| peak-to-trough inside window, from window start balance.          |
//+------------------------------------------------------------------+
void GetRealizedMaxDD(datetime from, datetime to, double startBal, double &ddAmt, double &ddPct)
{
   datetime ctArr[5000]; double pnlArr[5000];
   int n = 0;
   for(int i = 0; i < t_tradeCount && n < 5000; i++)
   {
      if(t_closetime[i] == 0 || t_closetime[i] < from || t_closetime[i] >= to) continue;
      if(!PassesFilter(i)) continue;
      ctArr[n] = t_closetime[i]; pnlArr[n] = t_calcPnl[i]; n++;
   }
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
         datetime diff = (datetime)MathAbs((double)(r_dt[idx] - startDt));
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
         prevBal = AcctBalance();
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
      prevBal = AcctBalance();
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

         if(t_type[i] == 0) bBuy++; else bSell++;

         if(p > 0) { bw++; gW += p; } else gL += MathAbs(p);

         if(first) { bestT = p; worstT = p; first = false; }
         else { if(p > bestT) bestT = p; if(p < worstT) worstT = p; }

         string sym = t_symbol[i];
         double pt = SymPoint(sym);
         int digits = SymDigits(sym);
         double pv = (digits == 5 || digits == 3) ? pt*10 : pt;
         if(pv < 0.0000001) pv = 0.0001;

         double pips = (t_closeprice[i] - t_openprice[i]) / pv;
         if(t_type[i] == 1) pips = -pips;
         bpips += pips;
      }

      if(bn > 0 || (g_offset==0 && b==nB-1))
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

      g_cMarg[g_cNumB-1]  = AcctMargin();
      g_cFMarg[g_cNumB-1] = AcctFreeMarg();
   }
}

//+------------------------------------------------------------------+
//| Dump Summary CSV                                                 |
//+------------------------------------------------------------------+
void DumpSummaryCSV()
{
   int fh = FileOpen("TD5_summary.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) return;

   FileWrite(fh, "View","Period","Trades","Buy","Sell","WR%","Gain$","Gain%",
             "WPips","Lot","TotalLot","Balance","Margin","FreeMarg",
             "MaxP","MaxDD$","MaxDD%",
             "PF","AvgP&L","Best","Worst");

   string viewNames[4]; viewNames[0]="Time"; viewNames[1]="Date"; viewNames[2]="Week"; viewNames[3]="Month";

   datetime now = TimeCurrent();

   for(int v = 0; v < 4; v++)
   {
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

            if(t_type[i] == 0) bBuy++; else bSell++;
            if(p > 0) { bw++; gW += p; } else gL += MathAbs(p);

            if(first) { bestT = p; worstT = p; first = false; }
            else { if(p > bestT) bestT = p; if(p < worstT) worstT = p; }

            string sym = t_symbol[i];
            double pt = SymPoint(sym);
            int digits = SymDigits(sym);
            double pv = (digits == 5 || digits == 3) ? pt*10 : pt;
            if(pv < 0.0000001) pv = 0.0001;

            double pips = (t_closeprice[i] - t_openprice[i]) / pv;
            if(t_type[i] == 1) pips = -pips;
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
               viewNames[v], periodStr,
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
//| DrawChartArea - draw cumulative P&L bars                         |
//+------------------------------------------------------------------+
void DrawChartArea(int px, int py, int w, int h, int scale)
{
   HideChartBars();

   if(g_cNumB < 1) return;

   UpdTxt("CLBL", "Cumulative P&L", px+5, py, clrWhite, 7*scale);

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

   UpdRect("CZERO", px+2, zeroY, w-4, 1, C'60,70,100', C'60,70,100');

   int availW = w - 8;
   int barW = availW / g_cNumB;
   if(barW < 3) barW = 3;

   for(int i2 = 0; i2 < g_cNumB; i2++)
   {
      int barX = px + 4 + i2 * barW;
      double val = cumArr[i2];
      int barH = (int)(MathAbs(val) / range * innerH);
      if(barH < 1) barH = 1;

      int barY;
      if(val >= 0) barY = zeroY - barH;
      else         barY = zeroY;

      color bColor = (val >= 0) ? C'30,200,100' : C'220,70,70';
      UpdRect("CBAR_"+IntegerToString(i2), barX, barY, barW-1, barH, bColor, bColor);
   }
}

//+------------------------------------------------------------------+
//| v1.27: hide main-table objects when on other tabs                |
//+------------------------------------------------------------------+
void HideMainTable()
{
   string ids[] = {"TTL","SUB","AC1","AC2","S_P","S_R","FLBL","FS_EDIT","CLBL2","FC_EDIT","SAVELBL",
                   "CLBL","CZERO","SGT","SGN","FT","TABCZ","HISTW","TPH","TPC2","TPC3","TPC4","TPC5","TAX2","TAM2"};
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
   for(int g6=0;g6<14;g6++){ ObjectDelete(0,PFX+"DDC"+IntegerToString(g6)); ObjectDelete(0,PFX+"DDN"+IntegerToString(g6)); ObjectDelete(0,PFX+"DDB"+IntegerToString(g6)); ObjectDelete(0,PFX+"DDF"+IntegerToString(g6)); ObjectDelete(0,PFX+"DDP"+IntegerToString(g6)); ObjectDelete(0,PFX+"DDM"+IntegerToString(g6)); }
   ObjectDelete(0,PFX+"TDB"); ObjectDelete(0,PFX+"TDF");
   string tids[]={"TNX","TA0","TAX","TAM","TD0","TD1","TD2","TD3","TD4","TDB","TDF","TS0","TS1","TS2","TS3","TS4"};
   for(int g5=0;g5<ArraySize(tids);g5++) ObjectDelete(0,PFX+tids[g5]);
}

void TD_ClearTabContent()
{
   ObjectsDeleteAll(0, PFX+"TABCZ");
   ObjectsDeleteAll(0, PFX+"TN");  ObjectsDeleteAll(0, PFX+"TA0");
   ObjectsDeleteAll(0, PFX+"TAM"); ObjectsDeleteAll(0, PFX+"TAX");
   ObjectsDeleteAll(0, PFX+"TSY"); ObjectsDeleteAll(0, PFX+"TSG");
   for(int k=0;k<5;k++){ ObjectsDeleteAll(0, PFX+"TD"+IntegerToString(k)); ObjectsDeleteAll(0, PFX+"TS"+IntegerToString(k)); }
   ObjectsDeleteAll(0, PFX+"TDB"); ObjectsDeleteAll(0, PFX+"TDF");
   ObjectsDeleteAll(0, PFX+"TPH"); ObjectsDeleteAll(0, PFX+"TPC");
   ObjectsDeleteAll(0, PFX+"DDC"); ObjectsDeleteAll(0, PFX+"DDN");
   ObjectsDeleteAll(0, PFX+"DDB"); ObjectsDeleteAll(0, PFX+"DDF");
   ObjectsDeleteAll(0, PFX+"DDP"); ObjectsDeleteAll(0, PFX+"DDM");
   ObjectsDeleteAll(0, PFX+"TAX2"); ObjectsDeleteAll(0, PFX+"TAM2");
}

//+------------------------------------------------------------------+
//| v1.27: tab content renderers                                     |
//+------------------------------------------------------------------+
void TabRender_Alerts(int x,int y,int scale,int w)
{
   datetime now=TimeCurrent();
   UpdTxtBold("TN0","UPCOMING NEWS -> affected open symbols",x,y,clrDeepSkyBlue,10*scale);
   int ln=1;
   for(int i=0;i<g_ngEventCount && ln<9;i++)
   {
      datetime ev=NG_EvTime(g_ngEvents[i][0]);
      if(ev+InpNewsAfterMinutes*60 < now) continue;
      bool hot=(now >= ev-InpNewsBeforeMinutes*60 && now <= ev+InpNewsAfterMinutes*60);
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
   UpdTxt("TAM",StringFormat("NG mode=%s | window %dm/%dm | push on entry | tzOff %dh",(InpNewsGuardMode==0?"OFF":InpNewsGuardMode==1?"ALERT":InpNewsGuardMode==2?"BLOCK":"CLOSE"),InpNewsBeforeMinutes,InpNewsAfterMinutes,InpNewsServerOffsetHours), x, sy+15*scale+MathMax(MathMin(g_sgSymN,8),1)*15*scale, clrWhite, 9*scale);
}

// v1.29: per-symbol DD from closed-trade history (t_ arrays)
string g_ddSyms[32]; int g_ddSymN=0;
double g_ddSymDD[32];      // max DD in $
double g_ddSymDDPct[32];   // max DD as % of cumulative peak

//--- v1.61 (1400 §三 MT5 port): BINGO CLOSE BOARD state -------------------
//--- ARM is deliberately memory-only: EA reload / account switch / 60s expiry
//--- all reset it, so a stale ARM can never outlive a re-init (0745 rule).
int      g_bingoPage    = 0;     // v1.61: DDGuard table page (12 rows/page over g_ddSymN, cap 32)
datetime g_bingoCool[12][5];     // per-row per-button 30s cooldown (12 visible rows)
datetime g_bingoCoolAll = 0;     // [CLOSE 全倉] 30s cooldown
bool     g_bingoArmed   = false; // ARM gate - whole board disabled until armed
datetime g_bingoArmT    = 0;     // ARM start time (60s window)
string   g_bingoLast    = "";    // LAST action line (table tail)
string   g_bingoResidSym= "";    // last symbol with residual after close
int      g_bingoResidN  = 0;
datetime g_bingoResidT  = 0;
double g_ddSymCum[32];     // current cumulative pnl
bool g_ddUsed[MAX_TRADES];

void DD_BuildSymbols()
{
   ArrayInitialize(g_ddUsed,false);
   g_ddSymN=0;
   ArrayInitialize(g_ddSymDD,0); ArrayInitialize(g_ddSymDDPct,0); ArrayInitialize(g_ddSymCum,0);
   for(int i=0;i<t_tradeCount;i++)
   {
      string sym=t_symbol[i];
      bool f1=false;
      for(int j=0;j<g_ddSymN;j++) if(g_ddSyms[j]==sym){f1=true;break;}
      if(!f1 && g_ddSymN<32){ g_ddSyms[g_ddSymN]=sym; g_ddSymN++; }
   }
   // also live positions not yet in t_ list
   for(int p4=0;p4<PositionsTotal();p4++)
   {
      ulong tk=PositionGetTicket(p4);
      if(tk==0) continue;
      string sym2=PositionGetString(POSITION_SYMBOL);
      bool f2=false;
      for(int j2=0;j2<g_ddSymN;j2++) if(g_ddSyms[j2]==sym2){f2=true;break;}
      if(!f2 && g_ddSymN<32){ g_ddSyms[g_ddSymN]=sym2; g_ddSymN++; }
   }
   // walk trades in close-time order per symbol, track cumulative peak/trough
   for(int j=0;j<g_ddSymN;j++)
   {
      string sym=g_ddSyms[j];
      double cum=0, peak=0, maxdd=0;
      for(int pass=0; pass<t_tradeCount; pass++)
      {
         datetime bestT=0; int bestI=-1;
         for(int i=0;i<t_tradeCount;i++)
         {
            if(t_symbol[i]!=sym) continue;
            if(g_ddUsed[i]) continue;
            datetime ct=(t_closetime[i]==0)?TimeCurrent()+1:t_closetime[i];
            if(ct>bestT) { bestT=ct; bestI=i; }
         }
         if(bestI<0) break;
         double pnl=(t_closetime[bestI]==0)?t_calcPnl[bestI]:(t_profit[bestI]+t_swap[bestI]+t_commission[bestI]);
         cum += pnl;
         g_ddUsed[bestI]=true;
         if(cum>peak) peak=cum;
         if(peak-cum>maxdd) maxdd=peak-cum;
      }
      g_ddSymCum[j]=cum; g_ddSymDD[j]=maxdd;
      // v1.60 FIX (1425 §三-1): % denominator is DDG_Base() balance - the same
      //   base as the DD-now column, NOT the realized-P/L curve peak (tiny on
      //   losing symbols -> absurd percentages). peak=0 branch gone too.
      double mbase = DDG_Base();
      g_ddSymDDPct[j]=(mbase>0)?maxdd/mbase*100:0.0;
   }
}

//================= v1.61 FIX (1400 §三 MT5 port): BINGO CLOSE BOARD =========
// 覆蓋 0745 信全部硬約束（MT4 v1.54/v1.60 同源，Order 引擎移植為 Position）：
//   - 平倉只准即時重掃 PositionsTotal()，禁 t_ 陣列；行標籤 = DDGuard 表行
//     (v1.60 1400 §三 ruling：g_ddSyms[page*12+row] 只做行標籤，關倉路徑 live rescan)
//   - ARM 60s 倒數未 ARM 全板禁用灰；到期自動失效；切 TAB／帳號變更解除
//   - 每按鈕獨立 30s 冷卻；橙紅色；即按即執行無延遲；殘留顯示 RESID n（LAST 行）
//   - 底部 LAST 行；[CLOSE 全倉] 含刪除全部 pending（MT5 OrdersTotal = pending 集）
// MT5 語義差異（REPORT 記錄）：WIN/LOSE 以 POSITION_PROFIT+SWAP 分類
//   （MT5 commission 落 deals 唔落 position，與 Float$ 欄同口徑）。
string BINGO_BtnName(int b)
{
   if(b == 0) return("BUY");
   if(b == 1) return("SELL");
   if(b == 2) return("WIN");
   if(b == 3) return("LOSE");
   return("ALL");
}

//--- count open positions matching a BINGO mode (live rescan, never caches)
int BINGO_CountMatch(int mode, string sym)
{
   int n = 0;
   for(int p = PositionsTotal()-1; p >= 0; p--)
   {
      ulong tk = PositionGetTicket(p);
      if(tk == 0) continue;
      if(mode != 5 && PositionGetString(POSITION_SYMBOL) != sym) continue;
      long pty = PositionGetInteger(POSITION_TYPE);
      if(mode == 0 && pty != POSITION_TYPE_BUY)  continue;
      if(mode == 1 && pty != POSITION_TYPE_SELL) continue;
      double pf = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      if(mode == 2 && pf <= 0) continue;                // WIN = floating profit
      if(mode == 3 && pf >= 0) continue;                // LOSE = floating loss
      n++;
   }
   return(n);
}

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
//--- v1.61: row = DDGuard table visible row on the current page; symbol =
//--- g_ddSyms[page*12+row] (row label only). Close path = LIVE rescan at
//--- press time via DDG_CloseMatch — 0745 hard rule, never caches.
void BINGO_Press(int row, int b)
{
   if(row < 0 || row >= 12 || b < 0 || b >= 5) return;
   if(!g_bingoArmed) return;                                            // 未 ARM 全板禁用
   if(TimeCurrent() > g_bingoArmT + 60) { g_bingoArmed = false; return; } // 到期自動失效
   if(TimeCurrent() - g_bingoCool[row][b] < 30) return;                 // 每按鈕獨立冷卻 30s
   int idx = g_bingoPage * 12 + row;                                    // v1.61: table row
   if(idx >= g_ddSymN || idx >= 32) return;
   string sym = g_ddSyms[idx];
   int closed = BINGO_CountMatch(b, sym);
   if(closed == 0) return;                                              // 該範圍無單，唔燒冷卻
   double balBefore = AcctBalance();
   int residual = DDG_CloseMatch(b, sym);
   double realized = AcctBalance() - balBefore;
   g_bingoCool[row][b] = TimeCurrent();
   if(residual > 0) { g_bingoResidSym = sym; g_bingoResidN = residual; g_bingoResidT = TimeCurrent(); }
   else if(sym == g_bingoResidSym) { g_bingoResidSym = ""; g_bingoResidN = 0; }
   // v1.61: RESID lives in the LAST line (0745: residual must stay visible)
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
   double balBefore = AcctBalance();
   int residual = DDG_CloseMatch(5, "");
   double realized = AcctBalance() - balBefore;
   g_bingoCoolAll = TimeCurrent();
   g_bingoLast = StringFormat("LAST: CLOSE全倉 %d張 %+.2f @%s", closed, realized, TimeToString(TimeCurrent(), TIME_MINUTES))
             + (residual > 0 ? StringFormat(" ⚠RESID %d!", residual) : "");
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
      for(int i = 0; i < 12 && !busy; i++)
         for(int b = 0; b < 5; b++)
            if(TimeCurrent() - g_bingoCool[i][b] < 30) { busy = true; break; }
   if(!busy && TimeCurrent() - g_bingoCoolAll < 30) busy = true;
   if(!busy && g_bingoResidN > 0 && TimeCurrent() - g_bingoResidT < 60) busy = true;
   if(busy) RenderOnly();
}

//+------------------------------------------------------------------+
//| v1.61: DDG_CloseMatch — MT5 port of the MT4 retry-until-zero     |
//| close executor. mode 0=BUY 1=SELL 2=WIN 3=LOSE 4=SYM-ALL(keeps   |
//| pending) 5=GLOBAL(all positions + delete ALL pending).           |
//| Live rescans PositionsTotal()/OrdersTotal() only, never t_* arr. |
//| MT5: CTrade trade.PositionClose / trade.OrderDelete; WIN/LOSE    |
//| split on POSITION_PROFIT+SWAP (commission lives on deals).       |
//+------------------------------------------------------------------+
int DDG_CloseMatch(int mode, string sym)
{
   bool global  = (mode == 5);
   bool delPend = (mode == 5);          // v1.61: MT5 has no legacy mode-6 caller
   int retries = MathMax(1, InpDdgCloseRetry);
   int residual = 9999;
   for(int r = 0; r < retries; r++)
   {
      if(delPend)
      {
         for(int p = OrdersTotal()-1; p >= 0; p--)
         {
            ulong ot = OrderGetTicket(p);
            if(ot == 0) continue;
            if(!trade.OrderDelete(ot))
               Print("DDG close-match pending-del fail #", ot, " ret=", trade.ResultRetcode());
         }
      }
      for(int p2 = PositionsTotal()-1; p2 >= 0; p2--)
      {
         ulong tk = PositionGetTicket(p2);
         if(tk == 0) continue;
         if(!global && PositionGetString(POSITION_SYMBOL) != sym) continue;
         long pty = PositionGetInteger(POSITION_TYPE);
         if(mode == 0 && pty != POSITION_TYPE_BUY)  continue;
         if(mode == 1 && pty != POSITION_TYPE_SELL) continue;
         double pf = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
         if(mode == 2 && pf <= 0) continue;   // WIN = floating profit
         if(mode == 3 && pf >= 0) continue;   // LOSE = floating loss
         if(!trade.PositionClose(tk))
            Print("DDG close-match fail #", tk, " ret=", trade.ResultRetcode());
      }
      Sleep(150);
      residual = 0;
      for(int p3 = PositionsTotal()-1; p3 >= 0; p3--)
      {
         ulong tk3 = PositionGetTicket(p3);
         if(tk3 == 0) continue;
         if(!global && PositionGetString(POSITION_SYMBOL) != sym) continue;
         long pty3 = PositionGetInteger(POSITION_TYPE);
         if(mode == 0 && pty3 != POSITION_TYPE_BUY)  continue;
         if(mode == 1 && pty3 != POSITION_TYPE_SELL) continue;
         double pf3 = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
         if(mode == 2 && pf3 <= 0) continue;
         if(mode == 3 && pf3 >= 0) continue;
         residual++;
      }
      if(residual == 0) break;
   }
   return residual;
}

void TabRender_DDG(int x,int y,int scale,int w)
{
   double eq=AcctEquity();
   double base=DDG_Base();     // v1.47 Q6: same Balance denominator as the guards
   double dd=MathMax(0.0,(g_ddgPeakEquity>0)?(g_ddgPeakEquity-eq)/base*100:0);   // v1.60 (1425 §三-2): clamp, never negative
   UpdTxtBold("TD0","DDGuard - Account Drawdown",x,y,clrDeepSkyBlue,10*scale);
   UpdTxt("TD1",StringFormat("Peak $%.2f | Eq $%.2f | DD %.2f%% (limit %.1f%% / $%.2f)",g_ddgPeakEquity,eq,dd,InpDdgAccountMaxPercent,InpDdgAccountMaxMoney),x,y+16*scale,clrWhite,9*scale);   // v1.60 §3.3: both limits
   UpdTxt("TD4",StringFormat("Acc: %s | Sym: %s | SymMaxDD: %.1f%% / $%.2f | Lock: %dmin",(InpDdgAccountEnable?"ON":"OFF"),(InpDdgSymbolEnable?"ON":"OFF"),InpDdgSymbolMaxPercent,InpDdgSymbolMaxMoney,InpDdgLockMinutes),x,y+31*scale,clrKhaki,9*scale);   // v1.60 §3.3
   int bw=w-20;
   UpdRect("TDB", x, y+44*scale, bw, 10*scale, C'40,50,80', C'40,50,80');
   double pct=MathMin(1.0, dd/InpDdgAccountMaxPercent);
   color bc=(pct>=1.0)?clrRed:(pct>=0.7?clrYellow:clrLime);
   UpdRect("TDF", x, y+44*scale, (int)(bw*pct), 10*scale, bc, bc);

   //--- v1.37: aligned column table, one row per traded symbol ---
   //--- v1.61 (1400 §三 MT5 port): CLOSE buttons INLINE — five buttons per
   //--- row right of MaxDD$; ARM + pager live in the table header, LAST in
   //--- the tail (MT4 v1.60 parity, direct translation).
   //--- v1.63 (1915 §一/§二, boss 19:04): five-button column RIGHT-ALIGNED to
   //---   the panel edge; ARM renamed UNLOCK/LOCK (1925); [CLOSE ALL] moved to
   //---   the header beside UNLOCK, pure-ASCII label (MQL button font mangles CJK).
   int ty = y + 96*scale;   // v1.49: table pushed down, fixed reset-block above
   double bal = DDG_Base(); if(bal <= 0) bal = 1;
   int c1 = x + 8*scale;
   int c2 = x + 100*scale;
   int c3 = x + 175*scale;
   int c4 = x + 250*scale;
   int c5 = x + 320*scale;
   int bx0 = x + w - 6*scale - 185*scale;   // v1.63r3 (2305): five-button column +65s flush-right (boss 6DB4 pixel: gap 71px -> ~6px; was -250s)
   int rows = 12;                 // v1.61: rows per page (12 over g_ddSymN, cap 32 => max 3 pages)
   int pages = (g_ddSymN + rows - 1) / rows;
   if(pages < 1) pages = 1;
   if(g_bingoPage >= pages) g_bingoPage = pages - 1;
   if(g_bingoPage < 0) g_bingoPage = 0;
   int row0 = g_bingoPage * rows;
   UpdTxtBold("TPH", "SYMBOL",   c1, ty, clrDeepSkyBlue, 9*scale);
   UpdTxtBold("TPC2","Float $",  c2, ty, clrDeepSkyBlue, 9*scale);
   UpdTxtBold("TPC3","DD now %", c3, ty, clrDeepSkyBlue, 9*scale);
   UpdTxtBold("TPC4","MaxDD %",  c4, ty, clrDeepSkyBlue, 9*scale);
   UpdTxtBold("TPC5","MaxDD $",  c5, ty, clrDeepSkyBlue, 9*scale);
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
      int i2 = k - row0;               // v1.61: visible row index (object suffix)
      int ry2=ty+16*scale+i2*15*scale;
      double fl=0;
      for(int p3=PositionsTotal()-1;p3>=0;p3--)
      {
         ulong tk=PositionGetTicket(p3);
         if(tk==0) continue;
         if(PositionGetString(POSITION_SYMBOL)!=g_ddSyms[k]) continue;
         fl += PositionGetDouble(POSITION_PROFIT)+PositionGetDouble(POSITION_SWAP);
      }
      double ddNow = MathMax(0.0, -fl/bal*100.0);   // v1.60 (1425 §三-2): clamp display
      color cFl  = (fl>=0)?clrLime:clrTomato;
      color cDn  = (ddNow>=InpDdgSymbolMaxPercent)?clrRed:(ddNow>=InpDdgSymbolMaxPercent*0.7?clrYellow:clrWhite);
      color cMx  = (g_ddSymDDPct[k]>=InpDdgSymbolMaxPercent)?clrRed:(g_ddSymDDPct[k]>=InpDdgSymbolMaxPercent*0.7?clrYellow:clrKhaki);
      UpdTxt("DDN"+IntegerToString(i2), g_ddSyms[k], c1, ry2, clrWhite, 9*scale);
      UpdTxt("DDF"+IntegerToString(i2), StringFormat("%+.2f", fl), c2, ry2, cFl, 9*scale);
      UpdTxt("DDP"+IntegerToString(i2), StringFormat("%.2f%%", ddNow), c3, ry2, cDn, 9*scale);
      UpdTxt("DDM"+IntegerToString(i2), StringFormat("%.2f%%", g_ddSymDDPct[k]), c4, ry2, cMx, 9*scale);
      UpdTxt("DDC"+IntegerToString(i2), StringFormat("%.2f", g_ddSymDD[k]), c5, ry2, cMx, 9*scale);
      // v1.61 (1400 §三): inline [BUY][SELL][WIN][LOSE][ALL] for this row's
      //   symbol — identical semantics to the MT4 v1.60 inline buttons.
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
   // v1.61: hide stale row objects on shorter pages (page 2+ tails)
   for(int i3=0; i3<rows; i3++)
   {
      if(row0 + i3 < g_ddSymN) continue;
      HideObj("DDN"+IntegerToString(i3)); HideObj("DDF"+IntegerToString(i3)); HideObj("DDP"+IntegerToString(i3));
      HideObj("DDM"+IntegerToString(i3)); HideObj("DDC"+IntegerToString(i3));
      for(int b3=0; b3<5; b3++) HideObj("BGB_"+IntegerToString(i3)+"_"+IntegerToString(b3));
   }
   int shown = MathMin(g_ddSymN - row0, rows); if(shown < 0) shown = 0;
   if(g_ddSymN==0) UpdTxt("TAX2","(no traded symbols yet)",x+8*scale,ty+16*scale,clrKhaki,9*scale);
   // v1.63 (1915 §二): table tail — LAST only ([CLOSE ALL] moved to the header)
   int ly = ty + 18*scale + shown*15*scale;
   UpdTxt("BGL", (g_bingoLast == "" ? "LAST: -" : g_bingoLast), x, ly, clrKhaki, 9*scale);
   // v1.60 (1230 §3.4): Gain definition note - MT5 Gain is broker-true
   //   DEAL_PROFIT+SWAP+COMMISSION (MT4 recomputes from prices).
   //   v1.61: note moved below the CLOSE tail; WIN/LOSE split uses
   //   POSITION_PROFIT+SWAP (MT5 commission lives on deals, not positions).
   UpdTxt("TAM2","DD now = live floating loss / balance | MaxDD = historical peak decline | base = balance | Gain = broker-true P/L (profit+swap+comm)", x, ly + 16*scale, clrKhaki, 8*scale);
   // v1.14 T3: manual confirm / reset-peak button
   int by = y + 58*scale;   // v1.49: FIXED below progress bar (was floating y+284*scale, fell outside panel)
   bool needConfirm = (g_ddgAccountArmed || g_tdStoppedAT || TimeCurrent() < g_ddgLockUntil);
   if(needConfirm)
   {
      UpdTxtBold("DDRESETLBL","⚠️ RISK LOCKED — verify manually, then press [Confirm / Reset Peak]",x,by,clrOrangeRed,9*scale);
      UpdBtn("DDRESET","[ Confirm / Reset Peak ]",x+w-230*scale,by+16*scale,220*scale,16*scale,true);
   }
   else UpdBtn("DDRESET","[ Reset Peak ]",x+w-230*scale,by+16*scale,220*scale,16*scale,false);
}

void TabRender_Set(int x,int y,int scale,int w)
{
   UpdTxtBold("TS0","Settings Quick View (change via EA inputs)",x,y,clrDeepSkyBlue,10*scale);
   UpdTxt("TS1",StringFormat("Refresh: %ds   Record: %ds   Scale: %d   Chart: %s",InpRefreshSeconds,InpRecordSeconds,InpPanelScale,(InpShowPnlChart?"ON":"OFF")),x,y+16*scale,clrWhite,9*scale);
   UpdTxt("TS2",StringFormat("SymbolGuard: %s   DefaultMode: %s   NG tzOff: %dh",(InpSymbolGuardEnable?"ON":"OFF"),SG_ModeName(InpSymbolGuardMode),InpNewsServerOffsetHours),x,y+30*scale,clrWhite,9*scale);
   UpdTxt("TS3",StringFormat("Snapshot: %s   Records: %d / %d",(InpSnapshotEnable?"ON":"OFF"),r_count,InpMaxRecords),x,y+44*scale,clrWhite,9*scale);
   UpdTxt("TS4","Tip: click tabs to switch. Guard tab = per-symbol ON/ALERT/BLOCK/CLOSE (CLOSE needs 2nd press).",x,y+59*scale,clrWhite,9*scale);
}

//+------------------------------------------------------------------+
//| RenderOnly                                                       |
//+------------------------------------------------------------------+
void RenderOnly()
{
   int scale = MathMax(1, MathMin(3, InpPanelScale));
   int px = 10;
   int py = 18;
   int padR = 15;

   string vn[4]; vn[0]="Hour"; vn[1]="Day"; vn[2]="Week"; vn[3]="Month";
   string viewLabel = (g_offset==0) ? vn[g_view]+" (Latest)" : StringFormat("%s %+d", vn[g_view], g_offset);

   double tPnl=0, tPips=0, tLots=0;
   int tN=0, tW=0, tBuy=0, tSell=0;
   for(int i=0; i<g_cNumB; i++)
   {
      tPnl+=g_cPnl[i]; tPips+=g_cPips[i]; tLots+=g_cLots[i];
      tN+=g_cN[i]; tW+=g_cW[i]; tBuy+=g_cBuy[i]; tSell+=g_cSell[i];
   }
   double tWR=(tN>0) ? 100.0*tW/tN : 0;

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
   if(g_tab==2 && panelW<620*scale) panelW=620*scale;   // v1.61: DDGuard hosts inline CLOSE button column (MT4 v1.60 parity)
   int chartWpx=(int)ChartGetInteger(0,CHART_WIDTH_IN_PIXELS,0);
   if(chartWpx>100 && panelW>chartWpx-20) panelW=chartWpx-20;   // v1.33 clamp

   int rowH=14*scale, headerH=124*scale, btnH=18*scale;

   int maxRows=MathMin(10, g_cNumB);
   if(maxRows<1) maxRows=1;

   int chartH=InpShowPnlChart ? 60*scale : 0;
   int panelH=headerH+chartH+18+maxRows*rowH+40;
   // v1.39: non-Positions tabs need their own height
   int tabNeedH = 0;
   if(g_tab != 0)
   {
      tabNeedH = (14 + 17) + 8;
      if(g_tab == 2)
         tabNeedH = tabNeedH + 96*scale + 16*scale + ((g_ddSymN>0)?12:0)*15*scale + 18*scale + 34*scale + 12;   // v1.61: fixed 12-row pages + LAST/[CLOSE 全倉] tail + Gain note (was MathMin(g_ddSymN,12))
      else if(g_tab == 1)
         tabNeedH = tabNeedH + 8*14*scale + 8*16*scale + 40*scale + 12;
      else
         tabNeedH = tabNeedH + 70*scale + 12;
      if(tabNeedH > panelH) panelH = tabNeedH;
   }

   UpdRect("BG", px, py, panelW, panelH, C'16,21,46', C'40,50,80');

   //--- v1.27: TAB bar (top-right) ---
   string tabNames[4]; tabNames[0]="Positions"; tabNames[1]="Alerts"; tabNames[2]="DDGuard"; tabNames[3]="Set";
   int tbW=64*scale, tbH=14*scale;
   int tbx=px+panelW-4-(tbW+3)*4, tby=py+2;
   for(int t=0;t<4;t++)
   {
      UpdBtn("TAB"+IntegerToString(t), tabNames[t], tbx, tby, tbW, tbH, (g_tab==t));
      tbx+=tbW+3;
   }
   int tabY=tby+tbH+3;

   //--- v1.27: non-Positions tabs draw own panel and skip main table ---
   if(g_tab != 0)
   {
      int czY=tabY+4, czH=panelH-(czY-py)-8;
      HideMainTable();
      TD_ClearTabContent();
      UpdRect("TABCZ", px+6, czY, panelW-12, czH, C'12,16,36', C'40,50,80');
      if(g_tab==1)      { SG_CollectSymbols(); TabRender_Alerts(px+14, czY+6, scale, panelW-28); }
      else if(g_tab==2) { DD_BuildSymbols(); TabRender_DDG(px+14, czY+6, scale, panelW-28); }
      else              TabRender_Set(px+14, czY+6, scale, panelW-28);
      ChartRedraw();
      return;
   }
   TD_ClearTabContent();

   //--- Left side header
   int lh = 16*scale;
   int ttlY=py+2+14*scale+4;
   UpdTxtBold("TTL", InpTitleLine1, px+4, ttlY, clrLime, 13*scale);
   if(g_histTruncated) UpdTxt("HISTW", "HIST truncated! Check history range", px+170*scale, ttlY, clrOrangeRed, 8*scale); else ObjectDelete(0,PFX+"HISTW");
   UpdTxtBold("SUB", InpTitleLine2, px+4, ttlY+lh, clrLime, 10*scale);
   int acY = ttlY+lh*2;
   UpdTxt("AC1", StringFormat("AC: %I64d  |  Balance: $%.2f  |  Equity: $%.2f",
      AccountInfoInteger(ACCOUNT_LOGIN), AcctBalance(), AcctEquity()),
      px+4, acY, clrWhite, 9*scale);
   UpdTxt("AC2", StringFormat("Free Margin: $%.2f  |  Margin: $%.2f  |  Snap: %d trades",
      AcctFreeMarg(), AcctMargin(), t_tradeCount),
      px+4, acY+lh, clrWhite, 9*scale);
   int spY = acY+lh*2;
   color pClr=(tPnl>=0) ? clrLimeGreen : clrTomato;
   UpdTxt("S_P", StringFormat("P&L: $%+.2f", tPnl), px+4, spY, pClr, 9*scale);
   UpdTxt("S_R", StringFormat("  WR: %.1f%%  Buy: %d  Sell: %d  WPips: %.0f  Lots: %.2f  [%s]",
      tWR, tBuy, tSell, tPips, tLots, viewLabel),
      px+150*scale, spY, clrWhite, 9*scale);

   //--- Right side: H/D/W/M buttons + paging + filter
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
   UpdTxt("FLBL", "Symbol:", bx, fY, clrWhite, 8*scale);
   EnsureEdit("FS_EDIT", g_filterSymbol, bx+42*scale, fY-2, 90*scale, 16*scale);
   UpdTxt("CLBL2", "Comment:", bx+140*scale, fY, clrWhite, 8*scale);
   EnsureEdit("FC_EDIT", g_filterComment, bx+190*scale, fY-2, 70*scale, 16*scale);

   //--- SAVE PROFILE button
   int sY2 = fY + 18*scale;
   bool saveFlash = (TimeLocal() < g_saveBtnFlashUntil);
   UpdBtn("SAVE","SAVE", bx, sY2, 56*scale, btnH, saveFlash);
   if(saveFlash)
   {
      ObjectSetInteger(0, PFX+"SAVE", OBJPROP_BGCOLOR, clrLime);
      ObjectSetInteger(0, PFX+"SAVE", OBJPROP_COLOR, clrBlack);
   }
   UpdTxt("SAVELBL", "PROFILE SNAPSHOT", bx+62*scale, sY2+2, clrKhaki, 8*scale);

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
   for(int c2=0; c2<NC; c2++)
   {
      string nm="H"+IntegerToString(c2);
      if(g_vis[c2]) UpdTxt(nm, g_name[c2], colX[c2], yPos, clrWhite, 8*scale);
      else HideObj(nm);
   }
   yPos+=16*scale;

   // Data rows
   for(int r=0; r<10; r++)
   {
      int idx=g_cNumB-1-r;
      int ry=yPos+r*rowH;
      string pp="D"+IntegerToString(r);

      if(idx < 0)
      {
         for(int c3=0; c3<NC; c3++) HideObj(pp+"_"+IntegerToString(c3));
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

      UpdCell(pp+"_0",  tStr, colX[0], ry, clrWhite, f8(scale), g_vis[0]);
      UpdCell(pp+"_1",  IntegerToString(g_cN[idx]), colX[1], ry, clrWhite, f8(scale), g_vis[1]);
      UpdCell(pp+"_2",  bsStr, colX[2], ry, clrDeepSkyBlue, f8(scale), g_vis[2]);
      UpdCell(pp+"_3",  DoubleToString(bwr,0)+"%", colX[3], ry, cWR, f8(scale), g_vis[3]);
      UpdCell(pp+"_4",  "$"+DoubleToString(g_cPnl[idx],2), colX[4], ry, cPnl, f8(scale), g_vis[4]);
      UpdCell(pp+"_5",  StringFormat("%.2f%%",g_cGPct[idx]), colX[5], ry, cGP, f8(scale), g_vis[5]);
      UpdCell(pp+"_6",  DoubleToString(g_cPips[idx],0), colX[6], ry, clrWhite, f8(scale), g_vis[6]);
      UpdCell(pp+"_7",  DoubleToString(g_cLots[idx],2), colX[7], ry, clrWhite, f8(scale), g_vis[7]);
      UpdCell(pp+"_8",  DoubleToString(g_cTLots[idx],2), colX[8], ry, clrWhite, f8(scale), g_vis[8]);
      UpdCell(pp+"_9",  "$"+DoubleToString(g_cBal[idx],2), colX[9], ry, clrWhite, f8(scale), g_vis[9]);
      UpdCell(pp+"_10", (g_cMarg[idx]>0?"$"+DoubleToString(g_cMarg[idx],2):"-"), colX[10], ry, clrWhite, f8(scale), g_vis[10]);
      UpdCell(pp+"_11", (g_cFMarg[idx]>0?"$"+DoubleToString(g_cFMarg[idx],2):"-"), colX[11], ry, clrWhite, f8(scale), g_vis[11]);
      UpdCell(pp+"_12", (g_cFMaxPos[idx]>0?"$"+DoubleToString(g_cFMaxPos[idx],2):"-"), colX[12], ry, cFMP, f8(scale), g_vis[12]);
      UpdCell(pp+"_13", (g_cFMaxNeg[idx]<0?"$"+DoubleToString(g_cFMaxNeg[idx],2):"-"), colX[13], ry, cFMN, f8(scale), g_vis[13]);
      UpdCell(pp+"_14", DoubleToString(g_cPF[idx],2), colX[14], ry, clrWhite, f8(scale), g_vis[14]);
      UpdCell(pp+"_15", "$"+DoubleToString(g_cAvgP[idx],2), colX[15], ry, cAvg, f8(scale), g_vis[15]);
      UpdCell(pp+"_16", "$"+DoubleToString(g_cBest[idx],2), colX[16], ry, cB, f8(scale), g_vis[16]);
      UpdCell(pp+"_17", "$"+DoubleToString(g_cWorst[idx],2), colX[17], ry, cW, f8(scale), g_vis[17]);
      UpdCell(pp+"_18", (g_cMaxDD[idx]>0?"$"+DoubleToString(g_cMaxDD[idx],2):"$0.00"), colX[18], ry, cDD, f8(scale), g_vis[18]);
      UpdCell(pp+"_19", (g_cMaxDDPct[idx]>0?DoubleToString(g_cMaxDDPct[idx],1)+"%":"0.0%"), colX[19], ry, cDDP, f8(scale), g_vis[19]);
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
      px+10, yPos, clrWhite, 7*scale);

   yPos+=14*scale;
   SG_Render(px+10, yPos, scale);

   DumpSummaryCSV();
   ChartRedraw();
}

int f8(int scale){ return 8*scale; }

//+------------------------------------------------------------------+
//| Object helpers (MT5: direct ObjectSetInteger/String)             |
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
   ObjectSetString(0,o,OBJPROP_TEXT,txt);
   ObjectSetInteger(0,o,OBJPROP_TIMEFRAMES,OBJ_ALL_PERIODS);
}

//+------------------------------------------------------------------+
//| Symbol Guard v1.25                                               |
//+------------------------------------------------------------------+
string  g_sgSym[64]; int g_sgSymN=0;
datetime g_sgAlertT[64];
ulong   g_sgKnownTickets[4096]; int g_sgKnownN=0;

//--- v1.47 Q7: 4 states: 0=ON 1=ALERT 2=BLOCK(new only) 3=CLOSE(old+new)
string SG_ModeName(int m)
{
   if(m == 0) return("ON");
   if(m == 1) return("ALERT");
   if(m == 2) return("BLOCK");
   return("CLOSE");
}
//--- v1.47 Q8: temporary NewsGuard mode, auto-expires at window end
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
   for(int i=0;i<PositionsTotal() && g_sgSymN<64;i++)
   {
      ulong tk=PositionGetTicket(i);
      if(tk==0) continue;
      string s=PositionGetString(POSITION_SYMBOL);
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
      for(int oc = 0; oc < PositionsTotal(); oc++)
      {
         if(PositionGetTicket(oc) == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != cs) continue;
         open++;
      }
      if(open == 0) continue;
      int resid = DDG_CloseSymbolWithRetry(cs);
      Print("SG[", cs, "] CLOSE mode: closed old positions, residual=", resid);
      TG_Notify("SG_CLOSE_LOOP_"+cs, "🔒 SymbolGuard CLOSE — " + cs + "\n▪ Re-closed " + IntegerToString(open) + " position(s) (old/new)" + (resid>0?"\n⚠ Residual "+IntegerToString(resid):" ✅"));
   }

   for(int i=0;i<PositionsTotal();i++)
   {
      ulong tk=PositionGetTicket(i);
      if(tk==0) continue;
      bool known=false;
      for(int kk=0;kk<g_sgKnownN;kk++) if(g_sgKnownTickets[kk]==tk){known=true;break;}
      if(known) continue;
      if(g_sgKnownN<4096){g_sgKnownTickets[g_sgKnownN]=tk;g_sgKnownN++;}
      { ulong opened=(ulong)PositionGetInteger(POSITION_TIME); ulong ageSec=(ulong)TimeCurrent()-opened; if(ageSec>120) continue; }
      string sym=PositionGetString(POSITION_SYMBOL);
      int mode=SG_EffMode(sym);
      if(mode==0) continue;
      long ptype=PositionGetInteger(POSITION_TYPE);
      double lots=PositionGetDouble(POSITION_VOLUME);
      string msg;
      if(mode==1)
         msg=StringFormat("SG[%s] ALERT: new %s #%I64u %.2f lots",
                sym, (ptype==POSITION_TYPE_BUY?"BUY":"SELL"), tk, lots);
      else
      {
         msg=StringFormat("SG[%s] %s: %s #%I64u %.2f lots closed by guard",
                sym, (mode==2?"BLOCK":"CLOSE"), (ptype==POSITION_TYPE_BUY?"BUY":"SELL"), tk, lots);
         if(!trade.PositionClose(tk))
            msg=msg+" [close FAILED ret "+IntegerToString(trade.ResultRetcode())+"]";
      }
      Print(msg);
      SendNotification(msg);
      for(int fi=0; fi<g_sgSymN; fi++) if(g_sgSym[fi]==sym) { g_sgAlertT[fi]=TimeCurrent(); break; }
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
      if(!(i<64 && g_sgAlertT[i]>0 && TimeCurrent()-g_sgAlertT[i] < 60) && NG_SymbolHot(s))
      {
         int phn=(int)(TimeCurrent()%2);
         bg = (phn==0)?clrRed:C'255,140,0';
         fg = clrWhite;
         lbl = s+" N!";
      }
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
   else ObjectDelete(0,PFX+"SGN");
}

//+------------------------------------------------------------------+
//| v1.23 NewsGuard + DDGuard module                                 |
//+------------------------------------------------------------------+
void NGDDG_Init()
{
   if(__ng_init_done) return;
   __ng_init_done = 1;
   TD_CheckHistoryDepth();
   for(int v = GlobalVariablesTotal()-1; v >= 0; v--)
   {
      string n = GlobalVariableName(v);
      if(StringFind(n, "TD5_NEWSGUARD_") == 0) GlobalVariableDel(n);
   }
   if(GlobalVariableCheck(DDG_PeakKey()))
      g_ddgPeakEquity = GlobalVariableGet(DDG_PeakKey());
   DDG_LoadState();   // v1.47 Q9: restore armed / lock-until / AT-stopped
}

void TD_CheckHistoryDepth()
{
   g_histTruncated = false;
   if(InpReportStart == "") return;
   datetime rs = StringToTime(InpReportStart);
   if(rs <= 0) return;
   // MT5: check earliest deal in selectable history
   HistorySelect(rs, TimeCurrent()+86400);
   int nd = HistoryDealsTotal();
   datetime earliest = 0;
   for(int i = 0; i < nd; i++)
   {
      ulong dk = HistoryDealGetTicket(i);
      datetime ct = (datetime)HistoryDealGetInteger(dk, DEAL_TIME);
      if(ct <= 0) continue;
      if(earliest == 0 || ct < earliest) earliest = ct;
   }
   if(nd == 0 || earliest == 0 || earliest > rs + 86400)
   {
      g_histTruncated = true;
      Print("TD5: history may be truncated vs ReportStart=", InpReportStart);
   }
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
   string cc = ccy;
   StringToUpper(cc);
   return (StringFind(s, cc) >= 0);
}

//+------------------------------------------------------------------+
//| NewsGuard loop (30s scan)                                        |
//+------------------------------------------------------------------+
void NG_Guard()
{
   if(InpNewsGuardMode == 0) return;
   if(TimeCurrent() - g_ngLastScan < 30) return;
   g_ngLastScan = TimeCurrent();
   NG_LoadNews();
   TG_LoadToken();      // v1.15 Q2: refresh token each scan (idempotent)

   for(int i = 0; i < g_ngEventCount; i++)
   {
      datetime evT = NG_EvTimeHKT(g_ngEvents[i][0]);
      string   ccy = g_ngEvents[i][1];
      datetime now = NG_NowHKT();
      if(now <  evT - InpNewsBeforeMinutes*60) continue;
      if(now >  evT + InpNewsAfterMinutes*60)  continue;

      string msg = StringFormat("NewsGuard: %s %s @ %s (-%dm/+%dm) mode=%s",
                   ccy, g_ngEvents[i][2], TimeToString(evT, TIME_MINUTES), InpNewsBeforeMinutes, InpNewsAfterMinutes,
                   (InpNewsGuardMode==1?"ALERT":InpNewsGuardMode==2?"BLOCK":"CLOSE"));
      if(msg != g_ngLastAlert)
      {
         Print(msg);
         if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) SendNotification(msg);
         g_ngLastAlert = msg;
      }
      GlobalVariableSet("TD5_NEWSGUARD_" + ccy, 1);

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
            for(int p = PositionsTotal() - 1; p >= 0; p--)
            {
               ulong tk = PositionGetTicket(p);
               if(tk == 0) continue;
               if(!NG_SymbolAffected(PositionGetString(POSITION_SYMBOL), ccy)) continue;
               if(!trade.PositionClose(tk))
                  Print("NewsGuard close fail #", tk, " ret=", trade.ResultRetcode());
            }
         }
      }
   }
   for(int i2 = 0; i2 < g_ngEventCount; i2++)
   {
      datetime evT2 = NG_EvTimeHKT(g_ngEvents[i2][0]);
      string   c2   = g_ngEvents[i2][1];
      if(NG_NowHKT() > evT2 + InpNewsAfterMinutes*60)
         GlobalVariableSet("TD5_NEWSGUARD_" + c2, 0);
   }
}

//+------------------------------------------------------------------+
//| DD Guard: account / per-symbol drawdown protection               |
//+------------------------------------------------------------------+
//--- v1.15 Q2: Telegram via MT5 built-in WebRequest (no wininet DLL) ---
//---            NOTE: add https://api.telegram.org to WebRequest whitelist
//---            (Tools -> Options -> Expert Advisors -> Allow WebRequest)
void TG_LoadToken()
{
   // v1.63 (2010 §三): InpTelegramBotToken non-empty overrides the token file
   if(InpTelegramBotToken != "")
   {
      g_tgToken = InpTelegramBotToken;
      StringTrimLeft(g_tgToken); StringTrimRight(g_tgToken);
      return;
   }
   int th = FileOpen(InpTelegramTokenFile, FILE_READ|FILE_TXT|FILE_ANSI);
   if(th != INVALID_HANDLE)
   {
      g_tgToken = FileReadString(th);
      StringTrimLeft(g_tgToken); StringTrimRight(g_tgToken);
      // v1.14 T5: strip CR/LF from token
      int tp = StringFind(g_tgToken, "\r"); if(tp >= 0) g_tgToken = StringSubstr(g_tgToken, 0, tp);
      tp = StringFind(g_tgToken, "\n"); if(tp >= 0) g_tgToken = StringSubstr(g_tgToken, 0, tp);
      FileClose(th);
   }
}
string TG_URLEncode(string s)
{
   uchar b[]; int n = StringToCharArray(s, b, 0, WHOLE_ARRAY, CP_UTF8);
   string o = "";
   for(int i=0; i<n-1; i++)
   {
      uchar c = b[i];
      if((c>='0'&&c<='9')||(c>='A'&&c<='Z')||(c>='a'&&c<='z')||c=='-'||c=='.'||c=='_'||c=='~') o += CharToString(b[i]);
      else if(c==0x20) o += "+";
      else o += StringFormat("%%%02X", c);
   }
   return(o);
}
bool TG_SendRaw(string text)
{
   // v1.15 Q2: MT5 built-in WebRequest - no wininet DLL needed
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
      // v1.15 Q2: WebRequest failed (whitelist missing / no network) -> fallback phone push
      Print("TD5: WebRequest failed err=", GetLastError(),
            " - add api.telegram.org to MT5 WebRequest whitelist (Tools->Options->EA)");
      SendNotification(StringSubstr(text,0,200));
      return(false);
   }
   if(code != 200) { Print("TD5: Telegram HTTP ", code); return(false); }
   string body = CharArrayToString(resp, 0, WHOLE_ARRAY, CP_UTF8);
   // v1.15 Q2: verify Telegram responded with ok:true
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

//--- v1.11: toggle AlgoTrading via WM_COMMAND (MT5 cmd id 32851)
bool TD_TerminalHandle(long &root)
{
   long h = ChartGetInteger(0, CHART_WINDOW_HANDLE, 0);
   if(h <= 0) return(false);
   root = GetAncestor(h, 2);
   return(root > 0);
}
void TD_ToggleAlgo()
{
   long root;
   if(!TD_TerminalHandle(root)) return;
   PostMessageW(root, 0x0111, 32851, 0);
}
void DDG_StopAT()
{
   if(!TerminalInfoInteger(TERMINAL_DLLS_ALLOWED)) { Print("TD5: DLL not allowed — cannot toggle AlgoTrading"); return; }
   bool atOn = (TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0);
   if(!atOn) { g_tdStoppedAT = true; DDG_SaveState(); return; }
   TD_ToggleAlgo();
   Sleep(250);
   if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) == 0) { g_tdStoppedAT = true; DDG_SaveState(); }
}

void DDG_RestoreAT()
{
   if(!g_tdStoppedAT) return;
   if(!TerminalInfoInteger(TERMINAL_DLLS_ALLOWED)) { Print("TD5: DLL not allowed — cannot restore AlgoTrading"); return; }
   if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0) { g_tdStoppedAT = false; return; }
   TD_ToggleAlgo();
   Sleep(250);
   if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0) { g_tdStoppedAT = false; DDG_SaveState(); }
}

void DDG_ATStatusCheck()
{
   bool atOn = (TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0);
   if(atOn && g_tdStoppedAT) { g_tdStoppedAT = false; DDG_SaveState(); }
}

void DDG_ResetPeakConfirm()
{
   g_ddgPeakEquity = AcctEquity();
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
   Print("TD5 v1.47: manual reset peak -> ", DoubleToString(g_ddgPeakEquity,2));
}

void SG_ForceClose(string sym)
{
   for(int k = 0; k < g_sgSymN; k++)
      if(g_sgSym[k] == sym) { g_sgForcedClose[k] = true; }
   GlobalVariableSet(SG_ModeKey(sym), 3);   // v1.47: account-scoped CLOSE
}

// v1.14 T8: deposit/withdrawal-aware peak adjustment
int DDG_CloseAllWithRetry()
{
   int retries = MathMax(1, InpDdgCloseRetry);
   int residual = 9999;
   for(int r = 0; r < retries; r++)
   {
      for(int p = PositionsTotal()-1; p >= 0; p--)
      {
         ulong tk = PositionGetTicket(p);
         if(tk == 0) continue;
         if(!trade.PositionClose(tk))
            Print("DDGuard5 close fail #", tk, " ret=", trade.ResultRetcode());
      }
      Sleep(150);
      residual = 0;
      for(int p = PositionsTotal()-1; p >= 0; p--)
      {
         ulong tk = PositionGetTicket(p);
         if(tk > 0) residual++;
      }
      if(residual == 0) break;
   }
   return residual;
}

int DDG_CloseSymbolWithRetry(string sym)
{
   int retries = MathMax(1, InpDdgCloseRetry);
   int residual = 9999;
   for(int r = 0; r < retries; r++)
   {
      for(int p = PositionsTotal()-1; p >= 0; p--)
      {
         ulong tk = PositionGetTicket(p);
         if(tk == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != sym) continue;
         if(!trade.PositionClose(tk))
            Print("DDGuard5 sym close fail #", tk, " ret=", trade.ResultRetcode());
      }
      Sleep(150);
      residual = 0;
      for(int p = PositionsTotal()-1; p >= 0; p--)
      {
         ulong tk = PositionGetTicket(p);
         if(tk == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != sym) residual++;
      }
      if(residual == 0) break;
   }
   return residual;
}

//+------------------------------------------------------------------+
//| v1.14 T8: deposit/withdrawal-aware peak adjustment (MT5)         |
//+------------------------------------------------------------------+
void DDG_ScanBalanceOps()
{
   if(!InpDdgEnable) return;
   datetime now = TimeCurrent();
   if(now - g_lastBalScan < 60) return;
   g_lastBalScan = now;
   double base = AccountInfoDouble(ACCOUNT_BALANCE);
   double sum  = 0;
   bool   found = false;
   HistorySelect(now - 7*24*3600, now);
   for(int i = HistoryDealsTotal()-1; i >= 0; i--)
   {
      ulong dk = HistoryDealGetTicket(i);
      if(dk == 0) continue;
      long dtype = HistoryDealGetInteger(dk, DEAL_TYPE);
      if(dtype != DEAL_TYPE_BALANCE && dtype != DEAL_TYPE_CREDIT) continue;
      sum += HistoryDealGetDouble(dk, DEAL_PROFIT);
      found = true;
   }
   if(!found) return;
   if(!g_balBaseSet) { g_balBase = base - sum; g_balBaseSet = true; return; }
   double delta = sum;
   if(delta != 0)
   {
      g_ddgPeakEquity = MathMax(AccountInfoDouble(ACCOUNT_EQUITY), g_ddgPeakEquity + delta);
      GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
      Print("TD v1.14: balance op detected $" + DoubleToString(delta,2) + " — peak adjusted to $" + DoubleToString(g_ddgPeakEquity,2));
   }
   g_balBase = base;
}

void DDG_Guard()
{
   //--- v1.60 (1425 §三-2): the ratchet is UNCONDITIONAL. It used to sit
   //---   behind the master gate, so a disabled DDGuard froze the peak
   //---   and the panel showed phantom negative DD (6DB4 -97.51%
   //---   symptom). The high-water mark tracks even when DDGuard is off.
   double eqP = AcctEquity();
   if(eqP > g_ddgPeakEquity) g_ddgPeakEquity = eqP;   // never lowered
   if(!InpDdgEnable) return;
   DDG_ScanBalanceOps();
   double eq  = AcctEquity();
   double base = DDG_Base();                 // v1.47 Q6: single balance denominator
   if(g_ddgPeakEquity <= 0) return;
   if(TimeCurrent() < g_ddgLockUntil) return;   // v1.35: lockout window
   if(g_ddgAccountArmed) return;               // v1.14 T3: manual-confirm lock

   // ---- account check (v1.60 §3.3: pct OR money, spec 1230) ----
   double ddPct   = MathMax(0.0, (g_ddgPeakEquity - eq) / base * 100.0);   // v1.47 Q6 denominator
   double ddMoney = MathMax(0.0, g_ddgPeakEquity - eq);
   bool hitPct   = (InpDdgAccountMaxPercent > 0 && ddPct   >= InpDdgAccountMaxPercent);
   bool hitMoney = (InpDdgAccountMaxMoney   > 0 && ddMoney >= InpDdgAccountMaxMoney);
   if(InpDdgAccountEnable && (hitPct || hitMoney))
   {
      string trig = hitPct ? StringFormat("DD %.2f%% >= limit %.1f%%", ddPct, InpDdgAccountMaxPercent)
                           : StringFormat("DD $%.2f >= limit $%.2f", ddMoney, InpDdgAccountMaxMoney);
      string msg = StringFormat("DDGuard5: account %s - %s",
                   trig, InpDdgCloseOnHit ? "CLOSE ALL" : "no new trades");
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
         TG_Notify("DDG_ACC", "🚨 DDGuard TRIGGERED — ACCOUNT LEVEL\n━━━━━━━━━━━━━━\n🏦 AC: " + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "\n📉 DD: " + trig + " (limits " + DoubleToString(InpDdgAccountMaxPercent,1) + "% / $" + DoubleToString(InpDdgAccountMaxMoney,2) + ")\n💰 Peak: $" + DoubleToString(g_ddgPeakEquity,2) + "\n💸 Equity: $" + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2) + "\n⚡ Action: close all" + (residual>0?" (residual "+IntegerToString(residual)+" open!)":" ✅") + " + AlgoTrading " + (InpDdgAccountStopAutotrade?"STOPPED":"not stopped") + "\n⏱ Awaiting manual confirm [Reset Peak]\n🕐 " + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + " server");   // anti-ratchet: peak NOT lowered
         if(InpDdgAlertPopup){ long rh; if(TD_TerminalHandle(rh)) MessageBoxW(rh, msg, "DDGuard5", 0x30); }
      }
      return;
   }

   // ---- per-symbol check (Scope=0) ----
   if(InpDdgSymbolEnable && (InpDdgSymbolMaxPercent > 0 || InpDdgSymbolMaxMoney > 0))   // v1.60 §3.3: OR money limit
   {
      string syms = InpDdgSymbolList;
      if(syms == "") syms = Symbol();
      string parts[]; int n = StringSplit(syms, ',', parts);
      for(int s = 0; s < n; s++)
      {
         string sym = parts[s];
         StringTrimLeft(sym); StringTrimRight(sym);
         if(sym == "") continue;
         bool symLocked = DDG_SymLocked(sym);        // v1.47 Q9: persisted per-symbol lock
         if(symLocked) continue;
         double floating = 0;
         for(int p2 = PositionsTotal()-1; p2 >= 0; p2--)
         {
            ulong tk2 = PositionGetTicket(p2);
            if(tk2 == 0) continue;
            if(PositionGetString(POSITION_SYMBOL) != sym) continue;
            floating += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
         }
         bool symHitPct   = (InpDdgSymbolMaxPercent > 0 && -floating >= base * InpDdgSymbolMaxPercent / 100.0);   // v1.47 Q6: was AcctEquity-based
         bool symHitMoney = (InpDdgSymbolMaxMoney   > 0 && -floating >= InpDdgSymbolMaxMoney);
         if(symHitPct || symHitMoney)   // v1.60 §3.3: OR money limit
         {
            string trig2 = symHitPct ? StringFormat("%.1f%% limit", InpDdgSymbolMaxPercent)
                                     : StringFormat("$%.2f limit", InpDdgSymbolMaxMoney);
            string m2 = StringFormat("DDGuard5: %s floating %.0f hit %s - %s",
                        sym, floating, trig2, InpDdgCloseOnHit?"CLOSE":"no new");
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
               TG_Notify("DDG_"+sym, "⚠️ DDGuard TRIGGERED — SYMBOL LEVEL\n━━━━━━━━━━━━━━\n.Symbol: " + sym + "\n📉 Floating: $" + DoubleToString(floating,2) + " (hit " + trig2 + ")\n⚡ Action: close symbol" + (residual2>0?" (residual "+IntegerToString(residual2)+" open!)":" ✅") + " + SymbolGuard CLOSE locked" + (InpDdgSymbolStopAutotrade?" + AlgoTrading STOPPED":"") + "\n⏱ Awaiting manual confirm\n🕐 " + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + " server");
               if(InpDdgAlertPopup){ long rh2; if(TD_TerminalHandle(rh2)) MessageBoxW(rh2, m2, "DDGuard5", 0x30); }
            }
         }
      }
   }
}
//+------------------------------------------------------------------+
