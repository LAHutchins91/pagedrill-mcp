"""Word-level equality. Citation mechanics and regulation date/time forms are the only deltas."""

from __future__ import annotations

import re

from .errors import PagedrillRefusal

TOKEN = re.compile(r"[\w’'-]+|[^\w\s]", re.UNICODE)


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text)


def assert_apa_body_words(before: str, after: str, surnames: set[str], years: set[str]) -> None:
    """Body prose may change only by citation punctuation and name-list mechanics.

    A removed token must be punctuation, 'and', '&', a reference surname, or a year
    already in the paper. An added token must be punctuation, 'et', 'al', 'and', '&',
    or a surname or year already in the paper. Any other word is a refusal.
    """
    import difflib

    bw = tokens(before)
    aw = tokens(after)
    punctuation = {",", ";", ".", "(", ")", "&"}
    allowed_add = punctuation | {"and", "et", "al"} | surnames | years
    allowed_del = punctuation | {"and"} | surnames | years
    unexpected: list[str] = []
    for line in difflib.ndiff(bw, aw):
        if line.startswith("+ "):
            tok = line[2:]
            if tok not in allowed_add:
                unexpected.append("+" + tok)
        elif line.startswith("- "):
            tok = line[2:]
            if tok not in allowed_del:
                unexpected.append("-" + tok)
    if unexpected:
        raise PagedrillRefusal(
            "The format would change the author's words. Pagedrill refused it and did not save.",
            "word_change",
        )


def assert_ieee_body_words(before: str, after: str, surnames: set[str], years: set[str]) -> None:
    """Body sentences may change only by [n] citation markers.

    Added tokens are brackets or citation numbers. Removed tokens are citation
    punctuation, 'and', 'et', 'al', a surname, or a year already in the paper.
    """
    import difflib

    punctuation = {",", ";", ".", "(", ")", "&"}
    allowed_add = {"[", "]"}
    allowed_del = punctuation | {"and", "et", "al"} | surnames | years
    unexpected: list[str] = []
    for line in difflib.ndiff(tokens(before), tokens(after)):
        if line.startswith("+ "):
            tok = line[2:]
            if tok not in allowed_add and not tok.isdigit():
                unexpected.append("+" + tok)
        elif line.startswith("- "):
            tok = line[2:]
            if tok not in allowed_del:
                unexpected.append("-" + tok)
    if unexpected:
        raise PagedrillRefusal(
            "The format would change the author's words. Pagedrill refused it and did not save.",
            "word_change",
        )
