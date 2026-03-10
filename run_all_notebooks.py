#!/usr/bin/env python3
"""
Run all keyword extraction notebooks across all datasets.
This script executes HRank and DRank notebooks for each dataset and generates results.
"""

import os
import sys
import subprocess
from pathlib import Path
import time

# Base directory containing all notebooks
BASE_DIR = Path(__file__).parent / "toFinalReport"

# Define all notebooks to run (in order)
NOTEBOOKS = [
    "german/HRank_german.ipynb",
    "german/DRank_german.ipynb",
    "indianexpress/HRank_Indian.ipynb",
    "indianexpress/DRank_Indian.ipynb",
    "Kotiliesi/HRank_ruoka.ipynb",
    "Kotiliesi/DRank_Kotiliesi.ipynb",
    "ruoka/HRank_ruoka.ipynb",
    "ruoka/DRank_ruoka.ipynb",
    "herald/HRank_herald.ipynb",
    "herald/DRank_herald.ipynb",
]


def run_notebook(notebook_path):
    """Execute a Jupyter notebook using nbconvert."""
    print(f"\n{'='*80}")
    print(f"Running: {notebook_path}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        # Execute notebook in-place
        result = subprocess.run(
            [
                "jupyter", "nbconvert",
                "--to", "notebook",
                "--execute",
                "--inplace",
                "--ExecutePreprocessor.timeout=600",  # 10 minute timeout per cell
                str(notebook_path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        elapsed = time.time() - start_time
        print(f"✓ SUCCESS ({elapsed:.1f}s): {notebook_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"✗ FAILED ({elapsed:.1f}s): {notebook_path}")
        print(f"Error: {e.stderr}")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"✗ ERROR ({elapsed:.1f}s): {notebook_path}")
        print(f"Error: {str(e)}")
        return False


def main():
    print("="*80)
    print("Keyword Extraction Batch Processor")
    print("="*80)
    print(f"Base directory: {BASE_DIR}")
    print(f"Total notebooks: {len(NOTEBOOKS)}")
    
    # Check if jupyter is available
    try:
        subprocess.run(["jupyter", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n✗ ERROR: Jupyter not found. Install with: pip install jupyter nbconvert")
        sys.exit(1)
    
    # Verify all notebooks exist
    missing = []
    for nb in NOTEBOOKS:
        nb_path = BASE_DIR / nb
        if not nb_path.exists():
            missing.append(nb)
    
    if missing:
        print(f"\n✗ ERROR: {len(missing)} notebook(s) not found:")
        for nb in missing:
            print(f"  - {nb}")
        sys.exit(1)
    
    print("\nAll notebooks found. Starting execution...\n")
    
    # Run all notebooks
    results = {}
    start_time = time.time()
    
    for notebook in NOTEBOOKS:
        nb_path = BASE_DIR / notebook
        success = run_notebook(nb_path)
        results[notebook] = success
    
    total_time = time.time() - start_time
    
    # Print summary
    print("\n" + "="*80)
    print("EXECUTION SUMMARY")
    print("="*80)
    
    successful = sum(1 for v in results.values() if v)
    failed = len(results) - successful
    
    print(f"\nTotal notebooks: {len(results)}")
    print(f"✓ Successful: {successful}")
    print(f"✗ Failed: {failed}")
    print(f"Total time: {total_time/60:.1f} minutes")
    
    if failed > 0:
        print("\nFailed notebooks:")
        for nb, success in results.items():
            if not success:
                print(f"  - {nb}")
    
    print(f"\nResults saved to: {BASE_DIR / 'Results' / 'results.csv'}")
    print(f"Visualizations saved to: {BASE_DIR / 'Results' / '*.png'}")
    
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
