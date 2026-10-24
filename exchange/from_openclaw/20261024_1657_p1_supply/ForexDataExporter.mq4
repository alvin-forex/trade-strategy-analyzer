//+------------------------------------------------------------------+
//|                                            ForexDataExporter.mq4 |
//|                                    OpenClaw Forex Report V2 EA    |
//+------------------------------------------------------------------+
//| v1.02 - 2026-05-27 23:35 HKT - All English, UTF-8 encoding        |
//| Scans 28 pairs + XAUUSD across D1/H4/H1 timeframes                |
//| Exports STC, CCY POWER, River, BB, EMA, ATR, RSI, MACD to CSV    |
//| Output: MQL4/Files/forex_data.csv                                 |
//+------------------------------------------------------------------+
#property copyright "OpenClaw AI"
#property link      "https://openclaw.ai"
#property version   "1.02"
#property strict
#property description "v1.02 - 2026-05-27 23:35 HKT - All English UTF-8"

// === Input Parameters ===
input int    ExportIntervalMinutes = 60;      // Export interval (minutes)
input string CSV_Filename = "forex_data.csv"; // CSV filename
input bool   DebugMode = false;               // Print debug info

// === Symbol List ===
string Symbols[] = {
    "AUDUSD", "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD",
    "CADCHF", "CADJPY",
    "CHFJPY",
    "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD",
    "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD",
    "USDCAD", "USDCHF", "USDJPY",
    "XAUUSD", "US500"
};

// === Timeframes ===
int Timeframes[] = { PERIOD_D1, PERIOD_H4, PERIOD_H1 };
string TF_Names[] = { "D1", "H4", "H1" };

// === Global Variables ===
datetime lastExportTime = 0;
int totalSymbols = 30;

//+------------------------------------------------------------------+
int OnInit()
{
    Print("=== ForexDataExporter v1.02 Start ===");
    Print("Symbols: ", totalSymbols);
    Print("Timeframes: D1, H4, H1");
    Print("Interval: ", ExportIntervalMinutes, " min");
    Print("CSV: ", CSV_Filename);
    Print("=====================================");
    
    ExportAllData();
    
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("=== ForexDataExporter Stopped ===");
}

//+------------------------------------------------------------------+
void OnTick()
{
    datetime currentTime = TimeCurrent();
    if(currentTime - lastExportTime >= ExportIntervalMinutes * 60)
    {
        ExportAllData();
        lastExportTime = currentTime;
    }
}

