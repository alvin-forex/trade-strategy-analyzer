//+------------------------------------------------------------------+
//| MarketGlanceExporter.mq5 — Market Glance 7 項 MT5 本地源 exporter |
//| 任務 A 步驟 2（ZCODE 出品 2026-10-23）                            |
//|                                                                  |
//| 老闆規則：                                                        |
//|  - 每 5 分鐘寫 MQL5/Files/market_glance.csv                       |
//|  - 7 項 SymbolSelect 容錯；找唔到寫 status=missing 行，唔准靜默跳過 |
//|  - 禁止外部檔案／外部 API，全部 SymbolInfoDouble / iClose          |
//|                                                                  |
//| 部署（需要老闆 Windows 側人手一次）：                              |
//|   1. 放入 MT5 (725B) MQL5/Experts/                                |
//|   2. MetaEditor 編譯（F7，0 errors）                              |
//|   3. 掛上任意一張 chart（建議閒置 chart，例如 XAUUSD H1）           |
//|      ※ 純寫檔 EA，唔使剔 Allow Algo Trading 都寫到（保險起見剔咗都得）|
//|   4. 首啟動即寫一次快照，之後每 5 分鐘覆寫                          |
//+------------------------------------------------------------------+
#property copyright "ZCODE for TSA — task A step 2"
#property version   "1.00"
#property strict

input string InpSymbols     = "SP500.r;DJ30.r;NAS100.r;DXYZ;vix.r;UKOUSD;HK50.r";
input string InpNames       = "S&P 500;Dow;Nasdaq;DXY;VIX;Brent;HK50";
input int    InpIntervalSec = 300;              // 5 分鐘
input string InpFile        = "market_glance.csv";

datetime g_lastWrite = 0;

//--- symbol 容錯解析：精確名→strip 尾點／忽略 .r/.raw/.m 後綴比對
string ResolveSym(const string want)
{
   if(SymbolSelect(want, true))
      return want;

   string wu = want; StringToUpper(wu);
   // normalize want：strip 尾點＋後綴
   wu = NormalizeSym(wu);

   int total = SymbolsTotal(false);
   for(int i = 0; i < total; i++)
   {
      string s  = SymbolName(i, false);
      string su = s;   StringToUpper(su);
      su = NormalizeSym(su);
      if(su == wu && SymbolSelect(s, true))
         return s;
   }
   return "";
}

string NormalizeSym(string s)
{
   // strip 尾點（例如 "XAUUSD." → "XAUUSD"）
   while(StringLen(s) > 0 &&
         StringGetCharacter(s, StringLen(s)-1) == '.')
      s = StringSubstr(s, 0, StringLen(s)-1);
   // strip 常見 broker 後綴（".R" / ".RAW" / ".M"，例如 "SP500.r" → "SP500"）
   string suffixes[3] = {".RAW", ".R", ".M"};
   for(int k = 0; k < 3; k++)
   {
      int pos = StringFind(s, suffixes[k]);
      if(pos > 0)
         s = StringSubstr(s, 0, pos);
   }
   return s;
}

//--- 寫快照（覆寫式：永遠係最新一份，方便 report 讀 + mtime 判新鮮度）
void WriteSnapshot()
{
   g_lastWrite = TimeCurrent();
   int fh = FileOpen(InpFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE)
   {
      Print("MarketGlanceExporter: FileOpen fail err=", GetLastError());
      return;
   }
   FileWrite(fh, "timestamp","symbol","name","bid","ask","last",
             "prev_day_close","change_pct","spread","status");

   string syms[], names[];
   int n = StringSplit(InpSymbols, ';', syms);
   int m = StringSplit(InpNames,   ';', names);
   int missing = 0;

   for(int i = 0; i < n; i++)
   {
      string nm  = (i < m && StringLen(names[i]) > 0) ? names[i] : syms[i];
      string sym = ResolveSym(syms[i]);
      string ts  = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);

      if(sym == "")
      {
         // 老闆規則：找唔到寫 missing 行，唔准靜默跳過
         missing++;
         FileWrite(fh, ts, syms[i], nm, "", "", "", "", "", "", "missing");
         continue;
      }

      MqlTick tick;
      if(!SymbolInfoTick(sym, tick))
      {
         missing++;
         FileWrite(fh, ts, sym, nm, "", "", "", "", "", "", "missing");
         continue;
      }

      double px   = (tick.last != 0.0) ? tick.last : tick.bid;
      double prev = iClose(sym, PERIOD_D1, 1);   // 昨日 D1 收市
      double chg  = (prev != 0.0 && px != 0.0) ? (px/prev - 1.0) * 100.0 : 0.0;
      long   spr  = SymbolInfoInteger(sym, SYMBOL_SPREAD);

      FileWrite(fh, ts, sym, nm,
                DoubleToString(tick.bid, 5),
                DoubleToString(tick.ask, 5),
                DoubleToString(tick.last, 5),
                DoubleToString(prev, 5),
                DoubleToString(chg, 2),
                IntegerToString(spr),
                "ok");
   }

   FileClose(fh);
   PrintFormat("MarketGlanceExporter: wrote %d items (missing=%d) at %s",
               n, missing, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
}

int OnInit()
{
   EventSetTimer(InpIntervalSec);
   WriteSnapshot();               // 啟動即寫一次
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTimer()
{
   WriteSnapshot();
}

void OnTick()
{
   // 有 tick 時亦檢查（Timer 冇被觸發嘅情況下兜底；快過 interval 就 skip）
   if(TimeCurrent() - g_lastWrite >= InpIntervalSec)
      WriteSnapshot();
}
