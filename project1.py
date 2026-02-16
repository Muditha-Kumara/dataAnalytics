import os
import re
from bs4 import BeautifulSoup
from collections import Counter

# Project Configuration
DATASETS_ROOT = "dataSets"
# Required tags per Project 1 specifications [cite: 14-22]
TARGET_TAGS = ["title", "h1", "h2", "h3", "h4", "p", "a", "strong", "b", "em"]


def get_ground_truth(soup):
    """Extracts keywords from meta tags as per newspaper dataset structure[cite: 147, 148]."""
    gt_keywords = set()

    # Extract from standard meta keywords and news_keywords [cite: 20]
    meta_tags = soup.find_all("meta", attrs={"name": True})
    for meta in meta_tags:
        name = meta.get("name", "").lower()
        if name in ["keywords", "news_keywords"] and meta.get("content"):
            keywords = [k.strip().lower() for k in meta["content"].split(",")]
            gt_keywords.update(keywords)

    # Extract from OpenGraph article tags
    property_tags = soup.find_all("meta", attrs={"property": True})
    for meta in property_tags:
        prop = meta.get("property", "").lower()
        if prop == "article:tag" and meta.get("content"):
            gt_keywords.add(meta["content"].strip().lower())

    return list(gt_keywords)


def analyze_local_dataset(dataset_dir):
    tag_counts = Counter()
    total_keywords_found = 0

    # Locate all HTML files
    html_files = []
    for root, _, files in os.walk(dataset_dir):
        for file in files:
            if file.lower().endswith((".htm", ".html")):
                html_files.append(os.path.join(root, file))

    print(f"Analyzing {len(html_files)} files in {dataset_dir}...")

    for file_path in html_files:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "lxml")
        except Exception:
            continue

        gt_keywords = get_ground_truth(soup)
        if not gt_keywords:
            continue

        # 1. Analyze Standard HTML Tags [cite: 15-21]
        for tag_name in TARGET_TAGS:
            elements = soup.find_all(tag_name)
            for el in elements:
                text = el.get_text().lower()
                for kw in gt_keywords:
                    # Use Regex for whole-word matching to avoid partial hits
                    if re.search(rf"\b{re.escape(kw)}\b", text):
                        tag_counts[tag_name] += 1
                        total_keywords_found += 1

        # 2. Analyze URL Components
        # Checks if ground-truth words appear in the file path/URL string
        path_text = file_path.lower()
        for kw in gt_keywords:
            if kw in path_text:
                tag_counts["URL path"] += 1
                total_keywords_found += 1

    return tag_counts, total_keywords_found


def generate_report(counts, total, dataset_name):
    """Produces the ranked list and importance scores[cite: 37, 41]."""
    print(f"\n===== REPORT: {dataset_name} =====")
    print(
        f"{'HTML Tag':<15} | {'Occurrences':<12} | {'Percentage':<12} | {'Importance Score':<12}"
    )
    print("-" * 75)

    # Ranking top 10 tags by frequency [cite: 39]
    sorted_tags = counts.most_common(10)
    if not sorted_tags:
        print("No keyword occurrences found in the analyzed tags.")
        return

    # Normalization: highest occurrence gets 1.0 [cite: 45, 50]
    max_occ = sorted_tags[0][1]

    for tag, occ in sorted_tags:
        percentage = (occ / total) * 100 if total > 0 else 0
        importance_score = round(occ / max_occ, 2)

        tag_display = f"<{tag}>" if tag != "URL path" else tag
        print(
            f"{tag_display:<15} | {occ:<12} | {percentage:>10.2f}% | {importance_score:>15.2f}"
        )


if __name__ == "__main__":
    if not os.path.isdir(DATASETS_ROOT):
        print(f"Error: Datasets folder '{DATASETS_ROOT}' not found.")
    else:
        # The project requires analyzing at least 5 datasets [cite: 7, 33]
        datasets = [
            d
            for d in os.listdir(DATASETS_ROOT)
            if os.path.isdir(os.path.join(DATASETS_ROOT, d))
        ]

        for dataset_name in datasets:
            path = os.path.join(DATASETS_ROOT, dataset_name)
            stats, total_found = analyze_local_dataset(path)
            generate_report(stats, total_found, dataset_name)
