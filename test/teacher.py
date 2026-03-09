import re
import urllib.request
from urllib.parse import urlparse
from collections import Counter
from bs4 import BeautifulSoup, Comment
from nltk.corpus import stopwords
from nltk import wordpunct_tokenize
import nltk

# --- CONFIGURATION & NLTK SETUP ---
try:
    stopwords.words("english")
except LookupError:
    nltk.download("stopwords")

# Noise words to filter out during cleaning
COMMON_NOISE_WORDS = set(
    """
january debt est dec big than who use jun jan feb mar apr may jul agust dec oct nov sep dec
product continue one two three four five please thanks find helpful week job experience women girl
apology read show eve knowledge benefit appointment street way staff salon discount gift cost thing
world close party love letters rewards offers special close page week dollars voucher gifts vouchers
welcome therefore march nights need name pleasure show sisters thank menu today always time needs
welcome march february april may june jully aguast september october november december day year
month minute second secodns
""".split()
)

# Regex for special character removal
SPECIAL_CHARS_RE = re.compile(
    r"[ \~\!\@\#\\$\%\^\&\*\(\)\_\+\=\\\|\{\}\[\]\:\;\'\"\<\>\,\/\.\-]"
)

# --- HELPER FUNCTIONS ---


def _is_visible_text(element) -> bool:
    if element.parent.name in ["html", "style", "script", "head", "[document]", "img"]:
        return False
    if isinstance(element, Comment):
        return False
    return True


def _extract_visible_text_from_html(html: bytes) -> str:
    soup = BeautifulSoup(html, "lxml")
    texts = soup.find_all(string=True)
    visible_texts = filter(_is_visible_text, texts)
    return "".join(t.strip() for t in visible_texts)


def _normalize_whitespace(text: str) -> str:
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split(" "))
    return "\n".join(chunk for chunk in chunks if chunk)


