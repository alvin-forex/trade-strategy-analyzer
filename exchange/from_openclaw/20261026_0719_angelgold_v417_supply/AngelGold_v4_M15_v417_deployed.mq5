//+------------------------------------------------------------------+
//|                                              AngelGold.mq5  v4.09|
//|        Session-Trend core EA (8-year validated, 2018-2026)       |
//|                                                                  |
//|  Core logic (validated on XAUUSD H1, PF 1.94, maxDD 12.7%):      |
//|   - Up to 5 sessions per day (BROKER=Market Watch / LOCAL clock) |
//|   - Bias from signal TF (config SignalTF_Minutes, default H1):   |
//|     close vs MA20 (SMA/EMA/SMMA/LWMA selectable), slope, RSI14   |
//|   - MAIN order : limit pullback to MA, SL 1.8*ATR, TP 1.5/3.0    |
//|   - BREAK order: stop beyond 6-bar extreme, SL 1.6*ATR           |
//|   - Half exit at TP1, rest to TP2; MFE >= $10/0.1lot -> BE       |
//|   - Daily loss/profit fuse as % of day-start equity              |
//|   - Optional per-bar bias reevaluation inside session (REEVAL)   |
//|  SessionEndClose=false: session end cancels pendings only,      |
//|   open positions carry over (TP/SL/BE still managed).          |
//|  DayEndClose + DayEndTime (HH:MM, per SessionClock): daily     |
//|   hard flat + no new sessions until next day.                   |
//|   - Spread gate, news blackout                                   |
//|  Lot logic: LotSize is standard-lot sizing; cent accounts        |
//|  (USDC/EURC/CENT) auto x100.                                     |
//|  Panel: pink minimalist dashboard (ShowPanel)                    |
//+------------------------------------------------------------------+
#property copyright "Alvin"
#property version   "4.17"
#property strict
#include <Trade\Trade.mqh>
#define COL_WHITE        C'255,255,255'
#define COL_GREEN_BORDER C'180,240,200'

//=== A. 時間 (Time) ================================================
enum ENUM_SESSION_CLOCK { BROKER=0, LOCAL=1 };
input group "A. 時間 Time"
input ENUM_SESSION_CLOCK SessionClock = BROKER; // 時間基準: BROKER=Market Watch / LOCAL=PC clock
input string Session1           = "07:00-10:00"; // A. Session 1 視窗 HH:MM-HH:MM (空=停用)
input string Session2           = "10:00-13:00"; // A. Session 2 視窗 HH:MM-HH:MM (空=停用)
input string Session3           = "";            // A. Session 3 視窗 HH:MM-HH:MM (空=停用)
input string Session4           = "";            // A. Session 4 視窗 HH:MM-HH:MM (空=停用)
input string Session5           = "";            // A. Session 5 視窗 HH:MM-HH:MM (空=停用)
input bool   DayEndClose        = true;          // A. 日終平倉: 收市時間後全平+唔再開新節
input string DayEndTime         = "23:55";       // A. 日終時間 HH:MM
input string NewsFile           = "xau_news.txt"; // A. 新聞封盤檔 (空=停用)
input int    NewsBlockBeforeMin = 90;            // A. 新聞前封盤分鐘
input int    NewsBlockAfterMin  = 120;           // A. 新聞後封盤分鐘
input bool   NewsCloseOpen      = false;         // A. 新聞前連持倉都平埋

//=== B. 入市條件 (Entry) ===========================================
enum ENUM_STRATEGY_MODE { SESSION_TREND=0, FVG_M15=1 };
enum ENUM_MA_KIND { MA_SMA=0, MA_EMA=1, MA_SMMA=2, MA_LWMA=3 };
enum ENUM_ENTRY_MODE { SMA_LEVEL=0, ZONE=1 };
input group "B. 入市條件 Entry"
input ENUM_STRATEGY_MODE StrategyMode = SESSION_TREND; // B. 策略模式: SESSION_TREND(H1) 或 FVG_M15
input int    SignalTF_Minutes   = 15;      // B. 訊號時間框架 (分鐘, M15 版預設 15)
input int    SMA_Period         = 20;      // B. 趨勢濾網: SMA 週期
input ENUM_MA_KIND MAKind       = MA_SMA;  // B. MA 類型
input int    RSI_Period         = 14;      // B. 動能: RSI 週期
input int    ATR_Period         = 14;      // B. 波幅: ATR 週期
input ENUM_ENTRY_MODE EntryMode = SMA_LEVEL; // B. MAIN 入場: SMA_LEVEL 或 ZONE 帶
input double ZoneWidthATR       = 0.25;    // B. ZONE 模式: 帶半寬 = ATR x this
input bool   ReevalPerBar       = false;   // B. 節內每 bar 重評 bias
input int    MaxSpreadPoints    = 50;      // B. 點差上限 (points, 0=不限)
input double FVG_MinGapATR     = 0.3;     // B. FVG: 最細 gap 闊度 = ATR x this
input int    FVG_WaitBars      = 48;      // B. FVG: 等回補最大 bar 數

//=== C. 出市條件 (Exit) ============================================
input group "C. 出市條件 Exit"
input double StopLoss_ATR       = 1.8;     // C. SL = ATR x this (MAIN)
input double BreakSL_ATR        = 1.6;     // C. SL = ATR x this (BREAK)
input double TakeProfit1_ATR    = 1.5;     // C. TP1 = ATR x this (半倉)
input double TakeProfit2_ATR    = 3.0;     // C. TP2 = ATR x this
input double BreakEvenTrigger   = 10.0;    // C. MFE 達此值後移 SL 到入場價
input bool   SessionEndClose    = true;    // C. 節尾: true=全平 / false=留倉(只撤掛單)
input double FVG_SL_ATR        = 0.8;     // C. FVG: SL = ATR(M15) x this
input double FVG_TP_ATR        = 1.0;     // C. FVG: TP = ATR(M15) x this
input int    FVG_TimeLimitBars = 16;      // C. FVG: 時限出場 bar 數 (16=4小時)

//=== D. 資金及風險管理 (Money & Risk) ==============================
input group "D. 資金及風險管理 Money & Risk"
input bool   EnableTrading      = true;    // D. 開關: true=實盤 / false=SHADOW 只記錄
input double LotSize            = 0.02;    // D. 固定 lot (cent 帳戶自動 x100)
input bool   UseMarginPercent  = true;   // D. AutoLot: 以 Balance x RiskPercent 做按金落單
input double RiskPercent       = 5.0;     // D. AutoLot: 每單按金 = 餘額 %
input long   MagicNumber        = 20260919;// D. Magic (MAIN=+1, BREAK=+2)
input long   FVG_MagicOffset   = 100;     // D. FVG 單 magic = MagicNumber + this
input double DailyLossPct       = 2.5;     // D. 日蝕 fuse (日初權益 %, 0=停用)
input double DailyProfitPct     = 3.7;     // D. 日贏鎖定 (日初權益 %, 0=停用)

//=== E. 介面 (Display) =============================================
input group "E. 介面 Display"
input bool   ShowPanel          = true;    // E. 顯示監察 panel
input bool   ShowIndicators     = true;    // E. 圖上顯示 SMA線/FVG框/RSI+ATR子窗/開平倉箭頭+標籤
input bool   ApplyPinkTheme     = true;    // E. 粉紅主題

