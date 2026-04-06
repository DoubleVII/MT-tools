from __future__ import annotations

import re
import unicodedata


_whitespace_re = re.compile(r"\s+")
_space_before_punct_re = re.compile(r"\s+([,.;:!?])")
_multi_newline_re = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\u200e", "")
    text = text.replace("\u200f", "")
    text = text.replace("\ufeff", "")

    text = _whitespace_re.sub(" ", text)
    text = _space_before_punct_re.sub(r"\1", text)
    return text.strip()


def normalize_multiline_text(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\u200e", "")
    text = text.replace("\u200f", "")
    text = text.replace("\ufeff", "")

    lines = [normalize_text(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    text = "\n".join(lines)
    text = _multi_newline_re.sub("\n\n", text)
    return text.strip()


def truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0:
        return "", bool(text)

    if len(text) <= max_chars:
        return text, False

    truncated = text[:max_chars].rstrip()

    # 尽量在句子/空格附近截断
    cut_positions = [
        truncated.rfind("\n\n"),
        truncated.rfind(". "),
        truncated.rfind("。"),
        truncated.rfind("! "),
        truncated.rfind("? "),
        truncated.rfind(" "),
    ]
    cut = max(cut_positions)
    if cut > max_chars * 0.6:
        truncated = truncated[:cut].rstrip()

    return truncated, True


def normalize_section_title(title: str) -> str:
    title = normalize_text(title).lower()
    title = title.replace("_", " ")
    return title
