import urllib.request
from bs4 import BeautifulSoup
import re
import nltk
from nltk.corpus import stopwords
from collections import Counter

# Ladataan tarvittavat NLTK-tiedot
try:
    stopwords.words("english")
except LookupError:
    nltk.download("stopwords")

# --- KONFIGURAATIO ---
BASE = "https://cs.uef.fi/~himat/WebRank/dataset_12/dataset_12/herald"
COMMON_NOISE_WORDS = set("""
january debt est dec big than who use jun jan feb mar apr may jul agust dec oct nov sep dec
product continue one two three four five please thanks find helpful week job experience 
""".split())

# --- DRANK-ALGORITMI ---

def get_top_keywords(url, k=10):
    try:
        # Haetaan sivu
        req = urllib.request.Request(url, headers={'User-Agent': 'KeywordScraper/1.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read()
            soup = BeautifulSoup(html, 'lxml')
        
        # Tekstin puhdistus ja tokenisointi
        raw_text = soup.get_text()
        stopword_list = set(stopwords.words("english"))
        words = [w.lower() for w in re.findall(r'\w+', raw_text) 
                 if len(w) > 1 and w.lower() not in stopword_list and w.lower() not in COMMON_NOISE_WORDS]
        
        # Pisteytys (TF + Tag-painotus)
        freq = Counter(words)
        total_tokens = len(words)
        word_info = {}
        
        # Painotukset Project 1 -analyysin perusteella
        tag_weights = {
            'title': 4, 'h1': 6, 'h2': 5, 'h3': 4, 
            'h4': 3, 'h5': 2, 'h6': 2, 'a': 5
        }

        for w, count in freq.items():
            # TF-pisteet
            base = (count / 100.0) * (50 if total_tokens < 50 else 20)
            
            # Tag-lisäpisteet
            boost = 0
            for tag, weight in tag_weights.items():
                if any(w in el.get_text().lower() for el in soup.find_all(tag)):
                    boost += weight
            
            word_info[w] = base + boost

        # Lajitellaan ja palautetaan parhaat
        top = sorted(word_info.items(), key=lambda x: x[1], reverse=True)[:k]
        return [w for w, score in top]
    except:
        return []

# --- EVALUOINTI ---

def calculate_metrics(ground_truth, keywords):
    matches = [word for word in ground_truth if word in keywords]
    
    gt_count = len(ground_truth)
    kw_count = len(keywords)
    match_count = len(matches)
    
    if gt_count == 0 or kw_count == 0:
        return (0, 0, 0)
        
    precision = match_count / kw_count
    recall = match_count / gt_count
    
    if precision + recall == 0:
        return (0, 0, 0)
        
    f_score = (2 * precision * recall) / (precision + recall)
    return precision, recall, f_score

def read_url(url):
    with urllib.request.urlopen(url) as f:
        return f.read().decode("utf-8-sig").strip()

def run_evaluation(total_pages=10):
    p_sum, r_sum, f_sum = 0.0, 0.0, 0.0
    
    print(f"--- Evaluoidaan {total_pages} sivua Herald-aineistosta ---")
    
    for i in range(total_pages):
        base_path = f"{BASE}/{i}"
        try:
            target_url = read_url(f"{base_path}/URL.txt")
            gt_keywords = read_url(f"{base_path}/GT.txt").lower().split()
            
            predicted = get_top_keywords(target_url)
            p, r, f = calculate_metrics(gt_keywords, predicted)
            
            p_sum += p
            r_sum += r
            f_sum += f
            print(f"Sivu {i}: Precision={p:.2f}, Recall={r:.2f}, F1={f:.2f}")
        except:
            continue

    # Lasketaan keskiarvot
    avg_p = round(p_sum / total_pages, 2)
    avg_r = round(r_sum / total_pages, 2)
    avg_f = round(f_sum / total_pages, 2)
    
    print("\n=== KESKIARVOT KAIKISTA SIVUISTA ===")
    print(f"Average Precision: {avg_p}")
    print(f"Average Recall: {avg_r}")
    print(f"Average F-score: {avg_f}")

if __name__ == "__main__":
    run_evaluation(10)