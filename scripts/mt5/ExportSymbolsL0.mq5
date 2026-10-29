//+------------------------------------------------------------------+
//| ExportSymbolsL0.mq5 — COPYTRADE v1.3 L0 symbols 導出（催辦①鑰匙）|
//|                                                                  |
//| 用途：MT5 terminal 跑一次 → MQL5/Files/l0_symbols.json           |
//|       餵 COPYTRADE run_sim（symbols 表）——解鎖 M1/M4/M5/cent/   |
//|       Realistic/Stress 全線（§6.7 鐵律 2：tick_value 唯一權威）  |
//|                                                                  |
//| 對應 schema.py symbols 表欄位（逐欄對齊，唔使再轉換）：          |
//|   symbol / pip_size / tick_size / tick_value / contract_size /   |
//|   quote_currency / margin_initial / exported_at / source         |
//| 另附 fx_at_export（8 主要貨幣 vs USD bid）——pipcalc 按日 fx 修正 |
//| 用（非 USD 報價 symbol 唔使再 BLOCKED MissingFx）。              |
//|                                                                  |
//| 掛法：MT5 → Scripts → 拖落任何圖表（Navigator→Scripts→雙擊）。  |
//| 產物：MQL5/Files/l0_symbols.json（FTP/檔案總管拎走，交 ZCODE）。 |
//+------------------------------------------------------------------+
#property copyright "ZCODE_w"
#property version   "1.0"
#property script_show_inputs
// 可選：淨導 Market Watch 可見（true）定全 Symbol 表（false）
input bool OnlyMarketWatch = false;

void OnStart()
  {
   string json = "{\n  \"exported_at\": \"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS)
               + "\",\n  \"source\": \"MT5 SymbolInfoDouble\",\n  \"symbols\": [\n";
   int    total = SymbolsTotal(OnlyMarketWatch);
   int    n     = 0;
   string skip  = "";
   for(int i = 0; i < total; i++)
     {
      string sym = SymbolName(i, OnlyMarketWatch);
      double pip_size    = SymbolInfoDouble(sym, SYMBOL_TRADE_PIP_SIZE);
      double tick_size   = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
      double tick_value  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
      double contract    = SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE);
      double margin_init = SymbolInfoDouble(sym, SYMBOL_MARGIN_INITIAL);
      string quote_ccy   = SymbolInfoString(sym, SYMBOL_CURRENCY_PROFIT);
      // 過濾未訂閱／零規格嘅 symbol（零 tick_value 會污染權威鏈——零估算原則照跳）
      if(tick_size <= 0.0 || tick_value <= 0.0 || contract <= 0.0 || StringLen(quote_ccy) != 3)
        {
         skip += (StringLen(skip) ? "," : "") + sym;
         continue;
        }
      json += (n > 0 ? ",\n" : "")
            + "    {\"symbol\": \"" + sym + "\""
            + ", \"pip_size\": " + DoubleToString(pip_size, 8)
            + ", \"tick_size\": " + DoubleToString(tick_size, 8)
            + ", \"tick_value\": " + DoubleToString(tick_value, 8)
            + ", \"contract_size\": " + DoubleToString(contract, 2)
            + ", \"quote_currency\": \"" + quote_ccy + "\""
            + ", \"margin_initial\": " + DoubleToString(margin_init, 8)
            + "}";
      n++;
     }
   // fx_at_export：8 主要報價貨幣 vs USD（bid；pipcalc 按日 fx 修正用）
   json += "\n  ],\n  \"fx_at_export\": {\n";
   string fxSyms[8] = {"USDJPY", "USDCHF", "USDCAD", "USDAUD",
                       "USDNZD", "USDEUR", "USDGBP", "XAUUSD"};
   string fxKeys[8] = {"JPY", "CHF", "CAD", "AUD", "NZD", "EUR", "GBP", "XAU"};
   int m = 0;
   for(int k = 0; k < 8; k++)
     {
      double bid = SymbolInfoDouble(fxSyms[k], SYMBOL_BID);
      if(bid > 0.0)
        {
         // USDXXX → 1/xxx＝XXX 值幾多 USD；XXXUSD 直用 bid
         double v = (StringFind(fxSyms[k], "USD") == 0)
                    ? 1.0 / bid : bid;
         json += (m > 0 ? ",\n" : "")
               + "    \"" + fxKeys[k] + "\": " + DoubleToString(v, 8);
         m++;
        }
     }
   json += "\n  },\n  \"skipped_zero_spec\": \"" + skip + "\"\n}\n";

   int fh = FileOpen("l0_symbols.json", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(fh == INVALID_HANDLE)
     {
      Print("❌ FileOpen 失敗 err=", GetLastError());
      return;
     }
   FileWriteString(fh, json);
   FileClose(fh);
   Print("✅ L0 導出完成：", n, " 個 symbol（跳過零規格 ",
         StringLen(skip) > 0 ? "見 skipped_zero_spec" : "0",
         " 個）＋", m, " 個 fx → MQL5/Files/l0_symbols.json（", StringLen(json), " bytes）");
  }
//+------------------------------------------------------------------+
