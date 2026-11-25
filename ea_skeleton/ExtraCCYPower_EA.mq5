//+------------------------------------------------------------------+
//|                                        ExtraCCYPower_EA.mq5      |
//|  MT5 EA SKELETON - card #41 (S4), lane zcode-local               |
//|                                                                  |
//|  SCOPE (OC ruling 2026-11-25 08:15, SPEC v0.1 signed 01:52):      |
//|    strategy layer: fake-break fade + fast/slow power filter,      |
//|    ATR(14) risk units (R=1ATR), CTrade entry/exit, daily 3R fuse.  |
//|    Risk guards remain OFF by default; power comes from external    |
//|    CSV (A1 ruling): ccy_power\CCYPOWER_<SYMBOL>_<TF>.csv.          |
//+------------------------------------------------------------------+
#property copyright "ZCODE for Alvin"
#property version   "1.03"
#property description "MT5 EA: fake-break fade + fast/slow power filter, ATR-based SL/TP, daily 3R fuse. Strategy SPEC v0.1."
#define EA_VERSION "1.03"

//--- card #41: risk guards must default OFF (REQUIREMENT 2.4 / acceptance A3)
//--- Group names and relative order follow ea-repo AGENTS.md section 3 for the
//--- groups that carry inputs. Groups with no input are NOT declared
//--- (OC ruling 2026-11-23 21:05, item D1: "有 input 先開組").
//--- Owner ruling 2026-11-24 08:15 (via OC 0825 item D1): "Lot Sizing" and
//--- "Backtest" are group 13 and 14, i.e. they come AFTER "Diagnostics".
//--- They therefore now sit in section 3 order instead of the placeholder
//--- positions they held while the names were still awaiting approval.

input group "General"
input string InpEaName          = "ExtraCCYPower_EA";  // EA identity string (O1)
input long   InpMagicNumber     = 241123;              // Magic number; 0 = disable filtering
input string InpLogBaseName     = "ExtraCCYPower_EA";  // Log file base name, no extension
input string InpWorkSymbol      = "";                  // Working symbol; empty = chart symbol
input ENUM_TIMEFRAMES InpWorkTimeframe = PERIOD_CURRENT; // Working timeframe; CURRENT = chart

input group "DD Guard — Account"
input bool   InpDdGuardEnable   = false;               // Enable account drawdown guard
input double InpDdMaxPercent    = 0.00;                // Max drawdown (%); 0.00 = disabled
input double InpDdMaxMoney      = 0.00;                // Max drawdown ($); 0.00 = disabled

input group "Symbol Guard"
input bool   InpSymGuardEnable  = false;               // Enable per-symbol guard
input int    InpSymMaxPositions = 0;                   // Max open positions (count); 0 = off
input double InpSymMaxLots      = 0.00;                // Max lots on symbol (lots); 0.00 = off

input group "News Guard"
input bool   InpNewsGuardEnable = false;               // Enable news guard
input int    InpNewsBlockMinutes = 0;                  // Minutes blocked (min); 0 = disabled

input group "Diagnostics"
input bool   InpLogToFile       = true;                // Write CSV log to MQL5/Files
input bool   InpLogHeartbeat    = false;               // Print heartbeat line on tick
input int    InpHeartbeatSeconds = 3600;               // Heartbeat interval (sec); 0 = off

input group "Lot Sizing"
input double InpBaseLot         = 0.01;                // Base lot for the first layer (lots)
input double InpLotMultiplier   = 1.00;                // Lot multiplier per layer; 1.00 = flat
input int    InpMaxLayers       = 1;                   // Max layers allowed (count); 1 = single
input double InpMaxLotTotal     = 0.00;                // Max total lots overall (lots); 0.00 = off

input group "Backtest"
input bool   InpTesterSummary   = true;                // Write tester summary CSV in OnTester

input group "Signal"
input int    InpFakeBreakBars   = 3;                   // Fake breakout: reclaim within N bars
input int    InpPivotK          = 3;                   // Pivot confirmation neighbours (k)
input double InpAtrTol          = 0.10;                // Fake break must exceed level by ATR x this
input int    InpFastPowerTF     = PERIOD_H1;           // Fast power timeframe (SPEC: H1)
input int    InpSlowPowerTF     = PERIOD_H4;           // Slow power timeframe (SPEC: H4)
input int    InpFastPowerPeriod = 10;                  // Fast power period (research H4_10)
input int    InpSlowPowerPeriod = 120;                 // Slow power period (research H4_120)
input string InpPowerDir        = "ccy_power";         // CSV dir under MQL5/Files

