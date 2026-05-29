//+------------------------------------------------------------------+
//|                                              AccountMonitor.mq4  |
//|                              MT4 Multi-Account Monitor System    |
//|                              PRD v1.1 — Phase 1 MVP              |
//+------------------------------------------------------------------+
#property copyright "Alvin Forex System"
#property link      ""
#property version   "1.00"
#property strict
#property description "MT4 Account Monitor - HTTP POST to Python service"

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input string   AccountLabel      = "";          // 自定義帳戶名稱（留空用預設）
input int      ExportInterval    = 30;          // 導出頻率（秒）
input string   ApiUrl            = "http://localhost:8788"; // Python API 地址
input bool     EnableHTTP        = true;        // 啟用 HTTP POST（主通道）
input bool     EnableCSV         = true;        // 啟用 CSV 導出（fallback）
input string   CsvPrefix         = "monitor_";  // CSV 檔案前綴
input int      HistoryDays       = 30;          // 首次同步歷史天數
input bool     IncludeHistory    = true;        // 導出歷史交易

//+------------------------------------------------------------------+
//| Global Variables                                                  |
//+------------------------------------------------------------------+
datetime g_lastExport = 0;
datetime g_lastHistoryExport = 0;
bool     g_firstRun = true;
string   g_accountId = "";
int      g_lastHistoryCount = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   // 生成唯一帳戶 ID
   g_accountId = AccountCompany() + "_" + IntegerToString(AccountNumber());
   
   // 設置定時器
   EventSetTimer(ExportInterval);
   
   Print("AccountMonitor v1.00 started");
   Print("  Account: ", AccountCompany(), " #", AccountNumber());
   Print("  Balance: ", AccountBalance(), " Equity: ", AccountEquity());
   Print("  API: ", ApiUrl);
   Print("  Interval: ", ExportInterval, "s");
   
   // 首次運行標記
   g_firstRun = true;
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                    |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   Print("AccountMonitor stopped. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Timer function — 主邏輯入口                                        |
//+------------------------------------------------------------------+
void OnTimer()
{
   // 檢查連線
   if(!IsConnected())
   {
      Print("WARNING: Not connected to server");
      return;
   }
   
   // 檢查是否允許交易（EA 確保在活躍狀態）
   if(!IsExpertEnabled())
   {
      return;
   }
   
   // 導出帳戶狀態 + 持倉
   ExportAccountState();
   
   // 導出歷史交易（頻率較低）
   if(IncludeHistory)
   {
      datetime now = TimeCurrent();
      if(g_lastHistoryExport == 0 || (now - g_lastHistoryExport) >= 60)
      {
         ExportHistory();
         g_lastHistoryExport = now;
      }
   }
   
   g_firstRun = false;
}

//+------------------------------------------------------------------+
//| Export Account State + Positions                                   |
//+------------------------------------------------------------------+
void ExportAccountState()
{
   // 建構 JSON
   string json = BuildStateJson();
   
   // HTTP POST（主通道）
   if(EnableHTTP)
   {
      if(!HttpPost("/api/account/state", json))
      {
         Print("HTTP POST failed, falling back to CSV");
         // HTTP 失敗時寫 CSV
         if(EnableCSV) WriteStateCsv(json);
      }
   }
   else if(EnableCSV)
   {
      WriteStateCsv(json);
   }
}

//+------------------------------------------------------------------+
//| Build State JSON                                                   |
//+------------------------------------------------------------------+
string BuildStateJson()
{
   string label = AccountLabel;
   if(label == "") label = AccountCompany() + "_" + IntegerToString(AccountNumber());
   
   string json = "{";
   
   // 帳戶基本資料
   json += "\"timestamp\":\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\",";
   json += "\"account_id\":\"" + EscapeJson(g_accountId) + "\",";
   json += "\"label\":\"" + EscapeJson(label) + "\",";
   json += "\"login\":" + IntegerToString(AccountNumber()) + ",";
   json += "\"broker\":\"" + EscapeJson(AccountCompany()) + "\",";
   json += "\"server\":\"" + EscapeJson(AccountServer()) + "\",";
   json += "\"name\":\"" + EscapeJson(AccountName()) + "\",";
   json += "\"currency\":\"" + AccountCurrency() + "\",";
   json += "\"leverage\":" + IntegerToString(AccountLeverage()) + ",";
   
   // 帳戶財務
   json += "\"balance\":" + DoubleToStr(AccountBalance(), 2) + ",";
   json += "\"equity\":" + DoubleToStr(AccountEquity(), 2) + ",";
   json += "\"margin\":" + DoubleToStr(AccountMargin(), 2) + ",";
   json += "\"free_margin\":" + DoubleToStr(AccountFreeMargin(), 2) + ",";
   json += "\"margin_level\":" + DoubleToStr(GetMarginLevel(), 2) + ",";
   json += "\"profit\":" + DoubleToStr(AccountProfit(), 2) + ",";
   
   // 持倉統計
   int openPositions = 0;
   int pendingOrders = 0;
   for(int i = 0; i < OrdersTotal(); i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderType() <= OP_SELL)
            openPositions++;
         else
            pendingOrders++;
      }
   }
   json += "\"open_positions\":" + IntegerToString(openPositions) + ",";
   json += "\"pending_orders\":" + IntegerToString(pendingOrders) + ",";
   
   // 持倉詳情
   json += "\"positions\":[";
   bool first = true;
   for(int i = 0; i < OrdersTotal(); i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderType() <= OP_SELL)
         {
            if(!first) json += ",";
            first = false;
            json += BuildPositionJson();
         }
      }
   }
   json += "],";
   
   // 掛單詳情
   json += "\"pending\":[";
   first = true;
   for(int i = 0; i < OrdersTotal(); i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderType() > OP_SELL)
         {
            if(!first) json += ",";
            first = false;
            json += BuildPendingOrderJson();
         }
      }
   }
   json += "],";
   
   // 首次運行標記
   json += "\"first_run\":" + (g_firstRun ? "true" : "false");
   
   json += "}";
   
   return json;
}