//+------------------------------------------------------------------+
void ExportAllData()
{
    string filePath = CSV_Filename;
    int handle = FileOpen(filePath, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
    
    if(handle == INVALID_HANDLE)
    {
        Print("ERROR: Cannot open file: ", filePath, " Error: ", GetLastError());
        return;
    }
    
    // CSV Header
    FileWrite(handle,
        "timestamp", "symbol", "timeframe",
        "open", "high", "low", "close", "volume",
        "stc_main", "stc_signal",
        "ccy_buy_signal", "ccy_sell_signal",
        "ccy_base_power", "ccy_quote_power", "ccy_market_avg",
        "river_upper", "river_middle", "river_lower",
        "river_upper_blue", "river_lower_blue",
        "river_arrow_up", "river_arrow_down",
        "bb_upper", "bb_middle", "bb_lower",
        "ema20", "ema50", "ema200",
        "atr14",
        "rsi14",
        "macd_line", "macd_signal", "macd_hist"
    );
    
    datetime exportTime = TimeCurrent();
    string timeStr = TimeToString(exportTime, TIME_DATE|TIME_MINUTES);
    int successCount = 0;
    int failCount = 0;
    
    for(int s = 0; s < totalSymbols; s++)
    {
        string sym = Symbols[s];
        
        for(int t = 0; t < 3; t++)
        {
            int tf = Timeframes[t];
            string tfName = TF_Names[t];
            
            int bars = iBars(sym, tf);
            if(bars < 200)
            {
                if(DebugMode)
                    Print("WARN: ", sym, " ", tfName, " bars=", bars, " (skipped)");
                failCount++;
                continue;
            }
            
            // OHLCV
            double openVal  = iOpen(sym, tf, 0);
            double highVal  = iHigh(sym, tf, 0);
            double lowVal   = iLow(sym, tf, 0);
            double closeVal = iClose(sym, tf, 0);
            long   volVal   = iVolume(sym, tf, 0);
            
            // STC (Stochastic 5,3,3)
            double stcMain   = iStochastic(sym, tf, 5, 3, 3, MODE_SMA, 0, MODE_MAIN, 0);
            double stcSignal = iStochastic(sym, tf, 5, 3, 3, MODE_SMA, 0, MODE_SIGNAL, 0);
            
            // CCY Power Indicator v1.00
            double ccyBuySignal  = iCustom(sym, tf, "CCY Power Indicator v1.00", 0, 0);
            double ccySellSignal = iCustom(sym, tf, "CCY Power Indicator v1.00", 1, 0);
            double ccyBasePower  = iCustom(sym, tf, "CCY Power Indicator v1.00", 2, 0);
            double ccyQuotePower = iCustom(sym, tf, "CCY Power Indicator v1.00", 3, 0);
            double ccyMarketAvg  = iCustom(sym, tf, "CCY Power Indicator v1.00", 4, 0);
            
            // River v1.00
            double riverUpper     = iCustom(sym, tf, "River v1.00", 0, 0);
            double riverMiddle    = iCustom(sym, tf, "River v1.00", 1, 0);
            double riverLower     = iCustom(sym, tf, "River v1.00", 2, 0);
            double riverUpperBlue = iCustom(sym, tf, "River v1.00", 3, 0);
            double riverLowerBlue = iCustom(sym, tf, "River v1.00", 4, 0);
            double riverArrowUp   = iCustom(sym, tf, "River v1.00", 5, 0);
            double riverArrowDn   = iCustom(sym, tf, "River v1.00", 6, 0);
            
            // Bollinger Bands (20, 2)
            double bbUpper  = iBands(sym, tf, 20, 2, 0, PRICE_CLOSE, MODE_UPPER, 0);
            double bbMiddle = iBands(sym, tf, 20, 2, 0, PRICE_CLOSE, MODE_MAIN, 0);
            double bbLower  = iBands(sym, tf, 20, 2, 0, PRICE_CLOSE, MODE_LOWER, 0);
            
            // EMA 20/50/200
            double ema20  = iMA(sym, tf, 20, 0, MODE_EMA, PRICE_CLOSE, 0);
            double ema50  = iMA(sym, tf, 50, 0, MODE_EMA, PRICE_CLOSE, 0);
            double ema200 = iMA(sym, tf, 200, 0, MODE_EMA, PRICE_CLOSE, 0);
            
            // ATR (14)
            double atr14 = iATR(sym, tf, 14, 0);
            
            // RSI (14)
            double rsi14 = iRSI(sym, tf, 14, PRICE_CLOSE, 0);
            
            // MACD (12, 26, 9)
            double macdLine   = iMACD(sym, tf, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 0);
            double macdSignal = iMACD(sym, tf, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 0);
            double macdHist   = macdLine - macdSignal;
            
            // Write row
            FileWrite(handle,
                timeStr, sym, tfName,
                DoubleToStr(openVal, GetDigits(sym)),
                DoubleToStr(highVal, GetDigits(sym)),
                DoubleToStr(lowVal, GetDigits(sym)),
                DoubleToStr(closeVal, GetDigits(sym)),
                IntegerToString(volVal),
                DoubleToStr(stcMain, 2),
                DoubleToStr(stcSignal, 2),
                DoubleToStr(ccyBuySignal, 4),
                DoubleToStr(ccySellSignal, 4),
                DoubleToStr(ccyBasePower, 4),
                DoubleToStr(ccyQuotePower, 4),
                DoubleToStr(ccyMarketAvg, 4),
                DoubleToStr(riverUpper, GetDigits(sym)),
                DoubleToStr(riverMiddle, GetDigits(sym)),
                DoubleToStr(riverLower, GetDigits(sym)),
                DoubleToStr(riverUpperBlue, GetDigits(sym)),
                DoubleToStr(riverLowerBlue, GetDigits(sym)),
                DoubleToStr(riverArrowUp, GetDigits(sym)),
                DoubleToStr(riverArrowDn, GetDigits(sym)),
                DoubleToStr(bbUpper, GetDigits(sym)),
                DoubleToStr(bbMiddle, GetDigits(sym)),
                DoubleToStr(bbLower, GetDigits(sym)),
                DoubleToStr(ema20, GetDigits(sym)),
                DoubleToStr(ema50, GetDigits(sym)),
                DoubleToStr(ema200, GetDigits(sym)),
                DoubleToStr(atr14, GetDigits(sym)),
                DoubleToStr(rsi14, 2),
                DoubleToStr(macdLine, GetDigits(sym)),
                DoubleToStr(macdSignal, GetDigits(sym)),
                DoubleToStr(macdHist, GetDigits(sym))
            );
            
            successCount++;
            
            if(DebugMode)
                Print("OK: ", sym, " ", tfName);
        }
    }
    
    FileClose(handle);
    
    Print("=== Export Complete ===");
    Print("Time: ", timeStr);
    Print("Success: ", successCount, " rows");
    Print("Failed: ", failCount, " rows");
    Print("File: ", filePath);
}

//+------------------------------------------------------------------+
int GetDigits(string symbol)
{
    if(symbol == "XAUUSD") return 2;
    if(StringFind(symbol, "JPY") >= 0) return 3;
    return 5;
}
//+------------------------------------------------------------------+
