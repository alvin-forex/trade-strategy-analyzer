//+------------------------------------------------------------------+
//| CcyPowerExporter_MT4.mq4 — R12 Round 2 #3 工具（ZCODE_w 2026-11-06）|
//| 用途：MT4 側讀 CurrencyPower 指標 buffer 0-8 收黑 bar 寫 CSV（同 MT5 版格式）|
//| ✅ 已對齊 MT4 v3.07-MQ4 實源碼（1820 補供正本）：input 位置序＝          |
//|    RSI_Period,ATR_Period,Slope_Lookback,Lookback_Bars,Alert_On,       |
//|    TickStyle,Show_Panel,PairTF（8 個，MT4 版無等權 input）——          |
//|    ⚠️ 與 MT5 v3.10/v3.11 序唔同，兩側 exporter 唔可以互抄參數序。     |
//|    Alert_On 移植後指標 bump v3.08-MQ4，input 序不變。                 |
//| CSV 欄：time,pair,idx0..idx8（與 ccy_comparator.py 約定一致）         |
//+------------------------------------------------------------------+
#property copyright "ZCODE_w"
#property version   "1.00"
#property strict

input string InpSymbol       = "";           // 採集符號（空=圖表符號）
input int    InpTFMinutes    = 0;            // 採集時間框（分鐘；0=圖表時間框；60=H1 等）
input string InpIndicator    = "CurrencyPower_v3_MQ4"; // 指標名（MQL4/Indicators 內編譯後 ex4 名，照 terminal 實名調）
// —— 指標 input（位置序照 MT4 v3.07-MQ4 正本實序，8 個，無 InpEqualWeight）——
input int    RSI_Period      = 14;
input int    ATR_Period      = 14;
input int    Slope_Lookback  = 10;
input int    Lookback_Bars   = 300;
input bool   Alert_On        = true;
input int    TickStyle       = 0;
input bool   Show_Panel      = true;
input int    PairTF_Minutes  = 60;           // MT4 版 PairTF input 為 int（PERIOD_H1=60）
input string InpCsvName      = "ccy_export_mt4.csv"; // 輸出檔（MQL4/Files）

datetime g_lastBar = 0;
string   g_sym;

int OnInit()
{
   g_sym = (InpSymbol=="" ? Symbol() : InpSymbol);
   int fh = FileOpen(InpCsvName, FILE_WRITE|FILE_CSV, ',');
   if(fh != INVALID_HANDLE)
   {
      FileWrite(fh, "time", "pair", "idx0","idx1","idx2","idx3","idx4","idx5","idx6","idx7","idx8");
      FileClose(fh);
   }
   Print("Exporter MT4 啟動（模板版）：sym=", g_sym, " csv=", InpCsvName);
   return(INIT_SUCCEEDED);
}

int TF() { return(InpTFMinutes==0 ? Period() : InpTFMinutes); }

void OnTick()
{
   datetime cur = iTime(g_sym, TF(), 0);
   if(cur == 0 || cur == g_lastBar) return;
   g_lastBar = cur;

   int fh = FileOpen(InpCsvName, FILE_READ|FILE_WRITE|FILE_CSV, ',');
   if(fh == INVALID_HANDLE) { Print("Exporter: FileOpen 失敗 err=", GetLastError()); return; }
   FileSeek(fh, 0, SEEK_END);
   // MT4 iCustom：位置參數直接跟在指標名後，尾二參數=buffer, shift(1=已完成黑 bar)
   double v0 = iCustom(g_sym, TF(), InpIndicator, RSI_Period, ATR_Period, Slope_Lookback,
                       Lookback_Bars, Alert_On, TickStyle, Show_Panel, PairTF_Minutes, 0, 1);
   double v1 = iCustom(g_sym, TF(), InpIndicator, RSI_Period, ATR_Period, Slope_Lookback,
                       Lookback_Bars, Alert_On, TickStyle, Show_Panel, PairTF_Minutes, 1, 1);
   double v2 = iCustom(g_sym, TF(), InpIndicator, RSI_Period, ATR_Period, Slope_Lookback,
                       Lookback_Bars, Alert_On, TickStyle, Show_Panel, PairTF_Minutes, 2, 1);
   double v3 = iCustom(g_sym, TF(), InpIndicator, RSI_Period, ATR_Period, Slope_Lookback,
                       Lookback_Bars, Alert_On, TickStyle, Show_Panel, PairTF_Minutes, 3, 1);
   double v4 = iCustom(g_sym, TF(), InpIndicator, RSI_Period, ATR_Period, Slope_Lookback,
                       Lookback_Bars, Alert_On, TickStyle, Show_Panel, PairTF_Minutes, 4, 1);
   double v5 = iCustom(g_sym, TF(), InpIndicator, RSI_Period, ATR_Period, Slope_Lookback,
                       Lookback_Bars, Alert_On, TickStyle, Show_Panel, PairTF_Minutes, 5, 1);
   double v6 = iCustom(g_sym, TF(), InpIndicator, RSI_Period, ATR_Period, Slope_Lookback,
                       Lookback_Bars, Alert_On, TickStyle, Show_Panel, PairTF_Minutes, 6, 1);
   double v7 = iCustom(g_sym, TF(), InpIndicator, RSI_Period, ATR_Period, Slope_Lookback,
                       Lookback_Bars, Alert_On, TickStyle, Show_Panel, PairTF_Minutes, 7, 1);
   double v8 = iCustom(g_sym, TF(), InpIndicator, RSI_Period, ATR_Period, Slope_Lookback,
                       Lookback_Bars, Alert_On, TickStyle, Show_Panel, PairTF_Minutes, 8, 1);
   FileWrite(fh, TimeToString(cur, TIME_DATE|TIME_MINUTES|TIME_SECONDS), g_sym,
             DoubleToString(v0,4), DoubleToString(v1,4), DoubleToString(v2,4),
             DoubleToString(v3,4), DoubleToString(v4,4), DoubleToString(v5,4),
             DoubleToString(v6,4), DoubleToString(v7,4), DoubleToString(v8,4));
   FileClose(fh);
}
//+------------------------------------------------------------------+
