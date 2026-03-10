#!/bin/bash
# Simple bash script to run all notebooks
# Usage: ./run_all_notebooks.sh

echo "============================================"
echo "Running All Keyword Extraction Notebooks"
echo "============================================"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Array of all notebooks
notebooks=(
    "toFinalReport/german/HRank_german.ipynb"
    "toFinalReport/german/DRank_german.ipynb"
    "toFinalReport/indianexpress/HRank_Indian.ipynb"
    "toFinalReport/indianexpress/DRank_Indian.ipynb"
    "toFinalReport/Kotiliesi/HRank_ruoka.ipynb"
    "toFinalReport/Kotiliesi/DRank_Kotiliesi.ipynb"
    "toFinalReport/ruoka/HRank_ruoka.ipynb"
    "toFinalReport/ruoka/DRank_ruoka.ipynb"
    "toFinalReport/herald/HRank_herald.ipynb"
    "toFinalReport/herald/DRank_herald.ipynb"
)

success=0
failed=0

# Run each notebook
for notebook in "${notebooks[@]}"; do
    echo ""
    echo "========================================"
    echo "Running: $notebook"
    echo "========================================"
    
    if jupyter nbconvert --to notebook --execute --inplace \
        --ExecutePreprocessor.timeout=600 "$notebook"; then
        echo "✓ SUCCESS: $notebook"
        ((success++))
    else
        echo "✗ FAILED: $notebook"
        ((failed++))
    fi
done

# Print summary
echo ""
echo "========================================"
echo "SUMMARY"
echo "========================================"
echo "Total: ${#notebooks[@]}"
echo "✓ Successful: $success"
echo "✗ Failed: $failed"
echo ""
echo "Results: toFinalReport/Results/results.csv"
echo "Graphs: toFinalReport/Results/*.png"
