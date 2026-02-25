import re
import urllib.request
from collections import Counter
from bs4 import BeautifulSoup
from bs4.element import Comment

import nltk
from nltk.corpus import stopwords, wordnet as wn
from nltk.stem import WordNetLemmatizer
from sklearn.cluster import AgglomerativeClustering

# ----------------------------
# 0) NLTK downloads (once)
# ----------------------------
nltk.download("punkt", quiet=True)
nltk.download("averaged_perceptron_tagger", quiet=True)
nltk.download("stopwords", quiet=True)
nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)

# ----------------------------
# 1) Dataset config
# ----------------------------
BASE = "https://cs.uef.fi/~himat/WebRank/dataset_12/dataset_12/herald"

# ----------------------------
# 2) Fetch helpers
# ----------------------------
def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as con:
        return con.read().decode("utf-8", errors="replace")

def read_doc_meta(doc_id: int):
    page_url = fetch_text(f"{BASE}/{doc_id}/URL.txt").strip()
    gt_txt = fetch_text(f"{BASE}/{doc_id}/GT.txt")
    # split robustly
    raw = re.split(r"[,\n;]+", gt_txt)
    gt_phrases = [w.strip() for w in raw if w.strip()]
    return page_url, gt_phrases

def fetch_html_from_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as con:
        return con.read().decode("utf-8", errors="replace")

# ----------------------------
# 3) HTML -> visible text
# ----------------------------
BLOCK_TAGS = {"style", "script", "head", "title", "meta", "noscript", "svg"}

def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    texts = soup.find_all(string=True)
    visible = []
    for t in texts:
        if isinstance(t, Comment):
            continue
        parent = t.parent.name.lower() if (t.parent and t.parent.name) else ""
        if parent in BLOCK_TAGS:
            continue
        s = t.strip()
        if s:
            visible.append(s)
    text = " ".join(visible)
    return re.sub(r"\s+", " ", text).strip()

# ----------------------------
# 4) Normalization utilities (CRITICAL)
# ----------------------------
ENG_STOP = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()

SITE_NOISE = {
    "home","menu","search","show","hide","view","back","next","previous","copyright",
    "facebook","instagram","linkedin","tiktok","youtube","twitter","x",
    "arrowdown","arrowup","arrowleft","arrowright","hamburger","openinnewtab",
    "squarefacebook","squareinstagram","squarelinkedin","squaretwitter","squarextwitter","squareyoutube",
    "bookmark","bookmarkfilled","threedots","thumbup","thumbdown","visibility","visibilityoff",
}

def normalize_text(s: str) -> str:
    """
    lower + unify hyphen/apostrophe + remove extra punctuation but keep spaces
    """
    s = s.lower()
    s = s.replace("’", "'")
    # keep hyphens as space (important!)
    s = re.sub(r"[-_/]", " ", s)
    # remove punctuation except spaces
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def tokenize_words(s: str):
    s = normalize_text(s)
    toks = s.split()
    # light filtering
    out = []
    for t in toks:
        if len(t) < 3:
            continue
        if t in ENG_STOP or t in SITE_NOISE:
            continue
        if t.isdigit():
            continue
        out.append(t)
    return out

# ----------------------------
# 5) HRANK keyword extraction (unigram + phrase extension)
# ----------------------------
def pos_separate(tokens):
    tagged = nltk.pos_tag(tokens)
    nouns, adjs, verbs = [], [], []
    for w, t in tagged:
        if t.startswith("NN"):
            nouns.append(w)
        elif t.startswith("JJ"):
            adjs.append(w)
        elif t.startswith("VB"):
            verbs.append(w)
    return nouns, adjs, verbs

def lemmatize_words(words):
    return [lemmatizer.lemmatize(w) for w in words]

def compute_similarity_matrix(words):
    syn_cache = {w: wn.synsets(w) for w in words}
    mat = []
    for w1 in words:
        row = []
        syn1 = syn_cache[w1]
        for w2 in words:
            syn2 = syn_cache[w2]
            if not syn1 or not syn2:
                row.append(1.0)
                continue
            sim = syn1[0].wup_similarity(syn2[0])
            row.append(1.0 - (sim if sim is not None else 0.0))
        mat.append(row)
    return mat