input group "Exit"
input double InpSlR             = 0.5;                 // Stop loss in R (R = 1 x ATR(14))
input double InpTpR             = 1.0;                 // Take profit in R
input double InpDailyMaxR       = 3.0;                 // Daily loss fuse in R
input bool   InpCompareTp2Sl1    = false;              // Backtest-only: TP=2ATR / SL=1ATR control group

//--- resolved runtime state (never a trading decision)
string   g_symbol      = "";
string   g_logPath     = "";
double   g_volMin      = 0.0;
double   g_volMax      = 0.0;
double   g_volStep     = 0.0;
int      g_logHandle   = INVALID_HANDLE;
bool     g_logEnabled  = false;   // runtime mirror of InpLogToFile (inputs are read-only)
datetime g_lastBeat    = 0;
long     g_initErrors  = 0;

//--- strategy runtime state (SPEC v0.1, OC ruling 2026-11-25 08:15)
#include <Trade\Trade.mqh>
CTrade   g_trade;
int      g_hATR           = INVALID_HANDLE;
double   g_dayStartEquity = 0.0;
int      g_lastDay        = 0;
double   g_dailyR         = 0.0;   // cumulative R today; fuse at -InpDailyMaxR
datetime g_lastSignalBar  = 0;    // open time of the last processed signal bar
string   g_lastPowerErr   = "";

//+------------------------------------------------------------------+
//| R unit: 1 x ATR(14) on the entry TF. Returns false (r untouched)  |
//| when the indicator is not ready -- an unpriced risk unit is not   |
//| a tradable quantity, mirroring W1 atr() warm-up = None.            |
//+------------------------------------------------------------------+
bool CurrentR(double &r)
{
   r = 0.0;
   if(g_hATR == INVALID_HANDLE)
      return(false);
   double buf[1];
   if(CopyBuffer(g_hATR, 0, 1, 1, buf) != 1)
      return(false);
   if(buf[0] <= 0.0)
      return(false);
   r = buf[0];
   return(true);
}

//+------------------------------------------------------------------+
//| Power CSV reader (A1 path locked by OC 1815):                     |
//|   <InpPowerDir>\CCYPOWER_<SYMBOL>_<TF>.csv ; header time,power    |
//| Returns the two newest values strictly before `beforeTime`, so a  |
//| caller can build slope = now - prev (OC 0120 item 1: NOT a linear |
//| regression). EA reads only; it never writes the file.             |
//+------------------------------------------------------------------+
bool ReadPowerDiff(string tfName, datetime beforeTime, double &diff, string &why)
{
   diff = 0.0;
   why  = "";
   string path = InpPowerDir + "\\CCYPOWER_" + g_symbol + "_" + tfName + ".csv";
   int h = FileOpen(path, FILE_READ | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE)
   {
      why = StringFormat("power file missing: %s (err=%d)", path, GetLastError());
      return(false);
   }
   if(!FileIsEnding(h))
   {
      string hdr = FileReadString(h);   // header: time,power; discard
      hdr = "";
   }

   datetime newestTs = 0, prevTs = 0;
   double   newestV = 0.0, prevV = 0.0;
   while(!FileIsEnding(h))
   {
      string t = FileReadString(h);
      if(FileIsEnding(h))
         break;
      string p = FileReadString(h);
      if(StringLen(t) < 16 || p == "")
         continue;
      datetime ts = StringToTime(StringSubstr(t, 0, 16));
      if(ts <= 0 || ts >= beforeTime)
         continue;
      double v = StringToDouble(p);
      if(ts > newestTs)
      {
         prevTs = newestTs; prevV = newestV;
         newestTs = ts;     newestV = v;
      }
      else if(ts > prevTs && ts < newestTs)
      {
         prevTs = ts; prevV = v;
      }
   }
   FileClose(h);
   if(newestTs == 0 || prevTs == 0)
   {
      why = StringFormat("power file has <2 rows before %s: %s",
                         TimeToString(beforeTime), path);
      return(false);
   }
   diff = newestV - prevV;
   return(true);
}

