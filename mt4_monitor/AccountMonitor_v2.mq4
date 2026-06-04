//+------------------------------------------------------------------+
//|                                        AccountMonitor_v2.mq4     |
//|                         MT4 Smart Account Monitor with Indicators |
//|                         v2.00 — Trade Detection + Indicator Snap  |
//+------------------------------------------------------------------+
#property copyright "Alvin Forex System"
#property version   "2.00"
#property strict
#property description "Monitor account, detect new/closed trades, snapshot indicators, notify via CSV"

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input string   AccountLabel      = "";          // Account label (empty = auto)
input int      CheckInterval     = 10;          // Check interval (seconds)
input string   ApiUrl            = "http://localhost:8788"; // API endpoint
input bool     EnableHTTP        = false;       // Enable HTTP POST
input bool     EnableCSV         = true;        // Enable CSV event log
input bool     EnableIndicators  = true;        // Collect indicator data
input bool     EnableStateLog    = true;        // Periodic state log

//+------------------------------------------------------------------+
//| Global Variables                                                  |
//+------------------------------------------------------------------+
datetime g_lastCheck       = 0;
string   g_accountId       = "";
string   g_label           = "";
int      g_knownTickets[];                        // Known position tickets
int      g_knownTicketsSize = 0;
int      g_stateCount       = 0;                  // State export counter

//+------------------------------------------------------------------+
//| Expert initialization                                              |
//+------------------------------------------------------------------+
int OnInit()
{
   g_accountId = AccountCompany() + "_" + IntegerToString(AccountNumber());
   g_label = AccountLabel;
   if(g_label == "") g_label = AccountCompany() + "_T" + IntegerToString(AccountNumber());
   
   EventSetTimer(CheckInterval);
   
   // Init known positions (avoid false alerts on startup)
   SnapshotKnownPositions();
   
   // Write startup event
   WriteEvent("STARTUP", "", 0, "", 0, 0, 0, 0, 0, "", "", "");
   
   // Write initial state
   WriteAccountState();
   
   Print("AccountMonitor v2.00 started on ", g_label);
   Print("  Account: ", AccountNumber(), " Balance: ", AccountBalance());
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   WriteEvent("SHUTDOWN", "", 0, "", 0, 0, 0, 0, 0, "", "", "");
   Print("AccountMonitor v2.00 stopped. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Timer — Main Loop                                                  |
//+------------------------------------------------------------------+
void OnTimer()
{
   if(!IsConnected()) return;
   if(!IsExpertEnabled()) return;
   
   DetectTradeChanges();
   
   // 每 5 分鐘寫一次完整狀態
   g_stateCount++;
   if(EnableStateLog && g_stateCount >= (300 / CheckInterval))
   {
      WriteAccountState();
      g_stateCount = 0;
   }
}

//+------------------------------------------------------------------+
//| Detect New/Closed Trades                                           |
//+------------------------------------------------------------------+
void DetectTradeChanges()
{
   int currentTickets[];
   int currentSize = 0;
   
   // 收集當前所有持倉
   for(int i = 0; i < OrdersTotal(); i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderType() <= OP_SELL)
         {
            ArrayResize(currentTickets, currentSize + 1);
            currentTickets[currentSize] = OrderTicket();
            currentSize++;
         }
      }
   }
   
   // === 偵測新開倉 ===
   for(int i = 0; i < currentSize; i++)
   {
      bool isNew = true;
      for(int j = 0; j < g_knownTicketsSize; j++)
      {
         if(currentTickets[i] == g_knownTickets[j])
         {
            isNew = false;
            break;
         }
      }
      
      if(isNew)
      {
         // 找到新訂單！
         if(OrderSelect(currentTickets[i], SELECT_BY_TICKET))
         {
            string indicators = "";
            if(EnableIndicators)
               indicators = SnapshotIndicators(OrderSymbol());
            
            WriteEvent(
               "NEW_ORDER",
               OrderSymbol(),
               OrderTicket(),
               OrderTypeString(OrderType()),
               OrderLots(),
               OrderOpenPrice(),
               OrderStopLoss(),
               OrderTakeProfit(),
               OrderMagicNumber(),
               OrderComment(),
               indicators,
               ""
            );
            
            Print("🔔 NEW ORDER: ", OrderSymbol(), " ", OrderTypeString(OrderType()), " ", OrderLots(), " @ ", OrderOpenPrice());
         }
      }
   }
   
   // === 偵測平倉 ===
   for(int j = 0; j < g_knownTicketsSize; j++)
   {
      bool isClosed = true;
      for(int i = 0; i < currentSize; i++)
      {
         if(g_knownTickets[j] == currentTickets[i])
         {
            isClosed = false;
            break;
         }
      }
      
      if(isClosed)
      {
         // 持倉已平——從歷史搵返
         string symbol = "";
         string type = "";
         double lots = 0;
         double openPrice = 0;
         double closePrice = 0;
         double profit = 0;
         double swap = 0;
         double commission = 0;
         string comment = "";
         int magic = 0;
         datetime openTime = 0;
         datetime closeTime = 0;
         double pips = 0;
         
         if(OrderSelect(g_knownTickets[j], SELECT_BY_TICKET))
         {
            // 喺 history 入面搵到
            symbol = OrderSymbol();
            type = OrderTypeString(OrderType());
            lots = OrderLots();
            openPrice = OrderOpenPrice();
            closePrice = OrderClosePrice();
            profit = OrderProfit();
            swap = OrderSwap();
            commission = OrderCommission();
            comment = OrderComment();
            magic = OrderMagicNumber();
            openTime = OrderOpenTime();
            closeTime = OrderCloseTime();
            
            double point = MarketInfo(symbol, MODE_POINT);
            if(point > 0)
            {
               pips = (closePrice - openPrice) / point;
               if(type == "SELL") pips = -pips;
               int digits = (int)MarketInfo(symbol, MODE_DIGITS);
               if(digits == 3 || digits == 5) pips /= 10;
            }
         }
         
         string closeSummary = StringFormat("%.2f pips, P&L=$%.2f", pips, profit + swap + commission);
         
         WriteEvent(
            "CLOSE_ORDER",
            symbol,
            g_knownTickets[j],
            type,
            lots,
            openPrice,
            0, 0,
            magic,
            comment,
            "",
            closeSummary
         );
         
         Print("🔔 CLOSED: ", symbol, " ", type, " ", closeSummary);
      }
   }
   
   // 更新已知持倉列表
   ArrayResize(g_knownTickets, currentSize);
   for(int i = 0; i < currentSize; i++)
      g_knownTickets[i] = currentTickets[i];
   g_knownTicketsSize = currentSize;
}

