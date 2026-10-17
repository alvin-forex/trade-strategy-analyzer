//+------------------------------------------------------------------+
//|                                             TradeDashboard5.mq5  |
//|        MT5 port of TradeDashboard v1.39 (broker summary-proof)   |
//|        v1.10 - full feature port: 21-col table, 4 tabs,          |
//|               NewsGuard / DDGuard / SymbolGuard, snap bin        |
//+------------------------------------------------------------------+
#property copyright "FF48 Alvin"
#property version   "1.13"
#property description "TradeDashboard5 v1.10 (MT5 port of v1.39)"

#include <Trade/Trade.mqh>

//--- v1.11 DLL imports (require Allow DLL imports)
#import "user32.dll"
   int PostMessageW(long hWnd, uint Msg, long wParam, long lParam);
   long GetAncestor(long hWnd, uint gaFlags);
   int MessageBoxW(long hWnd, string text, string caption, uint type);
#import "wininet.dll"
   int InternetOpenW(string agent, int access, string proxy, string bypass, int flags);
   int InternetConnectW(int hInet, string server, int port, string user, string pass, int service, int flags, long ctx);
   int HttpOpenRequestW(int hConn, string verb, string obj, string ver, string ref, string &accept[], int flags, long ctx);
   int HttpSendRequestW(int hReq, string headers, int hlen, char &data[], int dlen);
   int InternetCloseHandle(int h);
#import
#import
CTrade trade;

//=== INPUTS ===
input string ___SCALE___     = "=== Panel Scale ===";
input int    Scale           = 1;
input string ___VIEW___      = "=== Default View ===";
input int    View            = 0;       // 0=Hour, 1=Day, 2=Week, 3=Month
input string ___REFRESH___   = "=== Refresh ===";
input int    RefreshSec      = 10;
input string ___RECORD___    = "=== Recording ===";
input int    RecordSec       = 1;       // Min seconds between records (1=every tick)
input int    MaxRecords      = 12000;   // Records in ring buffer (max 20000)
input string ___SNAP___      = "=== Trade Snapshot ===";
input bool   SnapEnable      = true;    // Enable local trade snapshots
input int    SnapHours       = 72;      // Snapshot lookback hours
input string ___FILTER___    = "=== Data Filter ===";
input string ReportStart     = "";      // Report start date YYYY.MM.DD (empty=no filter)
input string FilterSymbol    = "";      // Filter by symbol (empty=all)
input string FilterComment   = "";      // Filter by comment (empty=all)
input string ___COLS___      = "=== Column Visibility ===";
input bool   ShowDay         = true;
input bool   ShowTrades      = true;
input bool   ShowBuySell     = true;    // Buy/Sell count
input bool   ShowWR          = true;
input bool   ShowGain        = true;
input bool   ShowGainPct     = true;
input bool   ShowWPips       = true;
input bool   ShowLot         = true;
input bool   ShowTotalLot    = true;
input bool   ShowBalance     = true;
input bool   ShowMargin      = true;
input bool   ShowFreeMarg    = true;
input bool   ShowFMaxPos     = true;    // Max floating profit (peak)
input bool   ShowFMaxNeg     = true;    // Max floating loss = intraday MaxDD
input bool   ShowPF          = true;
input bool   ShowAvgP        = true;
input bool   ShowBest        = true;
input bool   ShowWorst       = true;
input bool   ShowMaxDD       = true;    // Max drawdown $
input bool   ShowMaxDDPct    = true;    // Max drawdown %
input string ___LABEL___     = "=== Label ===";
input string Title1          = "TradeDashboard5 v1.10"; // Line 1 (max 30 chars)
input string Title2          = "Flying to the moon";     // Line 2 Subtitle
input string ___CHART___     = "=== Chart ===";
input bool   ChartEnable     = false;   // Show cumulative P&L chart
input string ___NEWSGUARD___  = "=== NewsGuard ===";
input int    NG_Mode          = 1;      // 0=OFF 1=ALERT 2=GUARD(close positions)
input int    NG_BeforeMin     = 30;
input int    NG_AfterMin      = 15;
input bool   NG_HighOnly      = true;
input string NG_NewsFile      = "news_guard.csv";
input int    NG_ServerOffsetHours = -5;  // news CSV(HKT+8) -> broker server hours
input string ___DDGUARD___    = "=== DD Guard ===";
input bool   DDG_Enable       = true;
input double DDG_MaxDDPct     = 20.0;   // v1.12: boss setting
input int    DDG_Scope        = 1;      // 0=per-symbol 1=whole account
input string DDG_Symbols      = "";
input double DDG_SymMaxDDPct  = 12.0;   // v1.12: boss setting
input bool   DDG_CloseOnHit   = true;
input int    DDG_LockMinutes  = 60;
input bool   DDG_StopAutoTrade = true;   // v1.11: toggle terminal AlgoTrading button OFF on trigger (DLL)
input bool   DDG_Popup        = false;
input string TG_ChatID        = "920593269";   // v1.13: Telegram chat id
input string TG_TokenFile     = "tg_token.txt"; // token file in MQL5\Files
input bool   TG_Enable       = true;
input int    TG_MinGapMin    = 10;  // v1.11: native popup window on trigger     // lockout minutes after DD trigger (peak NOT lowered)
input string ___SYMGUARD___  = "=== Symbol Guard ===";
input bool   SG_Enable       = true;    // Symbol Guard: monitor per-symbol trading
input int    SG_DefaultMode  = 0;       // New symbol default: 0=ON 1=ALERT 2=CLOSE

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
bool g_tdStoppedAT = false;
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
string SNAP_BIN = "td5_snap.bin";
#define SNAP_MAGIC 0x35445054   // "TPD5"