CTrade  tradeMain, tradeBreak;
// v4.14: indicator handles created ONCE and reused (fixes 4805 handle leak)
int g_hSMA=INVALID_HANDLE, g_hRSI=INVALID_HANDLE, g_hATR=INVALID_HANDLE;
bool IndReady(){ return g_hSMA!=INVALID_HANDLE && g_hRSI!=INVALID_HANDLE && g_hATR!=INVALID_HANDLE; }
bool InitHandles()
{
   g_hSMA = iMA(_Symbol, SigTF(), SMA_Period, 0, MAMethod(), PRICE_CLOSE);
   g_hRSI = iRSI(_Symbol, SigTF(), RSI_Period, PRICE_CLOSE);
   g_hATR = iATR(_Symbol, SigTF(), ATR_Period);
   bool ok = IndReady();
   Print("v4.17 InitHandles: SMA=",g_hSMA," RSI=",g_hRSI," ATR=",g_hATR, ok?" [OK]":" [FAIL]");
   return ok;
}
datetime g_lastPanelDraw = 0;
datetime g_sessionStart = 0;
datetime g_sessionEnd   = 0;
int      g_sesIdx = 0;            // active session number
string   g_sesLabel = "";
int      g_bias = 0;           // +1 long, -1 short, 0 none
double   g_sma, g_rsi, g_atr;
bool     g_ordersPlaced = false;
bool     g_fuseTripped  = false;
double   g_dayStartEquity = 0;
bool     g_dayEnded  = false;
int      g_dayOfYear = -1;

// signal timeframe helpers
ENUM_TIMEFRAMES SigTF()
{
   // v4.15 ROOT FIX: ENUM_TIMEFRAMES is NOT seconds (PERIOD_H1=16385, not 3600).
   // Map minutes to the proper enum value.
   switch(SignalTF_Minutes)
   {
      case 1:  return PERIOD_M1;
      case 2:  return PERIOD_M2;
      case 3:  return PERIOD_M3;
      case 4:  return PERIOD_M4;
      case 5:  return PERIOD_M5;
      case 6:  return PERIOD_M6;
      case 10: return PERIOD_M10;
      case 12: return PERIOD_M12;
      case 15: return PERIOD_M15;
      case 20: return PERIOD_M20;
      case 30: return PERIOD_M30;
      case 60: return PERIOD_H1;
      case 120: return PERIOD_H2;
      case 180: return PERIOD_H3;
      case 240: return PERIOD_H4;
      default: return PERIOD_CURRENT;
   }
}
ENUM_MA_METHOD  MAMethod()
{
   switch(MAKind)
   {
      case MA_EMA:  return MODE_EMA;
      case MA_SMMA: return MODE_SMMA;
      case MA_LWMA: return MODE_LWMA;
      default:      return MODE_SMA;
   }
}
string MAKindStr()
{
   switch(MAKind)
   {
      case MA_EMA:  return "EMA";
      case MA_SMMA: return "SMMA";
      case MA_LWMA: return "LWMA";
      default:      return "SMA";
   }
}

//+------------------------------------------------------------------+
void EnsureSubIndicators();
int OnInit()
{
   tradeMain.SetExpertMagicNumber(MagicNumber+1);
   tradeBreak.SetExpertMagicNumber(MagicNumber+2);
   tradeMain.SetDeviationInPoints(30);
   tradeBreak.SetDeviationInPoints(30);
   WriteAlive();
   InitHandles();
   EnsureSubIndicators();
   EventSetTimer(3);   // v4.17: timer keeps retrying handles AND subwindows until all ready
   if(ApplyPinkTheme) ApplyPinkChartTheme();
   Print("=== AngelGold v4.17 core started ===");
   if(StrategyMode==FVG_M15)
      Print("Mode=FVG_M15 (v4.08) | SL=", DoubleToString(FVG_SL_ATR,1), "xATR TP=", DoubleToString(FVG_TP_ATR,1), "xATR TL=", FVG_TimeLimitBars, "bars");
   double effLot = EffectiveLot();
   Print("Trading ", EnableTrading ? "LIVE-DEMO" : "SHADOW",
         " | TF=M", SignalTF_Minutes, " MA=", MAKindStr(), SMA_Period,
         " | Lot=", DoubleToString(effLot,2),
         " | Acct=", AccountInfoString(ACCOUNT_CURRENCY), " | Mode=", IsCentAccount() ? "CENT":"STANDARD");
   return INIT_SUCCEEDED;
}

