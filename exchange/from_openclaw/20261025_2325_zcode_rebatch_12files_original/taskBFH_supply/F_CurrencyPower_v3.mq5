//+------------------------------------------------------------------+
//|                                        CurrencyPower_v3.mq5      |
//|  Clean rewrite. 9 power lines + diff + tickbox + ranking panel.  |
//|  v3.00 2026-09-26 full rewrite from spec                          |
//|  v3.10 2026-10-19 B1-B4: TOP PAIRS + expand block (MT4 port),    |
//|        ChartWindowFind(shortname), cached OnTimer, DRAW_NONE     |
//|        diff plot, Alert_On implemented, scoped OnDeinit           |
//+------------------------------------------------------------------+
#property copyright "OpenClaw for Alvin"
#property version   "3.10"
#property strict
#property indicator_separate_window
#property indicator_buffers 10
#property indicator_plots   10

#property indicator_type1  DRAW_LINE
#property indicator_color1 clrDarkGoldenrod
#property indicator_width1 3
#property indicator_label1 "XAU"
#property indicator_type2  DRAW_LINE
#property indicator_color2 clrDodgerBlue
#property indicator_label2 "USD"
#property indicator_type3  DRAW_LINE
#property indicator_color3 clrOrangeRed
#property indicator_label3 "EUR"
#property indicator_type4  DRAW_LINE
#property indicator_color4 clrSeaGreen
#property indicator_label4 "JPY"
#property indicator_type5  DRAW_LINE
#property indicator_color5 clrMediumPurple
#property indicator_label5 "GBP"
#property indicator_type6  DRAW_LINE
#property indicator_color6 clrChocolate
#property indicator_label6 "AUD"
#property indicator_type7  DRAW_LINE
#property indicator_color7 clrTeal
#property indicator_label7 "CAD"
#property indicator_type8  DRAW_LINE
#property indicator_color8 clrDeepPink
#property indicator_label8 "CHF"
#property indicator_type9  DRAW_LINE
#property indicator_color9 clrGray
#property indicator_label9 "NZD"
#property indicator_type10 DRAW_NONE
#property indicator_color10 clrSilver
#property indicator_label10 "Diff"

input int    RSI_Period     = 14;
input int    ATR_Period     = 14;
input int    Slope_Lookback = 10;
input int    Lookback_Bars  = 300;
input bool   Alert_On       = true;
input ENUM_TIMEFRAMES PairTF = PERIOD_H1;
input int    TickStyle      = 0;   // 0=[x]/[  ] 1=+ / x  2=● / ○
input bool   Show_Panel     = true;

string CCY[9] = {"XAU","USD","EUR","JPY","GBP","AUD","CAD","CHF","NZD"};
bool    Show[9] = {true,true,true,true,true,true,true,true,true};

string Pairs[28][2] = {
 {"EUR","USD"},{"GBP","USD"},{"AUD","USD"},{"NZD","USD"},{"USD","JPY"},{"USD","CHF"},{"USD","CAD"},
 {"EUR","GBP"},{"EUR","JPY"},{"EUR","CHF"},{"EUR","AUD"},{"EUR","CAD"},{"EUR","NZD"},
 {"GBP","JPY"},{"GBP","CHF"},{"GBP","AUD"},{"GBP","CAD"},{"GBP","NZD"},
 {"AUD","JPY"},{"AUD","CHF"},{"AUD","CAD"},{"AUD","NZD"},
 {"NZD","JPY"},{"NZD","CHF"},{"NZD","CAD"},
 {"CAD","JPY"},{"CAD","CHF"},{"CHF","JPY"}};
string GoldQ[7] = {"EUR","GBP","AUD","JPY","CHF","CAD","NZD"};

double B0[],B1[],B2[],B3[],B4[],B5[],B6[],B7[],B8[],B9[];

