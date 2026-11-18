# Taskboard v1 規格

六欄：Backlog｜Todo｜In Progress｜Review｜Blocked｜Done

欄頭：名稱＋卡數；In Progress 超 2 張數字變紅

卡面：標題最多兩行；左色條＝優先級(P0 紅/P1 琥珀/P2 灰)；
      底行＝lane＋owner＋issue 號＋到期日

卡內：描述、驗收 checklist、依賴(blocks/blocked by)、activity log

頂部：搜尋＋lane/owner/priority 篩選＋「只睇我 lane」

互動：拖卡只改視圖；真正改動＝改 issue 的 status label；CI 5 分鐘重建

外觀：頂欄 #16324F；白卡圓角 8px；hover 陰影；狀態顏色＋文字並排；
      字體 Segoe UI/Noto Sans TC；手機單欄

資料：GitHub Issues（lane:* 同 status:* labels）
