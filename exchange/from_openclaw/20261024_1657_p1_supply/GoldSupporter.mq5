//+------------------------------------------------------------------+
//| GoldSupporter.mq5  v1.00                                       |
//| 用途：由 MT5 導出 XAUUSD 真報價數據畀 WSL 分析用                  |
//| 輸出（MQL5/Files/）：                                             |
//|   gold_tick.csv   - 每分鐘 tick（server_time,bid,ask）            |
//|   gold_H1.csv     - H1 歷史 500 枝 OHLC（含 forming 旗標）        |
//|   gold_H4.csv     - H4 歷史 300 枝                                |
//|   gold_D1.csv     - D1 歷史 300 枝                                |
//|   forex_data.csv  - 整點快照（同 MT4 ForexDataExporter 格式）      |
//| 掛法：放入任何一張圖都得（EA 自動搵金價 symbol），開 Algo Trading |
//+------------------------------------------------------------------+
#property copyright "Alvin"
#property version   "1.00"

string g_sym;
datetime g_lastH1 = 0;

ENUM_TIMEFRAMES g_tfs[3] = {PERIOD_D1, PERIOD_H4, PERIOD_H1};
int g_hRsi[3], g_hBands[3], g_hEma20[3], g_hEma50[3], g_hEma200[3], g_hAtr[3], g_hMacd[3];

int Dg() { return (int)SymbolInfoInteger(g_sym, SYMBOL_DIGITS); }

string FindGoldSymbol()
{
   int total = SymbolsTotal(false);
   string candidates[6] = {"XAUUSD","XAUUSD.r","XAUUSDm","XAUUSD.i","XAUUSD.x","GOLD"};
   for(int c = 0; c < 6; c++)
      for(int i = 0; i < total; i++)
         if(SymbolName(i, false) == candidates[c])
            return candidates[c];
   for(int i = 0; i < total; i++) {
      string u = SymbolName(i, false);
      StringToUpper(u);
      if(StringFind(u, "XAUUSD") >= 0) return SymbolName(i, false);
   }
   for(int i = 0; i < total; i++) {
      string u = SymbolName(i, false);
      StringToUpper(u);
      if(StringFind(u, "XAU") >= 0 || StringFind(u, "GOLD") >= 0) return SymbolName(i, false);
   }
   return _Symbol;
}

