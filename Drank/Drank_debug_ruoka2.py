def get_top_keywords(url: str, k: int = 10, return_details: bool = False):
    import re
    import urllib.request
    from urllib.parse import urlparse
    from collections import Counter, defaultdict
    from bs4 import BeautifulSoup, Comment
    from nltk.corpus import stopwords
    import nltk
    import requests
    import math

    # --------------------- ensure NLTK data ---------------------
    try:
        stopwords.words("english")
    except LookupError:
        nltk.download("stopwords")

    # --------------------- ensure Finnish stemmer ---------------------
    try:
        from nltk.stem.snowball import SnowballStemmer
    except ImportError:
        nltk.download('snowball_data')
        from nltk.stem.snowball import SnowballStemmer

    # --------------------- ensure langdetect is installed ---------------------
    try:
        from langdetect import detect
    except ImportError:
        import subprocess
        subprocess.check_call(["pip", "install", "langdetect"])
        from langdetect import detect

    # --------------------- ensure yake is installed ---------------------
    try:
        import yake
    except ImportError:
        import subprocess
        subprocess.check_call(["pip", "install", "yake"])
        import yake

    # --------------------- config ---------------------
    COMMON_NOISE_WORDS = set("""
    January debt est dec big than who use jun jan feb mar apr may jul august dec oct nov sep dec
    product continue one two three four five please thanks find helpful week job experience women girl
    apology read show eve knowledge benefit appointment street way staff salon discount gift cost thing
    world close party love letters rewards offers special close pack wed dollars voucher gifts vouchers
    welcome therefore march nights need name please show sisters thank menu today always time needs
    welcome march february april may june jully august september october november december day year
    month minute second seconds
    """.split())

    my_noise_words_ruoka = set(
    )

    # Stemmed Noise Words（my_noise_words_india_2nd_set + 355 noise words observed in the output）
    my_noise_words_india_2nd_set = set(
        {
            # original set
            "bangkok", "tuli", "kaal", "bengal", "keitinpiir", "kylm", "kunia", "simpuk",
            "alkoholittom", "valm", "sitruunanmehu", "teen", "viera", "lihacury", "nauta",
            "leipomin", "silputu", "täyteläin", "aasialaisit", "jauhelihahapankaalipiirak",
            "juureks", "paistam", "makaron", "lihapal", "muna", "silpu", "tee", "oliiviöljy",
            "dick", "lehtikaalijuustopiirak", "vaniljat", "kaffirlimet", "sähköpostiosoit",
            "leivo", "sormisuol", "vesi", "kanalien", "raastetu", "ulkoasu", "ruoan", "iltat",
            "mausteöljy", "kof", "pastakastik", "koko", "mieto", "suikal", "bulgurkasvispae",
            "nap", "kyse", "keit", "peitä", "ruokaf", "keittim", "komment", "grillikastik",
            "kurpitsansiemen", "thaimaalain", "lihapullacury", "kimpal", "ohu", "appelsiin",
            "olkiperuno", "parsaperunapaistos", "balsamicokastik", "täytety", "jäätelökonekes",
            "pada", "kalaviipal", "voitaik", "pulo", "seos", "pikalei", "levä", "mustapippur",
            "juoksev", "savupaprikajauh", "maustein", "ruokaöljy", "herku", "maito", "levy",
            "pohj", "kokonaispist", "hienon", "past", "linssikasviscury", "kesk", "facebook",
            "mukav", "sitruunaruoho", "nyyti", "uun", "pata", "sitruunamehu", "vast", "savuin",
            "kauhallin", "valmistetu", "kattil", "jättilihapul", "vatk", "espanjalais",
            "kauraleip", "pippur", "muscovado", "vars", "jätä", "toimitus", "teko", "menu",
            "kunnes", "riis", "lämpö", "kypsen", "horitikimaalaissalaat", "limemarinoidu",
            "lautas", "herkul", "inkiväärilimebrl", "kinkkuperunamunakas", "koto", "elys",
            "makea", "paahd", "pommac", "kotiliesif", "tarvitae", "paahtaj", "file",
            "sienipiirak", "tabboulehsalaat", "savusuol", "hirvikaud", "voita", "seko",
            "karitsanpotk", "saa", "pitä", "puoluko", "kalaparsapiirak", "chorizomakkar",
            "valkosipul", "kaalikurpitsapiirak", "vaalea", "valkokaal", "majonees", "kuskus",
            "kurpitsamosk", "raaka", "kuumen", "lihamakaronilaatiko", "seoks", "timjam", "wok",
            "crme", "peking", "mari", "täyt", "maustetu", "salovaar", "väri", "maukas",
            "jamblaya", "koillisespanj", "lev", "sukker", "liuota", "espanjal", "kevätsipul",
            "aamu", "lieme", "marinoidu", "korvasienikastik", "sekoit", "rkl", "kyps", "oliiv",
            "punain", "herkullis", "keskustelu", "kilistelyy", "focaccialei", "ohue",
            "sekavihannesspaget", "itämais", "ohj", "kookoskaneliriisipuuro", "sekoitel",
            "käytä", "graavisiik", "kesäkurpits", "lihasienipiirak", "höyrytety", "cevich",
            "hienonnetu", "meksikol", "hurm", "verso", "kera", "paahtopai", "lämmittäv",
            "lihavok", "ota", "korianter", "reuno", "hetk", "japanilaistyylin", "riisinkeittim",
            "sipul", "sivel", "kauli", "pois", "maus", "punaviin", "munacury", "hunajapunav",
            "paistijauhelih", "ravents", "tein", "keitety", "vois", "karamelliomeno", "appels",
            "murskatu", "käyttäm", "soker", "malesialain", "simo", "viikonlopu", "korm", "panu",
            "chorizolammaspyöryk", "sitruunatillikastik", "mausteseos", "lohko", "nimi",
            "sitruun", "grillileik", "materiaal", "punakaalisalaat", "italialais", "tehd",
            "lindertz", "taik", "brle", "retiis", "broilerinleik", "pähkin", "pilko",
            "samosapiir", "pihv", "kup", "rasv", "kanapaprik", "koho", "pakkas", "ruisjauho",
            "kuori", "paksoi", "lisä", "marokkolais", "tervetulo", "sitruunak", "väle", "vaiva",
            "resept", "pin", "dijo", "mieti", "kasvist", "kanafond", "reikälei", "raikas",
            "kuoritu", "vaahdo", "liha", "louisianalais", "oregano", "sämpylätaikin", "huuhdo",
            "tasais", "kiehuv", "pais", "vuoka", "suolasitruun", "seesaminsiemen",
            "sienipinaattipiirak", "käyt", "nypi", "tila", "käytö", "creolekeitiö", "punasipul",
            "kampasimpuko", "pidä", "liina", "heinäkasaperun", "puolukkashot", "yojuhl", "pehm",
            "leik", "lehtikaalijuustopiiras", "valu", "keskitaso", "nino", "jäädäks", "laita",
            "muotoil", "hunaj", "suosik", "valmist", "paahdetu", "kermaseos", "kastik", "wasab",
            "klassin", "päät", "mehev", "artisok", "taina", "täyte", "kaada", "mit", "codornu",
            "chil", "sopiv", "peko", "brut", "kinkkujuustopiiras", "sisilialaist",
            "broilerikaalikeito", "piknik", "nos", "hallikaupia", "silkinsil", "kuivahtan",
            "tuoksu", "suikaloi", "lohicarpacio", "minuut", "expres", "kompressor", "hurmaav",
            "maun", "aasialais", "obh", "lap", "vastaus", "dan", "viipal", "italial", "fileoi",
            "suola", "sobanuudelisalaat", "kantarellikasvispanu", "tapaks", "kone", "taikin",
            "kurku", "make", "tapa", "hapattim", "kookoslimettinuget", "katkarapuparsapiiras",
            "marinad", "porkkan", "parmesaanilastu", "suikaloitu", "purjosipul",
            "chorizojauhelihapihv", "haukirapumurek", "knor", "hapa", "vink", "uunipanu",
            "mehu", "käs",
            # Additional noise words observed in the output (stemmed)
            "kohoam", "perusohj", "calzon", "tilant", "varustetu", "tul", "kanamun",
            "ranskalaist", "tabasco", "juustoraast", "kiehu", "rosado", "currytahn", "srirach",
            "ostosl", "vede", "jälkiruoa", "perunankuorrut", "siikasalaat", "kananpo",
            "worscester", "ilm", "cordo", "puhd", "kova", "paistinpanu", "palo", "pehmen",
            "ripaus", "mausteseoks", "kuulo", "rypsiöljy", "seurustelujuom", "min",
        }
    )

    # Finnish-specific noise words (site navigation, UI elements, etc.)
    finnish_noise_words = set("""
    blogit kommentit kommentoi peruuta avainsanat tunnisteet valmistusohje ainekset menu
    ruokalista viikon helpot herkulliset arkiruoat juhlamenu mukana maku pippurimylly
    yrttiopas myös sivusto sivu kuvat kuva video videot linkit linkki etusivu hae haku
    rekisteri rekisteröidy kirjaudu ulos sisään uutiset uutinen artikkelit artikkeli
    resept komment keskustelu vink tervetulo ohj make teko tehd nap keit kone
    sähköpostiosoit kulho keittim kokonaispist iso tila
    """.split())

    # Mapping from langdetect language codes to NLTK stopwords language names
    LANG_CODE_TO_NLTK = {
        'af': 'afrikaans', 'ar': 'arabic', 'bg': 'bulgarian', 'bn': 'bengali',
        'ca': 'catalan', 'cs': 'czech', 'cy': 'welsh', 'da': 'danish',
        'de': 'german', 'el': 'greek', 'en': 'english', 'es': 'spanish',
        'et': 'estonian', 'fa': 'persian', 'fi': 'finnish', 'fr': 'french',
        'gu': 'gujarati', 'he': 'hebrew', 'hi': 'hindi', 'hu': 'hungarian',
        'id': 'indonesian', 'it': 'italian', 'ja': 'japanese', 'kn': 'kannada',
        'ko': 'korean', 'lt': 'lithuanian', 'lv': 'latvian', 'mk': 'macedonian',
        'ml': 'malayalam', 'mr': 'marathi', 'ne': 'nepali', 'nl': 'dutch',
        'no': 'norwegian', 'pa': 'punjabi', 'pl': 'polish', 'pt': 'portuguese',
        'ro': 'romanian', 'ru': 'russian', 'sk': 'slovak', 'sl': 'slovenian',
        'so': 'somali', 'sq': 'squarish', 'sv': 'swedish', 'ta': 'tamil',
        'te': 'telugu', 'th': 'thai', 'tl': 'tagalog', 'tr': 'turkish',
        'uk': 'ukrainian', 'vi': 'vietnamese', 'zh-cn': 'chinese_simplified',
        'zh-tw': 'chinese_traditional',
    }

    # --------------------- helpers ---------------------
    def _extract_meta_keywords(soup, detected_lang='finnish'):
        """Extract keywords from meta tags and structured data"""
        keywords = []

        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            content = meta_keywords.get('content', '')
            for kw in content.split(','):
                kw = kw.strip().lower()
                if kw:
                    normalized = _normalize_finnish_word(kw, detected_lang)
                    keywords.append(normalized)

        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            desc = meta_desc.get('content', '').lower()
            for word in desc.split():
                word = re.sub(r'[^a-zA-ZåäöÅÄÖ]+', '', word)
                if len(word) > 2:
                    normalized = _normalize_finnish_word(word, detected_lang)
                    keywords.append(normalized)

        og_tags = ['og:title', 'og:description', 'og:site_name']
        for og_tag in og_tags:
            og_meta = soup.find('meta', property=og_tag)
            if og_meta and og_meta.get('content'):
                content = og_meta.get('content', '').lower()
                for word in content.split():
                    word = re.sub(r'[^a-zA-ZåäöÅÄÖ]+', '', word)
                    if len(word) > 2:
                        normalized = _normalize_finnish_word(word, detected_lang)
                        keywords.append(normalized)

        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    for key in ['name', 'headline', 'keywords', 'description', 'about']:
                        if key in data:
                            value = data[key]
                            if isinstance(value, str):
                                for word in value.lower().split():
                                    word = re.sub(r'[^a-zA-ZåäöÅÄÖ]+', '', word)
                                    if len(word) > 2:
                                        normalized = _normalize_finnish_word(word, detected_lang)
                                        keywords.append(normalized)
                            elif isinstance(value, list):
                                for item in value:
                                    if isinstance(item, str):
                                        for word in item.lower().split():
                                            word = re.sub(r'[^a-zA-ZåäöÅÄÖ]+', '', word)
                                            if len(word) > 2:
                                                normalized = _normalize_finnish_word(word, detected_lang)
                                                keywords.append(normalized)
            except:
                pass

        return keywords

    def _normalize_finnish_word(word, detected_lang='finnish'):
        """Normalize Finnish words using stemming"""
        word = word.lower()
        if detected_lang == 'finnish':
            try:
                stemmer = SnowballStemmer('finnish')
                return stemmer.stem(word)
            except:
                return word
        return word

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
        return " ".join(t.strip() for t in visible_texts)

    def _normalize_whitespace(text: str) -> str:
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return "\n".join(chunk for chunk in chunks if chunk)

    def _fetch_page(u: str):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(u, headers=headers, timeout=20)
        response.raise_for_status()
        html = response.content
        soup = BeautifulSoup(html, "lxml")
        raw_text = _extract_visible_text_from_html(html)
        clean_text = _normalize_whitespace(raw_text)
        return clean_text, soup

    def _detect_language_and_stopwords(text: str):
        """Detect language using langdetect and return appropriate stopwords"""
        try:
            lang_code = detect(text)
            nltk_lang = LANG_CODE_TO_NLTK.get(lang_code, 'english')
            try:
                sw = set(stopwords.words(nltk_lang))
                return nltk_lang, sw
            except Exception:
                print(f"Detected language: {nltk_lang} (code: {lang_code}), but no stopwords available. Using English.")
                return "english", set(stopwords.words("english"))
        except Exception as e:
            print(f"Language detection failed ({e}). Using English.")
            return "english", set(stopwords.words("english"))

    def _clean_text_to_words(text: str, stopword_list: set, detected_lang: str = 'english') -> list:
        words = []
        LETTERS_ONLY_RE = re.compile(r"[^a-zA-ZåäöÅÄÖ]+")

        for raw_word in text.split():
            token = LETTERS_ONLY_RE.sub("", raw_word).lower()

            # Stemming is performed first, and the stemmed form is compared with noise words.
            normalized_token = _normalize_finnish_word(token, detected_lang)

            if (
                len(normalized_token) > 1
                and not normalized_token[0].isdigit()
                and normalized_token not in stopword_list
                and normalized_token not in finnish_noise_words
                and normalized_token not in my_noise_words_india_2nd_set  # ★ 有効化
                and not normalized_token.isdigit()
                and len(normalized_token) < 25
            ):
                words.append(normalized_token)

        return words

    def _split_url_host(u: str) -> list:
        parsed = urlparse(u)
        host = parsed.hostname or ""
        parts = []
        for chunk in host.split("."):
            chunk = chunk.lower()
            if chunk not in ["", "https", "www", "com", "-", "php", "pk", "fi", "http"]:
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
                        and token not in [
                            "https", "www", "com", "-", "php", "pk", "fi",
                            "https:", "http", "http:", "http:",
                        ]
                        and token not in host_parts
                    ):
                        path_tokens.append(token)
        return path_tokens

    def _extract_tag_texts(soup, tag_name: str) -> list:
        out = []
        for el in soup.find_all(tag_name):
            t = el.get_text(strip=True).lower()
            if t:
                out.append(t)
        return out

    def _explode_texts_to_words(text_list: list, detected_lang: str = 'english') -> list:
        out = []
        for text in text_list:
            for comma_chunk in text.split(","):
                for w in comma_chunk.split():
                    normalized_w = _normalize_finnish_word(w, detected_lang)
                    out.append(normalized_w)
        return out

    def _extract_headers_anchors_title_words(soup, detected_lang: str = 'english'):
        h1 = _explode_texts_to_words(_extract_tag_texts(soup, "h1"), detected_lang)
        h2 = _explode_texts_to_words(_extract_tag_texts(soup, "h2"), detected_lang)
        h3 = _explode_texts_to_words(_extract_tag_texts(soup, "h3"), detected_lang)
        h4 = _explode_texts_to_words(_extract_tag_texts(soup, "h4"), detected_lang)
        h5 = _explode_texts_to_words(_extract_tag_texts(soup, "h5"), detected_lang)
        h6 = _explode_texts_to_words(_extract_tag_texts(soup, "h6"), detected_lang)
        a = _explode_texts_to_words(_extract_tag_texts(soup, "a"), detected_lang)
        ti = _explode_texts_to_words(_extract_tag_texts(soup, "title"), detected_lang)
        strong = _explode_texts_to_words(_extract_tag_texts(soup, "strong"), detected_lang)
        em = _explode_texts_to_words(_extract_tag_texts(soup, "em"), detected_lang)
        b = _explode_texts_to_words(_extract_tag_texts(soup, "b"), detected_lang)
        return h1, h2, h3, h4, h5, h6, a, ti, strong, em, b

    def _tf_idf_score(freq: int, total_tokens: int, position_boost: float = 0) -> float:
        """Improved TF-IDF-like scoring with position boost"""
        if total_tokens == 0:
            return 0
        tf_score = (1 + math.log(freq)) * 15 if freq > 0 else 0
        score = tf_score + position_boost * 1.5
        return score

    def _compute_keyword_scores(words: list, soup, u: str, detected_lang: str = 'english') -> dict:
        freq = Counter(words)
        total_tokens = len(words)

        word_positions = defaultdict(list)
        for idx, word in enumerate(words):
            word_positions[word].append(idx)

        position_boosts = {}
        for word, positions in word_positions.items():
            avg_position = sum(positions) / len(positions) / max(total_tokens, 1)
            position_boosts[word] = (1 - avg_position) * 5

        h1, h2, h3, h4, h5, h6, anchor, title, strong, em, b = _extract_headers_anchors_title_words(soup, detected_lang)
        url_host = _split_url_host(u)
        url_path = _split_url_path_and_query(u, url_host)
        meta_keywords = _extract_meta_keywords(soup, detected_lang)

        headers_names = ["H1", "H2", "H3", "H4", "H5", "H6", "A", "Title", "URL-H", "URL-Q", "Meta", "Strong", "Em", "B"]
        headers_scores = [15, 12, 10, 7, 5, 4, 2, 15, 12, 10, 20, 9, 8, 7]
        headers_lists = [h1, h2, h3, h4, h5, h6, anchor, title, url_host, url_path, meta_keywords, strong, em, b]

        word_info = {}
        for w, c in freq.items():
            position_boost = position_boosts.get(w, 0)
            base = _tf_idf_score(c, total_tokens, position_boost)
            tag_boost, tag_names = 0.0, []
            for idx, toks in enumerate(headers_lists):
                if w in toks:
                    tag_boost += headers_scores[idx]
                    tag_names.append(headers_names[idx])

            if len(tag_names) > 1:
                tag_boost *= 1.4
            elif len(tag_names) == 1 and tag_names[0] in ['Meta', 'Title', 'H1']:
                tag_boost *= 1.2

            word_info[w] = (c, tag_names, base + tag_boost)

        return word_info

    # --------------------- pipeline ---------------------
    clean_text, soup = _fetch_page(url)
    detected_lang, stopword_list = _detect_language_and_stopwords(clean_text)
    tokens = _clean_text_to_words(clean_text, stopword_list, detected_lang)

    if not tokens:
        return [] if not return_details else []

    # Method 1: Traditional TF-IDF-like scoring with tag boosts
    keyword_data = _compute_keyword_scores(tokens, soup, url, detected_lang)

    # Method 2: YAKE keyword extraction (statistical approach)
    yake_keywords = []
    try:
        lang_map = {'finnish': 'fi', 'english': 'en', 'swedish': 'sv', 'norwegian': 'no', 'danish': 'da'}
        yake_lang = lang_map.get(detected_lang, 'en')

        kw_extractor = yake.KeywordExtractor(
            lan=yake_lang,
            n=1,
            dedupLim=0.9,
            top=k*4,
            features=None
        )

        yake_results = kw_extractor.extract_keywords(clean_text)

        for keyword, score in yake_results:
            keyword_clean = re.sub(r'[^a-zA-ZåäöÅÄÖ]+', '', keyword.lower())
            if len(keyword_clean) > 1:
                normalized = _normalize_finnish_word(keyword_clean, detected_lang)
                yake_keywords.append((normalized, 120 - (score * 12)))
    except Exception as e:
        pass

    # Merge both methods with weighted combination
    combined_scores = {}

    for word, (freq, tags, score) in keyword_data.items():
        combined_scores[word] = score * 0.6

    for word, score in yake_keywords:
        if word in combined_scores:
            combined_scores[word] += score * 0.4
        else:
            combined_scores[word] = score * 0.4

    top_words = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:k]

    if return_details:
        result = []
        for word, combined_score in top_words:
            if word in keyword_data:
                freq, tags, _ = keyword_data[word]
                result.append((word, freq, combined_score, tags))
            else:
                result.append((word, 0, combined_score, ['YAKE']))
        return result
    else:
        return [w for w, _ in top_words]