//+------------------------------------------------------------------+
//| Snapshot Indicators for a Symbol                                   |
//+------------------------------------------------------------------+
string SnapshotIndicators(string symbol)
{
   string result = "";
   
   // === MA (Moving Averages) ===
   double ma20 = iMA(symbol, 0, 20, 0, MODE_EMA, PRICE_CLOSE, 0);
   double ma50 = iMA(symbol, 0, 50, 0, MODE_EMA, PRICE_CLOSE, 0);
   double ma200 = iMA(symbol, 0, 200, 0, MODE_EMA, PRICE_CLOSE, 0);
   double price = MarketInfo(symbol, MODE_BID);
   
   string maTrend = "NEUTRAL";
   if(price > ma20 && ma20 > ma50) maTrend = "BULLISH";
   else if(price < ma20 && ma20 < ma50) maTrend = "BEARISH";
   
   result += StringFormat("MA[E20=%.5f,E50=%.5f,E200=%.5f,Trend=%s]", ma20, ma50, ma200, maTrend);
   
   // === RSI ===
   double rsi = iRSI(symbol, 0, 14, PRICE_CLOSE, 0);
   string rsiZone = "NEUTRAL";
   if(rsi > 70) rsiZone = "OVERBOUGHT";
   else if(rsi < 30) rsiZone = "OVERSOLD";
   result += StringFormat(" RSI[%.1f,%s]", rsi, rsiZone);
   
   // === MACD ===
   double macdMain = iMACD(symbol, 0, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 0);
   double macdSignal = iMACD(symbol, 0, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 0);
   double macdHist = macdMain - macdSignal;
   string macdDir = macdHist > 0 ? "BULL" : "BEAR";
   result += StringFormat(" MACD[M=%.5f,S=%.5f,H=%.5f,%s]", macdMain, macdSignal, macdHist, macdDir);
   
   // === Bollinger Bands ===
   double bbUpper = iBands(symbol, 0, 20, 2, 0, PRICE_CLOSE, MODE_UPPER, 0);
   double bbLower = iBands(symbol, 0, 20, 2, 0, PRICE_CLOSE, MODE_LOWER, 0);
   double bbMid = iBands(symbol, 0, 20, 2, 0, PRICE_CLOSE, MODE_MAIN, 0);
   string bbPos = "MID";
   if(price > bbUpper) bbPos = "ABOVE_UPPER";
   else if(price < bbLower) bbPos = "BELOW_LOWER";
   result += StringFormat(" BB[U=%.5f,M=%.5f,L=%.5f,%s]", bbUpper, bbMid, bbLower, bbPos);
   
   // === ATR (volatility) ===
   double atr = iATR(symbol, 0, 14, 0);
   result += StringFormat(" ATR[%.5f]", atr);
   
   // === ADX (trend strength) ===
   double adx = iADX(symbol, 0, 14, PRICE_CLOSE, MODE_MAIN, 0);
   double diPlus = iADX(symbol, 0, 14, PRICE_CLOSE, MODE_PLUSDI, 0);
   double diMinus = iADX(symbol, 0, 14, PRICE_CLOSE, MODE_MINUSDI, 0);
   string trendStr = "NO_TREND";
   if(adx > 25) trendStr = diPlus > diMinus ? "UP_TREND" : "DOWN_TREND";
   result += StringFormat(" ADX[%.1f,DI+=%.1f,DI-=%.1f,%s]", adx, diPlus, diMinus, trendStr);
   
   // === Stochastic ===
   double stochK = iStochastic(symbol, 0, 14, 3, 3, MODE_SMA, 0, MODE_MAIN, 0);
   double stochD = iStochastic(symbol, 0, 14, 3, 3, MODE_SMA, 0, MODE_SIGNAL, 0);
   string stochZone = "NEUTRAL";
   if(stochK > 80) stochZone = "OVERBOUGHT";
   else if(stochK < 20) stochZone = "OVERSOLD";
   result += StringFormat(" STOCH[K=%.1f,D=%.1f,%s]", stochK, stochD, stochZone);
   
   return result;
}