void OnTimer()
{
   if(!IndReady()) { InitHandles(); }
   EnsureSubIndicators();
   if(IndReady() && SubInd_Ready()) { EventKillTimer(); Print("v4.17 all indicators ready"); }
}
datetime g_lastAlive = 0;
void WriteAlive()
{
   if(TimeCurrent() - g_lastAlive < 60) return;   // throttle 1/min
   g_lastAlive = TimeCurrent();
   int h = FileOpen("angelgold.alive", FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE) return;
   FileWriteString(h, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
   FileClose(h);
}

//+------------------------------------------------------------------+
void OnTick()
{
   WriteAlive();
   CheckNewDay();
   if(g_fuseTripped) { DrawIndicators(); if(ShowPanel) DrawPanel(); return; }

   if(StrategyMode == FVG_M15) { RunFVGMode(); CheckDailyFuse(); DrawIndicators(); if(ShowPanel) DrawPanel(); return; }

   datetime t = SessionNow();   // BROKER -> TimeCurrent(), LOCAL -> TimeLocal()

   // ---- daily hard flat at DayEndTime (per SessionClock) ----
   if(DayEndClose && !g_dayEnded)
   {
      int det = ParseHM(DayEndTime);
      if(det >= 0 && SecOfDay(t) >= det)
      {
         CloseAll("DAY_END");
         CancelPending();
         g_dayEnded = true;
         Log("DAY_END", StringFormat("daily flat at %s, no new sessions today", DayEndTime));
      }
   }
   if(g_dayEnded) { ManagePositions(); if(ShowPanel) DrawPanel(); return; }

   int sesStarts[5]; datetime sesEnds[5];
   int nSes = ParseSessions(sesStarts, sesEnds);
   bool inSession = false;
   for(int i=0;i<nSes;i++)
   {
      datetime ss = TodayWindowStart(t, sesStarts[i]);
      datetime ee = ss + (sesEnds[i]-sesStarts[i]);
      if(t >= ss && t < ee && !g_dayEnded)
      {
         if(g_sessionStart != ss)  // new session just opened
         {
            g_sessionStart = ss; g_sessionEnd = ee;
            g_sesIdx = i+1; g_sesLabel = "S"+IntegerToString(i+1);
            g_ordersPlaced = false;
            if(NewsBlackout()) { Log("NEWS","session start blocked by news"); g_ordersPlaced = true; }
            else
            {
               ComputeIndicators();
               g_bias = DetermineBias();
               if(g_bias != 0) PlaceSessionOrders();
               g_ordersPlaced = true;
               Log("SESSION", StringFormat("%s start=%s bias=%d sma=%.1f rsi=%.1f atr=%.1f",
                    g_sesLabel, TimeToString(ss), g_bias, g_sma, g_rsi, g_atr));
            }
         }
         inSession = true;
         break;
      }
   }

   // per-bar bias reevaluation inside active session
   if(ReevalPerBar && inSession && g_bias != 0)
   {
      static datetime lastBarT = 0;
      datetime bt = iTime(_Symbol, SigTF(), 0);
      if(bt != 0 && bt != lastBarT)
      {
         lastBarT = bt;
         ComputeIndicators();
         int nb = DetermineBias();
         if(nb != 0 && nb != g_bias)
         {
            Log("REEVAL", StringFormat("%s bias flip %d->%d, cancel pending & re-place",
                g_sesLabel, g_bias, nb));
            CancelPending();
            g_bias = nb;
            PlaceSessionOrders();
         }
      }
   }

   // position management
   ManagePositions();
   // session end: close leftovers (or carry positions over if SessionEndClose=false)
   if(g_sessionStart > 0 && t >= g_sessionEnd)
   {
      if(SessionEndClose)
      {
         if(PositionsMine() > 0) CloseAll("SESSION_END");
         else CancelPending();
      }
      else
      {
         CancelPending();   // cancel unfilled pendings only; positions keep running via ManagePositions()
      }
      g_sessionStart = 0;
      if(!SessionEndClose) Log("SESSION_END", "SessionEndClose=false: pendings cancelled, positions carried over");
   }

   CheckDailyFuse();
   DrawIndicators();
   if(ShowPanel) DrawPanel();
}

//+------------------------------------------------------------------+
// v4.08: FVG M15 mode — gap retrace entry, SL/TP by ATR ratio, time stop
//+------------------------------------------------------------------+
CTrade tradeFVG;
bool g_fvgInit=false;
datetime g_fvgEntryBar=0;      // bar time when position opened
long FVGMagic(){ return MagicNumber + FVG_MagicOffset; }

void RunFVGMode()
{
   if(!g_fvgInit)
   {
      tradeFVG.SetExpertMagicNumber(FVGMagic());
      tradeFVG.SetDeviationInPoints(30);
      g_fvgInit=true;
   }
   // one position at a time
   if(FVGPositions() > 0) { FVGManage(); return; }
   if(NewsBlackout()) return;
   if(MaxSpreadPoints>0 && SymbolInfoInteger(_Symbol,SYMBOL_SPREAD) > MaxSpreadPoints) return;

   // v4.09: if any Session window is defined, only enter inside those windows (blank = all day)
   {
      int ss[5]; datetime se[5];
      int ns = ParseSessions(ss, se);
      if(ns > 0)
      {
         bool ok = false;
         datetime now = SessionNow();
         for(int k=0; k<ns && !ok; k++)
         {
            datetime ws = TodayWindowStart(now, ss[k]);
            datetime we = ws + (se[k]-ss[k]);
            if(now >= ws && now < we) ok = true;
         }
         if(!ok) return;
      }
   }

   // v4.11: detect FVG on SignalTF bars (shift 1 vs shift 3), no longer hardcoded M15
   double h3=iHigh(_Symbol,SigTF(),3), l3=iLow(_Symbol,SigTF(),3);
   double h1=iHigh(_Symbol,SigTF(),1), l1=iLow(_Symbol,SigTF(),1);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);

   int dir=0; double gapTop=0,gapBot=0;
   if(l1 > h3)      { dir=1;  gapTop=h3; gapBot=l1; }   // bullish FVG: buy at gap bottom edge on retrace down
   else if(h1 < l3) { dir=-1; gapTop=h1; gapBot=l3; }   // bearish FVG: sell at gap top edge on retrace up
   if(dir==0) return;

   double atr0=FVGATR();
   if(atr0<=0) return;
   // v4.09: skip too-narrow gaps (spread bleed killer)
   double gapW = gapBot - gapTop;
   if(gapW < FVG_MinGapATR*atr0) return;
   // v4.09: spread-aware touch — price must retrace INTO gap beyond current spread
   double spr = ask - bid;
   if(dir>0  && (bid - spr) > gapTop) return;   // buy: real touch below gap top, spread-adjusted
   if(dir<0  && (ask + spr) < gapBot) return;   // sell: real touch above gap bottom, spread-adjusted

   // fresh gap only: act on the bar right after gap bar closed (bar 0 is forming)
   static datetime lastGapBar=0;
   datetime bt=iTime(_Symbol,SigTF(),0);
   if(bt==lastGapBar) return;

   double atr=FVGATR();
   if(atr<=0) return;
   double lot=NormalizeLot(EffectiveLot());
   if(lot<=0) return;

   double entry,sl,tp;
   if(dir>0)
   {
      // price must come back down into gap now (touch of gapBot edge)
      if(bid > gapBot) return;
      entry=ask; sl=entry-FVG_SL_ATR*atr; tp=entry+FVG_TP_ATR*atr;
      if(EnableTrading && tradeFVG.Buy(lot,_Symbol,0,sl,tp,"FVG-B"))
         { g_fvgEntryBar=bt; lastGapBar=bt; MarkEntry(true,entry); Log("FVG",StringFormat("BUY lot=%.2f e=%.2f sl=%.2f tp=%.2f atr=%.2f",lot,entry,sl,tp,atr)); }
   }
   else
   {
      if(ask < gapTop) return;
      entry=bid; sl=entry+FVG_SL_ATR*atr; tp=entry-FVG_TP_ATR*atr;
      if(EnableTrading && tradeFVG.Sell(lot,_Symbol,0,sl,tp,"FVG-S"))
         { g_fvgEntryBar=bt; lastGapBar=bt; MarkEntry(false,entry); Log("FVG",StringFormat("SELL lot=%.2f e=%.2f sl=%.2f tp=%.2f atr=%.2f",lot,entry,sl,tp,atr)); }
   }
}

double FVGATR()
{
   if(!IndReady()) return 0;
   double b[1];
   if(CopyBuffer(g_hATR,0,1,1,b)!=1) return 0;
   return b[0];
}
int FVGPositions()
{
   int c=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i);
      if(PositionSelectByTicket(tk) && PositionGetInteger(POSITION_MAGIC)==FVGMagic() &&
          PositionGetString(POSITION_SYMBOL)==_Symbol) c++;
   }
   return c;
}
void FVGManage()
{
   // time-stop: close position after FVG_TimeLimitBars M15 bars
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i);
      if(!PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC)!=FVGMagic()) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      long barsPassed=(long)((TimeCurrent()-opened)/(SignalTF_Minutes*60));   // per signal-TF bar
      if(barsPassed >= FVG_TimeLimitBars)
      {
         long ptype=PositionGetInteger(POSITION_TYPE);
         if(EnableTrading) { double cp=(ptype==POSITION_TYPE_BUY)?SymbolInfoDouble(_Symbol,SYMBOL_BID):SymbolInfoDouble(_Symbol,SYMBOL_ASK); tradeFVG.PositionClose(tk); MarkExit(ptype==POSITION_TYPE_SELL,cp); }
         Log("FVG_TL",StringFormat("time-stop after %d bars",(int)barsPassed));
      }
   }
}

//+------------------------------------------------------------------+
bool IsCentAccount()
{
   string cur = AccountInfoString(ACCOUNT_CURRENCY);
   return (StringFind(cur, "USDC") >= 0 || StringFind(cur, "CENT") >= 0 || StringFind(cur, "EURC") >= 0);
}
double EffectiveLot()
{
   if(UseMarginPercent) return AutoLotByMargin();        // AutoLot mode: margin = Balance x %
   return IsCentAccount() ? LotSize*100.0 : LotSize;     // 0.02 standard -> 2.0 cent
}
double AutoLotByMargin()
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double budget  = balance * RiskPercent / 100.0;
   double marginPerLot = 0;
   if(!OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, 1.0, SymbolInfoDouble(_Symbol,SYMBOL_ASK), marginPerLot) || marginPerLot<=0)
   {
      Print("AutoLot: OrderCalcMargin failed, fallback to fixed lot");
      return IsCentAccount() ? LotSize*100.0 : LotSize;
   }
   return budget / marginPerLot;
}