//--- Local Trade Snapshot
string TRADES_FILE = "TD5_trades.csv";
#define MAX_TRADES 5000
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

//--- Summary event log
string EVENT_FILE = "TD5_events.log";

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
datetime NG_EvTime(string t){ return(StringToTime(t) + (datetime)(NG_ServerOffsetHours*3600)); }

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

double CalcTradePnl(string symbol, int type, double openPrice, double closePrice,
                    double volume, double swap, double commission)
{
   double pt = SymPoint(symbol);
   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double contractSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   if(contractSize < 1) contractSize = 100000;
   double priceDiff = (type == 0) ? (closePrice - openPrice) : (openPrice - closePrice);
   double pureProfit;
   if(tickValue > 0 && tickSize > 0)
      pureProfit = (priceDiff / tickSize) * tickValue * volume;
   else
      pureProfit = priceDiff * contractSize * volume;
   return pureProfit + swap + commission;
}

//+------------------------------------------------------------------+
//| OnInit                                                           |
//+------------------------------------------------------------------+
int OnInit()
{
   EventSetTimer(10);
   trade.SetDeviationInPoints(30);

   // Clean up objects from previous version
   ObjectsDeleteAll(0, PFX);

   g_view = MathMax(0, MathMin(3, View));
   g_tab = 0;
   g_offset = 0;

   // Initialize runtime filters from inputs
   g_filterSymbol = FilterSymbol;
   g_filterComment = FilterComment;

   // Parse ReportStart
   if(ReportStart != "")
   {
      g_reportStart = StringToTime(ReportStart + " 00:00:00");
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
   g_vis[0]=ShowDay;         g_vis[1]=ShowTrades;      g_vis[2]=ShowBuySell;
   g_vis[3]=ShowWR;          g_vis[4]=ShowGain;        g_vis[5]=ShowGainPct;
   g_vis[6]=ShowWPips;       g_vis[7]=ShowLot;         g_vis[8]=ShowTotalLot;
   g_vis[9]=ShowBalance;     g_vis[10]=ShowMargin;     g_vis[11]=ShowFreeMarg;
   g_vis[12]=ShowFMaxPos;    g_vis[13]=ShowFMaxNeg;    g_vis[14]=ShowPF;
   g_vis[15]=ShowAvgP;       g_vis[16]=ShowBest;       g_vis[17]=ShowWorst;
   g_vis[18]=ShowMaxDD;      g_vis[19]=ShowMaxDDPct;   g_vis[20]=false;

   LoadRecords();       // hydrate binary snapshot ring buffer
   LoadTrades();        // hydrate local trade snapshot CSV

   if(SnapEnable) SyncTradesFromHistory();

   RecordSnapshot();

   CollectData();
   RenderOnly();

   Print("=== TradeDashboard5 v1.10 STARTED === Trades: ", t_tradeCount,
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
   EventKillTimer();
   SaveRecordsBin();
   GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
   ObjectsDeleteAll(0, PFX);
}

//+------------------------------------------------------------------+
//| OnTick                                                           |
//+------------------------------------------------------------------+
void OnTick()
{
   NGDDG_Init();
   NG_Guard();
   DDG_Guard();
   DDG_AutoTradeGuard();
   SymbolGuard();
   NG_WindowPush();
   GlobalVariableSet(DDG_PeakKey(), g_ddgPeakEquity);
   RecordSnapshot();
   SG_CollectSymbols();

   if(SnapEnable && TimeCurrent() - g_lastSnap >= 300)
   {
      SyncTradesFromHistory();
      g_lastSnap = TimeCurrent();
   }

   if(TimeCurrent() - g_lastFull >= RefreshSec)
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
   NGDDG_Init();
   RecordSnapshot();
   if(TimeCurrent() - g_lastFull >= RefreshSec)
   {
      CollectData();
      DD_BuildSymbols();
      RenderOnly();
      g_lastFull = TimeCurrent();
   }
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
         {
            string asym = g_sgSym[ai];
            int am = SG_Mode(asym);
            am = (am + 1) % 3;
            SG_SetMode(asym, am);
            Print("SG: ", asym, " -> ", (am==0?"ON":am==1?"ALERT":"CLOSE"));
         }
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
      else if(StringFind(s, PFX+"SG_") == 0)
      {
         int gi = (int)StringToInteger(StringSubstr(s, StringLen(PFX)+3));
         if(gi >= 0 && gi < g_sgSymN && gi < 10)
         {
            string sym2 = g_sgSym[gi];
            int m2 = SG_Mode(sym2);
            m2 = (m2 + 1) % 3;
            SG_SetMode(sym2, m2);
            if(gi<64) g_sgAlertT[gi]=0;   // pressing acknowledges alert
            Print("SG: ", sym2, " -> ", (m2==0?"ON":m2==1?"ALERT":"CLOSE"));
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
   datetime since = TimeCurrent() - SnapHours * 3600;
   int newCount = 0;

   bool seen[MAX_TRADES];
   ArrayInitialize(seen, false);

   HistorySelect(since, TimeCurrent()+86400);
   int nd = HistoryDealsTotal();

   for(int i = 0; i < nd; i++)
   {
      ulong dt = HistoryDealGetTicket(i);
      if(dt == 0) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(dt, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;  // closing deal
      long dtype = HistoryDealGetInteger(dt, DEAL_TYPE);
      if(dtype != DEAL_TYPE_BUY && dtype != DEAL_TYPE_SELL) continue;
      string sym = HistoryDealGetString(dt, DEAL_SYMBOL);
      if(sym == "") continue;
      datetime ct = (datetime)HistoryDealGetInteger(dt, DEAL_TIME);
      if(ct == 0 || ct < since) continue;

      // netting may split a close into several OUT deals: aggregate per position id
      long posId = HistoryDealGetInteger(dt, DEAL_POSITION_ID);
      int idx = FindTrade(posId);

      double dProfit = HistoryDealGetDouble(dt, DEAL_PROFIT);
      double dSwap   = HistoryDealGetDouble(dt, DEAL_SWAP);
      double dComm   = HistoryDealGetDouble(dt, DEAL_COMMISSION);
      double dVol    = HistoryDealGetDouble(dt, DEAL_VOLUME);
      double dOpenPr = 0, dClosePr = HistoryDealGetDouble(dt, DEAL_PRICE);
      datetime dOpenTm = ct;
      // find matching IN deal price/time via entry deal on same position
      if(idx < 0 && t_tradeCount >= MAX_TRADES) continue;

      if(idx >= 0)
      {
         seen[idx] = true;
         // aggregate partial closes (netting) into the same record
         t_lots[idx]       += dVol;
         t_profit[idx]     += dProfit;
         t_swap[idx]       += dSwap;
         t_commission[idx] += dComm;
         t_closeprice[idx]  = dClosePr;
         t_closetime[idx]   = ct;
         t_calcPnl[idx]     = t_profit[idx] + t_swap[idx] + t_commission[idx];
      }
      else
      {
         // look up the entry deal for open price/time and direction
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
         // direction of the POSITION: closing deal direction is opposite; use IN deal type
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
   }

   if(newCount > 0)
   {
      LogEvent(StringFormat("SYNC %s | New: %d | Total: %d",
               TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS), newCount, t_tradeCount));
   }

   SaveTrades();
}

void SaveTrades()
{
   int fh = FileOpen(TRADES_FILE, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) return;

   FileWrite(fh, "Ticket", "Symbol", "Type", "OpenTime", "CloseTime",
             "OpenPrice", "ClosePrice", "Volume", "Profit", "Swap",
             "Commission", "CalcPnl", "Comment");

   for(int i = 0; i < t_tradeCount; i++)
   {
      FileWrite(fh,
         t_ticket[i],
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

   int fh = FileOpen(TRADES_FILE, FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) return;

   for(int h = 0; h < 13; h++) FileReadString(fh);

   while(!FileIsEnding(fh) && t_tradeCount < MAX_TRADES)
   {
      string sTicket = FileReadString(fh);
      if(sTicket == "") break;

      long tkt        = StringToInteger(sTicket);
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

      // Apply ReportStart filter when loading
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
   Print("TD5 trades loaded: ", t_tradeCount);
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
   if(now - g_lastRec < MathMax(1, RecordSec)) return;
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
   int fh = FileOpen(SNAP_BIN, FILE_WRITE|FILE_BIN);
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

   int fh = FileOpen(SNAP_BIN, FILE_READ|FILE_BIN);
   if(fh == INVALID_HANDLE) return;

   int magic = FileReadInteger(fh, INT_VALUE);
   if(magic != SNAP_MAGIC) { FileClose(fh); Print("TD5 snap bin: bad magic, ignored"); return; }

   int cnt = FileReadInteger(fh, INT_VALUE);
   if(cnt < 0 || cnt > MAX_REC) { FileClose(fh); return; }

   int cap = MathMin(cnt, MathMin(MaxRecords, MAX_REC));
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
         GetRecMaxDD(bS, bE, ddAmt, ddPct);
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
             "MaxP","MaxDD$",
             "PF","AvgP&L","Best","Worst","MaxDD$","MaxDD%");

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
            double pf = (gL > 0.01) ? gW/gL : (gW > 0 ? 99.0 : 0);
            double avgp = bpnl / bn;

            double ddAmt, ddPct;
            GetRecMaxDD(bS, bE, ddAmt, ddPct);
            double recMarg = GetRecMargin(bS, bE);
            double recFMarg = GetRecFreeMargin(bS, bE);
            double recFPos = GetRecFloatMaxPos(bS, bE);
            double recFNeg = GetRecFloatMaxNeg(bS, bE);

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
               DoubleToString(recFNeg, 2),
               DoubleToString(pf, 2),
               DoubleToString(avgp, 2),
               DoubleToString(bestT, 2),
               DoubleToString(worstT, 2),
               DoubleToString(ddAmt, 2),
               DoubleToString(ddPct, 2)
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
      if(ev+NG_AfterMin*60 < now) continue;
      bool hot=(now >= ev-NG_BeforeMin*60 && now <= ev+NG_AfterMin*60);
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
   UpdTxtBold("TA0","SYMBOL STATUS  (red = news window | click = ON/ALERT/CLOSE)",x,sy,clrDeepSkyBlue,10*scale);
   for(int k=0;k<g_sgSymN && k<8;k++)
   {
      string s2=g_sgSym[k];
      bool hot2=NG_SymbolHot(s2);
      int m2=SG_Mode(s2);
      color stc=hot2?clrRed:clrLime;
      UpdTxt("TSY"+IntegerToString(k), StringFormat("%s  %s",s2,(hot2?"NEWS RISK":"clear")), x, sy+14*scale+k*16*scale, stc, 9*scale);
      string lbl=(m2==0)?"[ON]":(m2==1)?"[ALERT]":"[CLOSE]";
      color  bg=(m2==0)?C'20,90,40':(m2==1)?C'160,110,20':C'150,30,30';
      color  fg=(m2==0)?clrLime:(m2==1)?clrYellow:clrWhite;
      int bw=40*MathMax(1,scale/2)+52;
      UpdBtn("TSG_"+IntegerToString(k), lbl, x+w-bw-10, sy+12*scale+k*16*scale, bw, 13*scale, false);
      ObjectSetInteger(0,PFX+"TSG_"+IntegerToString(k),OBJPROP_BGCOLOR,bg);
      ObjectSetInteger(0,PFX+"TSG_"+IntegerToString(k),OBJPROP_COLOR,fg);
   }
   if(g_sgSymN==0) UpdTxt("TAX","(no open symbols)",x,sy+14*scale,clrKhaki,9*scale);
   UpdTxt("TAM",StringFormat("NG mode=%s | window %dm/%dm | push on entry | tzOff %dh",(NG_Mode==0?"OFF":NG_Mode==1?"ALERT":"GUARD"),NG_BeforeMin,NG_AfterMin,NG_ServerOffsetHours), x, sy+15*scale+MathMax(MathMin(g_sgSymN,8),1)*15*scale, clrWhite, 9*scale);
}

// v1.29: per-symbol DD from closed-trade history (t_ arrays)
string g_ddSyms[32]; int g_ddSymN=0;
double g_ddSymDD[32];      // max DD in $
double g_ddSymDDPct[32];   // max DD as % of cumulative peak
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
      g_ddSymDDPct[j]=(peak>0)?maxdd/peak*100:(maxdd>0?100:0);
   }
}

void TabRender_DDG(int x,int y,int scale,int w)
{
   double eq=AcctEquity();
   double dd=(g_ddgPeakEquity>0)?(g_ddgPeakEquity-eq)/g_ddgPeakEquity*100:0;
   UpdTxtBold("TD0","DDGuard - Account Drawdown",x,y,clrDeepSkyBlue,10*scale);
   UpdTxt("TD1",StringFormat("Peak $%.2f | Now $%.2f | DD %.2f%% (limit %.1f%%)",g_ddgPeakEquity,eq,dd,DDG_MaxDDPct),x,y+16*scale,clrWhite,9*scale);
   UpdTxt("TD4",StringFormat("Scope: %s | SymMaxDD: %.1f%% | Lock: %dmin",(DDG_Scope==0?"per-symbol":"account"),DDG_SymMaxDDPct,DDG_LockMinutes),x,y+31*scale,clrKhaki,9*scale);
   int bw=w-20;
   UpdRect("TDB", x, y+44*scale, bw, 10*scale, C'40,50,80', C'40,50,80');
   double pct=MathMin(1.0, dd/DDG_MaxDDPct);
   color bc=(pct>=1.0)?clrRed:(pct>=0.7?clrYellow:clrLime);
   UpdRect("TDF", x, y+44*scale, (int)(bw*pct), 10*scale, bc, bc);

   //--- v1.37: aligned column table, one row per traded symbol ---
   int ty = y + 64*scale;
   double bal = AcctBalance(); if(bal <= 0) bal = 1;
   int c1 = x + 8*scale;
   int c2 = x + 100*scale;
   int c3 = x + 175*scale;
   int c4 = x + 250*scale;
   int c5 = x + 320*scale;
   UpdTxtBold("TPH", "SYMBOL",   c1, ty, clrDeepSkyBlue, 9*scale);
   UpdTxtBold("TPC2","Float $",  c2, ty, clrDeepSkyBlue, 9*scale);
   UpdTxtBold("TPC3","DD now %", c3, ty, clrDeepSkyBlue, 9*scale);
   UpdTxtBold("TPC4","MaxDD %",  c4, ty, clrDeepSkyBlue, 9*scale);
   UpdTxtBold("TPC5","MaxDD $",  c5, ty, clrDeepSkyBlue, 9*scale);
   for(int k=0;k<g_ddSymN && k<12;k++)
   {
      int ry2=ty+16*scale+k*15*scale;
      double fl=0;
      for(int p3=PositionsTotal()-1;p3>=0;p3--)
      {
         ulong tk=PositionGetTicket(p3);
         if(tk==0) continue;
         if(PositionGetString(POSITION_SYMBOL)!=g_ddSyms[k]) continue;
         fl += PositionGetDouble(POSITION_PROFIT)+PositionGetDouble(POSITION_SWAP);
      }
      double ddNow = -fl/bal*100.0;
      color cFl  = (fl>=0)?clrLime:clrTomato;
      color cDn  = (ddNow>=DDG_SymMaxDDPct)?clrRed:(ddNow>=DDG_SymMaxDDPct*0.7?clrYellow:clrWhite);
      color cMx  = (g_ddSymDDPct[k]>=DDG_SymMaxDDPct)?clrRed:(g_ddSymDDPct[k]>=DDG_SymMaxDDPct*0.7?clrYellow:clrKhaki);
      UpdTxt("DDN"+IntegerToString(k), g_ddSyms[k], c1, ry2, clrWhite, 9*scale);
      UpdTxt("DDF"+IntegerToString(k), StringFormat("%+.2f", fl), c2, ry2, cFl, 9*scale);
      UpdTxt("DDP"+IntegerToString(k), StringFormat("%.2f%%", ddNow), c3, ry2, cDn, 9*scale);
      UpdTxt("DDM"+IntegerToString(k), StringFormat("%.2f%%", g_ddSymDDPct[k]), c4, ry2, cMx, 9*scale);
      UpdTxt("DDC"+IntegerToString(k), StringFormat("%.2f", g_ddSymDD[k]), c5, ry2, cMx, 9*scale);
   }
   if(g_ddSymN==0) UpdTxt("TAX2","(no traded symbols yet)",x+8*scale,ty+16*scale,clrKhaki,9*scale);
   UpdTxt("TAM2","DD now = live floating loss / balance | MaxDD = historical peak decline", x, ty+18*scale+MathMin(g_ddSymN,12)*15*scale, clrKhaki, 8*scale);
}

void TabRender_Set(int x,int y,int scale,int w)
{
   UpdTxtBold("TS0","Settings Quick View (change via EA inputs)",x,y,clrDeepSkyBlue,10*scale);
   UpdTxt("TS1",StringFormat("Refresh: %ds   Record: %ds   Scale: %d   Chart: %s",RefreshSec,RecordSec,Scale,(ChartEnable?"ON":"OFF")),x,y+16*scale,clrWhite,9*scale);
   UpdTxt("TS2",StringFormat("SymbolGuard: %s   DefaultMode: %d   NG tzOff: %dh",(SG_Enable?"ON":"OFF"),SG_DefaultMode,NG_ServerOffsetHours),x,y+30*scale,clrWhite,9*scale);
   UpdTxt("TS3",StringFormat("Snapshot: %s   Records: %d / %d",(SnapEnable?"ON":"OFF"),r_count,MaxRecords),x,y+44*scale,clrWhite,9*scale);
   UpdTxt("TS4","Tip: click tabs to switch. Guard tab = per-symbol ON/ALERT/CLOSE.",x,y+59*scale,clrWhite,9*scale);
}

//+------------------------------------------------------------------+
//| RenderOnly                                                       |
//+------------------------------------------------------------------+
void RenderOnly()
{
   int scale = MathMax(1, MathMin(3, Scale));
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
   int chartWpx=(int)ChartGetInteger(0,CHART_WIDTH_IN_PIXELS,0);
   if(chartWpx>100 && panelW>chartWpx-20) panelW=chartWpx-20;   // v1.33 clamp

   int rowH=14*scale, headerH=124*scale, btnH=18*scale;

   int maxRows=MathMin(10, g_cNumB);
   if(maxRows<1) maxRows=1;

   int chartH=ChartEnable ? 60*scale : 0;
   int panelH=headerH+chartH+18+maxRows*rowH+40;
   // v1.39: non-Positions tabs need their own height
   int tabNeedH = 0;
   if(g_tab != 0)
   {
      tabNeedH = (14 + 17) + 8;
      if(g_tab == 2)
         tabNeedH = tabNeedH + 64*scale + 16*scale + MathMin(g_ddSymN,12)*15*scale + 30*scale + 12;
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
   UpdTxtBold("TTL", Title1, px+4, ttlY, clrLime, 13*scale);
   if(g_histTruncated) UpdTxt("HISTW", "HIST truncated! Check history range", px+170*scale, ttlY, clrOrangeRed, 8*scale); else ObjectDelete(0,PFX+"HISTW");
   UpdTxtBold("SUB", Title2, px+4, ttlY+lh, clrLime, 10*scale);
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
   if(ChartEnable)
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

   UpdTxt("FT", "v1.10  |  Updated: "+TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS)+
      "  |  Refresh: "+IntegerToString(RefreshSec)+"s"+
      "  |  Rec: "+IntegerToString(RecordSec)+"s ("+IntegerToString(r_count)+" recs)"+
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

int SG_Mode(string sym)
{
   string gv="TD5_SG_"+sym;
   if(!GlobalVariableCheck(gv)) return SG_DefaultMode;
   return (int)GlobalVariableGet(gv);
}
void SG_SetMode(string sym,int m)
{
   GlobalVariableSet("TD5_SG_"+sym, m);
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
}
void SymbolGuard()
{
   if(!SG_Enable) return;
   static datetime lastScan=0;
   if(TimeCurrent()-lastScan < 3) return;
   lastScan=TimeCurrent();
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
      int mode=SG_Mode(sym);
      if(mode==0) continue;
      long ptype=PositionGetInteger(POSITION_TYPE);
      double lots=PositionGetDouble(POSITION_VOLUME);
      string msg;
      if(mode==1)
         msg=StringFormat("SG[%s] ALERT: new %s #%I64u %.2f lots",
                sym, (ptype==POSITION_TYPE_BUY?"BUY":"SELL"), tk, lots);
      else
      {
         msg=StringFormat("SG[%s] CLOSE: %s #%I64u %.2f lots closed by guard",
                sym, (ptype==POSITION_TYPE_BUY?"BUY":"SELL"), tk, lots);
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
      int m=SG_Mode(s);
      string lbl=(m==0)?s+" [ON]":(m==1)?s+" [AL]":s+" [CL]";
      color  bg =(m==0)?C'20,90,40':(m==1)?C'160,110,20':C'150,30,30';
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
}

void TD_CheckHistoryDepth()
{
   g_histTruncated = false;
   if(ReportStart == "") return;
   datetime rs = StringToTime(ReportStart);
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
      Print("TD5: history may be truncated vs ReportStart=", ReportStart);
   }
}

void NG_LoadNews()
{
   g_ngEventCount = 0;
   int h = FileOpen(NG_NewsFile, FILE_READ|FILE_CSV|FILE_ANSI, ',');
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
      if(NG_HighOnly && im != "HIGH") continue;
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
   datetime now=TimeCurrent();
   for(int i=0;i<g_ngEventCount;i++)
   {
      datetime ev=NG_EvTime(g_ngEvents[i][0]);
      if(ev==0) continue;
      if(now >= ev-NG_BeforeMin*60 && now <= ev+NG_AfterMin*60)
         if(NG_SymbolAffected(sym, g_ngEvents[i][1])) return true;
   }
   return false;
}

// v1.28: push once per event when it enters the warning window
bool g_ngFired[64];
void NG_WindowPush()
{
   datetime now=TimeCurrent();
   for(int i=0;i<g_ngEventCount && i<64;i++)
   {
      datetime ev=NG_EvTime(g_ngEvents[i][0]);
      if(ev==0) continue;
      if(now >= ev-NG_BeforeMin*60 && now <= ev+NG_AfterMin*60 && !g_ngFired[i])
      {
         g_ngFired[i]=true;
         string syms="";
         for(int j=0;j<g_sgSymN;j++)
            if(NG_SymbolAffected(g_sgSym[j], g_ngEvents[i][1]))
               syms=syms+g_sgSym[j]+(SG_Mode(g_sgSym[j])==2?"[CL]":SG_Mode(g_sgSym[j])==1?"[AL]":"[ON]")+" ";
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
   if(NG_Mode == 0) return;
   if(TimeCurrent() - g_ngLastScan < 30) return;
   g_ngLastScan = TimeCurrent();
   NG_LoadNews();
   int th = FileOpen(TG_TokenFile, FILE_READ|FILE_TXT|FILE_ANSI);
   if(th != INVALID_HANDLE){ g_tgToken = FileReadString(th); StringTrimLeft(g_tgToken); StringTrimRight(g_tgToken); FileClose(th); }

   for(int i = 0; i < g_ngEventCount; i++)
   {
      datetime evT = NG_EvTime(g_ngEvents[i][0]);
      string   ccy = g_ngEvents[i][1];
      datetime now = TimeCurrent();
      if(now <  evT - NG_BeforeMin*60) continue;
      if(now >  evT + NG_AfterMin*60)  continue;

      string msg = StringFormat("NewsGuard: %s %s @ %s (-%dm/+%dm)",
                   ccy, g_ngEvents[i][2], TimeToString(evT, TIME_MINUTES), NG_BeforeMin, NG_AfterMin);
      if(msg != g_ngLastAlert)
      {
         Print(msg);
         if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) SendNotification(msg);
         g_ngLastAlert = msg;
      }
      GlobalVariableSet("TD5_NEWSGUARD_" + ccy, 1);

      if(NG_Mode == 2)
      {
         for(int p = PositionsTotal() - 1; p >= 0; p--)
         {
            ulong tk = PositionGetTicket(p);
            if(tk == 0) continue;
            string psym = PositionGetString(POSITION_SYMBOL);
            if(!NG_SymbolAffected(psym, ccy)) continue;
            if(!trade.PositionClose(tk))
               Print("NewsGuard close fail #", tk, " ret=", trade.ResultRetcode());
         }
      }
   }
   for(int i2 = 0; i2 < g_ngEventCount; i2++)
   {
      datetime evT2 = NG_EvTime(g_ngEvents[i2][0]);
      string   c2   = g_ngEvents[i2][1];
      if(TimeCurrent() > evT2 + NG_AfterMin*60)
         GlobalVariableSet("TD5_NEWSGUARD_" + c2, 0);
   }
}

//+------------------------------------------------------------------+
//| DD Guard: account / per-symbol drawdown protection               |
//+------------------------------------------------------------------+
//--- v1.13 Telegram via wininet ---
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
   if(!TG_Enable || g_tgToken == "") { SendNotification(StringSubstr(text,0,200)); return(false); }
   int hInet = InternetOpenW("TD5", 1, NULL, NULL, 0);
   if(hInet == 0) return(false);
   int hConn = InternetConnectW(hInet, "api.telegram.org", 443, NULL, NULL, 3, 0, 0);
   if(hConn == 0){ InternetCloseHandle(hInet); return(false); }
   string acc[]; ArrayResize(acc,1); acc[0] = "*/*";
   int hReq = HttpOpenRequestW(hConn, "POST", "/bot" + g_tgToken + "/sendMessage", "HTTP/1.1", NULL, acc, 0x00800000, 0);
   if(hReq == 0){ InternetCloseHandle(hConn); InternetCloseHandle(hInet); return(false); }
   string body = "chat_id=" + TG_ChatID + "&text=" + TG_URLEncode(text);
   char d[]; int dn = StringToCharArray(body, d, 0, WHOLE_ARRAY, CP_UTF8); dn--;
   string hdr = "Content-Type: application/x-www-form-urlencoded\r\n";
   bool ok = HttpSendRequestW(hReq, hdr, StringLen(hdr), d, dn);
   InternetCloseHandle(hReq); InternetCloseHandle(hConn); InternetCloseHandle(hInet);
   return(ok);
}
void TG_Notify(string key, string text)
{
   datetime now = TimeCurrent();
   for(int i=0;i<g_tgN;i++)
      if(g_tgKey[i]==key){ if(now - g_tgLast[i] < TG_MinGapMin*60) return; g_tgLast[i]=now; TG_SendRaw(text); return; }
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
void DDG_AutoTradeGuard()
{
   bool atOn = (TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0);
   bool inLock = (TimeCurrent() < g_ddgLockUntil);
   if(inLock && !g_tdStoppedAT && DDG_StopAutoTrade && atOn)
   {
      TD_ToggleAlgo();
      Sleep(200);
      if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) == 0) g_tdStoppedAT = true;
   }
   if(!inLock && g_tdStoppedAT)
   {
      if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) == 0) TD_ToggleAlgo();
      Sleep(200);
      if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0) g_tdStoppedAT = false;
      TG_Notify("DDG_RESTORE", "✅ 鎖盤結束 — AlgoTrading 已恢復\nDDGuard " + IntegerToString(DDG_LockMinutes) + " 分鐘鎖盤期滿，terminal 恢復自動交易。\n🕐 " + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + " server");
   }
}

void DDG_Guard()
{
   if(!DDG_Enable) return;
   double eq  = AcctEquity();
   if(eq > g_ddgPeakEquity) g_ddgPeakEquity = eq;   // high-water mark
   if(g_ddgPeakEquity <= 0) return;
   if(TimeCurrent() < g_ddgLockUntil) return;   // v1.35: lockout window

   // ---- account check ----
   double ddPct = (g_ddgPeakEquity - eq) / g_ddgPeakEquity * 100.0;
   if(DDG_Scope == 1 && ddPct >= DDG_MaxDDPct)
   {
      string msg = StringFormat("DDGuard5: account DD %.1f%% >= %.1f%% - %s",
                   ddPct, DDG_MaxDDPct, DDG_CloseOnHit ? "CLOSE ALL" : "no new trades");
      if(msg != g_ddgLastAlert)
      {
         Print(msg); SendNotification(msg); g_ddgLastAlert = msg;
      }
      if(DDG_CloseOnHit)
      {
         for(int p = PositionsTotal()-1; p >= 0; p--)
         {
            ulong tk = PositionGetTicket(p);
            if(tk > 0 && !trade.PositionClose(tk))
               Print("DDGuard close fail #", tk, " ret=", trade.ResultRetcode());
         }
         g_ddgLockUntil = TimeCurrent() + DDG_LockMinutes*60;
         DDG_AutoTradeGuard();
         if(DDG_Popup){ long rh; if(TD_TerminalHandle(rh)) MessageBoxW(rh, msg, "DDGuard5", 0x30); }
         TG_Notify("DDG_ACC", "🚨 DDGuard 觸發 — 帳戶級\n━━━━━━━━━━━━━━\n🏦 AC: " + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "\n📉 DD: " + DoubleToString(ddPct,2) + "% ≥ 限 " + DoubleToString(DDG_MaxDDPct,1) + "%\n💰 Peak: $" + DoubleToString(g_ddgPeakEquity,2) + "\n💸 Equity: $" + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2) + "\n⚡ 動作: 全倉平倉 + AlgoTrading 已停\n⏱ 鎖盤至: " + TimeToString(g_ddgLockUntil, TIME_MINUTES) + " (" + IntegerToString(DDG_LockMinutes) + "min)\n🕐 " + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + " server");   // anti-ratchet: peak NOT lowered
      }
      return;
   }

   // ---- per-symbol check (Scope=0) ----
   if(DDG_Scope == 0 && DDG_SymMaxDDPct > 0)
   {
      string syms = DDG_Symbols;
      if(syms == "") syms = Symbol();
      string parts[]; int n = StringSplit(syms, ',', parts);
      for(int s = 0; s < n; s++)
      {
         string sym = parts[s];
         StringTrimLeft(sym); StringTrimRight(sym);
         if(sym == "") continue;
         double floating = 0;
         for(int p2 = PositionsTotal()-1; p2 >= 0; p2--)
         {
            ulong tk2 = PositionGetTicket(p2);
            if(tk2 == 0) continue;
            if(PositionGetString(POSITION_SYMBOL) != sym) continue;
            floating += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
         }
         if(-floating >= AcctEquity() * DDG_SymMaxDDPct / 100.0)
         {
            string m2 = StringFormat("DDGuard5: %s floating %.0f hit %.1f%% - %s",
                        sym, floating, DDG_SymMaxDDPct, DDG_CloseOnHit?"CLOSE":"no new");
            Print(m2); SendNotification(m2);
            if(DDG_CloseOnHit)
               for(int p3 = PositionsTotal()-1; p3 >= 0; p3--)
               {
                  ulong tk3 = PositionGetTicket(p3);
                  if(tk3 == 0) continue;
                  if(PositionGetString(POSITION_SYMBOL) != sym) continue;
                  trade.PositionClose(tk3);
               }
         }
      }
   }
}
//+------------------------------------------------------------------+