int    hR[36];  // RSI handles: 0-27 majors, 28 XAUUSD, 29-35 gold crosses
int    hA[36];  // ATR handles
string gS[36];
int    gN = 0;          // resolved count
int    gGoldN = 0;
int    gSub = 0;
bool   gReady = false;
double g_diff = 0;
double g_prevDiff = 0;
double g_lastPw[9];
double g_prevPw[9];     // previous power values (Alert_On crossing detection)
int    g_expand = -1;   // expanded currency row index (CCY idx), -1 = none
bool   g_panelOn = true;
color LineColor2(int k)
{
   color C[9]={clrDarkGoldenrod,clrDodgerBlue,clrOrangeRed,clrSeaGreen,clrMediumPurple,clrChocolate,clrTeal,clrDeepPink,clrGray};
   return C[k];
}
string TickMark(bool on)
{
   if(TickStyle==1) return on?"+ ":"x ";
   if(TickStyle==2) return on?"\x25CF ":"\x25CB ";
   return on?"[x] ":"[  ] ";
}
datetime gLastBar = 0;

int Idx(string c){ if(c=="XAU")return 0; if(c=="USD")return 1; if(c=="EUR")return 2; if(c=="JPY")return 3;
                   if(c=="GBP")return 4; if(c=="AUD")return 5; if(c=="CAD")return 6; if(c=="CHF")return 7;
                   if(c=="NZD")return 8; return -1; }

string FindSym(string base,string quote)
{
   string want=base+quote, rev=quote+base;
   int total=SymbolsTotal(false);
   for(int i=0;i<total;i++)
   {
      string s=SymbolName(i,false);
      string c=s;
      StringToUpper(c);
      StringReplace(c,".R",""); StringReplace(c,".RAW",""); StringReplace(c,".M","");
      StringReplace(c,"M","");  StringReplace(c,".","");
      if(c==want || c==rev) return s;
   }
   return "";
}

int OnInit()
{
   SetIndexBuffer(0,B0,INDICATOR_DATA);  ArraySetAsSeries(B0,true);
   SetIndexBuffer(1,B1,INDICATOR_DATA);  ArraySetAsSeries(B1,true);
   SetIndexBuffer(2,B2,INDICATOR_DATA);  ArraySetAsSeries(B2,true);
   SetIndexBuffer(3,B3,INDICATOR_DATA);  ArraySetAsSeries(B3,true);
   SetIndexBuffer(4,B4,INDICATOR_DATA);  ArraySetAsSeries(B4,true);
   SetIndexBuffer(5,B5,INDICATOR_DATA);  ArraySetAsSeries(B5,true);
   SetIndexBuffer(6,B6,INDICATOR_DATA);  ArraySetAsSeries(B6,true);
   SetIndexBuffer(7,B7,INDICATOR_DATA);  ArraySetAsSeries(B7,true);
   SetIndexBuffer(8,B8,INDICATOR_DATA);  ArraySetAsSeries(B8,true);
   SetIndexBuffer(9,B9,INDICATOR_DATA);  ArraySetAsSeries(B9,true);
   IndicatorSetInteger(INDICATOR_DIGITS,1);
   IndicatorSetInteger(INDICATOR_LEVELS,1);
   IndicatorSetDouble(INDICATOR_LEVELVALUE,0,50.0);
   // auto scale (boss: scale-by-line feels better than fixed 40-60)
   IndicatorSetString(INDICATOR_SHORTNAME,"CP v3");
   for(int i=0;i<10;i++) PlotIndexSetInteger(i,PLOT_SHOW_DATA,false);
   gSub = ChartWindowFind(0,"CP v3");
   ArrayInitialize(g_prevPw,50.0);

   // build handle table
   for(int p=0;p<28;p++)
   {
      string s=FindSym(Pairs[p][0],Pairs[p][1]);
      if(s==""){ hR[p]=-1; hA[p]=-1; continue; }
      SymbolSelect(s,true);
      gS[p]=s; gN++;
      hR[p]=iRSI(s,PairTF,RSI_Period,PRICE_CLOSE);
      hA[p]=iATR(s,PairTF,ATR_Period);
   }
   // XAUUSD
   string xu=FindSym("XAU","USD");
   if(xu!=""){ SymbolSelect(xu,true); gS[28]=xu; gN++;
      hR[28]=iRSI(xu,PairTF,RSI_Period,PRICE_CLOSE); hA[28]=iATR(xu,PairTF,ATR_Period); }
   else { hR[28]=-1; hA[28]=-1; }
   // gold crosses direct
   for(int g=0;g<7;g++)
   {
      int k=29+g;
      string s=FindSym("XAU",GoldQ[g]);
      if(s==""){ hR[k]=-1; hA[k]=-1; continue; }
      SymbolSelect(s,true); gS[k]=s; gGoldN++;
      hR[k]=iRSI(s,PairTF,RSI_Period,PRICE_CLOSE);
      hA[k]=iATR(s,PairTF,ATR_Period);
   }
   PrintFormat("CP v3: majors=%d/28 goldcross=%d/7 XAUUSD=%s sub=%d",gN-1-gGoldN,gGoldN,gS[28],gSub);
   EventSetTimer(5);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   // B4: delete only our own CP3-prefixed objects (scoped cleanup)
   ObjectsDeleteAll(0,"CP3");
}