//+------------------------------------------------------------------+
int ParseHM(string s)
{
   string a[]; if(StringSplit(s,':',a)!=2) return -1;
   int v = (int)StringToInteger(a[0])*3600 + (int)StringToInteger(a[1])*60;
   if(v < 0 || v >= 86400) return -1;
   return v;
}
int SecOfDay(datetime t)
{
   MqlDateTime dt; TimeToStruct(t, dt);
   return dt.hour*3600 + dt.min*60 + dt.sec;
}
datetime SessionNow()
{
   return (SessionClock==BROKER) ? TimeCurrent() : TimeLocal();
}
int ParseSessions(int &starts[], datetime &ends[])
{
   string defs[5]; defs[0]=Session1; defs[1]=Session2; defs[2]=Session3; defs[3]=Session4; defs[4]=Session5;
   int n=0;
   for(int i=0;i<5;i++)
   {
      if(StringLen(defs[i])==0) continue;
      string hm[]; if(StringSplit(defs[i],'-',hm)!=2) continue;
      string a[],b[];
      if(StringSplit(hm[0],':',a)!=2 || StringSplit(hm[1],':',b)!=2) continue;
      int s = (int)StringToInteger(a[0])*3600 + (int)StringToInteger(a[1])*60;
      int e = (int)StringToInteger(b[0])*3600 + (int)StringToInteger(b[1])*60;
      if(e<=s) continue;
      ArrayResize(starts, n+1); ArrayResize(ends, n+1);
      starts[n]=s; ends[n]=e; n++;
   }
   return n;
}
datetime TodayWindowStart(datetime now, int secOfDay)
{
   MqlDateTime dt; TimeToStruct(now, dt);
   dt.hour = secOfDay/3600; dt.min = (secOfDay%3600)/60; dt.sec = 0;
   datetime ss = StructToTime(dt);
   if(now < ss) ss -= 86400;   // window from previous day (overnight sessions)
   return ss;
}

//+------------------------------------------------------------------+
void ComputeIndicators()
{
   if(!IndReady()) return;
   double buf[1];
   if(CopyBuffer(g_hSMA,0,1,1,buf)==1) g_sma=buf[0];
   if(CopyBuffer(g_hRSI,0,1,1,buf)==1) g_rsi=buf[0];
   if(CopyBuffer(g_hATR,0,1,1,buf)==1) g_atr=buf[0];
}

//+------------------------------------------------------------------+
int DetermineBias()
{
   double c1 = iClose(_Symbol, SigTF(), 1);
   double sma6 = 0; int cnt=0;
   for(int k=6;k<=11 && cnt<6;k++) { sma6 += iMAv(k); cnt++; }
   sma6 /= (cnt>0?cnt:1);
   if(c1 > g_sma && g_sma > sma6 && g_rsi > 50) return  1;
   if(c1 < g_sma && g_sma < sma6 && g_rsi < 50) return -1;
   return 0;
}
double iMAv(int shift){ if(!IndReady()) return 0; double b[1]; if(CopyBuffer(g_hSMA,0,shift,1,b)!=1) return 0; return b[0]; }

//+------------------------------------------------------------------+
void PlaceSessionOrders()
{
   if(!EnableTrading) { Log("PLAN", StringFormat("SHADOW plan bias=%d (no orders)", g_bias)); return; }
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double lot = NormalizeLot(EffectiveLot());

   if(g_bias > 0)
   {
      // MAIN: buy limit at MA pullback zone
      double entry = (EntryMode==ZONE) ? g_sma + ZoneWidthATR*g_atr : g_sma;  // zone: far edge of band
      if(entry < ask)
         tradeMain.BuyLimit(lot, entry, _Symbol, entry - StopLoss_ATR*g_atr, entry + TakeProfit2_ATR*g_atr, ORDER_TIME_GTC, 0, g_sesLabel+"-MAIN-L");
      // BREAK: buy stop above 6-bar high
      double hh = HighOf(6);
      double e2 = hh + 0.1*g_atr;
      tradeBreak.BuyStop(lot, e2, _Symbol, e2 - BreakSL_ATR*g_atr, e2 + TakeProfit2_ATR*g_atr, ORDER_TIME_GTC, 0, g_sesLabel+"-BREAK-L");
   }
   else if(g_bias < 0)
   {
      double entry = (EntryMode==ZONE) ? g_sma - ZoneWidthATR*g_atr : g_sma;
      if(entry > bid)
         tradeMain.SellLimit(lot, entry, _Symbol, entry + StopLoss_ATR*g_atr, entry - TakeProfit2_ATR*g_atr, ORDER_TIME_GTC, 0, g_sesLabel+"-MAIN-S");
      double ll = LowOf(6);
      double e2 = ll - 0.1*g_atr;
      tradeBreak.SellStop(lot, e2, _Symbol, e2 + BreakSL_ATR*g_atr, e2 - TakeProfit2_ATR*g_atr, ORDER_TIME_GTC, 0, g_sesLabel+"-BREAK-S");
   }
   if(g_bias!=0) MarkEntry(g_bias>0, g_sma);
   Log("ORDERS", StringFormat("bias=%d placed MAIN@%.1f BREAK, lot=%.2f (%s)", g_bias, g_sma, lot, UseMarginPercent?StringFormat("AUTOM %.1f%%",RiskPercent):"FIX"));
}
double HighOf(int n){ double h=0; for(int i=1;i<=n;i++) h=MathMax(h, iHigh(_Symbol,SigTF(),i)); return h; }
double LowOf(int n){ double l=1e9; for(int i=1;i<=n;i++) l=MathMin(l, iLow(_Symbol,SigTF(),i)); return l; }

//+------------------------------------------------------------------+
void ManagePositions()
{
   for(int i=PositionsTotal()-1; i>=0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(!PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber+1 &&
         PositionGetInteger(POSITION_MAGIC) != MagicNumber+2) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      long type = PositionGetInteger(POSITION_TYPE);
      double entry = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl    = PositionGetDouble(POSITION_SL);
      double vol   = PositionGetDouble(POSITION_VOLUME);

      // MFE-based break-even (half at TP1 handled by partial close)
      // use current favorable excursion via price
      double px = (type==POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol,SYMBOL_BID) : SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      double fav = (type==POSITION_TYPE_BUY) ? (px-entry) : (entry-px);
      if(fav*g_atr>0 && fav >= 1.0) // $10 MFE per 0.1 lot = $1 price move
      {
         if(type==POSITION_TYPE_BUY  && sl < entry) ModifySL(tk, entry);
         if(type==POSITION_TYPE_SELL && sl > entry) ModifySL(tk, entry);
      }
      // partial close half at TP1
      double tp1 = (type==POSITION_TYPE_BUY) ? entry + TakeProfit1_ATR*g_atr : entry - TakeProfit1_ATR*g_atr;
      double minvol = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      if(!IsPartialDone(tk) && vol >= minvol*1.9) // any position >= 2x min lot can halve
      {
         if((type==POSITION_TYPE_BUY && px >= tp1) || (type==POSITION_TYPE_SELL && px <= tp1))
         {
            if(EnableTrading) tradeMain.PositionClosePartial(tk, vol/2.0);
            MarkPartialDone(tk);
            Log("TP1", StringFormat("half closed @%.1f", px));
         }
      }
   }
   // cancel unfilled orders after session ends
   if(g_sessionStart>0 && SessionNow() >= g_sessionEnd) CancelPending();
}
void ModifySL(ulong tk, double sl)
{
   if(!EnableTrading) return;
   MqlTradeRequest req; MqlTradeResult res; ZeroMemory(req); ZeroMemory(res);
   req.action = TRADE_ACTION_SLTP; req.position = tk;
   req.symbol = _Symbol; req.sl = sl;
   req.tp = PositionGetDouble(POSITION_TP);
   if(!OrderSend(req, res)) Print("ModifySL failed: ", res.retcode);
}
// partial tracking via comment file in memory
ulong g_partialDone[]; int g_nPartial=0;
bool IsPartialDone(ulong tk){ for(int i=0;i<g_nPartial;i++) if(g_partialDone[i]==tk) return true; return false; }
void MarkPartialDone(ulong tk){ ArrayResize(g_partialDone,g_nPartial+1); g_partialDone[g_nPartial++]=tk; }

