# 缺陷派工：forex_news.html 刪「外匯早晚報」冗餘 quick links（老闆 21:44 實測）

老闆 21:44 實測截圖：外匯新聞頁「外匯早晚報」區塊嘅四條 quick links（報告總覽（歷史全檔）＋早報 10-29／10-28／10-27）——**同下面「報告列表」（17 組・194 份報告，按日期分組卡）完全重複，多餘**。

## 位置（源碼實測）
`docs/forex_news.html` 101-108 行：
```
<h2>外匯早晚報</h2>
  <ul>
    <li><a href="forex_reports/index.html">報告總覽（歷史全檔）</a></li>
    <li><a href="forex_reports/2026-10-29_morning.html">早報 2026-10-29</a></li>
    <li><a href="forex_reports/forex_morning_report_2026-10-28.html">早報 2026-10-28</a></li>
    <li><a href="forex_reports/forex_morning_report_2026-10-27.html">早報 2026-10-27</a></li>
  </ul>
</section>
```

## 指令
1. 整個「外匯早晚報」section（h2＋ul）刪走——下面「報告列表」（按日期分組，含全部 194 份早/晚盤報告連結）已完全覆蓋，留一個就夠
2. 全站檢查：呢個 pattern 得 forex_news.html 一頁有（我已掃），刪完唔影響其他頁
3. 驗收：頁面渲染乾淨（無空 section）＋報告列表功能不變；老闆手機實測終審

## 優先
細單，今晚出貨都得（跟 FIX-CHART 之後）。
