#!/bin/bash
# Generate all-levels comparison reports for all CSV files

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting batch all-levels comparison generation..."

# List of CSV files to process
csv_files=(
    "samples/forex-forest-signals-page-14341.csv"
    "samples/signal_14581_trades.csv"
    "samples/forex-forest-signals-page-16706.csv"
    "samples/forex-forest-signals-page-17611.csv"
    "samples/forex-forest-signals-page-17962.csv"
    "samples/forex-forest-signals-page-2351.csv"
    "samples/forex-forest-signals-page-36511.csv"
)

total_files=${#csv_files[@]}
current_file=0

for csv_file in "${csv_files[@]}"; do
    current_file=$((current_file + 1))
    
    echo ""
    echo "[$current_file/$total_files] Processing: $csv_file"
    
    # Extract signal ID from filename
    signal_id=$(basename "$csv_file" | sed 's/^forex-forest-signals-page-//' | sed 's/^signal_//' | sed 's/_trades.csv$//' | sed 's/.csv$//')
    
    echo "  Signal ID: $signal_id"
    
    # Generate report
    python3 generate_all_levels_from_csv.py "$csv_file" 2>&1 | grep -E "(Processing|Found|✅|Report saved|File size|analyzed|comparisons)"
    
    if [ $? -eq 0 ]; then
        echo "  ✅ Success"
    else
        echo "  ❌ Failed"
    fi
done

echo ""
echo "✅ Batch processing complete!"
