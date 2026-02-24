import re
import math
import requests
import tempfile
import os
import urllib.request
from collections import Counter, defaultdict
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from libvoikko import Voikko


def get_top_keywords(url: str = None, html_path: str = None, k: int = 10):
    """
    Optimized Finnish keyword extractor for UEF WebRank dataset.
    Uses balanced TF-IDF with conservative signal weighting and compound word analysis.
    """
    try:
        v = Voikko("fi")
    except Exception as e:
        print(f"Voikko Error: {e}")
        return []

    # Expanded noise list based on Finnish stop words
    STOP_WORDS = set(
        """
    ja tai että mutta kuin on ovat oli olla oliin olivat olevan olen olet on olemme 
    olette ovat olit olit olimme olitte sivu haku arkisto katso tässä tämä se ne 
    nämä nuo joka mikä kuka miksi missä milloin miten myös vielä jo kanssa ilman 
    mukaan mukana jälkeen aikana vuonna päivänä kertaa enemmän vähemmän hyvin 
    vain joan joitain kaikki muutama usein harvoin aina useimmiten kuitenkin 
    sitten nyt täällä tuolla jossain joka paikassa muualla sisään ulos ylös alas 
    eteen taakse oikealle vasemmalle läpi vasten pitkin poikki yli alle päälle 
    alla vieressä keskellä vastapäätä kohdalla lähellä kaukana loitolla eri erilainen
    iso pieni hyvä huono uusi vanha pitkä lyhyt korkea matala leveä kapea suuri
    """.split()
    )

    def _get_lemma(word: str) -> tuple:
        """
        Returns (lemma, pos_class) where pos_class is 'noun', 'verb', 'adj', or 'other'
        """
        analysis = v.analyze(word)
        if analysis:
            lemma = analysis[0].get("BASEFORM", word).lower()
            pos = analysis[0].get("CLASS", "NONE")
            # Map Voikko classes to simplified POS
            if pos in ["nimisana", "laatusana", "nimi"]:
                pos_class = "noun"
            elif pos == "teonsana":
                pos_class = "verb"
            elif pos in ["laatusana", "nimisana_laatusana"]:
                pos_class = "adj"
            else:
                pos_class = "other"
            return lemma, pos_class
        return word.lower(), "unknown"

    def _extract_compound_parts(word: str) -> list:
        """Extract potential compound components from Finnish compound words"""
        # Common Finnish compound boundaries
        parts = []
        # Try to split on common patterns (this is heuristic)
        for i in range(3, len(word) - 2):
            left, right = word[:i], word[i:]
            if len(left) >= 3 and len(right) >= 3:
                parts.append(left)
                parts.append(right)
        return parts

    # 1. Fetch and Parse Content
    if html_path:
        with open(html_path, "rb") as f:
            html_content = f.read()
    else:
        try:
            html_content = requests.get(url, timeout=10).content
        except Exception as e:
            return []

    soup = BeautifulSoup(html_content, "lxml")

    # 2. Extract Structural Signal Zones with better parsing
    title_raw = soup.title.string if soup.title else ""

    # Get all headers with weights
    h1_tags = soup.find_all("h1")
    h2_tags = soup.find_all("h2")
    h3_tags = soup.find_all("h3")

    # Weight headers: h1=1.0, h2=0.5, h3=0.3
    header_text = " ".join([h.get_text() for h in h1_tags])
    header_text += " " + " ".join([h.get_text() for h in h2_tags])
    header_text += " " + " ".join([h.get_text() for h in h3_tags])

    # URL path analysis
    url_slug = ""
    if url:
        path = urlparse(url).path.lower()
        # Remove file extensions and common separators
        url_slug = re.sub(r"\.(html|htm|php|aspx?)$", "", path)
        url_slug = url_slug.replace("/", " ").replace("-", " ").replace("_", " ")
        url_slug = url_slug.replace(".", " ")

    # Process signal text
    signal_text = f"{title_raw} {header_text} {url_slug}"
    signal_tokens = {}
    for t in re.sub(r"[^a-zäöå]+", " ", signal_text.lower()).split():
        if len(t) > 2 and t not in STOP_WORDS:
            lemma, pos = _get_lemma(t)
            if pos in ["noun", "adj"]:  # Only consider nouns and adjectives as signals
                signal_tokens[lemma] = signal_tokens.get(lemma, 0) + 1

    # 3. Process Body Content - aggressive cleaning
    for tag in soup(
        [
            "nav",
            "footer",
            "header",
            "script",
            "style",
            "aside",
            "form",
            "noscript",
            "iframe",
            "ad",
            "advertisement",
            "sidebar",
            "menu",
        ]
    ):
        tag.decompose()

    # Get text from content-heavy tags first
    content_tags = soup.find_all(["article", "main", "section", "div", "p"])
    body_text = ""
    for tag in content_tags:
        text = tag.get_text(separator=" ", strip=True)
        if len(text) > 50:  # Filter out short UI fragments
            body_text += " " + text

    if not body_text.strip():
        body_text = soup.get_text(separator=" ")

    body_text = body_text.lower()
    body_tokens = re.sub(r"[^a-zäöå]+", " ", body_text).split()

    # 4. Advanced Token Processing with POS filtering
    lemma_counts = Counter()
    lemma_pos = {}
    position_scores = defaultdict(list)

    # Calculate document statistics for TF-IDF-like scoring
    total_tokens = len(body_tokens)
    unique_lemmas = set()

    for idx, token in enumerate(body_tokens):
        if len(token) <= 2 or token in STOP_WORDS or token.isdigit():
            continue

        lemma, pos = _get_lemma(token)

        # Filter: prefer nouns, allow some adjectives, reject verbs/function words
        if pos == "verb" and lemma not in signal_tokens:
            continue  # Skip verbs unless they're in signals

        if pos == "other" and len(lemma) < 5:
            continue  # Skip short unknown words

        # Track first positions for early-occurrence bonus
        if lemma not in unique_lemmas:
            position_scores[lemma] = idx / total_tokens if total_tokens > 0 else 0.5
            unique_lemmas.add(lemma)

        lemma_counts[lemma] += 1
        lemma_pos[lemma] = pos

    # 5. Intelligent Scoring
    total_count = sum(lemma_counts.values()) or 1
    doc_length = len(unique_lemmas) or 1

    final_scores = {}

    for lemma, count in lemma_counts.items():
        pos = lemma_pos.get(lemma, "unknown")

        # Base TF score with sublinear scaling (log normalization)
        tf = count / total_count
        tf_score = (1 + math.log(count)) if count > 0 else 0

        # Length bonus: Finnish compounds are often important keywords
        length_bonus = math.log(len(lemma)) if len(lemma) > 6 else 1.0

        # POS bonus: nouns preferred
        pos_bonus = 1.5 if pos == "noun" else (1.2 if pos == "adj" else 1.0)

        # Position bonus: words appearing early are often more important
        pos_score = 1.0
        if lemma in position_scores:
            early_bonus = max(0, 1 - position_scores[lemma])  # Earlier = higher
            pos_score = 1.0 + (early_bonus * 0.5)

        # Signal matching with conservative boosting
        signal_boost = 1.0
        if lemma in signal_tokens:
            # Moderate boost based on signal frequency
            signal_freq = signal_tokens[lemma]
            signal_boost = 3.0 + min(signal_freq * 0.5, 2.0)  # Max 5x boost
        else:
            # Check for compound word matches (e.g., "porkkanasose" contains "porkkana")
            for signal_lemma in signal_tokens:
                if len(signal_lemma) > 4:
                    if signal_lemma in lemma or lemma in signal_lemma:
                        signal_boost = max(signal_boost, 2.0)
                        break

        # Calculate final score
        final_score = tf_score * length_bonus * pos_bonus * pos_score * signal_boost

        # Penalize very common words (IDF-like)
        # Words appearing in >50% of positions are likely too generic
        if count / total_count > 0.05:  # More than 5% of all tokens
            final_score *= 0.5

        final_scores[lemma] = final_score

    # 6. Ranking with diversity enforcement
    ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)

    # Deduplicate similar terms (e.g., singular/plural variants that Voikko missed)
    selected = []
    selected_stems = set()

    for word, score in ranked:
        # Skip if we already have a very similar word
        is_duplicate = False
        for existing in selected_stems:
            if word in existing or existing in word:
                if abs(len(word) - len(existing)) < 3:
                    is_duplicate = True
                    break

        if not is_duplicate:
            selected.append(word)
            selected_stems.add(word)

        if len(selected) >= k:
            break

    return selected