//+------------------------------------------------------------------+
//| Build Position JSON                                                |
//+------------------------------------------------------------------+
string BuildPositionJson()
{
   string json = "{";
   json += "\"ticket\":" + IntegerToString(OrderTicket()) + ",";
   json += "\"symbol\":\"" + EscapeJson(OrderSymbol()) + "\",";
   json += "\"type\":\"" + OrderTypeString(OrderType()) + "\",";
   json += "\"lots\":" + DoubleToStr(OrderLots(), 2) + ",";
   json += "\"open_price\":" + DoubleToStr(OrderOpenPrice(), (int)MarketInfo(OrderSymbol(), MODE_DIGITS)) + ",";
   json += "\"current_price\":" + DoubleToStr(MarketInfo(OrderSymbol(), MODE_BID), (int)MarketInfo(OrderSymbol(), MODE_DIGITS)) + ",";
   json += "\"sl\":" + DoubleToStr(OrderStopLoss(), (int)MarketInfo(OrderSymbol(), MODE_DIGITS)) + ",";
   json += "\"tp\":" + DoubleToStr(OrderTakeProfit(), (int)MarketInfo(OrderSymbol(), MODE_DIGITS)) + ",";
   json += "\"profit\":" + DoubleToStr(OrderProfit(), 2) + ",";
   json += "\"swap\":" + DoubleToStr(OrderSwap(), 2) + ",";
   json += "\"commission\":" + DoubleToStr(OrderCommission(), 2) + ",";
   json += "\"open_time\":\"" + TimeToString(OrderOpenTime(), TIME_DATE|TIME_SECONDS) + "\",";
   json += "\"magic\":" + IntegerToString(OrderMagicNumber()) + ",";
   json += "\"comment\":\"" + EscapeJson(OrderComment()) + "\",";
   
   // 計算 pips
   double pipValue = 0;
   double digits = MarketInfo(OrderSymbol(), MODE_DIGITS);
   double point = MarketInfo(OrderSymbol(), MODE_POINT);
   if(OrderType() == OP_BUY)
      pipValue = (MarketInfo(OrderSymbol(), MODE_BID) - OrderOpenPrice()) / point;
   else
      pipValue = (OrderOpenPrice() - MarketInfo(OrderSymbol(), MODE_ASK)) / point;
   if(digits == 3 || digits == 5) pipValue /= 10;
   json += "\"pips\":" + DoubleToStr(pipValue, 1);
   
   json += "}";
   return json;
}

