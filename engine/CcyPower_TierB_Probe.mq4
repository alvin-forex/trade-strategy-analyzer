//+------------------------------------------------------------------+
//|                                        CcyPower_TierB_Probe.mq4  |
//|  用途：在原版 CCY Power Indicator 的同一部 MT4 / 同一張圖上，      |
//|        同一個瞬間同時匯出「原作顯示值」＋「33 個 symbol 的 OHLC」   |
//|        → 用嚟釘死原作 'up 計數' 的精確定義（唯一可行方法）         |
//|                                                                  |
//|  安全聲明：純讀取。不寫 chart object、不下單、不改原作設定。        |
//|           只做 FileOpen(WRITE) 到 MQL4/Files。                    |
//|                                                                  |
//|  掛法：                                                            |
//|    1. 一張圖先掛原版 CCY Power Indicator（All Power 模式）         |
//|    2. 「同一張圖」再掛本 EA                                        |
//|    3. InpTF 必須等於原作指標的 Timeframe input                     |
//|  輸出（MQL4/Files/）：                                             |
//|    ccyprobe_panel.csv     ← 原作面板 9 個值 + bid/ask + server 時間 |
//|    ccyprobe_bars.csv      ← 33 symbol × N 根 bar 的 OHLC           |
//|    ccyprobe_objects.txt   ← 首次 capture 時傾印所有 chart object    |
//|    ccyprobe_candidates.txt← 首次 capture 時傾印面板解析候選         |
//+------------------------------------------------------------------+
#property copyright "ZCODE_w for Alvin"
#property version   "1.11"
#property strict

//=== 輸入 ==========================================================
input int    InpTF            = 60;      // 原作指標 Timeframe（分鐘）: 1440=D1 240=H4 60=H1 30=M30
input int    InpPeriod        = 10;      // 原作指標 Period（只寫入 CSV 做記錄）
input int    InpBars          = 14;      // 每個 symbol 匯出幾多根 bar
input int    InpPollSeconds   = 60;      // 每隔幾秒 capture 一次
input bool   InpEveryPoll     = true;    // true=每次 poll 都寫（用嚟驗 live 價）; false=只在新 bar 寫
input string InpPanelCsv      = "ccyprobe_panel.csv";
input string InpBarsCsv       = "ccyprobe_bars.csv";

//=== 9 個貨幣（照原作 .dat header 順序）=============================
string CCY[9] = {"EUR","GBP","AUD","NZD","CHF","JPY","XAU","CAD","USD"};

//=== 28 對（照原作 Pairs[] 原序，容許 broker 反向報價）==============
string Pairs[28][2] = {
 {"EUR","USD"},{"GBP","USD"},{"AUD","USD"},{"NZD","USD"},{"USD","JPY"},{"USD","CHF"},{"USD","CAD"},
 {"EUR","GBP"},{"EUR","JPY"},{"EUR","CHF"},{"EUR","AUD"},{"EUR","CAD"},{"EUR","NZD"},
 {"GBP","JPY"},{"GBP","CHF"},{"GBP","AUD"},{"GBP","CAD"},{"GBP","NZD"},
 {"AUD","JPY"},{"AUD","CHF"},{"AUD","CAD"},{"AUD","NZD"},
 {"NZD","JPY"},{"NZD","CHF"},{"NZD","CAD"},
 {"CAD","JPY"},{"CAD","CHF"},{"CHF","JPY"}};

//=== 黃金交叉（原作 GoldQ，XAU 作基礎貨幣）=========================
string GoldQ[7] = {"EUR","GBP","AUD","JPY","CHF","CAD","NZD"};

string   gSym[36];
bool     gOK[36];
bool     gRev[36];
bool     gRevFlag = false;
string   gPrefixes[64];
int      gPrefixCount = 0;
datetime gLastBar  = 0;
bool     gDumped   = false;
int      gCaptureN = 0;

//+------------------------------------------------------------------+
//| 找 symbol（容許反向），並記錄是否反向                              |
//+------------------------------------------------------------------+
string FindSym(string base, string quote)
{
   string want = base + quote;
   string rev  = quote + base;
   int total = SymbolsTotal(false);
   for(int i = 0; i < total; i++)
   {
      string s = SymbolName(i, false);
      string c = s;
      StringToUpper(c);
      StringReplace(c, ".R",   "");
      StringReplace(c, ".RAW", "");
      StringReplace(c, ".SC",  "");
      StringReplace(c, ".M",   "");
      StringReplace(c, "M",    "");
      StringReplace(c, ".",    "");
      if(c == want) { gRevFlag = false; return s; }
      if(c == rev ) { gRevFlag = true;  return s; }
   }
   gRevFlag = false;
   return "";
}