// weight of pair p at shift: relative ATR% (avg across pairs = 1)
double W(int p,int sh)
{
   if(hA[p]<0) return 1.0;
   double a[]; if(CopyBuffer(hA[p],0,sh,1,a)<1) return 1.0;
   double px=iClose(gS[p],PairTF,sh); if(px<=0) return 1.0;
   return a[0]/px*100.0;    // raw ATR% (normalized later)
}

void Calc(int sh, double &pw[])
{
   double raw[36], w[36];
   double sumW=0; int nW=0;
   for(int p=0;p<36;p++)
   {
      raw[p]=0; w[p]=1;
      if(hR[p]<0) continue;
      double b[]; if(CopyBuffer(hR[p],0,sh,1,b)<1){ raw[p]=0; w[p]=0; continue; }
      raw[p]=b[0]-50.0;
      w[p]=W(p,sh);
      if(w[p]>0){ sumW+=w[p]; nW++; }
   }
   double avgW = nW>0 ? sumW/nW : 1.0;
   if(avgW<=0) avgW=1.0;

   double c[9]; int cnt[9];
   ArrayInitialize(c,0.0); ArrayInitialize(cnt,0);
   for(int p=0;p<28;p++)
   {
      if(w[p]<=0) continue;
      double v = raw[p]*(w[p]/avgW);
      int bi=Idx(Pairs[p][0]), qi=Idx(Pairs[p][1]);
      if(bi>=0){ c[bi]+=v; cnt[bi]++; }
      if(qi>=0){ c[qi]-=v; cnt[qi]++; }
   }
   for(int k=1;k<9;k++)
      pw[k] = 50.0 + (cnt[k]>0 ? c[k]/cnt[k] : 0.0);

   // XAU: XAUUSD (weight 1) + direct gold crosses (XAU base)
   double gx=0; int gn=0;
   if(w[28]>0){ gx+=raw[28]*(w[28]/avgW); gn++; }
   for(int g=0;g<7;g++)
   {
      int k=29+g;
      if(w[k]<=0) continue;
      double v=raw[k]*(w[k]/avgW);
      gx+=v; gn++;
      int qi=Idx(GoldQ[g]);
      if(qi>=0){ c[qi]-=v*0.5; cnt[qi]++; pw[qi]=50.0+c[qi]/cnt[qi]; }
   }
   pw[0] = gn>0 ? 50.0+gx/gn : 50.0;
}

