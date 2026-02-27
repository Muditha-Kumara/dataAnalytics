# --- Cell 1: NLTK downloads ---
import nltk
nltk.download('punkt',                          quiet=True)
nltk.download('punkt_tab',                      quiet=True)
nltk.download('averaged_perceptron_tagger',     quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)
nltk.download('stopwords',                      quiet=True)
nltk.download('wordnet',                        quiet=True)
nltk.download('omw-1.4',                        quiet=True)

# --- Cell 2: Imports & Dataset config ---
import re
import urllib.request
from collections import Counter
from bs4 import BeautifulSoup
from bs4.element import Comment

from nltk.corpus import stopwords, wordnet as wn
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk import pos_tag
from sklearn.cluster import AgglomerativeClustering

BASE = "https://cs.uef.fi/~himat/WebRank/dataset_12/dataset_12/herald"


# =============================================================================
# Cell 3: Fetch helpers for herald dataset
# =============================================================================
def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as con:
        return con.read().decode("utf-8", errors="replace")


def read_doc_meta(doc_id: int):
    """Fetch URL.txt and GT.txt for a given document ID."""
    page_url   = fetch_text(f"{BASE}/{doc_id}/URL.txt").strip()
    gt_txt     = fetch_text(f"{BASE}/{doc_id}/GT.txt")
    raw        = re.split(r"[,\n;]+", gt_txt)
    gt_phrases = [w.strip() for w in raw if w.strip()]
    return page_url, gt_phrases


def Web_Scrapper_HTML(URL: str) -> str:
    """Fetch raw HTML (same function name as teacher)."""
    request = urllib.request.Request(URL, headers={"User-Agent": "Magic Browser"})
    with urllib.request.urlopen(request, timeout=15) as con:
        return con.read().decode("utf-8", errors="replace")


# =============================================================================
# Cell 4: HTML -> visible text
#         Improved: prioritise article/main, strip nav/footer
# =============================================================================
CONTENT_SELECTORS = [
    "article", "main", "[role='main']",
    ".article-body", ".article-content", ".post-content",
    ".entry-content", ".story-body", "#content", "#main-content"
]


def Web_scrapper_BeautifulSoup(URL: str) -> str:
    """Extract visible text, prioritising main article content."""
    Raw_HTML  = Web_Scrapper_HTML(URL)
    soup_html = BeautifulSoup(Raw_HTML, "lxml")

    # Try content selectors first
    main_parts = []
    for sel in CONTENT_SELECTORS:
        elements = soup_html.select(sel)
        if elements:
            for el in elements:
                main_parts.append(el.get_text(separator=" "))
            break

    if main_parts:
        Text = " ".join(main_parts)
    else:
        # Fallback: remove nav/footer/header then collect all remaining text
        for tag in soup_html.find_all(["nav", "footer", "header", "aside", "script", "style"]):
            tag.decompose()
        text         = soup_html.findAll(text=True)
        visible_text = []
        tag_names    = ["html", "style", "script", "head", "[document]", "img"]
        for element in text:
            if element.parent.name not in tag_names:
                if not isinstance(element, Comment):
                    visible_text.append(element.strip())
        Text = u" ".join(visible_text)

    text_lines = (line.strip() for line in Text.splitlines())
    chunks     = (phrase.strip() for line in text_lines for phrase in line.split(" "))
    return u" ".join(chunk for chunk in chunks if chunk)


# =============================================================================
# Cell 5: Preprocessing (same style as teacher, expanded noise list)
# =============================================================================
Special_Char_List = re.compile(
    r"`|~|!|@|\#|\$|\%|\^|\&|\*|\(|\)|\-|\_|\=|\+|\[|\]|\{|\}|\\|\||\;|\:|\\'|\"|,|\<|\.|\>|\?|\/"
)

eng_stopword_list = set(stopwords.words("english"))

common_nouns = (
    "gift debt free est dec big than who "
    "rss feed subscribe newsletter chatgpt openai desantis trending "
    "advertisement advertise sponsored cookie cookies privacy policy "
    "terms login signup signin register account profile "
    "share comment comments reply report flag like dislike follow "
    "related recommended popular latest breaking update updates live "
    "photo photos video videos gallery slideshow "
    "read more less expand collapse load loading error close "
    "open toggle dropdown sidebar widget banner popup modal "
    "edition network herald universityherald university "
    "print email save download upload send submit cancel reset "
    "skip content section page pages site website web "
    "click tap swipe scroll drag drop select choose pick "
    "arrowdown arrowup arrowleft arrowright hamburger openinnewtab "
    "squarefacebook squareinstagram squarelinkedin squaretwitter squarextwitter squareyoutube "
    "bookmark bookmarkfilled threedots thumbup thumbdown visibility visibilityoff "
    "facebook instagram linkedin tiktok youtube twitter "
    "home menu search show hide view back next previous copyright "
    "article articles htm html php asp aspx www http https com org net"
).split()


