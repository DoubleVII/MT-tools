import re
import unicodedata

WEAK_PUNCT_TRANSLATION = str.maketrans({
    "_": " ",
    "·": " ",
    "•": " ",
    "・": " ",
    "·": " ",
    "—": " ",
    "–": " ",
    "-": " ",
    "‑": " ",
    "‒": " ",
    "−": " ",
    ":": " ",
    "：": " ",
    "/": " ",
    "\\": " ",
    ",": " ",
    "，": " ",
    ".": " ",
    "。": " ",
    "(": " ",
    ")": " ",
    "（": " ",
    "）": " ",
    "[": " ",
    "]": " ",
    "{": " ",
    "}": " ",
    "'": " ",
    '"': " ",
    "“": " ",
    "”": " ",
    "‘": " ",
    "’": " ",
    "!": " ",
    "！": " ",
    "?": " ",
    "？": " ",
    ";": " ",
    "；": " ",
    "&": " ",
    "+": " ",
    "=": " ",
    "|": " ",
    "~": " ",
    "`": " ",
})


MULTISPACE_RE = re.compile(r"\s+")
ASCII_TOKEN_RE = re.compile(r"[a-z0-9]+")



def normalize_name(text: str | None) -> str | None:
    if not text:
        return None
    s = text.strip()
    if not s:
        return None
    s = unicodedata.normalize("NFC", s)
    s = s.casefold()
    s = s.translate(WEAK_PUNCT_TRANSLATION)
    s = MULTISPACE_RE.sub(" ", s).strip()
    return s or None


def normalize_name_loose(text: str | None) -> str | None:
    s = normalize_name(text)
    if not s:
        return None
    s = unicodedata.normalize("NFKC", s)
    s = s.replace(" ", "")
    return s or None



def char_script_flags(s: str):
    has_cjk = False
    has_hiragana_katakana = False
    has_hangul = False

    for ch in s:
        code = ord(ch)
        if (
            0x4E00 <= code <= 0x9FFF or
            0x3400 <= code <= 0x4DBF or
            0xF900 <= code <= 0xFAFF
        ):
            has_cjk = True
        elif 0x3040 <= code <= 0x30FF:
            has_hiragana_katakana = True
        elif 0xAC00 <= code <= 0xD7AF:
            has_hangul = True

    return has_cjk, has_hiragana_katakana, has_hangul


def contains_cjk_like(s: str) -> bool:
    has_cjk, has_jp, has_ko = char_script_flags(s)
    return has_cjk or has_jp or has_ko


def generate_char_ngrams(s: str, n_values=(2, 3)) -> list[str]:
    s = s.strip()
    if not s:
        return []

    chars = [ch for ch in s if not ch.isspace()]
    L = len(chars)
    if L == 0:
        return []

    out = []
    for n in n_values:
        if L < n:
            continue
        for i in range(L - n + 1):
            out.append("".join(chars[i:i+n]))
    return out


def build_fts_query(query: str) -> str | None:
    norm = normalize_name(query)
    loose = normalize_name_loose(query)

    terms = []
    seen = set()

    def add(x: str | None):
        if not x:
            return
        x = x.strip()
        if not x or x in seen:
            return
        seen.add(x)
        terms.append(x)

    add(norm)
    add(loose)

    if norm:
        for tok in ASCII_TOKEN_RE.findall(norm):
            add(tok)

    base_for_ngram = loose or norm or ""
    if base_for_ngram and contains_cjk_like(base_for_ngram):
        for gram in generate_char_ngrams(base_for_ngram, n_values=(2, 3)):
            add(gram)

    if not terms:
        return None

    # 用 AND 提高精确性；后续你可以再调成 OR / 混合
    return " AND ".join(f'"{t}"' for t in terms)
