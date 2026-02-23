import re
import math
import requests
import tempfile
import os
import urllib.request
from collections import Counter
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from libvoikko import Voikko


def get_top_keywords(url: str = None, html_path: str = None, k: int = 10):
    """
    Full implementation of the high-precision Finnish keyword extractor.
    Combines structural weighting with linguistic lemmatization.
    """
    try:
        v = Voikko("fi")
    except Exception as e:
        print(f"Voikko Error: {e}")
        return []

    # Use minimal noise filtering - let scoring handle frequency balance
    GENERIC_NOISE = set(
        "ja tai että mutta kuin on ovat oli sivu haku arkisto katso tässä".split()
    )

    def _get_lemma(word: str) -> str:
        """Reduces Finnish words to base form: e.g., 'porkkanoita' -> 'porkkana'"""
        analysis = v.analyze(word)
        if analysis:
            return analysis[0].get("BASEFORM", word).lower()
        return word.lower()

    # 1. Fetch and Parse Content
    if html_path:
        with open(html_path, "rb") as f:
            html_content = f.read()
    else:
        html_content = requests.get(url, timeout=10).content

    soup = BeautifulSoup(html_content, "lxml")

    # 2. Extract Structural Signal Zones
    title_raw = soup.title.string if soup.title else ""
    h1_raw = " ".join([h.get_text() for h in soup.find_all(["h1", "h2"])])
    url_slug = (
        urlparse(url).path.lower().replace("/", " ").replace("-", " ").replace("_", " ")
        if url
        else ""
    )

    # Build signal token set - filtering by minimum length
    signal_text = f"{title_raw} {h1_raw} {url_slug}"
    signal_tokens = set(
        [
            _get_lemma(t)
            for t in re.sub(r"[^a-zäöå]+", " ", signal_text.lower()).split()
            if len(t) > 3  # Increased from 2 to 3 for better quality
        ]
    )

    # 3. Process Body Content
    # Remove UI elements to avoid precision loss
    for tag in soup(["nav", "footer", "header", "script", "style", "aside", "form"]):
        tag.decompose()

    body_text = soup.get_text(separator=" ").lower()
    body_tokens = re.sub(r"[^a-zäöå]+", " ", body_text).split()

    # Generate lemmas and count frequencies - filter by length earlier
    lemmas = [
        _get_lemma(t)
        for t in body_tokens
        if len(t) > 3 and t not in GENERIC_NOISE  # Increased minimum length from 2 to 3
    ]
    counts = Counter(lemmas)

    # 4. Scoring Logic (Balanced approach)
    final_scores = {}
    total = sum(counts.values()) or 1

    for word, count in counts.items():
        # Baseline frequency score with TF-IDF-like weighting
        # Use sqrt to reduce impact of super-frequent words
        score = (count / total) * math.sqrt(count)

        # Signal boost: Words in Title/URL/H1 are likely GT candidates
        # Aggressive boost for high-confidence signal zones
        if word in signal_tokens:
            score *= 50.0

        # Fuzzy Match: Boost components of compound words found in signals
        # For longer compound words, give solid boost
        elif any(word in s or s in word for s in signal_tokens if len(word) > 4):
            score *= 30.0

        final_scores[word] = score

    # 5. Ranking - adaptive k based on available keywords
    ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)

    # Adaptive k: return up to k keywords, but cap at available options
    actual_k = min(k, len(ranked))
    return [w for w, s in ranked[:actual_k]]


# --------------------- Evaluation Utility ---------------------

BASE = "https://cs.uef.fi/~himat/WebRank/dataset_12/dataset_12/ruoka/"


def run_evaluation(total_pages=100):
    # Initialize Voikko once for evaluation
    try:
        v_eval = Voikko("fi")
    except Exception as e:
        print(f"Voikko Error in eval: {e}")
        return

    def _get_eval_lemma(word: str) -> str:
        """Lemmatize for evaluation matching"""
        analysis = v_eval.analyze(word)
        if analysis:
            return analysis[0].get("BASEFORM", word).lower()
        return word.lower()

    p_sum, r_sum, f_sum, actual_count = 0, 0, 0, 0

    print(f"Starting evaluation on {total_pages} pages...")
    for i in range(total_pages):
        try:
            # Fetch GT and HTML from UEF server
            gt_txt = (
                requests.get(f"{BASE}{i}/GT.txt").content.decode("utf-8-sig").strip()
            )
            html_content = requests.get(f"{BASE}{i}/HTML.txt").text

            # Prepare GT - properly lemmatized for fair comparison
            gt_raw = re.sub(r"[^a-zäöå]+", " ", gt_txt.lower()).split()
            gt_keywords = set(
                [
                    _get_eval_lemma(w)
                    for w in gt_raw
                    if len(w) > 3  # Match the extraction length threshold
                ]
            )

            # Extract
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", delete=False
            ) as f:
                f.write(html_content)
                t_path = f.name

            extracted = get_top_keywords(
                html_path=t_path, url=f"{BASE}{i}/", k=10
            )  # Using k=10
            os.unlink(t_path)

            # Metrics - Compare lemmas directly
            matches = [w for w in extracted if w in gt_keywords]
            p = len(matches) / len(extracted) if extracted else 0
            r = len(matches) / len(gt_keywords) if gt_keywords else 0
            f_score = (2 * p * r) / (p + r) if (p + r) > 0 else 0

            p_sum += p
            r_sum += r
            f_sum += f_score
            actual_count += 1
            if i % 20 == 0:
                print(f"Progress: {i}%")
        except Exception as e:
            continue

    print(
        f"\nFINAL: P: {p_sum/actual_count:.2f} | R: {r_sum/actual_count:.2f} | F: {f_sum/actual_count:.2f}"
    )


if __name__ == "__main__":
    run_evaluation(100)