//+------------------------------------------------------------------+
int OnInit()
{
   for(int p = 0; p < 28; p++)
   {
      gSym[p] = FindSym(Pairs[p][0], Pairs[p][1]);
      gRev[p] = gRevFlag;
      gOK[p]  = (gSym[p] != "");
      if(gOK[p]) SymbolSelect(gSym[p], true);
   }
   gSym[28] = FindSym("XAU","USD"); gRev[28] = gRevFlag; gOK[28] = (gSym[28] != "");
   if(gOK[28]) SymbolSelect(gSym[28], true);
   for(int g = 0; g < 7; g++)
   {
      gSym[29+g] = FindSym("XAU", GoldQ[g]);
      gRev[29+g] = gRevFlag;
      gOK[29+g]  = (gSym[29+g] != "");
      if(gOK[29+g]) SymbolSelect(gSym[29+g], true);
   }

   int okN = 0, goldN = 0; string revList = "";
   for(int a = 0; a < 28; a++) if(gOK[a]) { okN++; if(gRev[a]) revList += gSym[a] + " "; }
   for(int b = 0; b < 7;  b++) if(gOK[29+b]) goldN++;

   Print("=== TierB Probe v1.11 initialized ===");
   Print("  TF=", InpTF, "min  Period=", InpPeriod, "  Bars=", InpBars,
         "  everyPoll=", InpEveryPoll);
   Print("  chart symbol=", Symbol(), "  digits=", Digits);
   Print("  majors ", okN, "/28   reversed: [", revList, "]");
   Print("  XAUUSD=", gSym[28], "   gold crosses ", goldN, "/7");
   for(int q = 0; q < 7; q++)
      Print("    gold[", q, "] ", GoldQ[q], " -> [", gSym[29+q], "]");

   WritePanelHeader();
   WriteBarsHeader();

   Capture();
   EventSetTimer(InpPollSeconds);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) { EventKillTimer(); }

void OnTimer()
{
   datetime cur = iTime(Symbol(), InpTF, 0);
   if(InpEveryPoll || cur != gLastBar)
      Capture();
}

void OnTick()
{
   if(InpEveryPoll) return;                 // OnTimer 已處理
   datetime cur = iTime(Symbol(), InpTF, 0);
   if(cur != gLastBar) Capture();
}

//+------------------------------------------------------------------+
//| 面板解析                                                          |
//| v1.11: 先讀 GUI bitmap table __table_edit_*；找不到才 fallback。   |
//+------------------------------------------------------------------+
double gPanel[9];
bool   gPanelOK[9];

string TrimLeftSpaces(string s)
{
   int i = 0, n = StringLen(s);
   while(i < n)
   {
      ushort c = StringGetCharacter(s, i);
      if(c == ' ' || c == '\t') i++;
      else break;
   }
   return StringSubstr(s, i);
}

// 抽出字串中第一個 0..12 的數字
double ExtractNumber(string s)
{
   int len = StringLen(s);
   for(int i = 0; i < len; i++)
   {
      ushort ch = StringGetCharacter(s, i);
      if(!(ch >= '0' && ch <= '9')) continue;
      string num = "";
      int j = i;
      while(j < len)
      {
         ushort c2 = StringGetCharacter(s, j);
         if((c2 >= '0' && c2 <= '9') || c2 == '.') { num += ShortToString(c2); j++; }
         else break;
      }
      if(StringLen(num) > 0)
      {
         double v = StrToDouble(num);
         if(v >= 0.0 && v <= 12.0) return v;
      }
      i = j;
   }
   return -1.0;
}

void DetectTablePrefixes()
{
   gPrefixCount=0;
   int total=ObjectsTotal();
   for(int i=0;i<total;i++)
   {
      string nm=ObjectName(i);
      int marker=StringFind(nm,"__table_edit_");
      if(marker<0) continue;
      string prefix=StringSubstr(nm,0,marker);
      bool seen=false;
      for(int j=0;j<gPrefixCount;j++) if(gPrefixes[j]==prefix){ seen=true; break; }
      if(!seen && gPrefixCount<ArraySize(gPrefixes)) gPrefixes[gPrefixCount++]=prefix;
   }
}

