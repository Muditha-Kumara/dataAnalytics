import os
from bs4 import BeautifulSoup
from collections import Counter


# Configuration
DATASETS_ROOT = "dataSets"  # New root directory for all datasets
TARGET_TAGS = ["title", "h1", "h2", "h3", "h4", "p", "a", "strong", "b", "em"]



def analyze_local_dataset(dataset_dir):
    tag_counts = Counter()
    total_keywords_found = 0

    # Recursively find .htm/.html files in all subdirectories
    html_files = []
    for root, dirs, files in os.walk(dataset_dir):
        for file in files:
            if file.endswith(".htm") or file.endswith(".html"):
                html_files.append(os.path.join(root, file))

    print(f"Analyzing {len(html_files)} files in {dataset_dir}...")

    for file_path in html_files:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "lxml")

        # 1. Extract Ground Truth from Meta Tags
        # Common newspaper format: <meta name="keywords" content="word1, word2">
        gt_keywords = []
        # Find all meta tags with a name attribute
        meta_tags = soup.find_all("meta", attrs={"name": True})
        for meta in meta_tags:
            name = meta.get("name", "").lower()
            if name in ["keywords", "news_keywords"] and meta.get("content"):
                gt_keywords += [k.strip().lower() for k in meta["content"].split(",")]

        # Remove duplicates
        gt_keywords = list(set(gt_keywords))
        if not gt_keywords:
            continue

        # 2. Analyze occurrences in HTML elements [cite: 251, 258]
        for tag_name in TARGET_TAGS:
            elements = soup.find_all(tag_name)
            for el in elements:
                text = el.get_text().lower()
                for word in gt_keywords:
                    # Simple check if the keyword appears in the tag text
                    if word in text:
                        tag_counts[tag_name] += 1
                        total_keywords_found += 1

    return tag_counts, total_keywords_found



def generate_report(counts, total, dataset_name):
    """Produces the ranked list and importance scores for Project 1[cite: 283, 285]."""
    print(f"\n===== Report for dataset: {dataset_name} =====")
    print(f"{'HTML Tag':<15} | {'Occurrences':<12} | {'Percentage':<12} | {'Importance Score':<12}")
    print("-" * 75)

    # Ranking HTML tags by importance [cite: 253]
    sorted_tags = counts.most_common(10)
    if not sorted_tags:
        print("No keywords found. Check if meta tags exist in the HTML.")
        return

    max_occ = sorted_tags[0][1]

    for tag, occ in sorted_tags:
        percentage = (occ / total) * 100 if total > 0 else 0
        importance_score = round(occ / max_occ, 2)  # Normalized [cite: 289]
        print(f"<{tag}>{' ':<10} | {occ:<12} | {percentage:>10.2f}% | {importance_score:>15.2f}")



# Execute: Analyze all datasets in the root directory and generate separate reports
if __name__ == "__main__":
    if not os.path.isdir(DATASETS_ROOT):
        print(f"Datasets root directory '{DATASETS_ROOT}' not found.")
    else:
        for dataset_name in os.listdir(DATASETS_ROOT):
            dataset_path = os.path.join(DATASETS_ROOT, dataset_name)
            if os.path.isdir(dataset_path):
                stats, total_found = analyze_local_dataset(dataset_path)
                generate_report(stats, total_found, dataset_name)