double SlopeT(double &arr[],int n)  // slope/sd t-stat on last n points (chronological assumed)
{
   int m=MathMin(n,ArraySize(arr));
   if(m<4) return 0;
   double sx=0,sy=0,sxy=0,sxx=0;
   int st=ArraySize(arr)-m;
   for(int i=0;i<m;i++){ double x=i; double y=arr[st+i]; sx+=x; sy+=y; sxy+=x*y; sxx+=x*x; }
   double den=m*sxx-sx*sx; if(den==0) return 0;
   double slope=(m*sxy-sx*sy)/den;
   double mean=sy/m, v=0;
   for(int i=0;i<m;i++){ double d=arr[st+i]-mean; v+=d*d; }
   double sd=MathSqrt(v/m); if(sd<0.15) sd=0.15;
   return slope/sd;
}
string Arrow(double t)
{
   if(t> 0.30) return "^^";
   if(t> 0.10) return "^";
   if(t<-0.30) return "vv";
   if(t<-0.10) return "v";
   return "-";
}

void SetLbl(string nm,int x,int y,string txt,color c,int fs,string font)
{
   if(ObjectFind(0,nm)<0) ObjectCreate(0,nm,OBJ_LABEL,gSub,0,0);
   ObjectSetInteger(0,nm,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,nm,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,nm,OBJPROP_YDISTANCE,y);
   ObjectSetString(0,nm,OBJPROP_TEXT,txt);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,c);
   ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,fs);
   ObjectSetString(0,nm,OBJPROP_FONT,font);
   ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,nm,OBJPROP_HIDDEN,false);
   ObjectSetInteger(0,nm,OBJPROP_ZORDER,21);
}