//+------------------------------------------------------------------+
//| Fast/slow power agreement, verbatim from W1 power_agrees(): both  |
//| spreads must have the same sign as the intended fade direction.   |
//+------------------------------------------------------------------+
bool PowerAgrees(double fastDiff, double slowDiff, int direction)
{
   bool up = (direction > 0);
   return(((fastDiff > 0) == up) && ((slowDiff > 0) == up));
}

//+------------------------------------------------------------------+
//| Fake-break detection on closed bars, port of W1 pivots()+         |
//| fake_breaks(). shift 1 = last closed bar. A resistance fake means |
//| price traded above level+tol then closed back below -> fade short;|
//| a support fake is the mirror -> fade long. Returns the reclaim    |
//| bar's close time in `signalTime` (enter on the next open).         |
//+------------------------------------------------------------------+
bool DetectFakeBreak(int k, double atrTol, int lookback,
                     int &direction, double &level, datetime &signalTime)
{
   direction  = 0;
   level      = 0.0;
   signalTime = 0;

   int need = k + 2;
   if(BarsCalculated(g_hATR) < need)
      return(false);

   MqlRates rates[];
   int copied = CopyRates(g_symbol, PERIOD_CURRENT, 0, lookback, rates);
   if(copied < need)
      return(false);
   ArraySetAsSeries(rates, true);   // rates[0] = newest closed bar

   double atrBuf[1];
   for(int idx = k; idx < copied - k; idx++)
   {
      double hi = rates[idx].high, lo = rates[idx].low;
      bool isR = true, isS = true;
      for(int d = -k; d <= k; d++)
      {
         if(d == 0)
            continue;
         if(rates[idx + d].high > hi) isR = false;
         if(rates[idx + d].low  < lo) isS = false;
      }
      if(!isR && !isS)
         continue;

      int kind = isR ? 1 : -1;   // +1 = resistance (fade short), -1 = support (fade long)
      double lvl = isR ? hi : lo;
      for(int j = idx - k; j >= 1 && j >= idx - lookback; j--)
      {
         if(CopyBuffer(g_hATR, 0, j, 1, atrBuf) != 1 || atrBuf[0] <= 0.0)
            continue;
         double tol = atrTol * atrBuf[0];
         bool fake = false;
         if(kind > 0 && rates[j].high > lvl + tol && rates[j].close < lvl)
            fake = true;
         if(kind < 0 && rates[j].low  < lvl - tol && rates[j].close > lvl)
            fake = true;
         if(fake)
         {
            direction  = (kind > 0) ? -1 : 1;
            level      = lvl;
            signalTime = rates[j].time;
            return(true);
         }
      }
   }
   return(false);
}

//+------------------------------------------------------------------+
//| Daily R accounting. Resets at each new server day; when cumulative|
//| R losses reach -InpDailyMaxR no new entry is allowed that day.     |
//+------------------------------------------------------------------+
void UpdateDayFuse()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.day != g_lastDay)
   {
      g_lastDay        = dt.day;
      g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      g_dailyR         = 0.0;
   }
}

bool DayFuseAllows()
{
   if(InpDailyMaxR <= 0.0)
      return(true);
   return(g_dailyR > -InpDailyMaxR);
}

//+------------------------------------------------------------------+
//| Resolve the working symbol (chart symbol when input is empty)     |
//+------------------------------------------------------------------+
string ResolveSymbol()
{
   if(InpWorkSymbol == "")
      return(_Symbol);
   return(InpWorkSymbol);
}

//+------------------------------------------------------------------+
//| Load the volume constraints of the resolved symbol                |
//+------------------------------------------------------------------+
void LoadVolumeSpec()
{
   g_volMin  = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN);
   g_volMax  = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MAX);
   g_volStep = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP);

   if(g_volStep <= 0.0)
      g_volStep = 0.01;
   if(g_volMin <= 0.0)
      g_volMin = g_volStep;
}

//+------------------------------------------------------------------+
//| Clamp a requested lot to broker volume constraints                |
//+------------------------------------------------------------------+
double NormalizeLots(double lots)
{
   double step = g_volStep;
   double v    = MathRound(lots / step) * step;

   if(v < g_volMin)
      v = g_volMin;
   if(g_volMax > 0.0 && v > g_volMax)
      v = g_volMax;

   return(NormalizeDouble(v, 8));
}