def preprocess_text(HTML_text, common_nouns, Special_Char_List, eng_stopword_list):
    """Tokenise and filter (same interface as teacher)."""
    tokens_list = []
    noise_set   = set(common_nouns)
    for token in HTML_text.split():
        token = token.lower().replace("'", "")
        token = Special_Char_List.sub("", token.strip())
        if (
            len(token) > 2 and
            token not in eng_stopword_list and
            token not in noise_set and
            not token.isdigit() and
            not token[0].isdigit()
        ):
            tokens_list.append(token)
    return tokens_list


# =============================================================================
# Cell 6: POS Separator (same interface as teacher)
# =============================================================================
adj_tags  = ["JJ", "JJR", "JJS"]
verb_tags = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]


def POS_Separator(candidate_words):
    """Separate tokens by POS. Proper nouns are stored separately for weighting."""
    nouns, adj, verb, proper_nouns = [], [], [], []
    tagged = pos_tag(candidate_words)
    for word, tag in tagged:
        if tag in ("NNP", "NNPS"):
            proper_nouns.append(word)
            nouns.append(word)       # also include in the general noun list
        elif tag in ("NN", "NNS"):
            nouns.append(word)
        elif tag in adj_tags:
            adj.append(word)
        elif tag in verb_tags:
            verb.append(word)
    return nouns, adj, verb, proper_nouns


# =============================================================================
# Cell 7: Lemmatization (same as teacher)
# =============================================================================
lemmatizer = WordNetLemmatizer()


def word_lemmatization(pos_tokens):
    return [lemmatizer.lemmatize(word) for word in pos_tokens]


# =============================================================================
# Cell 8: Clean keyword tokens
#         Improved: WordNet validation added to remove compound noise tokens,
#                   informal words, and abbreviations
# =============================================================================

# Custom allow-list for proper nouns not in WordNet (acronyms, place names, etc.)
KNOWN_PROPER = {
    "ncaa", "nfl", "nba", "nhl", "mlb", "ufc", "mma", "usc", "ucla",
    "gop", "cia", "fbi", "nasa", "osha", "epa", "cdc", "who",
    "iowa", "ohio", "penn", "duke", "yale", "mit", "nyu",
    "trump", "obama", "biden", "putin",
}


def is_real_word(word: str) -> bool:
    """
    Returns True if the word is in WordNet, in KNOWN_PROPER,
    or starts with a capital letter (likely a proper noun).
    Used to filter out compound tokens such as 'michiganann'.
    """
    if word in KNOWN_PROPER:
        return True
    if wn.synsets(word):
        return True
    # Tokens that are too long are likely concatenated compounds -> exclude
    if len(word) > 15:
        return False
    return False


def clean_keywords_tokens(words):
    site_stop = {
        "guardian", "news", "world", "search", "hide", "show", "menu", "view",
        "home", "back", "edition", "international", "latest", "today", "paper",
        "jobs", "subscriptions", "europe", "uk", "us", "americas", "asia",
        "australia", "africa", "middle", "east", "facebook", "instagram",
        "linkedin", "tiktok", "youtube", "dcr",
        "herald", "university", "universityherald", "rss", "subscribe",
        "chatgpt", "openai", "desantis", "newsletter", "advertisement",
        # Overly generic words that hurt precision
        "said", "say", "says", "year", "years", "time", "day", "week",
        "month", "people", "man", "woman", "one", "two", "three", "four",
        "five", "six", "seven", "eight", "nine", "ten", "new", "old",
        "good", "great", "first", "last", "make", "made", "take",
        # Informal / colloquial / abbreviation noise
        "thats", "dont", "cant", "wont", "isnt", "arent", "didnt",
        "youre", "theyre", "heres", "whats", "lets", "its",
        "osu", "unt", "dnt", "dat", "lol", "omg",
    }
    cleaned = []
    for w in words:
        w = w.lower()
        if len(w) < 3:
            continue
        if not w.isalpha():
            continue
        if w in site_stop:
            continue
        # Compound word check: longer than 12 chars, not in WordNet, not a known proper noun -> remove
        if len(w) > 12 and not wn.synsets(w) and w not in KNOWN_PROPER:
            continue
        cleaned.append(w)
    return cleaned