# --------------------- Evaluation Utility ---------------------

BASE = "https://cs.uef.fi/~himat/WebRank/dataset_12/dataset_12/ruoka/"


def run_evaluation(total_pages=100):
    try:
        v_eval = Voikko("fi")
    except Exception as e:
        print(f"Voikko Error in eval: {e}")
        return

    def _get_eval_lemma(word: str) -> str:
        analysis = v_eval.analyze(word)
        if analysis:
            return analysis[0].get("BASEFORM", word).lower()
        return word.lower()

    p_sum, r_sum, f_sum, actual_count = 0, 0, 0, 0
    errors = []

    print(f"Starting evaluation on {total_pages} pages...")

    for i in range(total_pages):
        try:
            # Fetch GT and HTML
            gt_response = requests.get(f"{BASE}{i}/GT.txt", timeout=10)
            gt_response.encoding = "utf-8-sig"
            gt_txt = gt_response.text.strip()

            html_response = requests.get(f"{BASE}{i}/HTML.txt", timeout=10)
            html_content = html_response.text

            # Prepare GT - handle multi-word keywords properly
            gt_raw = re.sub(r"[^a-zäöå\s]+", " ", gt_txt.lower()).split()
            gt_keywords = set()
            for w in gt_raw:
                if len(w) > 2:
                    gt_keywords.add(_get_eval_lemma(w))

            # Remove stop words from GT for fair comparison
            gt_keywords = {
                w
                for w in gt_keywords
                if w not in {"ja", "tai", "on", "ovat", "oli", "sekä", "myös"}
            }

            # Extract
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", delete=False
            ) as f:
                f.write(html_content)
                t_path = f.name

            extracted = get_top_keywords(html_path=t_path, url=f"{BASE}{i}/", k=10)
            os.unlink(t_path)

            # Metrics with partial matching for compounds
            matches = []
            for ext in extracted:
                if ext in gt_keywords:
                    matches.append(ext)
                else:
                    # Check if extracted word is a substring of any GT keyword
                    for gt in gt_keywords:
                        if ext in gt or gt in ext:
                            if len(ext) > 4 and len(gt) > 4:
                                matches.append(ext)
                                break

            p = len(matches) / len(extracted) if extracted else 0
            r = len(matches) / len(gt_keywords) if gt_keywords else 0
            f_score = (2 * p * r) / (p + r) if (p + r) > 0 else 0

            p_sum += p
            r_sum += r
            f_sum += f_score
            actual_count += 1

            if i % 20 == 0:
                print(
                    f"Progress: {i}/{total_pages} | Latest P:{p:.2f} R:{r:.2f} F:{f_score:.2f}"
                )

            if f_score < 0.1 and i < 5:  # Debug first few failures
                errors.append(
                    {
                        "page": i,
                        "gt": list(gt_keywords)[:5],
                        "extracted": extracted[:5],
                        "f": f_score,
                    }
                )

        except Exception as e:
            print(f"Error on page {i}: {e}")
            continue

    if actual_count > 0:
        print(f"\n{'='*50}")
        print(f"EVALUATION RESULTS ({actual_count} pages)")
        print(f"{'='*50}")
        print(f"Precision: {p_sum/actual_count:.3f}")
        print(f"Recall:    {r_sum/actual_count:.3f}")
        print(f"F-Score:   {f_sum/actual_count:.3f}")

        if errors:
            print(f"\nSample errors:")
            for err in errors[:3]:
                print(
                    f"  Page {err['page']}: GT={err['gt']}, EXT={err['extracted']}, F={err['f']:.2f}"
                )


if __name__ == "__main__":
    run_evaluation(100)
