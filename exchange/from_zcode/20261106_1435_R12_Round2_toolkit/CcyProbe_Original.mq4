//+------------------------------------------------------------------+
//| CcyProbe_Original.mq4 — R12 Round 2 #4 Phase 1 工具（ZCODE_w 2026-11-06）|
//| 用途：原版 CCY Power Indicator v1.00（ex4 無源碼）輸出格式探測——       |
//|   (a) 列 chart objects（panel label 顯示嘅數值）                      |
//|   (b) probe iCustom buffer 0-7（邊條裝住 power 數值、非空 bar 段）     |
//| 輸出：probe_report.txt（MQL4/Files）——OpenClaw 報返格式結論後定 Phase 2|
//| 掛法：掛喺原版 indicator 已 attach 嘅同一 chart（同 chart 同 feed）。   |
//+------------------------------------------------------------------+
#property copyright "ZCODE_w"
#property version   "1.00"
#property strict

input string InpIndicator   = "CCY Power Indicator v1.00"; // 原版指標名（iCustom 用）
input int    InpProbeBars   = 20;    // 每條 buffer probe 幾多根 bar
input string InpReportName  = "probe_report.txt";

int OnInit()
{
   int fh = FileOpen(InpReportName, FILE_WRITE|FILE_TXT);
   if(fh == INVALID_HANDLE) { Print("Probe: FileOpen 失敗 err=", GetLastError()); return(INIT_FAILED); }

   FileWrite(fh, "==== CCY 原版 Probe 報告 ====");
   FileWrite(fh, "chart: ", Symbol(), "  period: ", Period());
   FileWrite(fh, "probe 指標: ", InpIndicator);
   FileWrite(fh, "");

   // (a) chart objects 列表（label/description/text）
   FileWrite(fh, "---- (a) Chart objects ----");
   int n = ObjectsTotal();
   for(int i = 0; i < n; i++)
   {
      string nm = ObjectName(i);
      string type = ObjectType(nm) == OBJ_LABEL ? "LABEL" :
                    ObjectType(nm) == OBJ_TEXT  ? "TEXT"  :
                    ObjectType(nm) == OBJ_ARROW ? "ARROW" : StringConcatenate("TYPE", ObjectType(nm));
      string txt  = ObjectDescription(nm);
      FileWrite(fh, StringConcatenate("[", type, "] ", nm, " = ", txt));
   }
   FileWrite(fh, "");

   // (b) iCustom buffer 0-7 probe（最近 InpProbeBars 根 bar，記非 EMPTY_VALUE 段）
   FileWrite(fh, "---- (b) iCustom buffer probe（shift 1..InpProbeBars）----");
   for(int b = 0; b < 8; b++)
   {
      FileWrite(fh, StringConcatenate("buffer ", b, ":"));
      int nonempty = 0;
      double last = 0.0;
      for(int sh = 1; sh <= InpProbeBars; sh++)
      {
         double v = iCustom(Symbol(), Period(), InpIndicator, b, sh);
         // MT4 EMPTY_VALUE = 2147483647 或 0（視指標 EMPTY 設定）——兩者都當空
         if(v != EMPTY_VALUE && v != 0.0)
         {
            nonempty++;
            last = v;
            if(sh <= 5) FileWrite(fh, StringConcatenate("  shift=", sh, "  ", DoubleToString(v, 4)));
         }
      }
      FileWrite(fh, StringConcatenate("  非空計數: ", nonempty, "/", InpProbeBars,
               "  最新值: ", DoubleToString(last, 4)));
   }
   FileWrite(fh, "");
   FileWrite(fh, "（buffer 判讀：非空計數高＋數值範圍 0-100 者＝power 候選；");
   FileWrite(fh, "  原 v3 我哋版 buffer 0-8=9 幣 power——原版結構未必同，以 probe 為準）");
   FileClose(fh);
   Print("Probe 完成 → MQL4/Files/", InpReportName);
   return(INIT_SUCCEEDED);
}

void OnTick() { }   // 單次探測，OnInit 完成
//+------------------------------------------------------------------+