def cluster_keywords(freq_counter: Counter, top_n_vocab=150, num_clusters=8):
    top_words = [w for w, _ in freq_counter.most_common(top_n_vocab)]
    if len(top_words) < max(2, num_clusters):
        return top_words

    dist = compute_similarity_matrix(top_words)
    labels = AgglomerativeClustering(n_clusters=num_clusters, metric="precomputed", linkage="complete").fit_predict(dist)

    clusters = {i: [] for i in range(num_clusters)}
    for i, lab in enumerate(labels):
        clusters[lab].append(top_words[i])

    reps = []
    for lab, ws in clusters.items():
        ws.sort(key=lambda w: freq_counter[w], reverse=True)
        reps.append(ws[0])

    # unique preserve
    seen, out = set(), []
    for w in reps:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out

def hrank_extract_keywords(visible_text: str, top_k=10):
    tokens = tokenize_words(visible_text)
    if not tokens:
        return []

    nouns, adjs, verbs = pos_separate(tokens)
    nouns = lemmatize_words(nouns)
    nouns = [w for w in nouns if len(w) >= 3 and w not in ENG_STOP and w not in SITE_NOISE and w.isalpha()]
    if not nouns:
        return []

    freq = Counter(nouns)
    base = cluster_keywords(freq, top_n_vocab=150, num_clusters=8)

    # Optional: also add frequent bigrams from the text (helps match GT phrases)
    bigrams = Counter(zip(tokens, tokens[1:]))
    bigram_phrases = [" ".join(bg) for bg, c in bigrams.most_common(20) if c >= 2]

    combined = base + bigram_phrases

    # unique + top_k
    seen, out = set(), []
    for w in combined:
        w = normalize_text(w)
        if not w:
            continue
        if w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) >= top_k:
            break
    return out

# ----------------------------
# 6) Evaluation (token-based to avoid "all zero")
# ----------------------------
def gt_to_token_set(gt_phrases):
    tokens = []
    for phrase in gt_phrases:
        tokens.extend(tokenize_words(phrase))
    return set(tokens)

def pred_to_token_set(pred_keywords):
    tokens = []
    for kw in pred_keywords:
        tokens.extend(tokenize_words(kw))
    return set(tokens)

def prf(pred: set[str], gt: set[str]):
    tp = len(pred & gt)
    fp = len(pred - gt)
    fn = len(gt - pred)
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = (2*p*r/(p+r)) if (p+r) else 0.0
    return p, r, f

# ----------------------------
# 7) Run
# ----------------------------
def run_herald(doc_ids=range(0, 20), top_k=10, debug_first=True):
    rows = []
    for doc_id in doc_ids:
        try:
            page_url, gt_phrases = read_doc_meta(doc_id)
            html = fetch_html_from_url(page_url)
            text = extract_visible_text(html)

            pred_keywords = hrank_extract_keywords(text, top_k=top_k)

            gt_tokens = gt_to_token_set(gt_phrases)
            pred_tokens = pred_to_token_set(pred_keywords)

            p, r, f = prf(pred_tokens, gt_tokens)

            if debug_first and doc_id == list(doc_ids)[0]:
                print("---- DEBUG (first doc) ----")
                print("URL:", page_url)
                print("GT phrases (sample):", gt_phrases[:10])
                print("GT tokens (sample):", list(gt_tokens)[:20])
                print("Pred keywords:", pred_keywords)
                print("Pred tokens:", list(pred_tokens)[:20])
                print("---------------------------")

            rows.append((doc_id, p, r, f))
        except Exception as e:
            rows.append((doc_id, 0.0, 0.0, 0.0))
            print(f"[ERROR] doc {doc_id}: {e}")

    avg_p = sum(x[1] for x in rows) / len(rows)
    avg_r = sum(x[2] for x in rows) / len(rows)
    avg_f = sum(x[3] for x in rows) / len(rows)

    print(f"Docs: {len(rows)}")
    print(f"AVG Precision={avg_p:.4f}, Recall={avg_r:.4f}, F1={avg_f:.4f}")

if __name__ == "__main__":
    run_herald(doc_ids=range(0, 20), top_k=10, debug_first=True)