# --------------------- evaluation (Ruoka.fi - Online) ---------------------

import urllib.request

BASE = "https://cs.uef.fi/~himat/WebRank/dataset_12/dataset_12/ruoka/"

from nltk.stem.snowball import SnowballStemmer

def _normalize_finnish_word_eval(word):
    """Normalize Finnish words using stemming"""
    word = word.lower()
    try:
        stemmer = SnowballStemmer('finnish')
        return stemmer.stem(word)
    except:
        return word

def Get_Prc_Rcl_Fscr_input_GT_and_Keywords_List(ground_truth, keywords):
    matches = [(word, ground_truth.count(word)) for word in ground_truth if word in keywords]

    ground_truth_count = len(ground_truth)
    keywords_count = len(keywords)
    match_count = len(matches)

    if ground_truth_count == 0 or keywords_count == 0:
        return (0, 0, 0, [])

    precision = match_count / keywords_count
    recall = match_count / ground_truth_count

    if precision + recall == 0:
        return (0, 0, 0, [])

    f_score = (2 * precision * recall) / (precision + recall)
    return (precision, recall, f_score, matches)


def Make_score_round_and_divide(precision_sum, recall_sum, fscore_sum, total_webpages):
    avg_precision = round(precision_sum / total_webpages, 2)
    avg_recall = round(recall_sum / total_webpages, 2)
    avg_fscore = round(fscore_sum / total_webpages, 2)
    return (avg_precision, avg_recall, avg_fscore)