bool ReadTableValues(const string prefix, double &values[], bool &valid[])
{
   bool any=false;
   for(int row=2;row<=10;row++)
   {
      string nameObj=prefix+"__table_edit_1_"+IntegerToString(row)+"__1";
      string valueObj=prefix+"__table_edit_2_"+IntegerToString(row)+"__1";
      string name=ObjectGetString(0,nameObj,OBJPROP_TEXT);
      string text=ObjectGetString(0,valueObj,OBJPROP_TEXT);
      StringTrimLeft(name); StringTrimRight(name);
      StringTrimLeft(text); StringTrimRight(text);
      int idx=-1;
      for(int k=0;k<9;k++) if(name==CCY[k]){ idx=k; break; }
      if(idx<0 || StringLen(text)==0) continue;
      double value=StrToDouble(text);
      if(value<0.0 || value>12.0) continue;
      values[idx]=value;
      valid[idx]=true;
      any=true;
   }
   return(any);
}

void ReadLegacyLabels()
{
   int total=ObjectsTotal();
   for(int i=0;i<total;i++)
   {
      string nm=ObjectName(i);
      int typ=(int)ObjectType(nm);
      if(typ!=OBJ_LABEL && typ!=OBJ_TEXT) continue;
      string txt=ObjectDescription(nm);
      if(StringLen(txt)==0 || StringLen(txt)>40) continue;
      int hits=0,lastIdx=-1;
      for(int k=0;k<9;k++) if(StringFind(txt,CCY[k])>=0){ hits++; lastIdx=k; }
      if(hits!=1) continue;
      double value=ExtractNumber(txt);
      if(value<0.0) continue;
      if(!gPanelOK[lastIdx]){ gPanel[lastIdx]=value; gPanelOK[lastIdx]=true; }
   }
}

void ReadPanel()
{
   for(int i=0;i<9;i++){ gPanel[i]=-1; gPanelOK[i]=false; }
   DetectTablePrefixes();
   bool found=false;
   for(int p=0;p<gPrefixCount;p++)
   {
      double values[9]; bool valid[9];
      ArrayInitialize(values,-1.0);
      ArrayInitialize(valid,false);
      if(!ReadTableValues(gPrefixes[p],values,valid)) continue;
      for(int k=0;k<9;k++)
         if(valid[k] && !gPanelOK[k]){ gPanel[k]=values[k]; gPanelOK[k]=true; }
      for(int k=0;k<9;k++) if(gPanelOK[k]){ found=true; break; }
      if(found) return;
   }
   // v1.10 fallback only when the GUI table object family was not found.
   if(gPrefixCount==0) ReadLegacyLabels();
}