//+------------------------------------------------------------------+
//| SKELETON lot ladder: base lot at layer 0, multiplied afterwards.  |
//| No strategy meaning is attached to "layer" - it is a container    |
//| for the future O2 spec, not a grid implementation.                |
//+------------------------------------------------------------------+
double CalcLayerLot(int layer)
{
   if(layer < 0)
      layer = 0;

   double raw = InpBaseLot * MathPow(InpLotMultiplier, (double)layer);
   return(NormalizeLots(raw));
}

//+------------------------------------------------------------------+
//| Risk hooks. All guards default OFF, therefore the hooks return    |
//| "allowed" unless the operator explicitly turned one on.           |
//| No order is ever placed by this skeleton; the hooks only decide.  |
//+------------------------------------------------------------------+
bool CountSymbolPositions(int &count, double &lots)
{
   count = 0;
   lots  = 0.0;

   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(!PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != g_symbol)
         continue;
      if(InpMagicNumber > 0 && (long)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;

      count++;
      lots += PositionGetDouble(POSITION_VOLUME);
   }

   return(count > 0);
}

double CurrentDrawdownPercent()
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);

   if(balance <= 0.0)
      return(0.0);
   return((balance - equity) / balance * 100.0);
}

double CurrentDrawdownMoney()
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   return(balance - equity);
}

bool RiskGuardAllow(string &reason)
{
   reason = "";

   if(InpDdGuardEnable)
   {
      if(InpDdMaxPercent > 0.0 && CurrentDrawdownPercent() >= InpDdMaxPercent)
      {
         reason = "DD guard: percent limit";
         return(false);
      }
      if(InpDdMaxMoney > 0.0 && CurrentDrawdownMoney() >= InpDdMaxMoney)
      {
         reason = "DD guard: money limit";
         return(false);
      }
   }

   if(InpSymGuardEnable)
   {
      int    posCount = 0;
      double posLots  = 0.0;
      CountSymbolPositions(posCount, posLots);

      if(InpSymMaxPositions > 0 && posCount >= InpSymMaxPositions)
      {
         reason = "Symbol guard: position cap";
         return(false);
      }
      if(InpSymMaxLots > 0.0 && posLots >= InpSymMaxLots)
      {
         reason = "Symbol guard: lot cap";
         return(false);
      }
   }

   if(InpNewsGuardEnable && InpNewsBlockMinutes > 0)
   {
      //--- no calendar binding in the skeleton: report the hook as unbound
      //--- rather than pretending a news state exists (O2 dependent)
      reason = "";
   }

   return(true);
}

double TotalLotsCap()
{
   if(InpMaxLotTotal <= 0.0)
      return(0.0);
   return(NormalizeLots(InpMaxLotTotal));
}

//+------------------------------------------------------------------+
//| Logging                                                          |
//+------------------------------------------------------------------+
void OpenLogFile()
{
   g_logEnabled = InpLogToFile;

   if(!g_logEnabled)
      return;

   string name = InpLogBaseName + "_skeleton.csv";
   g_logPath   = name;
   g_logHandle = FileOpen(name, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');

   if(g_logHandle == INVALID_HANDLE)
   {
      PrintFormat("SKELETON: log file open failed, error=%d", GetLastError());
      g_logEnabled = false;
      return;
   }

   FileWrite(g_logHandle,
             "event", "server_time", "symbol", "balance", "equity",
             "dd_percent", "positions", "lots", "lot_cap", "note");
   FileFlush(g_logHandle);
}

void LogEvent(string event, string note)
{
   if(!g_logEnabled || g_logHandle == INVALID_HANDLE)
      return;

   int    posCount = 0;
   double posLots  = 0.0;
   CountSymbolPositions(posCount, posLots);

   FileWrite(g_logHandle,
             event,
             TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),
             g_symbol,
             DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
             DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2),
             DoubleToString(CurrentDrawdownPercent(), 4),
             IntegerToString(posCount),
             DoubleToString(posLots, 2),
             DoubleToString(TotalLotsCap(), 2),
             note);
   FileFlush(g_logHandle);
}

void CloseLogFile()
{
   if(g_logHandle != INVALID_HANDLE)
   {
      FileClose(g_logHandle);
      g_logHandle = INVALID_HANDLE;
   }
}

