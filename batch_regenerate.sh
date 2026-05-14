#!/bin/bash
# Batch regenerate all signal reports with latest template
set -e
cd /home/alvin/.openclaw/workspace/trade_strategy_analyzer

SUCCESS=0
FAIL=0
TOTAL=0

for csv in downloads/forex-forest-signals-page-*.csv; do
    # Extract signal ID from filename
    BASE=$(basename "$csv" .csv)
    SID=$(echo "$BASE" | grep -oP '\d+')
    TOTAL=$((TOTAL + 1))
    
    echo -n "[$TOTAL] Signal #$SID ... "
    
    # Try to generate report
    if python3 generate_signal_report_v2.py "$SID" "$csv" "docs/reports/signal_${SID}.html" 2>/dev/null; then
        echo "✅"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "❌ failed"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "========================================="
echo "Batch Report Generation Complete"
echo "Total: $TOTAL | Success: $SUCCESS | Failed: $FAIL"
echo "========================================="
