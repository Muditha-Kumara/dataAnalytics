# Import Required Libraries
import os
from bs4 import BeautifulSoup
from collections import Counter

# Project configuration
DATASETS_ROOT = "dataSets"  # dataSets dir
TARGET_TAGS = ["title", "h1", "h2", "h3", "h4", "p", "a", "strong", "b", "em"]

def get_html_files(dataset_dir):
    """Recursively find .htm/.html files in all subdirectories."""
    html_files = []
    for root, dirs, files in os.walk(dataset_dir):
        for file in files:
            if file.endswith(".htm") or file.endswith(".html"):
                html_files.append(os.path.join(root, file))
    return html_files

def extract_keywords_from_meta(soup):
    """Extract ground truth keywords from meta tags."""
    gt_keywords = []
    # Extract from <meta name="keywords"> and <meta name="news_keywords">
    meta_tags = soup.find_all("meta", attrs={"name": True})
    for meta in meta_tags:
        name = meta.get("name", "").lower()
        if name in ["keywords", "news_keywords"] and meta.get("content"):
            gt_keywords += [k.strip().lower() for k in meta["content"].split(",")]
    # Extract from <meta property="article:tag" content="...">
    property_tags = soup.find_all("meta", attrs={"property": True})
    for meta in property_tags:
        prop = meta.get("property", "").lower()
        if prop == "article:tag" and meta.get("content"):
            gt_keywords.append(meta["content"].strip().lower())
    # Remove duplicates
    return list(set(gt_keywords))

def analyze_html_file(file_path, target_tags):
    """Analyze a single HTML file for keyword occurrences in target tags."""
    tag_counts = Counter()
    total_keywords_found = 0
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "lxml")
    gt_keywords = extract_keywords_from_meta(soup)
    if not gt_keywords:
        return tag_counts, total_keywords_found
    for tag_name in target_tags:
        elements = soup.find_all(tag_name)
        for el in elements:
            text = el.get_text().lower()
            for word in gt_keywords:
                if word in text:
                    tag_counts[tag_name] += 1
                    total_keywords_found += 1
    return tag_counts, total_keywords_found

def analyze_local_dataset(dataset_dir):
    """Analyze all HTML files in a dataset directory."""
    tag_counts = Counter()
    total_keywords_found = 0
    html_files = get_html_files(dataset_dir)
    print(f"Analyzing {len(html_files)} files in {dataset_dir}...")
    for file_path in html_files:
        file_counts, file_total = analyze_html_file(file_path, TARGET_TAGS)
        tag_counts.update(file_counts)
        total_keywords_found += file_total
    return tag_counts, total_keywords_found

def generate_report(counts, total, dataset_name):
    """Produces the ranked list and importance scores for Project 1."""
    print(f"\n===== Report for dataset: {dataset_name} =====")
    print(f"{'HTML Tag':<15} | {'Occurrences':<12} | {'Percentage':<12} | {'Importance Score':<12}")
    print("-" * 75)
    sorted_tags = counts.most_common(10)
    if not sorted_tags:
        print("No keywords found. Check if meta tags exist in the HTML.")
        return
    max_occ = sorted_tags[0][1]
    for tag, occ in sorted_tags:
        percentage = (occ / total) * 100 if total > 0 else 0
        importance_score = round(occ / max_occ, 2)
        print(f"<{tag}>{' ':<10} | {occ:<12} | {percentage:>10.2f}% | {importance_score:>15.2f}")

# Example usage (run step by step):
# 1. html_files = get_html_files(DATASETS_ROOT)
# 2. tag_counts, total_keywords_found = analyze_local_dataset(DATASETS_ROOT)
# 3. generate_report(tag_counts, total_keywords_found, DATASETS_ROOT)