void UI(double &last[], double &t[])
{
   static datetime lastLog=0;
   if(TimeLocal()-lastLog>60){ lastLog=TimeLocal(); Print("CP3 UI alive v3.10"); }
   if(!Show_Panel || !g_panelOn)
   {
      ObjectsDeleteAll(0,"CP3");
      ChartRedraw();
      return;
   }
   // rank by power
   int idx[9]; for(int i=0;i<9;i++) idx[i]=i;
   for(int a=0;a<9;a++) for(int b=a+1;b<9;b++)
      if(last[idx[b]]>last[idx[a]]){ int t2=idx[a]; idx[a]=idx[b]; idx[b]=t2; }

   // ONE panel, 9 rows: tickbox + [CCY value arrow] (click a row to expand vs others)
   int rowH=14, top=4;
   string pn="CP3PANEL";
   if(ObjectFind(0,pn)<0) ObjectCreate(0,pn,OBJ_RECTANGLE_LABEL,gSub,0,0);
   ObjectSetInteger(0,pn,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,pn,OBJPROP_XDISTANCE,4);  ObjectSetInteger(0,pn,OBJPROP_YDISTANCE,top);
   ObjectSetInteger(0,pn,OBJPROP_XSIZE,150);
   ObjectSetInteger(0,pn,OBJPROP_YSIZE,16*rowH+16);
   ObjectSetInteger(0,pn,OBJPROP_BGCOLOR,C'255,240,245');
   ObjectSetInteger(0,pn,OBJPROP_COLOR,C'231,84,128');
   ObjectSetInteger(0,pn,OBJPROP_BORDER_TYPE,BORDER_FLAT);
   ObjectSetInteger(0,pn,OBJPROP_BACK,false);
   ObjectSetInteger(0,pn,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,pn,OBJPROP_ZORDER,20);

   SetLbl("CP3HDR",10,top+2,"ON  CCY   POWER SLOPE",clrDimGray,8,"Courier New Bold");

   for(int r2=0;r2<9;r2++)
   {
      int k=idx[r2];
      int y=top+4+rowH+r2*rowH;
      SetLbl("CP3T_"+CCY[k],10,y,TickMark(Show[k]),Show[k]?LineColor2(k):clrDarkGray,9,"Courier New Bold");
      SetLbl("CP3R_"+CCY[k],38,y,CCY[k]+"  "+DoubleToString(last[k],1)+" "+Arrow(t[k])+(g_expand==k?" <":""),Show[k]?LineColor2(k):clrDarkGray,9,"Courier New Bold");
   }

   // TOP PAIRS: 3 pair combinations with the largest power gap
   int bi=-1,bj=-1; double bv=-1;
   int bi2=-1,bj2=-1; double bv2=-1;
   int bi3=-1,bj3=-1; double bv3=-1;
   for(int a2=0;a2<9;a2++) for(int b3=a2+1;b3<9;b3++)
   {
      double d=MathAbs(g_lastPw[a2]-g_lastPw[b3]);
      if(d>bv){ bv3=bv2;bi3=bi2;bj3=bj2; bv2=bv;bi2=bi;bj2=bj; bv=d;bi=a2;bj=b3; }
      else if(d>bv2){ bv3=bv2;bi3=bi2;bj3=bj2; bv2=d;bi2=a2;bj2=b3; }
      else if(d>bv3){ bv3=d;bi3=a2;bj3=b3; }
   }
   int ty=top+4+9*rowH+rowH;
   SetLbl("CP3TPH",10,ty,"-- TOP PAIRS --",C'214,51,108',8,"Courier New Bold");
   int ia[3]; ia[0]=bi; ia[1]=bi2; ia[2]=bi3;
   int ib[3]; ib[0]=bj; ib[1]=bj2; ib[2]=bj3;
   double iv[3]; iv[0]=bv; iv[1]=bv2; iv[2]=bv3;
   for(int q=0;q<3;q++)
   {
      if(ia[q]<0) continue;
      string strong=(g_lastPw[ia[q]]>=g_lastPw[ib[q]])?CCY[ia[q]]:CCY[ib[q]];
      string weak  =(g_lastPw[ia[q]]>=g_lastPw[ib[q]])?CCY[ib[q]]:CCY[ia[q]];
      SetLbl("CP3TP"+IntegerToString(q+1),10,ty+12+q*12,
             CCY[ia[q]]+CCY[ib[q]]+" "+DoubleToString(iv[q],1)+"  "+strong+">"+weak,clrBlack,8,"Courier New");
   }

   // DIFF footer + bar
   SetLbl("CP3DIFF",10,top+4+(10+5)*rowH-2,"DIFF "+DoubleToString(g_diff,1)+Arrow(g_diff-g_prevDiff),C'214,51,108',9,"Courier New Bold");
   string tb="CP3DB";
   if(ObjectFind(0,tb)<0) ObjectCreate(0,tb,OBJ_RECTANGLE_LABEL,gSub,0,0);
   ObjectSetInteger(0,tb,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,tb,OBJPROP_XDISTANCE,70); ObjectSetInteger(0,tb,OBJPROP_YDISTANCE,top+4+(10+5)*rowH);
   ObjectSetInteger(0,tb,OBJPROP_XSIZE,80); ObjectSetInteger(0,tb,OBJPROP_YSIZE,8);
   ObjectSetInteger(0,tb,OBJPROP_BGCOLOR,C'250,225,232');
   ObjectSetInteger(0,tb,OBJPROP_BORDER_TYPE,BORDER_FLAT); ObjectSetInteger(0,tb,OBJPROP_COLOR,clrSilver);
   ObjectSetInteger(0,tb,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,tb,OBJPROP_ZORDER,21);
   string fb="CP3DF";
   if(ObjectFind(0,fb)<0) ObjectCreate(0,fb,OBJ_RECTANGLE_LABEL,gSub,0,0);
   ObjectSetInteger(0,fb,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,fb,OBJPROP_XDISTANCE,70); ObjectSetInteger(0,fb,OBJPROP_YDISTANCE,top+4+(10+5)*rowH);
   ObjectSetInteger(0,fb,OBJPROP_XSIZE,(int)MathMax(1,MathMin(g_diff*3.2,80))); ObjectSetInteger(0,fb,OBJPROP_YSIZE,8);
   ObjectSetInteger(0,fb,OBJPROP_BGCOLOR,(g_diff>=g_prevDiff)?C'47,158,68':clrGray);
   ObjectSetInteger(0,fb,OBJPROP_BORDER_TYPE,BORDER_FLAT);
   ObjectSetInteger(0,fb,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,fb,OBJPROP_ZORDER,22);

   // expand block: clicked currency vs the other 8
   for(int e=0;e<9;e++) if(e!=g_expand) ObjectDelete(0,"CP3E_"+CCY[e]);
   if(g_expand>=0)
   {
      int ek[8]; double ev[8]; int m=0;
      for(int e=0;e<9;e++){ if(e==g_expand) continue; ek[m]=e; ev[m]=g_lastPw[g_expand]-g_lastPw[e]; m++; }
      for(int a4=0;a4<m;a4++) for(int b4=a4+1;b4<m;b4++)
         if(MathAbs(ev[b4])>MathAbs(ev[a4])){ int ti=ek[a4];ek[a4]=ek[b4];ek[b4]=ti; double tv=ev[a4];ev[a4]=ev[b4];ev[b4]=tv; }
      SetLbl("CP3EH",160,top+4+rowH,CCY[g_expand]+" vs:",clrBlack,8,"Courier New Bold");
      for(int q2=0;q2<m;q2++)
         SetLbl("CP3E_"+CCY[ek[q2]],160,top+4+rowH+(q2+1)*12,
                "  "+CCY[g_expand]+CCY[ek[q2]]+" "+DoubleToString(ev[q2],1)+(ev[q2]>0?" ^":" v"),
                ev[q2]>0?C'47,158,68':C'226,73,90',8,"Courier New");
   }
   else ObjectDelete(0,"CP3EH");
   SetLbl("CP3BADGE",0,4,"CurrencyPower v3.10",clrDimGray,8,"Arial");
   ObjectSetInteger(0,"CP3BADGE",OBJPROP_CORNER,CORNER_RIGHT_UPPER);
   ObjectSetInteger(0,"CP3BADGE",OBJPROP_XDISTANCE,8);
   g_prevDiff=g_diff;
}