//+------------------------------------------------------------------+
int PositionsMine()
{
   int c=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i);
      if(PositionSelectByTicket(tk) && PositionGetString(POSITION_SYMBOL)==_Symbol &&
        (PositionGetInteger(POSITION_MAGIC)==MagicNumber+1 || PositionGetInteger(POSITION_MAGIC)==MagicNumber+2)) c++;
   }
   return c;
}
void CloseAll(string reason)
{
   if(!EnableTrading) { Log("CLOSE", "SHADOW "+reason); return; }
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i);
      if(PositionSelectByTicket(tk) &&
        (PositionGetInteger(POSITION_MAGIC)==MagicNumber+1 || PositionGetInteger(POSITION_MAGIC)==MagicNumber+2))
         tradeMain.PositionClose(tk);
   }
   CancelPending();
   Log("CLOSE", reason);
}
void CancelPending()
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong tk=OrderGetTicket(i);
      if(OrderGetInteger(ORDER_MAGIC)==MagicNumber+1 || OrderGetInteger(ORDER_MAGIC)==MagicNumber+2)
         tradeMain.OrderDelete(tk);
   }
}

//+------------------------------------------------------------------+
void CheckNewDay()
{
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   if(dt.day_of_year != g_dayOfYear)
   {
      g_dayOfYear = dt.day_of_year;
      g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      g_fuseTripped = false;
      g_dayEnded = false;
      g_nPartial = 0;
   }
}
void CheckDailyFuse()
{
   if(DailyLossPct<=0 && DailyProfitPct<=0) return;
   if(g_dayStartEquity <= 0) return;
   double d = AccountInfoDouble(ACCOUNT_EQUITY) - g_dayStartEquity;
   double lossLimit  = g_dayStartEquity * DailyLossPct  / 100.0;
   double profitTgt  = g_dayStartEquity * DailyProfitPct / 100.0;
   if(DailyLossPct>0 && lossLimit>0 && d <= -lossLimit)
   { g_fuseTripped=true; CloseAll("DAILY_LOSS_FUSE"); Log("FUSE", StringFormat("daily loss %.1f%% hit", DailyLossPct)); }
   if(DailyProfitPct>0 && profitTgt>0 && d >= profitTgt)
   { g_fuseTripped=true; CloseAll("DAILY_PROFIT_LOCK"); Log("FUSE", StringFormat("daily profit %.1f%% locked", DailyProfitPct)); }
}

//+------------------------------------------------------------------+
bool NewsBlackout()
{
   if(NewsFile=="") return false;
   int h = FileOpen(NewsFile, FILE_READ|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE) return false;
   // simple: file contains "start|end" per line, format yyyy.mm.dd hh:mm
   bool blk=false; datetime now=TimeCurrent();
   while(!FileIsEnding(h))
   {
      string ln = FileReadString(h);
      string se[]; if(StringSplit(ln,'|',se)!=2) continue;
      datetime ev=StringToTime(se[0]);          // event time = first field
      datetime s = ev - NewsBlockBeforeMin*60;  // window expanded by params
      datetime e = ev + NewsBlockAfterMin*60;
      if(now>=s && now<=e){ blk=true; break; }
      // also support explicit range lines "start|end" (both parseable dates)
      datetime e2=StringToTime(se[1]);
      if(e2>ev+60 && now>=StringToTime(se[0]) && now<=e2){ blk=true; break; }
   }
   FileClose(h);
   return blk;
}

//+------------------------------------------------------------------+
double NormalizeLot(double l)
{
   double minL = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maxL = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double st   = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   l = MathMax(minL, MathMin(maxL, l));
   l = MathRound(l/st)*st;
   return l;
}

//+------------------------------------------------------------------+
void Log(string tag, string msg)
{
   string line = StringFormat("%s,%s,%s\r\n", TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS), tag, msg);
   int h = FileOpen("plan_actions.log", FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE) return;
   FileSeek(h, 0, SEEK_END);
   FileWriteString(h, line);
   FileClose(h);
   Print("[", tag, "] ", msg);
}

//+------------------------------------------------------------------+
//| Pink minimalist panel                                            |
//+------------------------------------------------------------------+
// v4.09: on-chart visuals — SMA polyline + FVG boxes + entry/exit arrows
void DrawIndicators()
{
   if(!ShowIndicators) return;
   if(TimeCurrent() - g_lastIndDraw < 15) return;   // throttle ~4x/min
   g_lastIndDraw = TimeCurrent();

   string P="AGI_";
   int maxBars = 300;

   // ---- 1. SMA polyline on signal TF ----
   ENUM_TIMEFRAMES tf = SigTF();
   int hSMA = g_hSMA;
   if(hSMA==INVALID_HANDLE) return;
   double buf[];
   ArraySetAsSeries(buf, true);            // buf[k] = shift k (0=current forming)
   int n = CopyBuffer(hSMA, 0, 0, maxBars, buf);
   if(n > 2)
   {
      // v4.13: label latest SMA value
      LabelObj(P+"smaLbl", iTime(_Symbol, tf, 1), buf[1], StringFormat("SMA%d", SMA_Period), clrDeepSkyBlue);
      for(int k=1; k<n-1; k++)
      {
         datetime t1 = iTime(_Symbol, tf, k+1);
         datetime t2 = iTime(_Symbol, tf, k);
         string nm = P+"sma"+IntegerToString(k);
         double v1=buf[k+1], v2=buf[k];
         if(v1==EMPTY_VALUE||v2==EMPTY_VALUE) continue;
         if(ObjectFind(0, nm) < 0)
         {
            ObjectCreate(0, nm, OBJ_TREND, 0, t1, v1, t2, v2);
            ObjectSetInteger(0, nm, OBJPROP_COLOR, clrDeepSkyBlue);
            ObjectSetInteger(0, nm, OBJPROP_WIDTH, 2);
            ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT, false);
            ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
         }
         else
         {
            ObjectMove(0, nm, 0, t1, v1);
            ObjectMove(0, nm, 1, t2, v2);
         }
      }
   }

   // ---- 2. FVG boxes (M15 mode only) — mark detected gaps green/red ----
   if(StrategyMode == FVG_M15)
   {
      for(int i=1; i<=60; i++)
      {
         double h1v=iHigh(_Symbol,SigTF(),i), l1v=iLow(_Symbol,SigTF(),i);
         double h3v=iHigh(_Symbol,SigTF(),i+2), l3v=iLow(_Symbol,SigTF(),i+2);
         string nm = P+"fvg"+IntegerToString(i);
         if(l1v > h3v || h1v < l3v)
         {
            double top=MathMax(h3v,h1v), bot=MathMin(l3v,l1v);
            datetime t1=iTime(_Symbol,SigTF(),i+2);
            datetime t2=iTime(_Symbol,SigTF(),i)+FVG_TimeLimitBars*SignalTF_Minutes*60;  // box spans the trade window
            bool bull = (l1v > h3v);
            if(ObjectFind(0,nm)<0)
            {
               ObjectCreate(0,nm,OBJ_RECTANGLE,0,t1,top,t2,bot);
               ObjectSetInteger(0,nm,OBJPROP_COLOR, bull?clrLimeGreen:clrTomato);
               ObjectSetInteger(0,nm,OBJPROP_FILL,false);
               ObjectSetInteger(0,nm,OBJPROP_STYLE,STYLE_DOT);
               ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
               LabelObj(nm+"_t", t1, top, StringFormat("%s FVG %.1f", bull?"BULL":"BEAR", top-bot), bull?clrLimeGreen:clrTomato);
            }
         }
         else
            ObjectDelete(0,nm);
      }
   }
   ChartRedraw();
}
datetime g_lastIndDraw=0;

