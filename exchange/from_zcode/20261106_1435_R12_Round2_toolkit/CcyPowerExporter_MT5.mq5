//+------------------------------------------------------------------+
//| CcyPowerExporter_MT5.mq5 — R12 Round 2 #3 工具（ZCODE_w 2026-11-06）|
//| 用途：讀本 terminal 上 CurrencyPower_v3 指標 buffer 0-8（9 幣 power），|
//|       收黑 bar（已完成 bar）寫 CSV，供 ccy_comparator.py 對齊 diff。   |
//| CSV 欄：time,pair,idx0..idx8（time=黑 bar 開盤時間，與對比器約定一致） |
//| 部署：任一 chart（建議 EURUSD H1）掛載；input 對齊實際指標設置值。     |
//| 配套：CCY Power v3.11（proposed+FixAB，9 input 含 InpEqualWeight）    |
//+------------------------------------------------------------------+
#property copyright "ZCODE_w"
#property version   "1.00"
#property strict

input string InpSymbol       = "";           // 採集符號（空=圖表符號）
input ENUM_TIMEFRAMES InpTF  = PERIOD_CURRENT; // 採集時間框
input string InpIndicator    = "CurrencyPower_v3"; // 指標名（iCustom 用）
// —— 指標 input（照 v3.11 proposed 位置序；必須同掛載的指標設置一致——
//    一致性測試嘅關鍵：兩邊 indicator input 唔同＝比較冇意義）——
input int    RSI_Period      = 14;
input int    ATR_Period      = 14;
input int    Slope_Lookback  = 10;
input int    Lookback_Bars   = 300;
input bool   Alert_On        = true;
input ENUM_TIMEFRAMES PairTF = PERIOD_H1;
input int    TickStyle       = 0;
input bool   Show_Panel      = true;
input bool   InpEqualWeight  = false;        // v3.11 等權模式（9th input）
input string InpCsvName      = "ccy_export_mt5.csv"; // 輸出檔（MQL5/Files）

int    g_h = INVALID_HANDLE;
string g_sym;
datetime g_lastBar = 0;

int OnInit()
{
   g_sym = (InpSymbol=="" ? _Symbol : InpSymbol);
   ENUM_TIMEFRAMES tf = (InpTF==PERIOD_CURRENT ? (ENUM_TIMEFRAMES)_Period : InpTF);
   // iCustom 位置參數序 = indicator input 位置序（9 個，照 v3.11 proposed）
   g_h = iCustom(g_sym, tf, InpIndicator,
                 RSI_Period, ATR_Period, Slope_Lookback, Lookback_Bars,
                 Alert_On, PairTF, TickStyle, Show_Panel, InpEqualWeight);
   if(g_h == INVALID_HANDLE)
   {
      Print("Exporter: iCustom handle 失敗 err=", GetLastError(), " — 指標名/參數檢查");
      return(INIT_FAILED);
   }
   // CSV header（新檔）
   int fh = FileOpen(InpCsvName, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh != INVALID_HANDLE)
   {
      FileWrite(fh, "time", "pair", "idx0","idx1","idx2","idx3","idx4","idx5","idx6","idx7","idx8");
      FileClose(fh);
   }
   Print("Exporter MT5 啟動：sym=", g_sym, " tf=", EnumToString(tf), " csv=", InpCsvName);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) { if(g_h != INVALID_HANDLE) IndicatorRelease(g_h); }

void OnTick()
{
   datetime cur = iTime(g_sym, (InpTF==PERIOD_CURRENT ? (ENUM_TIMEFRAMES)_Period : InpTF), 0);
   if(cur == 0 || cur == g_lastBar) return;   // 無新 bar
   g_lastBar = cur;

   ENUM_TIMEFRAMES tf = (InpTF==PERIOD_CURRENT ? (ENUM_TIMEFRAMES)_Period : InpTF);
   int fh = FileOpen(InpCsvName, FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) { Print("Exporter: FileOpen 失敗 err=", GetLastError()); return; }
   FileSeek(fh, 0, SEEK_END);
   double v[1];
   string vals[9];
   bool ok = true;
   for(int b = 0; b < 9; b++)            // buffer 0-8 = 9 幣 power
   {
      if(CopyBuffer(g_h, b, 1, 1, v) < 1) { ok = false; break; }  // shift 1 = 已完成黑 bar
      vals[b] = DoubleToString(v[0], 4);
   }
   if(ok)
      FileWrite(fh, TimeToString(cur, TIME_DATE|TIME_MINUTES|TIME_SECONDS), g_sym,
                vals[0],vals[1],vals[2],vals[3],vals[4],vals[5],vals[6],vals[7],vals[8]);
   FileClose(fh);
   if(!ok) Print("Exporter: CopyBuffer 未 ready（指標初算中，下 bar 重試）");
}
//+------------------------------------------------------------------+
