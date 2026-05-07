#!/bin/bash
# Regenerate all 58 detailed reports with v2 scoring (Alpha Capture + ETE)
# Processes CSVs one at a time to avoid timeout

CSV_DIR="/home/alvin/.openclaw/workspace/trade_strategy_analyzer/samples"
SCRIPT="/home/alvin/.openclaw/workspace/trade_strategy_analyzer/generate_all_levels_from_csv.py"
LOG="/tmp/openclaw/regenerate_v2.log"

mkdir -p /tmp/openclaw

count=0
total=$(ls "$CSV_DIR"/*.csv 2>/dev/null | wc -l)
failed=0

echo "[$(date)] Starting v2 regeneration of $total reports..." > "$LOG"

for csv_file in "$CSV_DIR"/*.csv; do
    count=$((count + 1))
    fname=$(basename "$csv_file")
    echo "[$count/$total] Processing $fname..." | tee -a "$LOG"
    
    python3 "$SCRIPT" "$csv_file" >> "$LOG" 2>&1
    if [ $? -ne 0 ]; then
        echo "  ❌ FAILED: $fname" | tee -a "$LOG"
        failed=$((failed + 1))
    else
        echo "  ✅ Done" | tee -a "$LOG"
    fi
done

echo "[$(date)] Complete: $count processed, $failed failed" | tee -a "$LOG"