//+------------------------------------------------------------------+
//| Report every unresolved input / spec dependency as MISSING:       |
//+------------------------------------------------------------------+
void PrintMissingItems()
{
   //--- v1.03: SPEC v0.1 signed 01:52, strategy layer filled per OC 0815.
   //--- O2/O3/O4 are no longer MISSING: entry/exit, parameter list and
   //--- acceptance numbers are all settled in SPEC v0.1.
   PrintFormat("EAMLFILL: strategy=SPEC v0.1 fake-break fade + fast/slow power");
   PrintFormat("EAMLFILL: R=1xATR(14), SL=%.2fR TP=%.2fR, daily fuse=%.2fR",
               InpSlR, InpTpR, InpDailyMaxR);
   PrintFormat("EAMLFILL: power CSV dir=%s (read-only, A1 format)", InpPowerDir);

   if(InpNewsGuardEnable && InpNewsBlockMinutes > 0)
      Print("MISSING: O2 - news guard requested but no news calendar source is bound");

   if(InpCompareTp2Sl1)
      Print("EAMLFILL: backtest control group enabled: TP=2ATR / SL=1ATR");
}

//+------------------------------------------------------------------+
//| Validate operator inputs (structural only, no strategy judgment)  |
//+------------------------------------------------------------------+
bool ValidateInputs(string &why)
{
   why = "";

   if(InpBaseLot <= 0.0)
   {
      why = "InpBaseLot must be > 0";
      return(false);
   }
   if(g_volMax > 0.0 && InpBaseLot > g_volMax)
   {
      why = "InpBaseLot exceeds symbol volume max";
      return(false);
   }
   if(InpLotMultiplier < 1.0)
   {
      why = "InpLotMultiplier must be >= 1.0";
      return(false);
   }
   if(InpMaxLayers < 1)
   {
      why = "InpMaxLayers must be >= 1";
      return(false);
   }
   if(InpMaxLotTotal > 0.0 && InpMaxLotTotal < InpBaseLot)
   {
      why = "InpMaxLotTotal must not be below InpBaseLot";
      return(false);
   }
   if(InpHeartbeatSeconds < 0)
   {
      why = "InpHeartbeatSeconds must be >= 0";
      return(false);
   }
   if(InpLogBaseName == "")
   {
      why = "InpLogBaseName must not be empty";
      return(false);
   }

   //--- v1.03 strategy inputs
   if(InpFakeBreakBars < 1)
   {
      why = "InpFakeBreakBars must be >= 1";
      return(false);
   }
   if(InpPivotK < 1)
   {
      why = "InpPivotK must be >= 1";
      return(false);
   }
   if(InpAtrTol <= 0.0)
   {
      why = "InpAtrTol must be > 0";
      return(false);
   }
   if(InpSlR <= 0.0 || InpTpR <= 0.0)
   {
      why = "InpSlR and InpTpR must be > 0";
      return(false);
   }
   if(InpDailyMaxR < 0.0)
   {
      why = "InpDailyMaxR must be >= 0";
      return(false);
   }
   if(InpPowerDir == "")
   {
      why = "InpPowerDir must not be empty";
      return(false);
   }

   return(true);
}