void OnChartEvent(const int id,const long &lp,const double &dp,const string &sn)
{
   if(id==CHARTEVENT_OBJECT_CLICK)
   {
      for(int k=0;k<9;k++)
         if(sn=="CP3T_"+CCY[k])
         {
            Show[k]=!Show[k];
            PlotIndexSetInteger(k,PLOT_DRAW_TYPE,Show[k]?DRAW_LINE:DRAW_NONE);
            ChartRedraw();
            return;
         }
      if(sn=="CP3BADGE"){ g_panelOn=!g_panelOn; if(!g_panelOn) ObjectsDeleteAll(0,"CP3"); else { double pw9[9]; for(int q=0;q<9;q++) pw9[q]=g_lastPw[q]; double t9b[9]; ArrayInitialize(t9b,0.0); UI(pw9,t9b); } ChartRedraw(); return; }
      for(int k=0;k<9;k++)
         if(sn=="CP3R_"+CCY[k])
         {
            g_expand = (g_expand==k)?-1:k;
            // trigger UI redraw via lightweight refresh
            double pw[9]; for(int q=0;q<9;q++) pw[q]=g_lastPw[q];
            double t9[9]; ArrayInitialize(t9,0.0);
            UI(pw,t9);
            ChartRedraw();
            return;
         }
   }
}