// v4.09: entry/exit arrows called from trade logic
void MarkEntry(bool isBuy, double price)
{
   if(!ShowIndicators) return;
   string nm="AGI_E"+IntegerToString((int)TimeCurrent())+"_"+IntegerToString(MathRand()%9999);
   ObjectCreate(0,nm,OBJ_ARROW,0,TimeCurrent(),price);
   ObjectSetInteger(0,nm,OBJPROP_ARROWCODE, isBuy?233:234);   // up/down arrow
   ObjectSetInteger(0,nm,OBJPROP_COLOR, isBuy?clrLime:clrRed);
   ObjectSetInteger(0,nm,OBJPROP_WIDTH,2);
   ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
   LabelObj(nm+"_t", TimeCurrent(), price, isBuy?"BUY":"SELL", isBuy?clrLime:clrRed, isBuy?ANCHOR_LEFT_UPPER:ANCHOR_LEFT_LOWER);
}
void MarkExit(bool isBuy, double price)
{
   if(!ShowIndicators) return;
   string nm="AGI_X"+IntegerToString((int)TimeCurrent())+"_"+IntegerToString(MathRand()%9999);
   ObjectCreate(0,nm,OBJ_ARROW,0,TimeCurrent(),price);
   ObjectSetInteger(0,nm,OBJPROP_ARROWCODE, isBuy?234:233);
   ObjectSetInteger(0,nm,OBJPROP_COLOR, clrGold);
   ObjectSetInteger(0,nm,OBJPROP_WIDTH,1);
   ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
}

//+------------------------------------------------------------------+
// ── v4.17 子窗指標冪等管理 ────────────────────────────────────────────────
// v4.17 根因：process 級旗標 reinit 歸零，chart 舊指標仍在（.chr 固化），
// CHART_WINDOWS_TOTAL append 每次 reinit +2 子窗，OnDeinit hardcoded 名刪唔中。
// v4.17：以 chart 實態為準（掃描為真），先清重複、count==0 先加；OnDeinit 用
// 同一掃描邏輯全清。留邊份無實質差異（同參數），先到先 keep。

bool SubInd_IsRSI(const string nm)
{
   if(StringFind(nm, "RSI") == 0) return true;
   if(StringFind(nm, "Relative Strength Index") == 0) return true;
   return false;
}
bool SubInd_IsATR(const string nm)
{
   if(StringFind(nm, "ATR") == 0) return true;
   if(StringFind(nm, "Average True Range") == 0) return true;
   return false;
}

// 掃全 chart 子窗（w=1..wins-1），回報 RSI/ATR 各幾多份
void SubInd_Count(int &rsiCount, int &atrCount)
{
   rsiCount = 0; atrCount = 0;
   int wins = (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);
   for(int w = 1; w < wins; w++)
   {
      int total = ChartIndicatorsTotal(0, w);
      for(int k = 0; k < total; k++)
      {
         string nm = ChartIndicatorName(0, w, k);
         if(SubInd_IsRSI(nm)) rsiCount++;
         if(SubInd_IsATR(nm)) atrCount++;
      }
   }
}

// 清重複（removeAll=false，每種留一份）或全清（removeAll=true，OnDeinit 用）
// 由高窗刪起：刪空窗會令窗數收縮、index 移位——外層迴圈每次重新讀窗數就安全。
// guard 32：實際子窗唔會超過呢個數，純防死循環（delete 失敗時照收工唔癱）。
int SubInd_RemoveExcess(bool removeAll)
{
   int removed = 0;
   int rsiKept = 0, atrKept = 0;
   for(int guard = 0; guard < 32; guard++)
   {
      int wins = (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);
      if(wins <= 1) break;                       // 淨返主圖，收工
      bool deletedThisRound = false;
      for(int w = wins - 1; w >= 1; w--)         // 由高窗刪起
      {
         int total = ChartIndicatorsTotal(0, w);
         for(int k = total - 1; k >= 0; k--)     // 子窗內由尾刪起
         {
            string nm = ChartIndicatorName(0, w, k);
            bool isRSI = SubInd_IsRSI(nm), isATR = SubInd_IsATR(nm);
            if(!isRSI && !isATR) continue;
            bool keep = !removeAll &&
                        ((isRSI && rsiKept == 0) || (isATR && atrKept == 0));
            if(keep)
            {
               if(isRSI) rsiKept = 1; else atrKept = 1;
               continue;
            }
            if(ChartIndicatorDelete(0, w, nm))
            {
               removed++;
               deletedThisRound = true;
            }
         }
      }
      if(!deletedThisRound) break;               // 冇刪走任何嘢 → 收工
   }
   return removed;
}

// v4.17：chart 上 RSI 同 ATR 各至少一份（取代 v4.17 process 級旗標判斷）
bool SubInd_Ready()
{
   int r = 0, a = 0;
   SubInd_Count(r, a);
   return (r > 0 && a > 0);
}

// v4.17：以 chart 實態為準，唔再靠 process 級旗標
void EnsureSubIndicators()
{
   if(!ShowIndicators) return;
   if(!IndReady()) return;

   // 1) 先清重複（reinit 後 chart 上可能留存舊份——.chr 已固化，EA 重載唔會清）
   SubInd_RemoveExcess(false);

   // 2) 清完再數：count==0 先加（append 新子窗；RSI 加完 ATR 另開一窗）
   int rsiCount = 0, atrCount = 0;
   SubInd_Count(rsiCount, atrCount);
   if(rsiCount == 0 && g_hRSI != INVALID_HANDLE)
      ChartIndicatorAdd(0, (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL), g_hRSI);
   if(atrCount == 0 && g_hATR != INVALID_HANDLE)
      ChartIndicatorAdd(0, (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL), g_hATR);
}
// v4.09b: text labels on SMA line / FVG boxes / arrows
void LabelObj(string nm, datetime t, double price, string txt, color clr, int anchor=ANCHOR_LEFT_UPPER)
{
   if(ObjectFind(0,nm)>=0) return;
   ObjectCreate(0,nm,OBJ_TEXT,0,t,price);
   ObjectSetString(0,nm,OBJPROP_TEXT,txt);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,8);
   ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,nm,OBJPROP_ANCHOR,anchor);
}

