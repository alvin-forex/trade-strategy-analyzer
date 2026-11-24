//+------------------------------------------------------------------+
//|                                        ExtraCCYPower_EA.mq5      |
//|  MT5 EA SKELETON - card #41 (S4), lane zcode-local               |
//|                                                                  |
//|  SCOPE (per docs/ea/REQUIREMENT_EA_v0.1.md section 2.2):         |
//|    input frame / risk-control hooks / logging / lot sizing       |
//|    skeleton / backtest entry                                     |
//|                                                                  |
//|  HARD EXCLUSION: no entry logic, no exit logic, no grid,         |
//|    no indicator calls, no order sending of any kind.             |
//|    Strategy spec is O2 (still pending) - MUST NOT be invented.   |
//|                                                                  |
//|  Unresolved items are reported at OnInit as "MISSING:" lines.    |
//|  Nothing is silently defaulted to a trading decision.            |
//+------------------------------------------------------------------+
#property copyright "ZCODE for Alvin"
#property version   "1.02"
#property description "MT5 EA skeleton: input frame, risk hooks, logging, lot sizing, backtest entry. No strategy logic."

//--- version string used by the STARTED banner; keep in lock-step with
//--- #property version above and with the README (AGENTS.md section 6).
#define EA_VERSION "1.02"

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
   if(InpEaName == "")
      Print("MISSING: O1 - EA name is empty, filename and .set name are undecided");
   else
      PrintFormat("SKELETON: O1 accepted, EA name = %s", InpEaName);

   Print("MISSING: O2 - strategy spec (entry/exit, grid or not, indicators, TF) not supplied");
   Print("MISSING: O2 - no order-sending code exists in this build, by design");
   Print("MISSING: O3 - parameter list must follow the real .set fields; not supplied yet");
   Print("MISSING: O4 - acceptance thresholds (backtest numbers) not settled by owner");
   Print("MISSING: G3 - group names now follow ea-repo AGENTS.md section 3 for the groups");
   Print("MISSING: G3 - that carry inputs; groups without inputs are not declared (OC 21:05 D1).");

   if(InpNewsGuardEnable && InpNewsBlockMinutes > 0)
      Print("MISSING: O2 - news guard requested but no news source is bound in the skeleton");

   if(InpMaxLayers > 1 || InpLotMultiplier != 1.0)
      Print("MISSING: O2 - lot ladder inputs set above 1 layer but no ladder logic exists");
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

   string why = "";
   if(!ValidateInputs(why))
   {
      PrintFormat("SKELETON: input validation failed, %s", why);
      return(INIT_PARAMETERS_INCORRECT);
   }

   OpenLogFile();

   //--- STARTED banner (AGENTS.md section 6: the version string must be in
   //--- lock-step with #property version, the description and the README).
   //--- Printed once from OnInit only, never repeated from OnTick
   //--- (OC ruling 2026-11-23 21:05, item D2).
   PrintFormat("%s STARTED v%s on %s %s", InpEaName, EA_VERSION,
               g_symbol, EnumToString(InpWorkTimeframe));

   PrintFormat("SKELETON: orders=DISABLED (no O2 spec)");

   PrintFormat("SKELETON: volume spec min=%s max=%s step=%s",
               DoubleToString(g_volMin, 4), DoubleToString(g_volMax, 4), DoubleToString(g_volStep, 4));

   PrintFormat("SKELETON: base lot=%s cap=%s layers=%d multiplier=%s",
               DoubleToString(InpBaseLot, 2), DoubleToString(TotalLotsCap(), 2),
               InpMaxLayers, DoubleToString(InpLotMultiplier, 3));

   PrintMissingItems();

   LogEvent("init", "skeleton ready, trading disabled");
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

   PrintFormat("SKELETON: detached, reason=%d, log=%s", reason,
               (InpLogToFile ? g_logPath : "disabled"));
}

//+------------------------------------------------------------------+
//| OnTick - deliberately performs NO trading action.                 |
//| Only the risk-hook evaluation and optional heartbeat are wired.   |
//+------------------------------------------------------------------+
void OnTick()
{
   string blockReason = "";
   bool   allowed     = RiskGuardAllow(blockReason);

   if(!InpLogHeartbeat)
      return;

   if(InpHeartbeatSeconds > 0 && (TimeCurrent() - g_lastBeat) < (datetime)InpHeartbeatSeconds && g_lastBeat != 0)
      return;

   g_lastBeat = TimeCurrent();

   int    posCount = 0;
   double posLots  = 0.0;
   CountSymbolPositions(posCount, posLots);

   PrintFormat("SKELETON: heartbeat symbol=%s equity=%s dd=%s%% pos=%d lots=%s gate=%s%s",
               g_symbol,
               DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2),
               DoubleToString(CurrentDrawdownPercent(), 3),
               posCount,
               DoubleToString(posLots, 2),
               (allowed ? "allow" : "block"),
               (allowed ? "" : (" (" + blockReason + ")")));

   LogEvent("heartbeat", (allowed ? "gate allow" : ("gate block: " + blockReason)));
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
