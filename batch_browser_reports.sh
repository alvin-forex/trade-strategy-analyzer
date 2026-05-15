#!/bin/bash
# Batch generate index reports using browser automation via OpenClaw
# This script uses curl + the running HTTP servers to trigger report generation

DOCS_DIR="/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs"
DOWNLOADS_DIR="/home/alvin/.openclaw/workspace/trade_strategy_analyzer/downloads"
REPORTS_DIR="$DOCS_DIR/reports"

# Get all CSV signal IDs
CSV_IDS=$(ls "$DOWNLOADS_DIR"/forex-forest-signals-page-*.csv | sed 's/.*page-//' | sed 's/\.csv//')

SUCCESS=0
FAIL=0
TOTAL=0

for SID in $CSV_IDS; do
    OUT="$REPORTS_DIR/index_${SID}.html"
    
    # Skip if already exists
    if [ -f "$OUT" ]; then
        echo "[$SID] ✅ already exists"
        continue
    fi
    
    TOTAL=$((TOTAL + 1))
    echo -n "[$SID] Generating... "
    
    # The actual generation is done by the browser automation
    # This script just lists what needs to be done
    echo "NEEDS_GENERATION"
done

echo ""
echo "Total to generate: $TOTAL"
echo "Run via browser automation with OpenClaw"