//+------------------------------------------------------------------+
void DrawPanel()
{
   if(TimeCurrent() - g_lastPanelDraw < 5) return;  // throttle
   g_lastPanelDraw = TimeCurrent();

   // ---- palette ----
   color COL_BG      = C'255,240,245';  // soft pink card bg
   color COL_HEADER  = C'231,84,128';   // deep pink header
   color COL_HEADER2 = C'255,143,177';  // header gradient light end
   color COL_CARD    = C'255,255,255';  // white cards
   color COL_BORDER  = C'245,184,206';  // card borders
   color COL_TITLE   = C'194,85,126';   // section titles
   color COL_TEXT    = C'122,64,85';    // body text
   color COL_MUTED   = C'160,96,112';   // small labels
   color COL_VALUE   = C'214,51,108';   // big values
   color COL_GREEN   = C'47,163,92';    // profit / status ok
   color COL_RED     = C'220,53,69';    // loss / tripped
   color COL_TRACK   = C'248,214,227';  // progress track
   color COL_ACCENT  = C'255,105,180';  // progress fill

   int X = 10, W = 230;                  // panel left/width
   int Y = 20;
   string P = "AG5_";

   // wipe old objects
   ObjectsDeleteAll(0, P);

   // full opaque backing board (hides all chart behind the panel column)
   ObjRect(P+"board", X-6, Y-6, W+12, 460, COL_BG, C'242,167,195');

   // ============ 1. header (56px, two-tone gradient feel) ============
   ObjRect(P+"hdr",  X, Y, W, 56, COL_HEADER);
   ObjRect(P+"hdr2", X+140, Y+18, W-140, 38, COL_HEADER2); // light end
   ObjRect(P+"hdr3", X, Y+18, 140, 38, COL_HEADER);        // seamless base
   ObjDot(P+"dot",  X+18, Y+28, COL_GREEN_BORDER, 9);       // status dot
   ObjText(P+"title", X+34, Y+16, "AngelGold v4.17", 11, COL_WHITE, "Arial");
   ObjText(P+"mode",  X+W-10, Y+20, EnableTrading ? "LIVE" : "SHADOW", 8, COL_HEADER2, "Arial Bold", true);

   Y += 64;
   // ============ 2. session strip ============
   ObjRect(P+"sesCard", X, Y, W, 46, COL_CARD, COL_BORDER);
   ObjText(P+"sesLbl", X+12, Y+6, "SESSION", 7, COL_MUTED);
   bool sesActive = (g_sessionStart > 0 && SessionNow() < g_sessionEnd);
   ObjText(P+"sesVal", X+12, Y+20, sesActive ? "ACTIVE" : "WAITING", 10,
           sesActive ? COL_VALUE : COL_MUTED, "Arial Bold");
   if(sesActive)
      ObjText(P+"sesWin", X+85, Y+20, TimeToString(g_sessionStart,TIME_MINUTES)+"-"+TimeToString(g_sessionEnd,TIME_MINUTES)+" ("+g_sesLabel+")", 8, COL_TEXT);
   // progress bar
   ObjRect(P+"sesTrack", X+150, Y+12, 68, 8, COL_TRACK);
   double prog = 0;
   if(sesActive)
      prog = MathMin(1.0, (double)(SessionNow()-g_sessionStart) / MathMax(1,(double)(g_sessionEnd-g_sessionStart)));
   ObjRect(P+"sesFill", X+150, Y+12, (int)(68*prog), 8, COL_ACCENT);

   Y += 54;
   // ============ 3. bias badge + positions ============
   string biasTxt = g_bias>0 ? "BIAS LONG" : (g_bias<0 ? "BIAS SHORT" : "NO BIAS");
   color  biasCol = g_bias>0 ? COL_GREEN : (g_bias<0 ? COL_RED : COL_MUTED);
   ObjRect(P+"bias", X, Y, 116, 30, biasCol, clrNONE, 15);
   ObjText(P+"biasT", X+58, Y+7, biasTxt, 9, COL_WHITE, "Arial Bold", false, true);
   ObjRect(P+"pos", X+122, Y, W-122, 30, COL_CARD, COL_BORDER, 8);
   ObjText(P+"posT", X+128, Y+8, StringFormat("Pos: %d", PositionsMine()), 9, COL_TEXT, "Arial Bold");

   Y += 40;
   // ============ 4. indicator cards (v4.17: live refresh) ============
   ComputeIndicators();
   ObjText(P+"indLbl", X, Y, "INDICATORS · M"+IntegerToString(SignalTF_Minutes), 7, COL_TITLE);
   Y += 14;
   int cw = (W - 12) / 3;
   string indT[3]; indT[0] = MAKindStr(); indT[1] = "RSI"; indT[2] = "ATR";
   double indV[3] = {g_sma, g_rsi, g_atr};
   for(int i=0;i<3;i++)
   {
      int cx = X + i*(cw+6);
      ObjRect(P+"ind"+IntegerToString(i), cx, Y, cw, 50, COL_CARD, COL_BORDER, 8);
      ObjText(P+"indT"+IntegerToString(i), cx+10, Y+6, indT[i]+IntegerToString(i==0?SMA_Period:(i==1?RSI_Period:ATR_Period)), 7, COL_MUTED);
      ObjText(P+"indV"+IntegerToString(i), cx+10, Y+22, DoubleToString(indV[i],1), 11, COL_VALUE, "Arial Bold");
   }

   Y += 58;
   // ============ 5. active orders (up to 2: MAIN + BREAK) ============
   ObjText(P+"ordLbl", X, Y, "ACTIVE ORDERS", 7, COL_TITLE);
   Y += 14;
   // enumerate pending+positions of ours
   string ordLines[4]; int nOrd = 0;
   for(int i=0;i<OrdersTotal() && nOrd<4;i++)
   {
      ulong tk = OrderGetTicket(i);
      if(tk==0) continue;
      long mg = OrderGetInteger(ORDER_MAGIC);
      if(mg!=MagicNumber+1 && mg!=MagicNumber+2) continue;
      string nm = (mg==MagicNumber+1) ? "MAIN" : "BREAK";
      long ty = OrderGetInteger(ORDER_TYPE);
      string tyS = (ty==ORDER_TYPE_BUY_LIMIT||ty==ORDER_TYPE_BUY_STOP) ? "Buy" : "Sell";
      string kS  = (ty==ORDER_TYPE_BUY_LIMIT||ty==ORDER_TYPE_SELL_LIMIT) ? "Limit" : "Stop";
      ordLines[nOrd] = StringFormat("%s %s %s|%.1f", nm, tyS, kS, OrderGetDouble(ORDER_PRICE_OPEN));
      nOrd++;
   }
   for(int i=PositionsTotal()-1; i>=0 && nOrd<4; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(!PositionSelectByTicket(tk)) continue;
      long mg = PositionGetInteger(POSITION_MAGIC);
      if(mg!=MagicNumber+1 && mg!=MagicNumber+2) continue;
      long ty = PositionGetInteger(POSITION_TYPE);
      ordLines[nOrd] = StringFormat("%s OPEN %s|%.1f sl %.1f", (mg==MagicNumber+1)?"MAIN":"BREAK",
          ty==POSITION_TYPE_BUY?"Buy":"Sell", PositionGetDouble(POSITION_PRICE_OPEN), PositionGetDouble(POSITION_SL));
      nOrd++;
   }
   if(nOrd==0)
   {
      ObjRect(P+"ord0", X, Y, W, 30, COL_CARD, COL_BORDER, 8);
      ObjText(P+"ord0T", X+12, Y+8, "no active orders", 8, COL_MUTED);
      Y += 38;
   }
   else
   {
      for(int i=0;i<nOrd;i++)
      {
         string det = ordLines[i];
         string head = StringSubstr(det, 0, StringFind(det,"|"));
         string tail = StringSubstr(det, StringFind(det,"|")+1);
         ObjRect(P+"ord"+IntegerToString(i), X, Y, W, 34, COL_CARD, COL_BORDER, 8);
         ObjRect(P+"ordBar"+IntegerToString(i), X, Y, 4, 34, COL_ACCENT);
         ObjText(P+"ordH"+IntegerToString(i), X+14, Y+5, head, 8, COL_TEXT);
         ObjText(P+"ordP"+IntegerToString(i), X+W-10, Y+5, tail, 8, COL_VALUE, "Arial Bold", true);
         Y += 40;
      }
   }

   // ============ 6. performance ============
   ObjText(P+"perfLbl", X, Y, "PERFORMANCE · TODAY", 7, COL_TITLE);
   Y += 14;
   double dayPnl = AccountInfoDouble(ACCOUNT_EQUITY) - g_dayStartEquity;
   color pnlCol = dayPnl >= 0 ? COL_GREEN : COL_RED;
   ObjRect(P+"perf", X, Y, W, 56, COL_CARD, COL_BORDER, 10);
   ObjText(P+"pnlLbl", X+12, Y+6, "Day P/L", 7, COL_MUTED);
   ObjText(P+"pnlVal", X+12, Y+20, StringFormat("%+.2f", dayPnl), 13, pnlCol, "Arial Bold");
   ObjText(P+"eqLbl", X+130, Y+6, "Equity", 7, COL_MUTED);
   ObjText(P+"eqVal", X+130, Y+20, DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2), 9, COL_TEXT, "Arial Bold");
   // fuse meter (% of day-start equity)
   double fuseLeft = 1.0;
   if(DailyLossPct > 0 && g_dayStartEquity > 0)
   {
      double lossLimit = g_dayStartEquity * DailyLossPct / 100.0;
      fuseLeft = MathMax(0.0, 1.0 - (-MathMin(0,dayPnl) / lossLimit));
   }
   ObjRect(P+"fuseTrack", X+130, Y+44, 88, 7, COL_TRACK);
   ObjRect(P+"fuseFill",  X+130, Y+44, (int)(88*fuseLeft), 7, fuseLeft>0.3?COL_GREEN:COL_RED);

   Y += 64;
   // ============ 7. footer status ============
   double sprd = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
   ObjRect(P+"foot", X, Y, W, 26, C'252,228,236', clrNONE, 8);
   ObjDot(P+"footDot", X+14, Y+10, g_fuseTripped ? COL_RED : COL_GREEN, 6);
   ObjText(P+"footT", X+28, Y+6, StringFormat("%s · NEWS %s · SPR %.2f",
           g_fuseTripped ? "FUSE TRIPPED" : "FUSE ARMED",
           NewsBlackout() ? "BLOCK" : "CLEAR", sprd), 7, COL_TEXT);

   ChartRedraw(0);
}