//+------------------------------------------------------------------+
//| Build Pending Order JSON                                           |
//+------------------------------------------------------------------+
string BuildPendingOrderJson()
{
   string json = "{";
   json += "\"ticket\":" + IntegerToString(OrderTicket()) + ",";
   json += "\"symbol\":\"" + EscapeJson(OrderSymbol()) + "\",";
   json += "\"type\":\"" + OrderTypeString(OrderType()) + "\",";
   json += "\"lots\":" + DoubleToStr(OrderLots(), 2) + ",";
   json += "\"price\":" + DoubleToStr(OrderOpenPrice(), (int)MarketInfo(OrderSymbol(), MODE_DIGITS)) + ",";
   json += "\"sl\":" + DoubleToStr(OrderStopLoss(), (int)MarketInfo(OrderSymbol(), MODE_DIGITS)) + ",";
   json += "\"tp\":" + DoubleToStr(OrderTakeProfit(), (int)MarketInfo(OrderSymbol(), MODE_DIGITS)) + ",";
   json += "\"open_time\":\"" + TimeToString(OrderOpenTime(), TIME_DATE|TIME_SECONDS) + "\",";
   json += "\"magic\":" + IntegerToString(OrderMagicNumber()) + ",";
   json += "\"comment\":\"" + EscapeJson(OrderComment()) + "\"";
   json += "}";
   return json;
}

//+------------------------------------------------------------------+
//| Export Trade History                                                |
//+------------------------------------------------------------------+
void ExportHistory()
{
   string json = BuildHistoryJson();
   
   if(EnableHTTP)
   {
      if(!HttpPost("/api/account/history", json))
      {
         if(EnableCSV) WriteHistoryCsv(json);
      }
   }
   else if(EnableCSV)
   {
      WriteHistoryCsv(json);
   }
}

//+------------------------------------------------------------------+
//| Build History JSON                                                 |
//+------------------------------------------------------------------+
string BuildHistoryJson()
{
   string json = "{";
   json += "\"account_id\":\"" + EscapeJson(g_accountId) + "\",";
   json += "\"timestamp\":\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\",";
   
   // 判斷導出範圍
   datetime fromTime;
   if(g_firstRun)
   {
      // 首次運行：導出 HistoryDays 天
      fromTime = TimeCurrent() - HistoryDays * 86400;
      json += "\"full_sync\":true,";
      json += "\"sync_days\":" + IntegerToString(HistoryDays) + ",";
   }
   else
   {
      // 增量：只導出今日
      fromTime = StringToTime(TimeToString(TimeCurrent(), TIME_DATE));
      json += "\"full_sync\":false,";
   }
   
   json += "\"trades\":[";
   
   bool first = true;
   int total = OrdersHistoryTotal();
   for(int i = 0; i < total; i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
      {
         // 只導出已平倉訂單
         if(OrderType() <= OP_SELL && OrderCloseTime() >= fromTime)
         {
            if(!first) json += ",";
            first = false;
            
            json += "{";
            json += "\"ticket\":" + IntegerToString(OrderTicket()) + ",";
            json += "\"symbol\":\"" + EscapeJson(OrderSymbol()) + "\",";
            json += "\"type\":\"" + OrderTypeString(OrderType()) + "\",";
            json += "\"lots\":" + DoubleToStr(OrderLots(), 2) + ",";
            json += "\"open_price\":" + DoubleToStr(OrderOpenPrice(), (int)MarketInfo(OrderSymbol(), MODE_DIGITS)) + ",";
            json += "\"close_price\":" + DoubleToStr(OrderClosePrice(), (int)MarketInfo(OrderSymbol(), MODE_DIGITS)) + ",";
            json += "\"open_time\":\"" + TimeToString(OrderOpenTime(), TIME_DATE|TIME_SECONDS) + "\",";
            json += "\"close_time\":\"" + TimeToString(OrderCloseTime(), TIME_DATE|TIME_SECONDS) + "\",";
            json += "\"profit\":" + DoubleToStr(OrderProfit(), 2) + ",";
            json += "\"swap\":" + DoubleToStr(OrderSwap(), 2) + ",";
            json += "\"commission\":" + DoubleToStr(OrderCommission(), 2) + ",";
            json += "\"magic\":" + IntegerToString(OrderMagicNumber()) + ",";
            json += "\"comment\":\"" + EscapeJson(OrderComment()) + "\"";
            json += "}";
         }
      }
   }
   
   json += "]}";
   return json;
}