# =============================================================================
# Cell 9: WordNet synsets (same as teacher)
# =============================================================================
def Get_Synsets(candidate_words):
    words_with_synsets    = []
    words_without_synsets = []
    for word in candidate_words:
        if len(wn.synsets(word)) > 0:
            words_with_synsets.append(word)
        else:
            words_without_synsets.append(word)
    return words_with_synsets, words_without_synsets


# =============================================================================
# Cell 10: Similarity matrix & clustering (same as teacher)
# =============================================================================
def compute_similarity_matrix(words):
    similarity_matrix = []
    for word1 in words:
        synsets1 = wn.synsets(word1)
        if not synsets1:
            similarity_matrix.append([1.0] * len(words))
            continue
        row = []
        for word2 in words:
            synsets2 = wn.synsets(word2)
            if not synsets2:
                row.append(1.0)
                continue
            similarity = synsets1[0].wup_similarity(synsets2[0])
            row.append(1.0 - (similarity if similarity is not None else 0.0))
        similarity_matrix.append(row)
    return similarity_matrix


def compute_clustering(sim_mat, num_clusters):
    clustering_model = AgglomerativeClustering(
        n_clusters=num_clusters, metric="precomputed", linkage="complete"
    )
    return clustering_model.fit_predict(sim_mat)


# =============================================================================
# Cell 11: extract_keywords & get_clusters
# =============================================================================
def extract_keywords(cluster_labels, words, words_fr, num_clusters):
    clusters = {i: [] for i in range(num_clusters)}
    for i, label in enumerate(cluster_labels):
        clusters[label].append((words[i], words_fr.get(words[i], 0)))

    keywords = []
    max_fr   = max(words_fr.values()) if words_fr else 1
    for cluster in clusters.values():
        cluster.sort(key=lambda x: x[1], reverse=True)
        # Always take the top representative word of each cluster
        keywords.append(cluster[0][0])
        # Add secondary words only if frequency is high enough (strict threshold)
        for word, fr in cluster[1:]:
            if fr > 5 and fr > 0.3 * max_fr:
                keywords.append(word)
    return keywords


def get_clusters(words_fr, words, num_clusters=8):
    if len(words) < num_clusters:
        return words
    similarity_matrix = compute_similarity_matrix(words)
    cluster_labels    = compute_clustering(similarity_matrix, num_clusters)
    return extract_keywords(cluster_labels, words, words_fr, num_clusters)


def fr_adj_ver(lemma_words, N):
    return [word for word, _ in Counter(lemma_words).most_common(N)]


# =============================================================================
# Cell 12: Bigram helpers
# =============================================================================
stop_bigram = {
    "guardian", "live", "news", "world", "edition", "search",
    "back", "home", "top", "hide", "show", "view", "all", "stories",
    "most", "today", "herald", "university", "rss", "chatgpt",
    "openai", "desantis", "said", "say", "says",
}


def extract_bigrams(HTML_Text, min_count=3, top_n=3):
    """Return top noun-pair bigrams (min_count >= 3, top 3 only)."""
    bpairs = []
    for sent in sent_tokenize(HTML_Text):
        toks   = word_tokenize(sent)
        tagged = pos_tag(toks)
        ns_s   = [w.lower() for w, t in tagged
                  if t.startswith("NN") and w.isalpha() and len(w) >= 3
                  and w.lower() not in stop_bigram
                  and w.lower() not in eng_stopword_list]
        for i in range(len(ns_s) - 1):
            bpairs.append((ns_s[i], ns_s[i + 1]))
    return [" ".join(p) for p, c in Counter(bpairs).most_common(top_n) if c >= min_count]


# =============================================================================
# Cell 13: Evaluation helpers
# =============================================================================
def gt_to_token_set(gt_phrases):
    tokens = []
    for phrase in gt_phrases:
        for token in phrase.lower().split():
            token = re.sub(r"[^a-z]", "", token)
            if len(token) >= 3 and token not in eng_stopword_list:
                tokens.append(token)
    return set(tokens)


def pred_to_token_set(pred_keywords):
    tokens = []
    for kw in pred_keywords:
        for token in kw.lower().split():
            token = re.sub(r"[^a-z]", "", token)
            if len(token) >= 3:
                tokens.append(token)
    return set(tokens)


