import re
import math
import urllib.request
import requests
import nltk
import tempfile
import os
from collections import Counter
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Comment
from nltk.corpus import stopwords


def get_top_keywords(url: str = None, html_path: str = None, k: int = 10):
    try:
        stopwords.words("finnish")
    except LookupError:
        nltk.download("stopwords")

    # Strict noise list: removing functional recipe verbs and measurement units
    STRICT_NOISE = set(
        """
        dl tl rkl kg g l m jan feb mar apr may jun jul aug sep oct nov dec
        tämä sivu haku ohje ainekset valmistus annosta minuuttia minuutti 
        uunissa asteessa lisää sekoita anna paista keitä tarjoile nauti
        reseptejä resepti arkisto kuva kommenttia vastaa lue lisää
        suosittelemme kokeile katso tästä sekä että mutta kuin
        leivonta ruokaohje reseptit vaiheet ainekset
    """.split()
    )

    def _stem(word: str) -> str:
        # Focused on the most common Finnish mutations in the Ruoka dataset
        suffixes = [
            "ssa",
            "ssä",
            "sta",
            "stä",
            "lle",
            "lla",
            "llä",
            "lta",
            "ltä",
            "ksi",
            "na",
            "nä",
            "n",
            "t",
        ]
        # Consonant gradation: handle k/v and t/d shifts (e.g., ruoan -> ruoka, vuoan -> vuoka)
        gradations = [
            ("ruoa", "ruoka"),
            ("leiwo", "leipä"),
            ("pöydä", "pöytä"),
            ("vuoa", "vuoka"),
        ]
        for s in suffixes:
            if len(word) > 4 and word.endswith(s):
                word = word[: -len(s)]
                break
        for s, r in gradations:
            if word.endswith(s):
                word = word.replace(s, r)
        return word

    # 1. Extraction & Cleaning
    if html_path:
        with open(html_path, "rb") as f:
            html_content = f.read()
    else:
        html_content = requests.get(url, timeout=10).content

    soup = BeautifulSoup(html_content, "lxml")

    # Isolate high-value zones before decomposing
    title_raw = soup.title.string if soup.title else ""
    h1_raw = " ".join([h.get_text() for h in soup.find_all("h1")])

    # Remove UI noise before full text extraction to improve Precision
    for tag in soup(["nav", "footer", "header", "script", "style", "aside", "form"]):
        tag.decompose()

    clean_text = soup.get_text(separator=" ").lower()

    # 2. Tokenization
    raw_tokens = re.sub(r"[^a-zäöå]+", " ", clean_text).split()
    sw = set(stopwords.words("finnish"))

    stemmed_pool = []
    for t in raw_tokens:
        if len(t) > 2 and t not in sw and t not in STRICT_NOISE:
            stemmed_pool.append(_stem(t))

    counts = Counter(stemmed_pool)

    # 3. Structural Analysis for Boosting
    header_text = (title_raw + " " + h1_raw).lower()
    header_stems = set(
        [
            _stem(t)
            for t in re.sub(r"[^a-zäöå]+", " ", header_text).split()
            if len(t) > 2
        ]
    )

    url_slug_stems = set()
    if url:
        path = urlparse(url).path.lower()
        url_slug_stems = set(
            [_stem(t) for t in re.split(r"[/._-]", path) if len(t) > 2]
        )

    # 4. Final Scoring Logic
    final_scores = {}
    total_tokens = len(stemmed_pool) if stemmed_pool else 1

    for word, count in counts.items():
        # Base: Relative frequency with log dampening to prevent "spam" words from winning
        freq_score = (count / total_tokens) * (1 + math.log(count))

        multiplier = 1.0

        # Massive boost for Header/Title presence (The "Golden Rule" for this dataset)
        if word in header_stems:
            multiplier += 25.0

        # Boost for URL presence
        if word in url_slug_stems:
            multiplier += 15.0

        # Decompounding boost: if the word is part of a longer word in the header
        # e.g., 'kana' is in 'kanapaprika'
        if any(word in h_word and word != h_word for h_word in header_stems):
            multiplier += 10.0

        # Precision Filter: Penalize words that appear ONLY in the body
        # but have very high frequency (likely process verbs not in STRICT_NOISE)
        if word not in header_stems and word not in url_slug_stems:
            if count > (
                total_tokens * 0.04
            ):  # If word is > 4% of text but not in title
                multiplier *= 0.3

        final_scores[word] = freq_score * multiplier

    # Sort and return top K
    top_k = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)[:k]
    return [w for w, s in top_k]


# --------------------- Evaluation Script ---------------------
BASE = "https://cs.uef.fi/~himat/WebRank/dataset_12/dataset_12/ruoka/"


def Get_Prc_Rcl_Fscr_input_GT_and_Keywords_List(ground_truth, keywords):
    matches = [word for word in keywords if word in ground_truth]
    match_count = len(matches)
    p = match_count / len(keywords) if keywords else 0
    r = match_count / len(set(ground_truth)) if ground_truth else 0
    f = (2 * p * r) / (p + r) if (p + r) > 0 else 0
    return (p, r, f)


def read_url(url):
    try:
        with urllib.request.urlopen(url) as f:
            return f.read().decode("utf-8-sig").strip()
    except:
        return ""


def load_ruoka_case(index):
    base = f"{BASE}{index}"
    gt_text = read_url(f"{base}/GT.txt")
    html_text = read_url(f"{base}/HTML.txt")

    def stem(w):
        w = re.sub(r"[^a-zäöå]+", "", w.lower())
        suffixes = ["ssa", "ssä", "sta", "stä", "n"]
        for s in suffixes:
            if len(w) > 4 and w.endswith(s):
                return w[: -len(s)]
        return w

    gt_tokens = [stem(w) for w in gt_text.replace(",", " ").split() if len(w) > 2]
    return html_text, gt_tokens


print("Starting Precision-Optimized Evaluation...")
p_sum, r_sum, f_sum, count = 0, 0, 0, 0
for i in range(100):
    html, gt = load_ruoka_case(i)
    if not html:
        continue

    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write(html.encode("utf-8"))
        t_path = f.name

    # Passing the URL is critical for the URL-Slug boost
    extracted = get_top_keywords(html_path=t_path, url=f"{BASE}{i}/")
    os.unlink(t_path)

    p, r, f = Get_Prc_Rcl_Fscr_input_GT_and_Keywords_List(gt, extracted)
    p_sum += p
    r_sum += r
    f_sum += f
    count += 1
    if i % 20 == 0:
        print(f"Progress: {i}%")

print(f"\nFINAL RESULTS:")
print(
    f"Precision: {round(p_sum/count, 2)} | Recall: {round(r_sum/count, 2)} | F-score: {round(f_sum/count, 2)}"
)