//+------------------------------------------------------------------+
//| Chart theme: white bg, green bull / red bear candles             |
//+------------------------------------------------------------------+
void ApplyPinkChartTheme()
{
   ChartSetInteger(0, CHART_COLOR_BACKGROUND,      C'255,255,255'); // white bg
   ChartSetInteger(0, CHART_COLOR_FOREGROUND,      C'140,70,95');
   ChartSetInteger(0, CHART_COLOR_GRID,            C'230,230,230');
   ChartSetInteger(0, CHART_COLOR_CANDLE_BULL,     C'38,166,91');   // green bull
   ChartSetInteger(0, CHART_COLOR_CANDLE_BEAR,     C'220,53,69');   // red bear
   ChartSetInteger(0, CHART_COLOR_CHART_UP,        C'38,166,91');
   ChartSetInteger(0, CHART_COLOR_CHART_DOWN,      C'220,53,69');
   ChartSetInteger(0, CHART_COLOR_CHART_LINE,      C'38,166,91');
   ChartSetInteger(0, CHART_COLOR_BID,             C'219,112,147');
   ChartSetInteger(0, CHART_COLOR_ASK,             C'176,105,135');
   ChartSetInteger(0, CHART_COLOR_STOP_LEVEL,      C'200,90,140');
   ChartSetInteger(0, CHART_COLOR_VOLUME,          C'219,112,147');
   ChartSetInteger(0, CHART_SHOW_GRID,             true);
   ChartSetInteger(0, CHART_MODE,                  0);
   ChartRedraw(0);
   Print("Chart theme applied");
}

// ---- object helpers ----
void ObjRect(string nm, int x, int y, int w, int h, color bg, color border=clrNONE, int radius=-1)
{
   ObjectCreate(0, nm, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, nm, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, nm, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, nm, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, nm, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, nm, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, border==clrNONE ? bg : border);
   ObjectSetInteger(0, nm, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, nm, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, nm, OBJPROP_BACK, false);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
}
void ObjText(string nm, int x, int y, string txt, int size, color col, string font="Arial", bool rightAlign=false, bool center=false)
{
   ObjectCreate(0, nm, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, nm, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   if(rightAlign) ObjectSetInteger(0, nm, OBJPROP_ANCHOR, ANCHOR_RIGHT_UPPER);
   else if(center) ObjectSetInteger(0, nm, OBJPROP_ANCHOR, ANCHOR_CENTER);
   else ObjectSetInteger(0, nm, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
   ObjectSetInteger(0, nm, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, nm, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, nm, OBJPROP_TEXT, txt);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, col);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, size);
   ObjectSetString(0, nm, OBJPROP_FONT, font);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
}
void ObjDot(string nm, int x, int y, color col, int d)
{
   ObjectCreate(0, nm, OBJ_BITMAP_LABEL, 0, 0, 0);
   // simple filled circle via ellipse label trick: use small rounded rect
   ObjectDelete(0, nm);
   ObjectCreate(0, nm, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, nm, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, nm, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, nm, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, nm, OBJPROP_XSIZE, d);
   ObjectSetInteger(0, nm, OBJPROP_YSIZE, d);
   ObjectSetInteger(0, nm, OBJPROP_BGCOLOR, col);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, col);
   ObjectSetInteger(0, nm, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_hSMA!=INVALID_HANDLE) IndicatorRelease(g_hSMA);
   if(g_hRSI!=INVALID_HANDLE) IndicatorRelease(g_hRSI);
   if(g_hATR!=INVALID_HANDLE) IndicatorRelease(g_hATR);
   ObjectsDeleteAll(0, "AGI_");
   // v4.17: 只有「EA 真係被移除／圖表關閉」才全清。TF 切換(3)、改參數(5)、
   // recompile(2)、換帳號(6) 等 reinit 一律保留子窗——保留後新一輪 OnInit 的
   // chart 實態掃描會自然收斂到每種一份；若喺 reinit 時刪走，新 TF 上
   // ChartIndicatorAdd 會失敗（實測 err 4114），子窗歸零。
   if(reason == REASON_REMOVE || reason == REASON_CHARTCLOSE)
      SubInd_RemoveExcess(true);

   ObjectsDeleteAll(0, "AG5_");
   Print("=== AngelGold v4.17 stopped (", reason, ") ===");
}
//+------------------------------------------------------------------+
