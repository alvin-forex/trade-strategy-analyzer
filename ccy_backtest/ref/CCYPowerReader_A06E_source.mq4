//+------------------------------------------------------------------+
//|                                         CCYPowerReader.mq4        |
//|  Reads CCY Power Indicator v1.00 values from chart objects       |
//|  and writes per-TF to ccy_power_reader.csv                      |
//|  Place on 3 charts: D1, H4, H1 (any symbol with the indicator)  |
//+------------------------------------------------------------------+
#property copyright "OpenClaw AI"
#property version   "1.00"
#property strict

input int    UpdateIntervalSeconds = 300;  // Update every 5 minutes
input string OutputFilename = "ccy_power_reader.csv";

datetime lastUpdate = 0;

int OnInit()
{
    Print("=== CCYPowerReader v1.00 Init on ", Symbol(), " ", EnumToString((ENUM_TIMEFRAMES)Period()), " ===");
    lastUpdate = 0;
    DoUpdate();
    return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {}

void OnTick()
{
    datetime now = TimeCurrent();
    if(now - lastUpdate >= UpdateIntervalSeconds)
    {
        DoUpdate();
        lastUpdate = now;
    }
}

string DetectCCYPowerPrefix()
{
    int total = ObjectsTotal();
    for(int i = 0; i < total; i++)
    {
        string name = ObjectName(0, i);
        int pos = StringFind(name, "__table_edit_");
        if(pos > 0)
        {
            string suffix = StringSubstr(name, pos + 14);
            if(StringLen(suffix) >= 3)
                return StringSubstr(name, 0, pos);
        }
    }
    return "";
}

void DoUpdate()
{
    string prefix = DetectCCYPowerPrefix();
    if(prefix == "")
    {
        Print("CCYPowerReader: No CCY Power Indicator found on chart");
        return;
    }
    
    string tfName = EnumToString((ENUM_TIMEFRAMES)Period());
    // Clean up TF name: PERIOD_D1 -> D1, PERIOD_H4 -> H4, PERIOD_H1 -> H1
    StringReplace(tfName, "PERIOD_", "");
    
    string timeStr = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES);
    
    // Read 9 currencies from chart objects
    string names[9];
    double powers[9];
    
    for(int row = 2; row <= 10; row++)
    {
        string nameObj = prefix + "__table_edit_1_" + IntegerToString(row) + "__1";
        string valObj = prefix + "__table_edit_2_" + IntegerToString(row) + "__1";
        names[row-2] = ObjectGetString(0, nameObj, OBJPROP_TEXT);
        powers[row-2] = StringToDouble(ObjectGetString(0, valObj, OBJPROP_TEXT));
    }
    
    // Write to CSV (append mode, one line per update)
    // Format: timestamp,tf,ccy1_name,ccy1_power,...,ccy9_name,ccy9_power
    int handle = FileOpen(OutputFilename, FILE_CSV | FILE_WRITE | FILE_READ | FILE_ANSI, ',');
    if(handle == INVALID_HANDLE)
    {
        Print("CCYPowerReader: Failed to open file");
        return;
    }
    
    // Check if file is empty (write header)
    if(FileSize(handle) == 0)
    {
        FileWrite(handle, "timestamp", "timeframe",
            "ccy1_name", "ccy1_power", "ccy2_name", "ccy2_power",
            "ccy3_name", "ccy3_power", "ccy4_name", "ccy4_power",
            "ccy5_name", "ccy5_power", "ccy6_name", "ccy6_power",
            "ccy7_name", "ccy7_power", "ccy8_name", "ccy8_power",
            "ccy9_name", "ccy9_power");
    }
    
    // Seek to end
    FileSeek(handle, 0, SEEK_END);
    
    FileWrite(handle, timeStr, tfName,
        names[0], DoubleToStr(powers[0], 4),
        names[1], DoubleToStr(powers[1], 4),
        names[2], DoubleToStr(powers[2], 4),
        names[3], DoubleToStr(powers[3], 4),
        names[4], DoubleToStr(powers[4], 4),
        names[5], DoubleToStr(powers[5], 4),
        names[6], DoubleToStr(powers[6], 4),
        names[7], DoubleToStr(powers[7], 4),
        names[8], DoubleToStr(powers[8], 4));
    
    FileClose(handle);
    
    // Log
    string top3 = "";
    for(int i = 0; i < 3 && i < 9; i++)
        top3 += names[i] + "=" + DoubleToStr(powers[i], 2) + " ";
    Print("CCYPowerReader ", tfName, " OK: ", top3);
}