//+------------------------------------------------------------------+
//| HTTP POST to Python API                                            |
//+------------------------------------------------------------------+
bool HttpPost(string endpoint, string json)
{
   string url = ApiUrl + endpoint;
   string headers = "Content-Type: application/json\r\n";
   char   post[];
   char   result[];
   string resultHeaders;
   int    timeout = 5000; // 5 秒 timeout
   
   // StringToCharArray 會自動加上 null terminator
   StringToCharArray(json, post, 0, WHOLE_ARRAY, CP_UTF8);
   // 移除最後的 null terminator
   ArrayResize(post, ArraySize(post) - 1);
   
   int res = WebRequest("POST", url, headers, timeout, post, result, resultHeaders);
   
   if(res == -1)
   {
      int err = GetLastError();
      if(err == 4060)
         Print("ERROR: WebRequest not allowed. Add '", ApiUrl, "' to Tools > Options > Expert Advisors > Allow WebRequest");
      else
         Print("ERROR: WebRequest failed. Code: ", err);
      return false;
   }
   
   if(res != 200)
   {
      Print("WARNING: HTTP ", res, " from ", endpoint);
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| CSV Fallback — State                                               |
//+------------------------------------------------------------------+
void WriteStateCsv(string json)
{
   string filename = CsvPrefix + "state_" + IntegerToString(AccountNumber()) + ".csv";
   
   // 寫入臨時檔
   string tmpFile = filename + ".tmp";
   int handle = FileOpen(tmpFile, FILE_CSV|FILE_WRITE|FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
   {
      Print("ERROR: Cannot open CSV file: ", tmpFile);
      return;
   }
   
   // 寫入 JSON 作為單一欄位（簡化處理）
   FileWrite(handle, "json_data");
   FileWrite(handle, json);
   FileClose(handle);
   
   // 刪除舊檔，重命名臨時檔
   FileDelete(filename);
   FileMove(tmpFile, 0, filename, FILE_REWRITE);
}

//+------------------------------------------------------------------+
//| CSV Fallback — History                                             |
//+------------------------------------------------------------------+
void WriteHistoryCsv(string json)
{
   string filename = CsvPrefix + "history_" + IntegerToString(AccountNumber()) + ".csv";
   
   string tmpFile = filename + ".tmp";
   int handle = FileOpen(tmpFile, FILE_CSV|FILE_WRITE|FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
   {
      Print("ERROR: Cannot open CSV file: ", tmpFile);
      return;
   }
   
   FileWrite(handle, "json_data");
   FileWrite(handle, json);
   FileClose(handle);
   
   FileDelete(filename);
   FileMove(tmpFile, 0, filename, FILE_REWRITE);
}

//+------------------------------------------------------------------+
//| Helper: Order Type to String                                       |
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

//+------------------------------------------------------------------+
//| Helper: Calculate Margin Level                                    |
//+------------------------------------------------------------------+
double GetMarginLevel()
{
   double margin = AccountMargin();
   if(margin <= 0) return 0;
   return (AccountEquity() / margin) * 100.0;
}

//+------------------------------------------------------------------+
//| Helper: Escape JSON string                                         |
//+------------------------------------------------------------------+
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