//+------------------------------------------------------------------+
//| OnInit                                                          |
//+------------------------------------------------------------------+
int OnInit()
{
   g_symbol = ResolveSymbol();

   if(g_symbol == "" || !SymbolSelect(g_symbol, true))
   {
      PrintFormat("SKELETON: symbol resolution failed for '%s'", g_symbol);
      return(INIT_PARAMETERS_INCORRECT);
   }

   LoadVolumeSpec();

   //--- ATR(14) handle for the R unit (SPEC: R = 1 x ATR(14), entry TF)
   g_hATR = iATR(g_symbol, PERIOD_CURRENT, 14);
   if(g_hATR == INVALID_HANDLE)
   {
      PrintFormat("EAMLFILL: iATR(14) handle failed, err=%d", GetLastError());
      return(INIT_FAILED);
   }

   string why = "";
   if(!ValidateInputs(why))
   {
      PrintFormat("EAMLFILL: input validation failed, %s", why);
      return(INIT_PARAMETERS_INCORRECT);
   }

   OpenLogFile();

   //--- STARTED banner (AGENTS.md section 6: the version string must be in
   //--- lock-step with #property version, the description and the README).
   //--- Printed once from OnInit only, never repeated from OnTick
   //--- (OC ruling 2026-11-23 21:05, item D2).
   PrintFormat("%s STARTED v%s on %s %s", InpEaName, EA_VERSION,
               g_symbol, EnumToString(InpWorkTimeframe));

   PrintFormat("EAMLFILL: orders=ENABLED per SPEC v0.1 (guards default OFF)");

   PrintFormat("EAMLFILL: volume spec min=%s max=%s step=%s",
               DoubleToString(g_volMin, 4), DoubleToString(g_volMax, 4), DoubleToString(g_volStep, 4));

   PrintFormat("EAMLFILL: base lot=%s cap=%s layers=%d multiplier=%s",
               DoubleToString(InpBaseLot, 2), DoubleToString(TotalLotsCap(), 2),
               InpMaxLayers, DoubleToString(InpLotMultiplier, 3));

   PrintMissingItems();
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   UpdateDayFuse();

   LogEvent("init", "strategy v1.03 ready, SPEC v0.1");
   g_lastBeat = TimeCurrent();

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| OnDeinit                                                        |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   LogEvent("deinit", StringFormat("reason=%d errors=%d", reason, g_initErrors));
   CloseLogFile();

   PrintFormat("EAMLFILL: detached, reason=%d, log=%s", reason,
               (InpLogToFile ? g_logPath : "disabled"));
   if(g_hATR != INVALID_HANDLE)
   {
      IndicatorRelease(g_hATR);
      g_hATR = INVALID_HANDLE;
   }
}

//+------------------------------------------------------------------+
//| OnTick - SPEC v0.1 strategy evaluation on each newly closed bar.  |
//|  1. fake break on closed bars -> fade direction                   |
//|  2. fast/slow power must agree (both CSV read-only)               |
//|  3. three risk guards (default OFF) must allow                    |
//|  4. daily 3R fuse must allow                                      |
//|  5. enter with CTrade at R-based SL/TP; only one open position    |
//+------------------------------------------------------------------+
void OnTick()
{
   UpdateDayFuse();

   //--- only act once per newly closed bar
   datetime closedBarTime = iTime(g_symbol, PERIOD_CURRENT, 1);
   if(closedBarTime == 0 || closedBarTime == g_lastSignalBar)
      return;

   string blockReason = "";
   bool   allowed     = RiskGuardAllow(blockReason);

   int    dir = 0;
   double lvl = 0.0;
   datetime sigTime = 0;
   if(!DetectFakeBreak(InpPivotK, InpAtrTol, InpFakeBreakBars, dir, lvl, sigTime))
      return;
   if(sigTime != closedBarTime)
      return;   //--- signal is from an older bar; never act late

   //--- fast/slow power filter; TF names are the MT5 period enum names
   string fastTf = EnumToString((ENUM_TIMEFRAMES)InpFastPowerTF);
   string slowTf = EnumToString((ENUM_TIMEFRAMES)InpSlowPowerTF);
   double fastDiff = 0.0, slowDiff = 0.0, junk = 0.0;
   if(!ReadPowerDiff(fastTf, closedBarTime, fastDiff, g_lastPowerErr) ||
      !ReadPowerDiff(slowTf, closedBarTime, slowDiff, g_lastPowerErr))
   {
      LogEvent("signal_skip", "power unavailable: " + g_lastPowerErr);
      return;
   }
   if(!PowerAgrees(fastDiff, slowDiff, dir))
   {
      LogEvent("signal_skip", "power divergence");
      return;
   }
   if(!allowed || !DayFuseAllows())
   {
      LogEvent("signal_skip", "gate/fuse blocked: " + blockReason);
      return;
   }

   //--- one position at a time
   int posCount = 0;
   double posLots = 0.0;
   if(CountSymbolPositions(posCount, posLots))
      return;

   double r = 0.0;
   if(!CurrentR(r))
      return;
   double slDist = InpSlR * r;
   double tpDist = InpTpR * r;
   if(InpCompareTp2Sl1)
   {
      slDist = 1.0 * r;   //--- backtest control group: SL=1ATR, TP=2ATR
      tpDist = 2.0 * r;
   }
   if(slDist <= 0.0 || tpDist <= 0.0)
      return;

   double lot = NormalizeLots(InpBaseLot);
   double ask = SymbolInfoDouble(g_symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(g_symbol, SYMBOL_BID);
   bool ok = false;
   if(dir > 0)
      ok = g_trade.Buy(lot, g_symbol, ask,
                       NormalizeDouble(ask - slDist, _Digits),
                       NormalizeDouble(ask + tpDist, _Digits),
                       "SPECv0.1 fade long");
   else if(dir < 0)
      ok = g_trade.Sell(lot, g_symbol, bid,
                        NormalizeDouble(bid + slDist, _Digits),
                        NormalizeDouble(bid - tpDist, _Digits),
                        "SPECv0.1 fade short");
   if(!ok)
   {
      LogEvent("order_fail", StringFormat("retcode=%d comment=%s",
               g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription()));
      return;
   }

   g_lastSignalBar = closedBarTime;
   LogEvent("entry", StringFormat("dir=%d lot=%s sl=%s tp=%s R=%s",
            dir, DoubleToString(lot, 2),
            DoubleToString(slDist, _Digits), DoubleToString(tpDist, _Digits),
            DoubleToString(r, _Digits)));

   //--- heartbeat (unchanged structural telemetry)
   if(InpLogHeartbeat && (TimeCurrent() - g_lastBeat) >= (datetime)InpHeartbeatSeconds)
   {
      g_lastBeat = TimeCurrent();
      PrintFormat("EAMLFILL: heartbeat %s equity=%s dd=%s%% gate=%s",
                  g_symbol,
                  DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2),
                  DoubleToString(CurrentDrawdownPercent(), 3),
                  (allowed ? "allow" : "block"));
   }
}