//+------------------------------------------------------------------+
//| Snapshot Known Positions at Startup                                |
//+------------------------------------------------------------------+
void SnapshotKnownPositions()
{
   g_knownTicketsSize = 0;
   for(int i = 0; i < OrdersTotal(); i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderType() <= OP_SELL)
         {
            ArrayResize(g_knownTickets, g_knownTicketsSize + 1);
            g_knownTickets[g_knownTicketsSize] = OrderTicket();
            g_knownTicketsSize++;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Write Event to CSV                                                 |
//+------------------------------------------------------------------+
void WriteEvent(string eventType, string symbol, int ticket, string orderType,
                double lots, double price, double sl, double tp, int magic,
                string comment, string indicators, string extra)
{
   if(!EnableCSV) return;
   
   string filename = "monitor_events_" + IntegerToString(AccountNumber()) + ".csv";
   int handle = FileOpen(filename, FILE_CSV|FILE_WRITE|FILE_READ|FILE_ANSI, '\t');
   
   if(handle == INVALID_HANDLE)
   {
      Print("ERROR: Cannot open event file");
      return;
   }
   
   // 檢查是否需要寫 header
   if(FileSize(handle) == 0)
   {
      FileWrite(handle,
         "timestamp", "account", "event_type", "symbol", "ticket",
         "order_type", "lots", "price", "sl", "tp", "magic",
         "balance", "equity", "free_margin", "profit",
         "comment", "indicators", "extra"
      );
   }
   else
   {
      FileSeek(handle, 0, SEEK_END);
   }
   
   string ts = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);
   
   FileWrite(handle,
      ts,
      g_label,
      eventType,
      symbol,
      IntegerToString(ticket),
      orderType,
      DoubleToStr(lots, 2),
      DoubleToStr(price, (int)MarketInfo(symbol, MODE_DIGITS)),
      DoubleToStr(sl, (int)MarketInfo(symbol, MODE_DIGITS)),
      DoubleToStr(tp, (int)MarketInfo(symbol, MODE_DIGITS)),
      IntegerToString(magic),
      DoubleToStr(AccountBalance(), 2),
      DoubleToStr(AccountEquity(), 2),
      DoubleToStr(AccountFreeMargin(), 2),
      DoubleToStr(AccountProfit(), 2),
      comment,
      indicators,
      extra
   );
   
   FileClose(handle);
}

//+------------------------------------------------------------------+
//| Write Full Account State                                           |
//+------------------------------------------------------------------+
void WriteAccountState()
{
   string filename = "monitor_state_" + IntegerToString(AccountNumber()) + ".json";
   
   string json = "{";
   json += "\"timestamp\":\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\",";
   json += "\"account_id\":\"" + EscapeJson(g_accountId) + "\",";
   json += "\"label\":\"" + EscapeJson(g_label) + "\",";
   json += "\"login\":" + IntegerToString(AccountNumber()) + ",";
   json += "\"broker\":\"" + EscapeJson(AccountCompany()) + "\",";
   json += "\"balance\":" + DoubleToStr(AccountBalance(), 2) + ",";
   json += "\"equity\":" + DoubleToStr(AccountEquity(), 2) + ",";
   json += "\"margin\":" + DoubleToStr(AccountMargin(), 2) + ",";
   json += "\"free_margin\":" + DoubleToStr(AccountFreeMargin(), 2) + ",";
   json += "\"margin_level\":" + DoubleToStr(GetMarginLevel(), 2) + ",";
   json += "\"profit\":" + DoubleToStr(AccountProfit(), 2) + ",";
   json += "\"leverage\":" + IntegerToString(AccountLeverage()) + ",";
   
   // 持倉統計
   int openPos = 0;
   double totalLots = 0;
   for(int i = 0; i < OrdersTotal(); i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES) && OrderType() <= OP_SELL)
      {
         openPos++;
         totalLots += OrderLots();
      }
   }
   json += "\"open_positions\":" + IntegerToString(openPos) + ",";
   json += "\"total_lots\":" + DoubleToStr(totalLots, 2);
   json += "}";
   
   // 寫入（原子操作）
   string tmpFile = filename + ".tmp";
   int handle = FileOpen(tmpFile, FILE_WRITE|FILE_ANSI);
   if(handle != INVALID_HANDLE)
   {
      FileWriteString(handle, json);
      FileClose(handle);
      FileDelete(filename);
      FileMove(tmpFile, 0, filename, FILE_REWRITE);
   }
}

//+------------------------------------------------------------------+
//| Helpers                                                            |
//+------------------------------------------------------------------+
string OrderTypeString(int type)
{
   switch(type)
   {
      case OP_BUY:       return "BUY";
      case OP_SELL:      return "SELL";
      case OP_BUYLIMIT:  return "BUYLIMIT";
      case OP_SELLLIMIT: return "SELLLIMIT";
      case OP_BUYSTOP:   return "BUYSTOP";
      case OP_SELLSTOP:  return "SELLSTOP";
      default:           return "UNKNOWN";
   }
}

double GetMarginLevel()
{
   double margin = AccountMargin();
   if(margin <= 0) return 0;
   return (AccountEquity() / margin) * 100.0;
}

string EscapeJson(string s)
{
   string result = "";
   for(int i = 0; i < StringLen(s); i++)
   {
      ushort ch = StringGetCharacter(s, i);
      if(ch == '"')       result += "\\\"";
      else if(ch == '\\') result += "\\\\";
      else if(ch == '\n') result += "\\n";
      else if(ch == '\r') result += "\\r";
      else if(ch == '\t') result += "\\t";
      else                result += ShortToString(ch);
   }
   return result;
}
//+------------------------------------------------------------------+