int OnCalculate(const int rt,const int pc,const datetime &tm[],
                const double &op[],const double &hi[],const double &lo[],const double &cl[],
                const long &tv[],const long &vl[],const int &sp[])
{
   if(rt<10) return(0);
   int limit=rt-pc; if(limit<=0) limit=1; if(limit>Lookback_Bars) limit=Lookback_Bars;

   double pw[9];
   for(int i=limit-1;i>=0;i--)
   {
      ArrayInitialize(pw,50.0);
      Calc(i,pw);
      double mx=pw[0],mn=pw[0];
      for(int k=1;k<9;k++){ if(pw[k]>mx)mx=pw[k]; if(pw[k]<mn)mn=pw[k]; }
      B0[i]=pw[0]; B1[i]=pw[1]; B2[i]=pw[2]; B3[i]=pw[3]; B4[i]=pw[4];
      B5[i]=pw[5]; B6[i]=pw[6]; B7[i]=pw[7]; B8[i]=pw[8]; B9[i]=EMPTY_VALUE;
   }
   // slopes + UI
   double last[9],t[9];
   for(int k=0;k<9;k++)
   {
      double tmp[]; ArrayResize(tmp,MathMin(Slope_Lookback*3,limit));
      int m=ArraySize(tmp);
      for(int i=0;i<m;i++)
      {
         double v=0;
         switch(k){case 0:v=B0[m-1-i];break; case 1:v=B1[m-1-i];break; case 2:v=B2[m-1-i];break;
                   case 3:v=B3[m-1-i];break; case 4:v=B4[m-1-i];break; case 5:v=B5[m-1-i];break;
                   case 6:v=B6[m-1-i];break; case 7:v=B7[m-1-i];break; case 8:v=B8[m-1-i];break;}
         tmp[i]=v;
      }
      double v0=0;
      switch(k){case 0:v0=B0[0];break; case 1:v0=B1[0];break; case 2:v0=B2[0];break; case 3:v0=B3[0];break;
                case 4:v0=B4[0];break; case 5:v0=B5[0];break; case 6:v0=B6[0];break; case 7:v0=B7[0];break;
                case 8:v0=B8[0];break;}
      last[k]=v0;
      t[k]=SlopeT(tmp,Slope_Lookback);
      // B3: Alert_On — fire on power extreme crossings (70/30), once per crossing
      if(Alert_On)
      {
         if(v0>=70.0 && g_prevPw[k]<70.0)
            Alert("CurrencyPower v3.10: ",CCY[k]," power ",DoubleToString(v0,1)," crossed above 70.0");
         if(v0<=30.0 && g_prevPw[k]>30.0)
            Alert("CurrencyPower v3.10: ",CCY[k]," power ",DoubleToString(v0,1)," crossed below 30.0");
      }
      g_prevPw[k]=v0;
   }
   // panel footer: global diff value (computed from last row)
   double mx=last[0], mn=last[0];
   for(int k=1;k<9;k++){ if(last[k]>mx)mx=last[k]; if(last[k]<mn)mn=last[k]; }
   g_diff = mx-mn;
   for(int q3=0;q3<9;q3++) g_lastPw[q3]=last[q3];
   UI(last,t);
   // slope arrows at right edge of each line's last value
   string an[9];
   for(int k=0;k<9;k++)
   {
      an[k]="CP3A_"+CCY[k];
      if(ObjectFind(0,an[k])<0) ObjectCreate(0,an[k],OBJ_ARROW_UP,gSub,0,0);
      ObjectSetInteger(0,an[k],OBJPROP_TIME,tm[1]);
      ObjectSetDouble(0,an[k],OBJPROP_PRICE,last[k]);
      ObjectSetInteger(0,an[k],OBJPROP_COLOR,LineColor2(k));
      ObjectSetInteger(0,an[k],OBJPROP_FONTSIZE,2);
      ObjectSetInteger(0,an[k],OBJPROP_ANCHOR,ANCHOR_LEFT);
      double t2=t[k];
      int code = (t2>0.10)?233:(t2<-0.10)?234:254;   // up / down / dash
      ObjectSetInteger(0,an[k],OBJPROP_ARROWCODE,code);
      ObjectSetInteger(0,an[k],OBJPROP_WIDTH,1);
      ObjectSetInteger(0,an[k],OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,an[k],OBJPROP_HIDDEN,true);
      if(!Show[k]) ObjectDelete(0,an[k]);
   }
   ChartRedraw();
   return(rt);
}

void OnTimer()
{
   // B2: refresh UI from cached values even without ticks (weekend/quiet);
   // no ChartSetSymbolPeriod — user zoom/scroll is never disturbed
   static datetime lk=0;
   if(TimeLocal()-lk<5) return;
   lk=TimeLocal();
   double pw[9]; for(int q=0;q<9;q++) pw[q]=g_lastPw[q];
   double t9[9]; ArrayInitialize(t9,0.0);
   UI(pw,t9);
   ChartRedraw();
}
//+------------------------------------------------------------------+
