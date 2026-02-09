import urllib.request
from bs4 import BeautifulSoup
from collections import Counter

# Configuration from project requirements
BASE_URL = "https://cs.uef.fi/~himat/WebRank/dataset_12/dataset_12/herald"
TARGET_TAGS = ['title', 'h1', 'h2', 'h3', 'h4', 'p', 'a', 'strong', 'b', 'em']
TOTAL_PAGES = 10  # Can be adjusted based on dataset size

def fetch_data(url):
    """Utility to read text from the dataset URLs."""
    try:
        with urllib.request.urlopen(url) as f:
            return f.read().decode("utf-8-sig").strip()
    except:
        return ""

def analyze_tag_frequencies(num_pages):
    tag_counts = Counter()
    total_keywords_found = 0

    for i in range(num_pages):
        # Load URL and Ground Truth (GT)
        page_dir = f"{BASE_URL}/{i}"
        target_url = fetch_data(f"{page_dir}/URL.txt")
        gt_keywords = fetch_data(f"{page_dir}/GT.txt").lower().split()
        
        if not target_url or not gt_keywords:
            continue

        # Fetch the actual HTML content of the page
        try:
            req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                soup = BeautifulSoup(response.read(), 'lxml')
        except:
            continue

        # Check each tag for keyword occurrences
        for tag_name in TARGET_TAGS:
            elements = soup.find_all(tag_name)
            for el in elements:
                text = el.get_text().lower()
                for word in gt_keywords:
                    if word in text:
                        tag_counts[tag_name] += 1
                        total_keywords_found += 1

    return tag_counts, total_keywords_found

def generate_report(counts, total):
    print(f"{'HTML Tag':<15} | {'Occurrences':<12} | {'Percentage':<12} | {'Score (0-1)':<12}")
    print("-" * 60)
    
    # Sort by frequency to find the "best places" [cite: 247, 283]
    sorted_tags = counts.most_common()
    if not sorted_tags:
        return

    max_occ = sorted_tags[0][1]
    
    for tag, occ in sorted_tags:
        percentage = (occ / total) * 100 if total > 0 else 0
        importance_score = occ / max_occ if max_occ > 0 else 0
        print(f"<{tag}> {'.'*8:<10} | {occ:<12} | {percentage:>10.2f}% | {importance_score:>10.2f}")

# Execute Analysis
print("Analyzing dataset for keyword locations...")
tag_stats, total_found = analyze_tag_frequencies(TOTAL_PAGES)
generate_report(tag_stats, total_found)