def prf(pred: set, gt: set):
    tp = len(pred & gt)
    fp = len(pred - gt)
    fn = len(gt - pred)
    p  = tp / (tp + fp) if (tp + fp) else 0.0
    r  = tp / (tp + fn) if (tp + fn) else 0.0
    f  = (2 * p * r / (p + r)) if (p + r) else 0.0
    return p, r, f


# =============================================================================
# Cell 14: Full pipeline for one document
# =============================================================================
def process_doc(doc_id: int, debug: bool = False):
    """Run full pipeline for one herald document. Returns (p, r, f)."""
    page_url, gt_phrases = read_doc_meta(doc_id)
    HTML_Text            = Web_scrapper_BeautifulSoup(page_url)

    # Preprocess
    candidate_words    = preprocess_text(HTML_Text, common_nouns, Special_Char_List, eng_stopword_list)
    nouns, adj, verb, proper_nouns = POS_Separator(candidate_words)
    lemma_nouns        = word_lemmatization(nouns)
    lemma_adj          = word_lemmatization(adj)
    lemma_verb         = word_lemmatization(verb)
    lemma_proper_nouns = word_lemmatization(proper_nouns)

    # Build frequency counter; proper nouns receive a x2 bonus
    clean_nouns  = clean_keywords_tokens(lemma_nouns)
    proper_set   = set(clean_keywords_tokens(lemma_proper_nouns))
    noun_counter = Counter()
    for w in clean_nouns:
        noun_counter[w] += 2 if w in proper_set else 1

    # Add keyword candidates from the URL slug (rich in proper nouns)
    url_slug   = page_url.split("?")[0]          # strip query string
    url_tokens = [t for t in re.split(r"[-_/.]", url_slug.lower())
                  if len(t) >= 3 and t.isalpha()
                  and t not in eng_stopword_list
                  and t not in set(common_nouns)
                  and t not in {"htm", "html", "php", "com", "org", "net", "www"}]
    for t in url_tokens:
        noun_counter[t] += 3   # URL-derived tokens are highly indicative

    top_nouns = [w for w, _ in noun_counter.most_common(100)]

    # Cluster keywords
    keywords  = get_clusters(dict(noun_counter), top_nouns, num_clusters=8)

    # Add top 1 adjective and top 1 verb
    keywords += fr_adj_ver(lemma_adj, 1) + fr_adj_ver(lemma_verb, 1)

    # Add top bigrams
    keywords += extract_bigrams(HTML_Text, min_count=3, top_n=3)

    # Deduplicate and post-filter residual compound tokens
    seen, unique_keywords = set(), []
    for kw in keywords:
        kw_clean = kw.lower().strip()
        if kw_clean in seen:
            continue
        seen.add(kw_clean)
        # Single-word compound check: >12 chars, not in WordNet, not a known proper noun -> skip
        if " " not in kw_clean:
            if len(kw_clean) > 12 and not wn.synsets(kw_clean) and kw_clean not in KNOWN_PROPER:
                continue
        unique_keywords.append(kw_clean)

    # Evaluate
    gt_tok   = gt_to_token_set(gt_phrases)
    pred_tok = pred_to_token_set(unique_keywords)
    p, r, f  = prf(pred_tok, gt_tok)

    if debug:
        print(f"--- Doc {doc_id} ---")
        print("URL :", page_url)
        print("GT  :", gt_phrases)
        print("Pred:", unique_keywords)
        print("GT tokens :", sorted(gt_tok))
        print("Pred tokens:", sorted(pred_tok))
        print(f"P={p:.3f}  R={r:.3f}  F1={f:.3f}")

    return p, r, f


# =============================================================================
# Cell 15: Run evaluation on all 120 documents
# =============================================================================
if __name__ == "__main__":
    DOC_IDS = range(0, 120)
    results = []

    for doc_id in DOC_IDS:
        try:
            p, r, f = process_doc(doc_id, debug=(doc_id == 0))
            results.append((doc_id, p, r, f))
            print(f"Doc {doc_id:2d}: P={p:.3f}  R={r:.3f}  F1={f:.3f}")
        except Exception as e:
            results.append((doc_id, 0.0, 0.0, 0.0))
            print(f"[ERROR] Doc {doc_id}: {e}")

    avg_p = sum(x[1] for x in results) / len(results)
    avg_r = sum(x[2] for x in results) / len(results)
    avg_f = sum(x[3] for x in results) / len(results)

    print(f"\n=== Results over {len(results)} docs ===")
    print(f"AVG Precision = {avg_p:.4f}")
    print(f"AVG Recall    = {avg_r:.4f}")
    print(f"AVG F1        = {avg_f:.4f}")