def read_url(url):
    with urllib.request.urlopen(url) as f:
        return f.read().decode("utf-8-sig").strip()


def load_ruoka_case(index):
    """Load a test case from online ruoka dataset"""
    base = f"{BASE}{index}"

    gt_text = read_url(f"{base}/GT.txt")
    gt_tokens = gt_text.lower().split()
    gt_tokens_stemmed = [_normalize_finnish_word_eval(token) for token in gt_tokens]

    html_url = f"{base}/"

    return html_url, gt_tokens_stemmed

def my_debug(URL, gt_keywords, drank_keywords, matches, p, r, f):
    print("URL:", URL)
    print("Ground Truth Keywords:", gt_keywords)
    print("Extracted Keywords:", drank_keywords)
    print("Matches:", matches)
    print("Precision:", p, "Recall:", r, "F-score:", f)

def Score_evaluation(total_webpages):
    precision_sum = 0.0
    recall_sum = 0.0
    fscore_sum = 0.0

    webpage_ids = []
    precisions = []
    recalls = []
    fscores = []
    total_gt = []
    total_kw = []

    for i in range(total_webpages):
        URL, gt_keywords = load_ruoka_case(str(i))
        drank_keywords = get_top_keywords(URL, k=15)
        total_gt.extend(gt_keywords)
        total_kw.extend(drank_keywords)

        p, r, f, matches = Get_Prc_Rcl_Fscr_input_GT_and_Keywords_List(gt_keywords, drank_keywords)
        # my_debug(URL, gt_keywords, drank_keywords, matches, p, r, f)

        webpage_ids.append(i)
        precisions.append(p)
        recalls.append(r)
        fscores.append(f)

        precision_sum += p
        recall_sum += r
        fscore_sum += f

    return precision_sum, recall_sum, fscore_sum, webpage_ids, precisions, recalls, fscores, total_gt, total_kw

total_webpages = 100
precision_sum, recall_sum, fscore_sum, webpage_ids, precisions, recalls, fscores, total_gt, total_kw = Score_evaluation(total_webpages)

avg_p, avg_r, avg_f = Make_score_round_and_divide(
    precision_sum, recall_sum, fscore_sum, total_webpages
)

print("=== AVERAGE OVER ALL WEBPAGES ===")
print("Average Precision:", avg_p)
print("Average Recall   :", avg_r)
print("Average F-score  :", avg_f)

print("\n=== Noise Words in Extracted Keywords (not in GT) ===")
noise_words = [word for word in total_kw if word not in total_gt]
print(f"Total noise words: {len(noise_words)}")
print(set(noise_words))
print(f"Total unique noise words: {len(set(noise_words))}")