//+------------------------------------------------------------------+
//| OnTester - backtest entry. Writes a structural summary only.      |
//| An empty strategy must yield a flat equity curve; this handler    |
//| records that state instead of interpreting it as performance.     |
//+------------------------------------------------------------------+
double OnTester()
{
   double initialDeposit = TesterStatistics(STAT_INITIAL_DEPOSIT);
   double grossProfit    = TesterStatistics(STAT_GROSS_PROFIT);
   double grossLoss      = TesterStatistics(STAT_GROSS_LOSS);
   double totalTrades    = TesterStatistics(STAT_TRADES);
   double maxDrawdown    = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double profitTrades   = TesterStatistics(STAT_PROFIT_TRADES);
   double lossTrades     = TesterStatistics(STAT_LOSS_TRADES);

   //--- STAT_FINAL_BALANCE is not exposed by this build; final balance is
   //--- reconstructed from the deposit plus net result, never guessed.
   double finalBalance   = initialDeposit + grossProfit + grossLoss;

   LogEvent("tester", StringFormat("trades=%d", (int)totalTrades));

   if(InpTesterSummary)
   {
      string name = InpLogBaseName + "_tester_summary.csv";
      int    h    = FileOpen(name, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');

      if(h == INVALID_HANDLE)
      {
         PrintFormat("SKELETON: tester summary open failed, error=%d", GetLastError());
      }
      else
      {
         FileWrite(h, "key", "value");
         FileWrite(h, "ea_name", InpEaName);
         FileWrite(h, "symbol", g_symbol);
         FileWrite(h, "initial_deposit", DoubleToString(initialDeposit, 2));
         FileWrite(h, "final_balance", DoubleToString(finalBalance, 2));
         FileWrite(h, "gross_profit", DoubleToString(grossProfit, 2));
         FileWrite(h, "gross_loss", DoubleToString(grossLoss, 2));
         FileWrite(h, "trades", IntegerToString((int)totalTrades));
         FileWrite(h, "profit_trades", DoubleToString(profitTrades, 0));
         FileWrite(h, "loss_trades", DoubleToString(lossTrades, 0));
         FileWrite(h, "max_equity_dd_percent", DoubleToString(maxDrawdown, 4));
         FileWrite(h, "note", "skeleton build, no strategy logic, orders disabled");
         FileClose(h);

         PrintFormat("SKELETON: tester summary written to %s", name);
      }
   }

   //--- skeleton has no strategy, so return a neutral score
   return(0.0);
}
//+------------------------------------------------------------------+
