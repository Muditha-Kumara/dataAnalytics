# Batch Notebook Execution Scripts

Two scripts are provided to run all keyword extraction notebooks automatically:

## Option 1: Python Script (Recommended)

```bash
python run_all_notebooks.py
```

Or directly:
```bash
./run_all_notebooks.py
```

**Features:**
- Detailed progress tracking
- Execution time reporting
- Error handling with summary
- Runs all 10 notebooks in sequence

## Option 2: Bash Script

```bash
./run_all_notebooks.sh
```

**Features:**
- Simple and lightweight
- Works on any Linux/MacOS system
- Auto-activates virtual environment if present

## Requirements

Make sure you have Jupyter and nbconvert installed:

```bash
pip install jupyter nbconvert
```

## What Gets Executed

The scripts run these notebooks in order:

1. `toFinalReport/german/HRank_german.ipynb`
2. `toFinalReport/german/DRank_german.ipynb`
3. `toFinalReport/indianexpress/HRank_Indian.ipynb`
4. `toFinalReport/indianexpress/DRank_Indian.ipynb`
5. `toFinalReport/Kotiliesi/HRank_ruoka.ipynb`
6. `toFinalReport/Kotiliesi/DRank_Kotiliesi.ipynb`
7. `toFinalReport/ruoka/HRank_ruoka.ipynb`
8. `toFinalReport/ruoka/DRank_ruoka.ipynb`
9. `toFinalReport/herald/HRank_herald.ipynb`
10. `toFinalReport/herald/DRank_herald.ipynb`

## Output

- **Consolidated results:** `toFinalReport/Results/results.csv`
- **Visualizations:** `toFinalReport/Results/*.png`
- **Updated notebooks:** Executed in-place with outputs saved

## Timeout Settings

- Default timeout: **10 minutes per cell**
- Adjust in script if needed for slower connections

## Troubleshooting

**If you get "jupyter: command not found":**
```bash
pip install jupyter nbconvert
```

**If notebooks fail to execute:**
- Check that all required packages are installed (see requirements.txt)
- Ensure spaCy models are downloaded (de_core_news_sm, fi_core_news_sm)
- Verify internet connection for downloading dataset URLs

**To run a single dataset:**
```bash
jupyter nbconvert --to notebook --execute --inplace toFinalReport/german/DRank_german.ipynb
```