def _fetch_page(u: str):
    req = urllib.request.Request(u, headers={"User-Agent": "KeywordScraper/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read()
        soup = BeautifulSoup(html, "lxml")
        raw_text = _extract_visible_text_from_html(html)
        clean_text = _normalize_whitespace(raw_text)
        return clean_text, soup


def _calculate_language_scores(text: str) -> dict:
    ratios = {}
    tokens = wordpunct_tokenize(text)
    words = [w.lower() for w in tokens]
    words_set = set(words)
    for lang in stopwords.fileids():
        try:
            stop_set = set(stopwords.words(lang))
            common = words_set.intersection(stop_set)
            ratios[lang] = len(common)
        except Exception:
            continue
    return ratios


def _detect_language_and_stopwords(text: str):
    ratios = _calculate_language_scores(text)
    if not ratios:
        return "english", set(stopwords.words("english"))
    detected_lang = max(ratios, key=ratios.get)
    try:
        sw = set(stopwords.words(detected_lang))
    except Exception:
        detected_lang, sw = "english", set(stopwords.words("english"))
    return detected_lang, sw


def _clean_text_to_words(text: str, stopword_list: set) -> list:
    words = []
    for raw_word in text.split():
        word = raw_word.replace("   ,  ¢", "").lower()
        word = SPECIAL_CHARS_RE.sub("", word).strip()
        if not word:
            continue
        for token in word.split():
            token = token.strip()
            if (
                len(token) > 1
                and not token[0].isdigit()
                and token not in stopword_list
                and token not in COMMON_NOISE_WORDS
                and not token.isdigit()
            ):
                words.append(token)
    return words


# --- URL & TAG ANALYSIS ---


def _split_url_host(u: str) -> list:
    parsed = urlparse(u)
    host = parsed.hostname or ""
    parts = []
    for chunk in host.split("."):
        chunk = chunk.lower()
        if chunk not in ["", "https", "www", "com", "php", "pk", "fi", "http"]:
            parts.append(chunk)
    return parts


def _split_url_path_and_query(u: str, host_parts: list) -> list:
    path_tokens = []
    for segment in u.split("/"):
        for dot_part in segment.split("."):
            for dash_part in dot_part.split("-"):
                token = dash_part.lower()
                if (
                    token
                    and token not in ["https", "www", "com", "php", "pk", "fi", "http"]
                    and token not in host_parts
                ):
                    path_tokens.append(token)
    return path_tokens


def _extract_tag_texts(soup, tag_name: str) -> list:
    return [
        el.get_text(strip=True).lower()
        for el in soup.find_all(tag_name)
        if el.get_text(strip=True)
    ]


def _explode_texts_to_words(text_list: list) -> list:
    out = []
    for text in text_list:
        for comma_chunk in text.split(","):
            for w in comma_chunk.split():
                out.append(w)
    return out


def _extract_headers_anchors_title_words(soup):
    h1 = _explode_texts_to_words(_extract_tag_texts(soup, "h1"))
    h2 = _explode_texts_to_words(_extract_tag_texts(soup, "h2"))
    h3 = _explode_texts_to_words(_extract_tag_texts(soup, "h3"))
    h4 = _explode_texts_to_words(_extract_tag_texts(soup, "h4"))
    h5 = _explode_texts_to_words(_extract_tag_texts(soup, "h5"))
    h6 = _explode_texts_to_words(_extract_tag_texts(soup, "h6"))
    anchor = _explode_texts_to_words(_extract_tag_texts(soup, "a"))
    title = _explode_texts_to_words(_extract_tag_texts(soup, "title"))
    return h1, h2, h3, h4, h5, h6, anchor, title


def _tf_score(freq: int, total_tokens: int) -> float:
    if total_tokens < 50:
        return (freq / 100.0) * 50
    return (freq / 100.0) * 20


def _compute_keyword_scores(words: list, soup, u: str) -> dict:
    freq = Counter(words)
    total_tokens = len(words)
    h1, h2, h3, h4, h5, h6, anchor, title = _extract_headers_anchors_title_words(soup)
    url_host = _split_url_host(u)
    url_path = _split_url_path_and_query(u, url_host)

    headers_names = ["H1", "H2", "H3", "H4", "H5", "H6", "A", "Title", "URL-H", "URL-Q"]
    headers_scores = [6, 5, 4, 3, 2, 1, 2, 5, 5, 4]
    headers_lists = [h1, h2, h3, h4, h5, h6, anchor, title, url_host, url_path]

    word_info = {}
    for w, c in freq.items():
        base = _tf_score(c, total_tokens)
        tag_boost, tag_names = 0.0, []
        for idx, toks in enumerate(headers_lists):
            if w in toks:
                tag_boost += headers_scores[idx]
                tag_names.append(headers_names[idx])
        word_info[w] = (c, tag_names, base + tag_boost)
    return word_info


# --- CORE PIPELINE ---


def get_top_keywords(url: str, k: int = 10, return_details: bool = False):
    clean_text, soup = _fetch_page(url)
    _, stopword_list = _detect_language_and_stopwords(clean_text)
    tokens = _clean_text_to_words(clean_text, stopword_list)

    if not tokens:
        return []

    keyword_data = _compute_keyword_scores(tokens, soup, url)
    top = sorted(keyword_data.items(), key=lambda kv: kv[1][2], reverse=True)[:k]

    if return_details:
        return [(w, meta[0], meta[2], meta[1]) for w, meta in top]
    return [w for w, _ in top]


# --- EVALUATION LOGIC ---


def Get_Prc_Rcl_Fscr_input_GT_and_Keywords_List(ground_truth, keywords):
    matches = [word for word in ground_truth if word in keywords]
    gt_count, kw_count, match_count = len(ground_truth), len(keywords), len(matches)

    if gt_count == 0 or kw_count == 0:
        return (0, 0, 0)

    precision = match_count / kw_count
    recall = match_count / gt_count
    f_score = (
        (2 * precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )
    return (precision, recall, f_score)


def read_url(url):
    with urllib.request.urlopen(url) as f:
        return f.read().decode("utf-8-sig").strip()


def load_herald_case(index):
    BASE = "https://cs.uef.fi/~himat/WebRank/dataset_12/dataset_12/herald"
    base_url = f"{BASE}/{index}"
    url_text = read_url(f"{base_url}/URL.txt")
    gt_text = read_url(f"{base_url}/GT.txt")
    return url_text, gt_text.split()


def run_evaluation(total_webpages=10):
    p_sum, r_sum, f_sum = 0.0, 0.0, 0.0
    for i in range(total_webpages):
        URL, gt_keywords = load_herald_case(str(i))
        found_keywords = get_top_keywords(URL)
        p, r, f = Get_Prc_Rcl_Fscr_input_GT_and_Keywords_List(
            gt_keywords, found_keywords
        )
        p_sum, r_sum, f_sum = p_sum + p, r_sum + r, f_sum + f

    avg_p = round(p_sum / total_webpages, 2)
    avg_r = round(r_sum / total_webpages, 2)
    avg_f = round(f_sum / total_webpages, 2)

    print("=== AVERAGE OVER ALL WEBPAGES ===")
    print(f"Average Precision: {avg_p}")
    print(f"Average Recall: {avg_r}")
    print(f"Average F-score: {avg_f}")


# --- EXECUTION ---
if __name__ == "__main__":
    run_evaluation(100)
