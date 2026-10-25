//+------------------------------------------------------------------+
//| MarketGlanceExporter.mq5 — Market Glance 7 項 MT5 本地源 exporter |
//| 任務 A 步驟 2（ZCODE 出品 2026-10-23）                            |
//| v1.01 - 2026-10-24 - ZCODE 新增#1 patch：                        |
//|   P1-1 InpSymbols 支援「|」多候選鏈（逐個試，首中即用）：          |
//|        對應老闆 2026-10-24 枚舉（DXYZ/CL-OIL/UKOUSD/USOUSD/       |
//|        NAS100.r/vix.r 確認存在）；Brent 候選 UKOUSD→USOUSD→       |
//|        CL-OIL；SP500 候選 SP500.r→US500                           |
//|   P1-2 候選全滅先寫 missing（規則不變：唔准靜默跳過）              |
//|   ※ 7 項最終映射仍以 mg_diagnose.csv 審核＋老闆確認為準（gate 不變）|
//| v1.02 - 2026-10-25 - ZCODE 任務A v102 patch（枚舉表實證修正）：    |
//|   A-1 DXYZ→USDX.r：DXYZ 實為美股 The Destiny Tech 100（ISIN        |
//|        US25063F1075，枚舉表 10-23 MCP 實查），非美元指數；broker    |
//|        美元指數正確 symbol = USDX.r（id 2575，bid 101.598 實證）    |
//|   A-2 vix.r→VIX.r：小寫形式唔存在（SymbolSelect 大小楷敏感），      |
//|        正確 symbol = VIX.r（id 2576，bid 19.509 實證）              |
//|   A-3 兩項均收窄為單候選（唔留 DXYZ/vix.r 做 fallback——錯來源      |
//|        唔好做後備，missing 就寫 missing，老闆規則不變）              |
//|   ※ InpNames 唔變：DXY/VIX 係業務名，正確；錯嘅係 symbol 映射       |
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
#property version   "1.02"
#property strict

input string InpSymbols     = "SP500.r|US500;DJ30.r;NAS100.r;USDX.r;VIX.r;UKOUSD|USOUSD|CL-OIL;HK50.r";
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

//--- P1-1: 多候選鏈解析："A|B|C" 逐個試，首中即用；全滅回 ""
string ResolveFirst(const string candidates)
{
   string parts[];
   int n = StringSplit(candidates, '|', parts);
   if(n <= 0)
      return "";
   for(int i = 0; i < n; i++)
   {
      string one = parts[i];
      // 清空格
      StringTrimLeft(one);
      StringTrimRight(one);
      if(StringLen(one) == 0)
         continue;
      string hit = ResolveSym(one);
      if(hit != "")
         return hit;
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
      string sym = ResolveFirst(syms[i]);   // P1-1: 多候選鏈
      string ts  = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);

      if(sym == "")
      {
         // 老闆規則：找唔到寫 missing 行，唔准靜默跳過（P1-2 候選全滅先 missing）
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
