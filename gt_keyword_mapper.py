import re
import urllib.request
from bs4 import BeautifulSoup, Comment
from collections import defaultdict
import nltk
from nltk.stem.snowball import SnowballStemmer
import matplotlib.pyplot as plt
import json

# Ensure NLTK data is available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    SnowballStemmer('finnish')
except:
    nltk.download('snowball_data')


# --- Normalization and Text Extraction ---

def _normalize_finnish_word(word):
    """Normalize Finnish words using stemming."""
    word = word.lower()
    try:
        stemmer = SnowballStemmer('finnish')
        return stemmer.stem(word)
    except Exception as e:
        print(f"Could not stem word: {word}. Error: {e}")
        return word

def _is_visible_text(element) -> bool:
    """Filter for visible text elements in BeautifulSoup."""
    if element.parent.name in ["style", "script", "head", "title", "meta", "[document]"]:
        return False
    if isinstance(element, Comment):
        return False
    return True

# --- Data Loading ---

def read_url_content(url):
    """Read content from a URL."""
    try:
        with urllib.request.urlopen(url) as f:
            return f.read()
    except Exception as e:
        print(f"Failed to read URL {url}: {e}")
        return None

def load_ruoka_case(index):
    """Load a test case from the online ruoka dataset."""
    base_url = f"https://cs.uef.fi/~himat/WebRank/dataset_12/dataset_12/ruoka/{index}"
    
    # URL to the stored HTML content
    html_content_url = f"{base_url}/"
    
    # URL to the ground truth keywords
    gt_url = f"{base_url}/GT.txt"
    
    # Read ground truth keywords
    gt_content = read_url_content(gt_url)
    if gt_content:
        gt_text = gt_content.decode("utf-8-sig").strip()
        gt_tokens = gt_text.lower().split()
        gt_stemmed = [_normalize_finnish_word(token) for token in gt_tokens]
    else:
        gt_stemmed = []

    # Read HTML content
    html_content = read_url_content(html_content_url)

    return html_content, gt_stemmed, base_url

# --- Keyword Mapping ---

def find_keyword_locations(soup, keyword):
    """Find all occurrences of a keyword and their parent tags."""
    locations = []
    # Search for the keyword in all visible text nodes
    text_nodes = soup.find_all(string=re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE))
    
    for node in text_nodes:
        if _is_visible_text(node):
            parent = node.parent
            parent_info = f"<{parent.name}>"
            # You could add more parent attributes here if needed
            # e.g., parent.get('class') or parent.get('id')
            locations.append(parent_info)
            
    return locations

def map_gt_keywords_in_html(html_content, gt_keywords):
    """Map the locations of ground truth keywords in the HTML."""
    if not html_content or not gt_keywords:
        return {}

    soup = BeautifulSoup(html_content, "lxml")
    keyword_locations = defaultdict(lambda: defaultdict(int))

    # We need to search for the original form of the word in the text,
    # but we match it to the stemmed GT keyword.
    # This is a simplification. A more robust way would be to stem the whole text.
    # For now, we'll iterate through all text and check if its stemmed form is a GT keyword.
    
    all_text = soup.find_all(string=True)
    
    for text_element in all_text:
        if not _is_visible_text(text_element):
            continue
            
        words_in_element = re.findall(r'\b\w+\b', text_element.lower())
        
        for word in words_in_element:
            stemmed_word = _normalize_finnish_word(word)
            if stemmed_word in gt_keywords:
                parent_tag = text_element.parent.name
                keyword_locations[stemmed_word][parent_tag] += 1
                
    return keyword_locations


# --- Main Execution ---

def main():
    """Main function to process the dataset and report keyword locations."""
    total_webpages = 100
    all_page_results = []
    gt_found_counts = []
    gt_given_counts = []
    gt_not_found_counts = []

    print(f"Analyzing {total_webpages} webpages from the dataset...")
    print("-" * 50)

    for i in range(total_webpages):
        html_content, gt_keywords, page_url = load_ruoka_case(str(i))
        
        num_given_gt = len(gt_keywords)
        gt_given_counts.append(num_given_gt)

        page_result = {
            "page_index": i,
            "url": page_url,
            "gt_keywords_stemmed": gt_keywords,
            "keyword_locations": {}
        }

        if not html_content:
            print(f"\nSkipping page {i} due to loading error.")
            all_page_results.append(page_result)
            gt_found_counts.append(0)
            gt_not_found_counts.append(num_given_gt)
            continue

        print(f"\n--- Processing Page {i}: {page_url} ---")
        print(f"Ground Truth Keywords (stemmed): {gt_keywords}")

        locations = map_gt_keywords_in_html(html_content, gt_keywords)
        page_result["keyword_locations"] = locations

        total_gt_found = sum(sum(tags.values()) for tags in locations.values())
        gt_found_counts.append(total_gt_found)

        num_gt_not_found = num_given_gt - len(locations)
        gt_not_found_counts.append(num_gt_not_found)

        if not locations:
            print("No ground truth keywords found on this page.")
        else:
            print("Keyword Locations:")
            for keyword, tags in locations.items():
                tag_counts = ", ".join([f"{tag}: {count}" for tag, count in tags.items()])
                print(f"  - '{keyword}': found in {tag_counts}")
        
        all_page_results.append(page_result)

    print("-" * 50)
    
    # --- Save results to JSON ---
    output_filename = "gt_keyword_analysis.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_page_results, f, ensure_ascii=False, indent=4)
    print(f"Detailed analysis saved to {output_filename}")

    # --- Generate and save the graph ---
    x = range(total_webpages)
    width = 0.25

    fig, ax = plt.subplots(figsize=(20, 7))
    rects1 = ax.bar([i - width for i in x], gt_given_counts, width, label='Given GT', color='dodgerblue')
    rects2 = ax.bar(x, gt_found_counts, width, label='Found GT', color='skyblue')
    rects3 = ax.bar([i + width for i in x], gt_not_found_counts, width, label='Not Found GT', color='lightcoral')


    ax.set_ylabel('Keyword Count')
    ax.set_title('Comparison of Given, Found, and Not Found Ground Truth Keywords per Page')
    ax.set_xlabel('Page Index')
    ax.set_xticks(x)
    ax.tick_params(axis='x', rotation=90)
    ax.legend()
    ax.grid(axis='y', linestyle='--')

    fig.tight_layout()
    
    graph_filename = "gt_keyword_summary.png"
    plt.savefig(graph_filename)
    print(f"Summary graph saved to {graph_filename}")
    
    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()