// Dump all chart objects so object-type/name/text mismatches are diagnosable.
void DumpAllObjects()
{
   int fh=FileOpen("ccyprobe_objects.txt",FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(fh==INVALID_HANDLE) return;
   FileWrite(fh,"server_time = ",TimeToString(TimeCurrent(),TIME_DATE|TIME_MINUTES|TIME_SECONDS));
   FileWrite(fh,"objects_total = ",ObjectsTotal());
   int total=ObjectsTotal();
   for(int i=0;i<total;i++)
   {
      string nm=ObjectName(i);
      int typ=(int)ObjectType(nm);
      string description=ObjectDescription(nm);
      string text=ObjectGetString(0,nm,OBJPROP_TEXT);
      FileWrite(fh,typ," | ",nm," | description=[",description,"] | text=[",text,"]");
   }
   FileClose(fh);
}

// 把面板解析的全部候選（含未採用者）傾印，方便我修正 parser
void DumpCandidates()
{
   int fh = FileOpen("ccyprobe_candidates.txt", FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(fh == INVALID_HANDLE) return;
   FileWrite(fh, "server_time = ", TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS));
   FileWrite(fh, "tf_min = ", InpTF, "   objects_total = ", ObjectsTotal());
   FileWrite(fh, "table_prefix_count = ", gPrefixCount);
   for(int p=0;p<gPrefixCount;p++) FileWrite(fh,"table_prefix[",p,"] = ",gPrefixes[p]);
   FileWrite(fh, "");
   FileWrite(fh, "--- 所有 LABEL/TEXT object 的文字（legacy fallback） ---");
   int total = ObjectsTotal();
   for(int i=0;i<total;i++)
   {
      string nm=ObjectName(i);
      int typ=(int)ObjectType(nm);
      if(typ!=OBJ_LABEL && typ!=OBJ_TEXT) continue;
      string txt=ObjectDescription(nm);
      int hits=0; string hitList="";
      for(int k=0;k<9;k++) if(StringFind(txt,CCY[k])>=0){ hits++; hitList+=CCY[k]+" "; }
      FileWrite(fh,typ," | ",nm," | len=",StringLen(txt)," | codes=",hits,"[",hitList,"] | text=[",txt,"] | num=",DoubleToString(ExtractNumber(txt),4));
   }
   FileWrite(fh,"");
   FileWrite(fh,"--- 採用結果 ---");
   for(int k2=0;k2<9;k2++) FileWrite(fh,CCY[k2]," = ",(gPanelOK[k2]?DoubleToString(gPanel[k2],4):"NOT_FOUND"));
   FileClose(fh);
   DumpAllObjects();
   Print("DumpCandidates + DumpAllObjects completed");
}


//+------------------------------------------------------------------+
void WritePanelHeader()
{
   int fh = FileOpen(InpPanelCsv, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) { Print("PanelHeader FileOpen 失敗 err=", GetLastError()); return; }
   FileWrite(fh, "server_time","tf_min","period","chart_symbol","bid","ask","spread_pt",
             "EUR","GBP","AUD","NZD","CHF","JPY","XAU","CAD","USD","found_mask");
   FileClose(fh);
}

void WriteBarsHeader()
{
   int fh = FileOpen(InpBarsCsv, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE) { Print("BarsHeader FileOpen 失敗 err=", GetLastError()); return; }
   FileWrite(fh, "server_time","tf_min","symbol","list_index","reversed","digits",
             "bar_time","open","high","low","close","tick_volume");
   FileClose(fh);
}

//+------------------------------------------------------------------+
void Capture()
{
   ReadPanel();
   if(!gDumped) { DumpCandidates(); gDumped = true; }

   datetime nowServer = TimeCurrent();
   string ts = TimeToString(nowServer, TIME_DATE|TIME_MINUTES|TIME_SECONDS);

   // ---- panel ----
   int fh = FileOpen(InpPanelCsv, FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh != INVALID_HANDLE)
   {
      FileSeek(fh, 0, SEEK_END);
      string mask = "";
      for(int i = 0; i < 9; i++) mask += (gPanelOK[i] ? "1" : "0");
      FileWrite(fh, ts, InpTF, InpPeriod, Symbol(),
                DoubleToString(Bid, Digits), DoubleToString(Ask, Digits),
                DoubleToString((Ask-Bid)/Point, 1),
                DoubleToString(gPanel[0], 4), DoubleToString(gPanel[1], 4),
                DoubleToString(gPanel[2], 4), DoubleToString(gPanel[3], 4),
                DoubleToString(gPanel[4], 4), DoubleToString(gPanel[5], 4),
                DoubleToString(gPanel[6], 4), DoubleToString(gPanel[7], 4),
                DoubleToString(gPanel[8], 4), mask);
      FileClose(fh);
   }

   // ---- bars ----
   fh = FileOpen(InpBarsCsv, FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh != INVALID_HANDLE)
   {
      FileSeek(fh, 0, SEEK_END);
      for(int k = 0; k < 36; k++)
      {
         if(!gOK[k]) continue;
         int dg = (int)MarketInfo(gSym[k], MODE_DIGITS);
         if(dg <= 0) dg = 5;
         for(int sh = InpBars - 1; sh >= 0; sh--)     // 舊 -> 新
         {
            datetime bt = iTime(gSym[k], InpTF, sh);
            if(bt == 0) continue;
            FileWrite(fh, ts, InpTF, gSym[k], k, (gRev[k] ? 1 : 0), dg,
                      TimeToString(bt, TIME_DATE|TIME_MINUTES),
                      DoubleToString(iOpen(gSym[k],  InpTF, sh), dg),
                      DoubleToString(iHigh(gSym[k],  InpTF, sh), dg),
                      DoubleToString(iLow(gSym[k],   InpTF, sh), dg),
                      DoubleToString(iClose(gSym[k], InpTF, sh), dg),
                      (double)iVolume(gSym[k], InpTF, sh));
         }
      }
      FileClose(fh);
   }

   gLastBar = iTime(Symbol(), InpTF, 0);
   gCaptureN++;

   int found = 0;
   for(int q = 0; q < 9; q++) if(gPanelOK[q]) found++;
   Print("TierB #", gCaptureN, " ", ts, "  panel ", found, "/9  tf=", InpTF);
}

//+------------------------------------------------------------------+
//| 手動工具：在圖上按 F7 改參數後，把 InpDumpOnly 設 true 再重掛，      |
//| 即可只傾印 object 而不寫 CSV（診斷用）                             |
//+------------------------------------------------------------------+
void DumpObjectsOnly()
{
   DumpCandidates();
}
//+------------------------------------------------------------------+