bool g_selfSaved = false;
void SaveSelfTemplate()
{
   if(g_selfSaved) return;
   if(ChartSaveTemplate(0, "GS_self")) { g_selfSaved = true; Print("GS_self.tpl saved (native)"); }
}
void WriteGsAlive()
{
   int h = FileOpen("gs_alive", FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   FileWriteString(h, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
   FileClose(h);
}

int OnInit()
{
   g_sym = FindGoldSymbol();
   SymbolSelect(g_sym, true);
   for(int i = 0; i < 3; i++) {
      g_hRsi[i]    = iRSI(g_sym, g_tfs[i], 14, PRICE_CLOSE);
      g_hBands[i]  = iBands(g_sym, g_tfs[i], 20, 0, 2.0, PRICE_CLOSE);
      g_hEma20[i]  = iMA(g_sym, g_tfs[i], 20, 0, MODE_EMA, PRICE_CLOSE);
      g_hEma50[i]  = iMA(g_sym, g_tfs[i], 50, 0, MODE_EMA, PRICE_CLOSE);
      g_hEma200[i] = iMA(g_sym, g_tfs[i], 200, 0, MODE_EMA, PRICE_CLOSE);
      g_hAtr[i]    = iATR(g_sym, g_tfs[i], 14);
      g_hMacd[i]   = iMACD(g_sym, g_tfs[i], 12, 26, 9, PRICE_CLOSE);
   }
   g_lastH1 = iTime(g_sym, PERIOD_H1, 0);
   EventSetTimer(60);
   WriteAll();
   SaveSelfTemplate();
   WriteGsAlive();
   Print("GoldSupporter v1.06 started, symbol=", g_sym);
   return INIT_SUCCEEDED;
}

int g_mountTries = 0;

bool PlanExecutorAlive()
{
   if(!FileIsExist("plan_executor.alive")) return false;
   int h = FileOpen("plan_executor.alive", FILE_READ|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE) return false;
   string s = FileReadString(h);
   FileClose(h);
   datetime t = StringToTime(s);
   return (t > 0 && (TimeCurrent() - t) < 180);
}

// v1.03: PE 生還時，閂晒啲冇 EA 嘅 XAUUSD 圖（清理 v1.02 開剩嘅空圖）
void CleanupOrphanCharts()
{
   if(!PlanExecutorAlive()) return;
   long c = ChartFirst();
   while(c >= 0) {
      long next = ChartNext(c);
      if(ChartSymbol(c) == g_sym && ChartGetString(c, CHART_EXPERT_NAME) == "")
         ChartClose(c);
      c = next;
   }
}

// v1.02: 用 alive 檔判斷 PlanExecutor 生死（v1.01 數圖數錯咗）
void MountPlanExecutor()
{
   if(PlanExecutorAlive()) return;
   if(g_mountTries >= 5) return;
   g_mountTries++;
   long cid = ChartOpen(g_sym, PERIOD_H1);
   if(cid <= 0) { Print("PlanExecutor ChartOpen failed: ", GetLastError()); return; }
   for(int attempt = 1; attempt <= 3; attempt++) {
      Sleep(800);
      if(ChartApplyTemplate(cid, "PlanExecutor.tpl")) {
         Print("PlanExecutor mounted on chart ", cid, " (try ", g_mountTries, ".", attempt, ")");
         return;
      }
   }
   Print("PlanExecutor template apply failed: ", GetLastError());
}

void OnDeinit(const int reason) { EventKillTimer(); }

void OnTimer()
{
   WriteGsAlive();
   ScanSPSymbols();
   WriteAll();
// [v2.01] 復活邏輯停用：固定兩圖架构，杜絕圖表增生
   CleanupOrphanCharts();    // v1.06: 清走冇 EA 嘅 XAUUSD 空圖
}

// 掃描 broker 有冇 S&P500 類 symbol（一次性寫檔）
void ScanSPSymbols()
{
   static bool done=false;
   if(done) return; done=true;
   int total=SymbolsTotal(false);
   int h=FileOpen("sp_symbols.txt",FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE) return;
   for(int i=0;i<total;i++){
      string s=SymbolName(i,false);
      string u=s; StringToUpper(u);
      if(StringFind(u,"US500")>=0||StringFind(u,"SPX")>=0||StringFind(u,"USA500")>=0
         ||StringFind(u,"SP500")>=0||StringFind(u,"NAS")>=0||StringFind(u,"US30")>=0
         ||StringFind(u,"US TECH")>=0||StringFind(u,"DJ")>=0){
         FileWriteString(h,s+"\r\n");
      }
   }
   FileClose(h);
}

void WriteAll()
{
   MqlTick t;
   if(!SymbolInfoTick(g_sym, t)) { Print("no tick for ", g_sym); return; }
   WriteTick(t);
   WriteHistory(PERIOD_H1, "gold_H1.csv", 50000);
   WriteHistory(PERIOD_H4, "gold_H4.csv", 1000);
   WriteHistory(PERIOD_D1, "gold_D1.csv", 300);
   WriteHistory(PERIOD_M30, "gold_M30.csv", 500000);
   WriteHistory(PERIOD_M15, "gold_M15.csv", 500000);
   WriteHistory(PERIOD_M5,  "gold_M5.csv",  500000);
   // v2.03: SP500 原產地回測用
   SymbolSelect("SP500.r", true);
   WriteHistory2("SP500.r", PERIOD_M5,  "sp_M5.csv",  500000);
   WriteHistory2("SP500.r", PERIOD_H1,  "sp_H1.csv",  500000);
   datetime cur = iTime(g_sym, PERIOD_H1, 0);
   if(cur != g_lastH1) { g_lastH1 = cur; WriteSnapshotRow(); }
}

void WriteTick(const MqlTick &t)
{
   int h = FileOpen("gold_tick.csv", FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(h == INVALID_HANDLE) return;
   FileSeek(h, 0, SEEK_END);
   if(FileTell(h) == 0)
      FileWrite(h, "server_time", "bid", "ask");
   else if(FileTell(h) > 200000) {   // ~200KB 即旋轉，唔好無限大
      FileClose(h);
      h = FileOpen("gold_tick.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
      if(h == INVALID_HANDLE) return;
      FileWrite(h, "server_time", "bid", "ask");
   }
   FileWrite(h, TimeToString(t.time, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
             DoubleToString(t.bid, Dg()), DoubleToString(t.ask, Dg()));
   FileClose(h);
}

bool WriteHistory(ENUM_TIMEFRAMES tf, string fname, int bars)
{
   return WriteHistory2(g_sym, tf, fname, bars);
}
bool WriteHistory2(string sym, ENUM_TIMEFRAMES tf, string fname, int bars)
{
   MqlRates r[];
   int copied = CopyRates(sym, tf, 0, bars, r);
   if(copied <= 0) { Print("CopyRates ", fname, " failed ", GetLastError()); return false; }
   ArraySetAsSeries(r, true);
   int h = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(h == INVALID_HANDLE) { Print("FileOpen ", fname, " failed"); return false; }
   FileWrite(h, "time", "open", "high", "low", "close", "tick_volume", "spread", "forming");
   for(int i = 0; i < copied; i++)
      FileWrite(h, TimeToString(r[i].time, TIME_DATE|TIME_MINUTES),
                DoubleToString(r[i].open, Dg()), DoubleToString(r[i].high, Dg()),
                DoubleToString(r[i].low, Dg()), DoubleToString(r[i].close, Dg()),
                r[i].tick_volume, r[i].spread, (i == 0) ? 1 : 0);
   FileClose(h);
   return true;
}
int Dg2(string sym){ return (int)SymbolInfoInteger(sym, SYMBOL_DIGITS); }

void WriteSnapshotRow()
{
   int h = FileOpen("forex_data.csv", FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(h == INVALID_HANDLE) { Print("FileOpen forex_data.csv failed ", GetLastError()); return; }
   FileSeek(h, 0, SEEK_END);
   if(FileTell(h) == 0) {
      FileWrite(h, "timestamp","symbol","timeframe","open","high","low","close","volume",
                "ccy_1_name","ccy_1_power","ccy_2_name","ccy_2_power","ccy_3_name","ccy_3_power",
                "ccy_4_name","ccy_4_power","ccy_5_name","ccy_5_power","ccy_6_name","ccy_6_power",
                "ccy_7_name","ccy_7_power","ccy_8_name","ccy_8_power","ccy_9_name","ccy_9_power",
                "bb_upper","bb_middle","bb_lower","ema20","ema50","ema200",
                "atr14","rsi14","macd_line","macd_signal","macd_hist","swing_high","swing_low");
   }
   for(int i = 0; i < 3; i++) WriteTFRow(h, i);
   FileClose(h);
}

void WriteTFRow(int h, int i)
{
   double o = iOpen(g_sym, g_tfs[i], 1), hi = iHigh(g_sym, g_tfs[i], 1),
          lo = iLow(g_sym, g_tfs[i], 1),  c  = iClose(g_sym, g_tfs[i], 1);
   long v = (long)iVolume(g_sym, g_tfs[i], 1);
   double buf[1];
   double rsi = 0, bbU = 0, bbM = 0, bbL = 0, e20 = 0, e50 = 0, e200 = 0, atr = 0, mc = 0, ms = 0;
   if(CopyBuffer(g_hRsi[i],    0, 1, 1, buf) == 1) rsi  = buf[0];
   if(CopyBuffer(g_hBands[i],  1, 1, 1, buf) == 1) bbU  = buf[0];
   if(CopyBuffer(g_hBands[i],  0, 1, 1, buf) == 1) bbM  = buf[0];
   if(CopyBuffer(g_hBands[i],  2, 1, 1, buf) == 1) bbL  = buf[0];
   if(CopyBuffer(g_hEma20[i],  0, 1, 1, buf) == 1) e20  = buf[0];
   if(CopyBuffer(g_hEma50[i],  0, 1, 1, buf) == 1) e50  = buf[0];
   if(CopyBuffer(g_hEma200[i], 0, 1, 1, buf) == 1) e200 = buf[0];
   if(CopyBuffer(g_hAtr[i],    0, 1, 1, buf) == 1) atr  = buf[0];
   if(CopyBuffer(g_hMacd[i],   0, 1, 1, buf) == 1) mc   = buf[0];
   if(CopyBuffer(g_hMacd[i],   1, 1, 1, buf) == 1) ms   = buf[0];
   int hiIdx = iHighest(g_sym, g_tfs[i], MODE_HIGH, 500, 1);
   int loIdx = iLowest(g_sym, g_tfs[i], MODE_LOW, 500, 1);
   double swH = (hiIdx >= 0) ? iHigh(g_sym, g_tfs[i], hiIdx) : 0;
   double swL = (loIdx >= 0) ? iLow(g_sym, g_tfs[i], loIdx) : 0;
   datetime bt = iTime(g_sym, g_tfs[i], 1);
   string tfName = (g_tfs[i] == PERIOD_D1) ? "D1" : (g_tfs[i] == PERIOD_H4) ? "H4" : "H1";
   FileWrite(h, TimeToString(bt, TIME_DATE|TIME_MINUTES), g_sym, tfName,
             DoubleToString(o, Dg()), DoubleToString(hi, Dg()),
             DoubleToString(lo, Dg()), DoubleToString(c, Dg()), (long)v,
             "","","","","","","","","","","","","","","","","","",
             DoubleToString(bbU, Dg()), DoubleToString(bbM, Dg()), DoubleToString(bbL, Dg()),
             DoubleToString(e20, Dg()), DoubleToString(e50, Dg()), DoubleToString(e200, Dg()),
             DoubleToString(atr, Dg()), DoubleToString(rsi, 2),
             DoubleToString(mc, 2), DoubleToString(ms, 2), DoubleToString(mc - ms, 2),
             DoubleToString(swH, Dg()), DoubleToString(swL, Dg()));
}
