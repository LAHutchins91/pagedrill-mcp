"""MLA Handbook, 9th ed. citation mechanics transcribed from a print copy.

Sections implemented: 2.90, 2.106–2.109, 2.139, 5.7, 5.8, 5.89–5.91, 5.120–5.130, 6.5, 6.6, 6.28–6.30.
Prose italics and quotation marks follow the works-cited source type (2.106–2.109).
A title with no type signal is left as typed. Sec. 2.110 was not supplied.
Quoted-inside-quoted and quoted-inside-italic title patterns were not on the supplied pages.
"""

from __future__ import annotations

import re
import unicodedata

EN = "\u2013"
EM_DASHES = "\u2014\u2014\u2014"
CITE = "MLA Handbook, 9th ed., sec. {section}"

# Sec. 2.110's own text was not supplied (2.107 only points at it).
# The section number for the unread title-within-a-title patterns was not on the pages.
UNSOURCED_SECTIONS = (
    "2.110",
    "title-within-a-title: quoted title inside a quoted title; quoted title inside an italic title",
)

# 2.106–2.109. Keys are citation source types. A bare title has no type, so it is not restyled.
_ITALIC_TYPES = {
    "book", "play", "newspaper", "journal", "magazine",
    "epic", "premodern-epic",
    "dissertation",
    "film", "movie",
    "tv-series", "television-series", "streaming-series",
    "website", "app",
    "video-game",
    "radio", "radio-program",
    "podcast",
    "album", "music-album",
    "musical-composition", "long-musical-composition",
    "visual-art", "artwork", "painting",
    "performing-arts", "performance",
    "court-case", "legal-case",
    "ship", "aircraft", "spacecraft",
}
_QUOTED_TYPES = {
    "article", "journal-article", "magazine-article",
    "encyclopedia-article",
    "essay",
    "short-story", "story",
    "poem",
    "chapter",
    "web-page", "webpage",
    "episode", "tv-episode",
    "song",
    "song-video", "music-video",
    "lecture",
}
# 2.107 names these as not italic. Earthwork, ancient artwork, and building are the
# one sentence that points at 2.110; only an explicit type is honored.
_PLAIN_TYPES = {
    "organization", "company",
    "board-game", "card-game",
    "earthwork", "ancient-artwork", "building",
}
_VESSEL_TYPES = {"ship", "aircraft", "spacecraft"}
_VESSEL_PREFIX = re.compile(r"^(?:USS|HMS)\s+", re.IGNORECASE)
_QUOTE_PAIRS = {"\u201c": "\u201d", "\u2018": "\u2019", '"': '"'}

# 2.90. The parenthetical lists in the transcription are examples of categories.
# Articles and coordinating conjunctions stay lowercase. Prepositions stay lowercase.
# Subordinating conjunctions are capitalized. "for" is a preposition and a coordinating
# conjunction, so it stays lowercase either way. "after", "before", and "as" (and
# "until" / "since", the same split) are prepositions unless they introduce a clause.
# A word whose part of speech cannot be settled is left as typed and flagged.
_ARTICLES = {"a", "an", "the"}
_COORD = {"and", "but", "for", "nor", "or", "so", "yet"}
_PREP_ALWAYS = {
    "against", "amid", "amidst", "among", "amongst", "beside", "besides", "beneath",
    "between", "beyond", "despite", "during", "except", "from", "into", "of", "onto",
    "per", "plus", "regarding", "throughout", "to", "toward", "towards", "underneath",
    "unto", "upon", "versus", "via", "with", "within", "without",
}
_PREP_IF_OBJECT = {
    "about", "above", "across", "along", "around", "at", "behind", "below", "by",
    "down", "in", "inside", "near", "off", "on", "out", "outside", "over", "past",
    "through", "under", "up",
}
# Preposition, or a subordinating conjunction when it introduces a clause.
_PREP_OR_SUBORD = {"after", "before", "as", "until", "since", "till"}
_SUBORD = {"although", "because", "if", "unless", "when", "where", "while", "whereas", "whether"}
_DET = {
    "a", "an", "the", "my", "your", "his", "her", "its", "our", "their",
    "this", "that", "these", "those", "some", "any", "no", "every", "each", "another",
}
_SUBJECT = {"i", "we", "you", "he", "she", "it", "they", "who", "whoever"}
_CLAUSE_OPENERS = _SUBORD | {"how", "what", "why", "who", "whom"}
_AUX = {
    "am", "is", "are", "was", "were", "be", "been", "being",
    "has", "have", "had", "do", "does", "did",
    "will", "would", "can", "could", "may", "might", "must", "shall", "should",
}
_CLEAR_VERBS = _AUX | {
    "ended", "ends", "fell", "falls", "came", "comes", "went", "goes",
    "died", "dies", "began", "begins", "started", "starts", "passed", "passes",
    "rose", "rises", "left", "leaves", "knew", "knows", "stopped", "stops",
    "worked", "works", "lived", "lives", "spoke", "speaks", "said", "says",
    "wrote", "writes", "made", "makes", "took", "takes", "gave", "gives",
    "saw", "sees", "found", "finds", "became", "becomes", "seemed", "seems",
    "remained", "remains", "appeared", "appears", "stood", "stands",
}
_CLEAR_ADJ = {
    "long", "great", "old", "new", "other", "high", "small", "large", "little",
    "big", "good", "bad", "early", "late", "next", "last", "first", "second",
    "third", "short", "young", "whole", "same", "few", "many", "major", "minor",
    "civil", "cold", "hot", "public", "private",
}
_NUMBER_WORDS = {
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety", "hundred", "thousand",
}
_ADVERBS = {
    "again", "away", "apart", "aside", "back", "forward", "now", "then", "still",
    "regardless", "ahead", "together", "abroad",
}
_LOWER_PHRASES = (("according", "to"),)
_CAP_PHRASES = (("as", "if"), ("as", "soon", "as"))
_HYPHEN_LOWER = _ARTICLES | _COORD | _PREP_ALWAYS
_ALL_PREPS = _PREP_ALWAYS | _PREP_IF_OBJECT | _PREP_OR_SUBORD | _COORD
# The transcription gives one closed prefix. No other prefix is treated as closed.
_CLOSED_HYPHEN = {"anti-slavery": "Anti-slavery"}

# 5.124 fixture, in handbook order. Spaces and punctuation are part of the labels.
HANDBOOK_5_124_ORDER = (
    "Achebe, Chinua",
    "Beatles",
    "Beowulf",
    "Christine de Pizan",
    "Descartes, René",
    "De Sica, Vittorio",
    "Duong Thu Huong",
    "Executive summary",
    "Film Crit Hulk",
    "Gott",
    "Götz",
    "MacDonald, George",
    "McCullers, Carson",
    "MLA Handbook",
    "Modern Language Association",
    "Moonlight",
    "Morris, Robert",
    "Morris, William",
    "Morrison, Toni",
    "Saint-Exupéry, Antoine de",
    "The Second Shepherds' Play",
    "St. Denis, Ruth",
    "United Nations",
    "United States, Congress, House, Permanent Select Committee on Intelligence",
    "United States, Department of Health and Human Services, Centers for Disease Control and Prevention",
)

# 2.139 examples. Keys are the unshortened span; values use an en dash.
RANGE_EXAMPLES = {
    "2-3": "2–3",
    "10-12": "10–12",
    "21-48": "21–48",
    "89-99": "89–99",
    "96-101": "96–101",
    "103-104": "103–04",
    "395-401": "395–401",
    "923-1003": "923–1,003",
    "1003-1005": "1,003–05",
    "1608-1774": "1,608–774",
    "ii-iii": "ii–iii",
    "xxi-xlviii": "xxi–xlviii",
    "A110-A112": "A110–A112",
}

_WORD = re.compile(
    r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*(?:-[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*)*"
)


def cite(section: str) -> str:
    return CITE.format(section=section)


def title_case(text: str, *, exact: bool = False) -> str:
    """Sec. 2.90. exact=True keeps an untitled poem or message as transcribed."""
    cased, _flags = title_case_with_flags(text, exact=exact)
    return cased


def title_case_with_flags(text: str, *, exact: bool = False) -> tuple[str, list[dict]]:
    """Sec. 2.90. Ambiguous parts of speech are returned as flags and left as typed."""
    if exact or not text or not text.strip():
        return text, []
    pieces = re.split(r"(?<=[A-Za-z])(\s*:\s*)(?=[A-Za-z])", text)
    out = []
    flags: list[dict] = []
    for piece in pieces:
        if re.fullmatch(r"\s*:\s*", piece):
            out.append(": ")
        else:
            out.append(_case_segment(piece, flags))
    return "".join(out), flags


def _case_segment(text: str, flags: list[dict]) -> str:
    tokens = re.findall(
        r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*(?:-[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*)*|[^A-Za-z0-9]+",
        text,
    )
    word_at = [i for i, token in enumerate(tokens) if _WORD.fullmatch(token)]
    if not word_at:
        return text
    lowered = [tokens[i].lower() for i in word_at]
    style = ["cap"] * len(lowered)
    claimed = _claim_phrases(lowered, style)
    last = len(lowered) - 1
    for i, word in enumerate(lowered):
        if i in (0, last) or i in claimed:
            continue
        if word in _ARTICLES or word in _COORD or word in _PREP_ALWAYS:
            style[i] = "lower"
        elif word in _SUBORD:
            style[i] = "cap"
        elif word in _PREP_OR_SUBORD:
            _style_prep_or_subord(style, flags, i, word, lowered[i + 1 :])
        elif word in _PREP_IF_OBJECT:
            _style_prep_object(style, flags, i, word, lowered[i + 1 :])
    style[0] = "cap"
    style[last] = "cap"
    cased = list(tokens)
    for n, index in enumerate(word_at):
        raw = tokens[index]
        if style[n] == "keep":
            continue
        if style[n] == "lower":
            cased[index] = raw.lower()
        elif raw.lower() in _CLOSED_HYPHEN:
            cased[index] = _CLOSED_HYPHEN[raw.lower()]
        elif "-" in raw:
            cased[index] = _one_word(raw, first=n == 0, last=n == last)
        else:
            cased[index] = _cap_word(raw)
    return "".join(cased)


def _claim_phrases(lowered: list[str], style: list[str]) -> set[int]:
    claimed: set[int] = set()
    for phrase in _LOWER_PHRASES:
        claimed |= _mark_phrase(lowered, style, phrase, "lower")
    for phrase in _CAP_PHRASES:
        claimed |= _mark_phrase(lowered, style, phrase, "cap")
    return claimed


def _style_prep_or_subord(style: list[str], flags: list[dict], index: int, word: str, tail: list[str]) -> None:
    kind = _tail_structure(tail)
    if kind == "np":
        style[index] = "lower"
    elif kind in ("clause", "clause-object"):
        style[index] = "cap"
    else:
        style[index] = "keep"
        flags.append(_pos_flag(
            word,
            f"Sec. 2.90 lowercases prepositions and capitalizes a subordinating conjunction. "
            f"'{word}' is a preposition unless it introduces a clause. "
            f"The part of speech could not be determined, so the word was left as typed.",
        ))


def _style_prep_object(style: list[str], flags: list[dict], index: int, word: str, tail: list[str]) -> None:
    if word == "about" and tail and (tail[0].isdigit() or tail[0] in _NUMBER_WORDS):
        style[index] = "keep"
        flags.append(_pos_flag(
            word,
            "Sec. 2.90 lowercases 'about' when it is a preposition. Before a numeral it can also "
            "be the adverb meaning approximately. The part of speech could not be determined, "
            "so the word was left as typed.",
        ))
        return
    kind = _tail_structure(tail)
    if kind == "adverb":
        style[index] = "keep"
        flags.append(_pos_flag(
            word,
            f"Sec. 2.90 lowercases '{word}' as a preposition and capitalizes it as an adverb. "
            f"The part of speech could not be determined, so the word was left as typed.",
        ))
    elif kind == "none":
        style[index] = "cap"
    else:
        # A following nominal or clause is the object, so the word is a preposition.
        style[index] = "lower"


def _pos_flag(word: str, why: str) -> dict:
    return {"item": f"Title word '{word}'", "why": why, "rule": cite("2.90")}


def _tail_structure(words: list[str]) -> str:
    """Classify what follows a preposition or a preposition/conjunction."""
    if not words:
        return "none"
    if len(words) == 1 and words[0] in _ADVERBS:
        return "adverb"
    if words[0] in _CLAUSE_OPENERS and len(words) > 1:
        return "clause-object"
    if words[0] in _SUBJECT and len(words) >= 2:
        return "clause"
    if words[0] in _ALL_PREPS:
        return "np"
    i = 0
    while i < len(words) and (words[i] in _DET or words[i] in _NUMBER_WORDS or words[i].isdigit()):
        i += 1
    while i < len(words) and words[i] in _CLEAR_ADJ:
        i += 1
    if i >= len(words):
        return "unclear"
    rest = words[i + 1 :]
    if words[i] in _SUBJECT and rest:
        return "clause"
    if not rest:
        return "np"
    if any(word in _CLEAR_VERBS for word in rest):
        return "clause"
    if rest[0] in _ALL_PREPS or rest[0] in _CLAUSE_OPENERS:
        return "np"
    return "unclear"


def _mark_phrase(lowered: list[str], style: list[str], phrase: tuple[str, ...], kind: str) -> set[int]:
    claimed: set[int] = set()
    size = len(phrase)
    last = len(lowered) - 1
    for offset in range(len(lowered) - size + 1):
        if tuple(lowered[offset : offset + size]) != phrase:
            continue
        for n in range(size):
            claimed.add(offset + n)
            if kind == "lower" and offset + n in (0, last):
                continue
            style[offset + n] = kind
    return claimed


def _one_word(token: str, *, first: bool, last: bool) -> str:
    closed = _CLOSED_HYPHEN.get(token.lower())
    if closed:
        return closed
    if "-" in token and token.lower() not in _CLOSED_HYPHEN:
        parts = token.split("-")
        cased = []
        for i, part in enumerate(parts):
            cased.append(_one_word(part, first=first and i == 0, last=last and i == len(parts) - 1))
        return "-".join(cased)
    lower = token.lower()
    if not first and not last and lower in _HYPHEN_LOWER:
        return lower
    return _cap_word(token)


def _cap_word(token: str) -> str:
    lower = token.lower()
    return lower[:1].upper() + lower[1:] if lower else token


def prose_title_treatment(source_type: str | None) -> str | None:
    """Italic, quotation marks, or plain, from a works-cited source type. Unknown types return None."""
    key = re.sub(r"[\s_]+", "-", str(source_type or "").strip().lower())
    if key in _ITALIC_TYPES:
        return "italic"
    if key in _QUOTED_TYPES:
        return "quotes"
    if key in _PLAIN_TYPES:
        return "plain"
    return None


def style_prose_titles(text: str, italic_spans: list[str] | None, entries: list[dict]) -> tuple[str, list[str], list[dict]]:
    """Secs. 2.106–2.109. Restyle a prose title only when an entry type settles it.

    The same title styled two ways, with no type, is flagged and left as typed.
    A quoted title whose entry is an italicized work is italicized and flagged.
    Two italic titles stay italic (2.108). An italic title inside a quoted title stays
    italic (2.109). Quoted-inside-quoted and quoted-inside-italic are left as typed.
    """
    spans = list(italic_spans or [])
    if not text:
        return text, spans, []
    catalog, flags = _title_catalog(entries)
    if not catalog:
        return text, spans, flags
    italic = _span_flags(text, spans)
    mentions = _title_mentions(text, catalog)
    if not mentions:
        return text, spans, flags
    frozen = _freeze_unread_nests(mentions, flags)
    _flag_inconsistent(text, italic, mentions, flags)
    edits = []
    for mention in mentions:
        if id(mention) in frozen or mention["treatment"] is None:
            continue
        if _styled_by_ancestor(mention, mentions, frozen):
            continue
        edit = _mention_edit(text, italic, mention, mentions)
        if edit:
            edits.append(edit)
    if not edits:
        return text, spans, flags
    updated, new_spans, edit_flags = _apply_title_edits(text, italic, edits)
    return updated, new_spans, flags + edit_flags


def _title_catalog(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    found: dict[str, dict] = {}
    flags: list[dict] = []
    for entry in entries or []:
        title = str(entry.get("title") or "").strip()
        if len(title) < 2:
            continue
        treatment = prose_title_treatment(entry.get("type"))
        vessel = _norm_type(entry.get("type")) in _VESSEL_TYPES or bool(_VESSEL_PREFIX.match(title))
        _add_title(found, flags, title, treatment, vessel)
        container = str(entry.get("container") or "").strip()
        # A short work's container is a long-form work (2.106, 2.107).
        if container and treatment == "quotes":
            _add_title(found, flags, container, "italic", bool(_VESSEL_PREFIX.match(container)))
    return list(found.values()), flags


def _add_title(found: dict, flags: list[dict], phrase: str, treatment: str | None, vessel: bool) -> None:
    key = phrase.casefold()
    prev = found.get(key)
    if prev is None:
        found[key] = {"phrase": phrase, "treatment": treatment, "vessel": vessel}
        return
    if prev["treatment"] is None and treatment is not None:
        prev["treatment"] = treatment
        prev["vessel"] = vessel
        return
    if treatment is not None and prev["treatment"] is not None and prev["treatment"] != treatment:
        prev["treatment"] = None
        flags.append({
            "item": f'Prose title "{phrase}"',
            "why": "Works-cited entries give this title more than one source type, so the prose was left as typed.",
            "rule": cite("2.106"),
        })


def _norm_type(value) -> str:
    return re.sub(r"[\s_]+", "-", str(value or "").strip().lower())


def _span_flags(text: str, spans: list[str]) -> list[bool]:
    flags = [False] * len(text)
    pos = 0
    for span in spans:
        if not span:
            continue
        at = text.find(span, pos)
        if at < 0:
            at = text.find(span)
        if at < 0:
            continue
        for index in range(at, at + len(span)):
            flags[index] = True
        pos = at + len(span)
    return flags


def _title_mentions(text: str, catalog: list[dict]) -> list[dict]:
    mentions = []
    for item in sorted(catalog, key=lambda row: len(row["phrase"]), reverse=True):
        pattern = re.compile(r"(?<!\w)" + re.escape(item["phrase"]) + r"(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(text):
            mentions.append({
                "start": match.start(),
                "end": match.end(),
                "text": text[match.start():match.end()],
                "phrase": item["phrase"],
                "treatment": item["treatment"],
                "vessel": item["vessel"],
            })
    return mentions


def _contains(outer: dict, inner: dict) -> bool:
    return (
        outer is not inner
        and outer["start"] <= inner["start"]
        and inner["end"] <= outer["end"]
        and (outer["start"], outer["end"]) != (inner["start"], inner["end"])
    )


def _direct_children(mention: dict, mentions: list[dict]) -> list[dict]:
    contained = [other for other in mentions if _contains(mention, other)]
    return [child for child in contained if not any(_contains(mid, child) for mid in contained)]


def _freeze_unread_nests(mentions: list[dict], flags: list[dict]) -> set[int]:
    """Quoted-inside-quoted and quoted-inside-italic were not on the supplied pages."""
    frozen: set[int] = set()
    seen = set()
    for outer in mentions:
        for inner in mentions:
            if not _contains(outer, inner):
                continue
            unread = (
                (outer["treatment"] == "quotes" and inner["treatment"] == "quotes")
                or (outer["treatment"] == "italic" and inner["treatment"] == "quotes")
            )
            if not unread:
                continue
            frozen.add(id(outer))
            frozen.add(id(inner))
            key = (outer["start"], outer["end"], inner["start"], inner["end"])
            if key in seen:
                continue
            seen.add(key)
            flags.append({
                "item": f'Prose title "{inner["text"]}" inside "{outer["text"]}"',
                "why": (
                    "A quoted title inside a quoted title, or a quoted title inside an italic title, "
                    "was left as typed. Those patterns were not on the supplied pages. "
                    "Sec. 2.108 keeps two italic titles italic. A sec. 2.109 web-page example keeps "
                    "an italic title italic inside quotation marks."
                ),
                "rule": cite("2.108"),
            })
    for mention in mentions:
        if id(mention) not in frozen:
            continue
        for other in mentions:
            if _contains(mention, other):
                frozen.add(id(other))
    return frozen


def _flag_inconsistent(text: str, italic: list[bool], mentions: list[dict], flags: list[dict]) -> None:
    grouped: dict[str, list] = {}
    labels: dict[str, str] = {}
    for mention in mentions:
        if mention["treatment"] is not None:
            continue
        key = mention["phrase"].casefold()
        labels.setdefault(key, mention["text"])
        grouped.setdefault(key, []).append(_mention_signature(text, italic, mention))
    for key, signatures in grouped.items():
        if len(set(signatures)) < 2:
            continue
        flags.append({
            "item": f'Prose title "{labels[key]}"',
            "why": (
                "This title is styled in more than one way, and the works-cited entry has no source type "
                "that settles italics or quotation marks. Each mention was left as typed."
            ),
            "rule": cite("2.106"),
        })


def _mention_signature(text: str, italic: list[bool], mention: dict) -> tuple:
    quoted = _quote_bounds(text, mention["start"], mention["end"]) is not None
    styled = any(italic[mention["start"]:mention["end"]])
    return (quoted, styled)


def _styled_by_ancestor(mention: dict, mentions: list[dict], frozen: set[int]) -> bool:
    for other in mentions:
        if not _contains(other, mention):
            continue
        if id(other) in frozen or other["treatment"] is None:
            continue
        return True
    return False


def _quote_bounds(text: str, start: int, end: int) -> tuple[int, int] | None:
    if start < 1 or end >= len(text):
        return None
    closing = _QUOTE_PAIRS.get(text[start - 1])
    if closing and text[end] == closing:
        return start - 1, end + 1
    return None


def _mention_edit(text: str, italic: list[bool], mention: dict, mentions: list[dict]) -> tuple | None:
    children = _direct_children(mention, mentions)
    treatment = mention["treatment"]
    quoted = _quote_bounds(text, mention["start"], mention["end"])
    mask = _style_mask(mention, children, italic, treatment)
    inner = mention["text"]
    changed = list(italic[mention["start"]:mention["end"]]) != mask
    if treatment == "italic":
        if quoted:
            changed = True
        if not changed:
            return None
        why = (
            "The works-cited entry is a self-contained work (secs. 2.106–2.107). "
            "The prose mention was set in italics."
        )
        if quoted:
            why = (
                "The works-cited entry is a self-contained work (secs. 2.106–2.107), "
                "but this mention is in quotation marks. The quotation marks were removed "
                "and the title was italicized."
            )
        start, end = quoted if quoted else (mention["start"], mention["end"])
        return _edit(start, end, inner, mask, mention["text"], why, "2.107")
    if treatment == "quotes":
        own_italic = _own_italic(mention, children, italic)
        if quoted and not own_italic and not changed:
            return None
        if quoted:
            start, end = mention["start"], mention["end"]
            replacement = inner
        else:
            start, end = mention["start"], mention["end"]
            replacement = "\u201c" + inner + "\u201d"
            mask = [False] + mask + [False]
            changed = True
        why = (
            "The works-cited type is a short work contained in another (secs. 2.106 and 2.109), "
            "so the prose mention is in quotation marks and that title itself is not italic."
        )
        return _edit(start, end, replacement, mask, mention["text"], why, "2.109")
    if treatment == "plain":
        if not any(italic[mention["start"]:mention["end"]]):
            return None
        why = _plain_why(mention["phrase"])
        return _edit(mention["start"], mention["end"], inner, mask, mention["text"], why, "2.107")
    return None


def _edit(start, end, replacement, mask, label, why, section) -> tuple:
    return (start, end, replacement, mask, {
        "item": f'Prose title "{label}"',
        "why": why,
        "rule": cite(section),
    })


def _plain_why(phrase: str) -> str:
    return (
        f'Secs. 2.106–2.107 do not italicize "{phrase}" when the source type is an organization, '
        "a board or card game, or an earthwork, ancient artwork, or building. Italics were removed. "
        "Sec. 2.110 itself was not supplied, so no further exception was applied."
    )


def _own_italic(mention: dict, children: list[dict], italic: list[bool]) -> bool:
    covered = [False] * (mention["end"] - mention["start"])
    for child in children:
        if child["treatment"] != "italic":
            continue
        for index in range(child["start"] - mention["start"], child["end"] - mention["start"]):
            covered[index] = True
    return any(
        italic[mention["start"] + index] and not covered[index]
        for index in range(len(covered))
    )


def _style_mask(mention: dict, children: list[dict], italic: list[bool], treatment: str) -> list[bool]:
    length = mention["end"] - mention["start"]
    if treatment == "italic":
        mask = [True] * length
        if mention.get("vessel"):
            prefix = _VESSEL_PREFIX.match(mention["text"])
            if prefix:
                for index in range(prefix.end()):
                    mask[index] = False
    else:
        mask = [False] * length
    for child in children:
        rel = child["start"] - mention["start"]
        if child["treatment"] == "italic":
            sub = _style_mask(child, [], italic, "italic")
            mask[rel:rel + len(sub)] = sub
        elif child["treatment"] == "plain":
            for index in range(child["end"] - child["start"]):
                mask[rel + index] = False
        elif child["treatment"] is None:
            for index in range(child["end"] - child["start"]):
                mask[rel + index] = italic[child["start"] + index]
    return mask


def _apply_title_edits(text: str, italic: list[bool], edits: list[tuple]) -> tuple[str, list[str], list[dict]]:
    chars = list(text)
    flags = []
    for start, end, replacement, mask, flag in sorted(edits, key=lambda item: item[0], reverse=True):
        chars[start:end] = list(replacement)
        italic[start:end] = list(mask)
        flags.append(flag)
    flags.reverse()
    updated = "".join(chars)
    spans = []
    index = 0
    while index < len(italic):
        if not italic[index]:
            index += 1
            continue
        end = index + 1
        while end < len(italic) and italic[end]:
            end += 1
        spans.append(updated[index:end])
        index = end
    return updated, spans, flags


def shorten_range(span: str) -> str:
    """Sec. 2.139. Inclusive numbers, en dash. Open ranges keep a space after the dash."""
    text = span.strip().replace(EN, "-").replace("\u2014", "-")
    if re.fullmatch(r".+-\s*", text) and text.rstrip().endswith("-") and text.count("-") == 1:
        head = text[:-1].strip()
        return f"{head}{EN} "
    if "-" not in text:
        return span.strip()
    left, right = text.split("-", 1)
    return _elide(left.strip(), right.strip())


def shorten_year_range(start: str, end: str, *, start_era: str = "", end_era: str = "") -> str:
    """Sec. 2.139 year spans. BCE years stay in full. CE years from 1000 drop a repeated century."""
    start_bce = _is_bce(start_era) or _is_bce(start)
    end_bce = _is_bce(end_era) or _is_bce(end)
    if start_bce or end_bce:
        start_n = re.sub(r"\D", "", start)
        end_n = re.sub(r"\D", "", end)
        if start_bce and end_bce:
            return f"{start_n}{EN}{end_n} BCE"
        left_era = "BCE" if start_bce else (start_era or "CE")
        right_era = "BCE" if end_bce else (end_era or "CE")
        return f"{start_n} {left_era}{EN}{end_n} {right_era}"
    start_n = int(re.sub(r"\D", "", start))
    end_n = int(re.sub(r"\D", "", end))
    if start_n >= 1000 and end_n >= 1000:
        left, right = str(start_n), str(end_n)
        if left[:2] == right[:2]:
            return f"{start_n}{EN}{right[2:]}"
        return f"{start_n}{EN}{end_n}"
    return _elide(str(start_n), str(end_n))


def format_pages(pages: str) -> str:
    """Secs. 5.89–5.91. A range takes pp.; one page takes p. Numeral style is kept."""
    text = pages.strip()
    if not text:
        return text
    if re.search(r"[-–—,]", text):
        parts = [_format_page_piece(part.strip()) for part in text.split(",")]
        return "pp. " + ", ".join(parts)
    return "p. " + _format_page_piece(text)


def shorten_locations(text: str) -> str:
    """Page lists inside a citation: commas between locations, en dashes inside spans."""
    parts = []
    for part in text.split(","):
        piece = part.strip()
        piece = re.sub(r"^(?:pp?)\.\s*", "", piece, flags=re.I)
        if re.search(r"[-–—]", piece):
            piece = shorten_range(piece)
        parts.append(piece)
    return ", ".join(parts)


def works_cited_authors(authors: list[dict], role: str | None = None, *, et_al: bool = False) -> str:
    """Secs. 5.7 and 5.8. Two names stay in source order; three or more become et al."""
    if not authors:
        return ""
    if et_al or len(authors) >= 3:
        base = f"{_inverted(authors[0])}, et al."
        if role:
            return f"{base}, {role}."
        return base
    if len(authors) == 2:
        first, second = authors
        base = f"{_inverted(first)}, and {second['given'].strip()} {second['family'].strip()}"
        if role:
            return f"{base}, {role}."
        return base if base.endswith(".") else base + "."
    base = _inverted(authors[0])
    if role:
        return f"{base}, {role}."
    return base if base.endswith(".") else base + "."


def in_text(
    authors: list[dict] | None = None,
    locator: str = "",
    *,
    et_al: bool = False,
    corporate: str | None = None,
) -> tuple[str, str | None]:
    """Secs. 6.5 and 6.6. Parenthetical surnames; corporate names drop a leading article."""
    flag = None
    people = authors or []
    if corporate:
        name, flag = corporate_parenthetical(corporate)
    elif et_al or len(people) >= 3:
        name = f"{people[0]['family']} et al."
    elif len(people) == 2:
        name = f"{people[0]['family']} and {people[1]['family']}"
    else:
        name = people[0]["family"]
    loc = shorten_locations(locator) if locator else ""
    if loc:
        return f"({name} {loc})", flag
    return f"({name})", flag


def corporate_parenthetical(name: str) -> tuple[str, str | None]:
    """Sec. 6.6. Drop a leading article. Further shortening is not exemplified in the transcription."""
    stripped = re.sub(r"^(?:the|a|an)\s+", "", name.strip(), count=1, flags=re.I)
    flag = None
    if re.search(r"\bof\b|,", stripped, flags=re.I):
        flag = (
            "Sec. 6.6 calls for the shortest noun phrase and dropping an initial article. "
            "The shortening examples were not transcribed, so only a leading article was removed."
        )
    return stripped, flag


def parenthetical(author: str, locator: str = "", *, title: str | None = None, label: str | None = None) -> str:
    """Secs. 6.28–6.30. No mark between author and page; a comma before a title or a labeled part."""
    loc = shorten_locations(locator) if locator else ""
    if title and label:
        extra = f", {title}, {label}" + (f" {loc}" if loc else "")
        return f"({author}{extra})"
    if title:
        return f"({author}, {title}" + (f" {loc}" if loc else "") + ")"
    if label:
        return f"({author}, {label}" + (f" {loc}" if loc else "") + ")"
    if loc:
        return f"({author} {loc})"
    return f"({author})"


def join_parentheticals(parts: list[str]) -> str:
    """Sec. 6.30. Several sources in one pair of parentheses, separated by semicolons."""
    inner = "; ".join(part.strip().strip("()") for part in parts)
    return f"({inner})"


def timestamp_span(start: str, end: str) -> str:
    """Sec. 6.28. hh:mm:ss, colons, no spaces; the second time keeps only the digits that change."""
    if ":" in start and ":" not in end:
        return f"{start}{EN}{end}"
    left = start.split(":")
    right = end.split(":")
    if len(left) == len(right) and len(left) >= 2:
        shared = 0
        for a, b in zip(left, right):
            if a != b:
                break
            shared += 1
        tail = ":".join(right[shared:]) if shared else end
        if shared and tail.isdigit() and left[-1].isdigit():
            tail = shorten_range(f"{left[-1]}-{right[-1]}").split(EN)[-1]
            return f"{start}{EN}{tail}"
        return f"{start}{EN}{tail}"
    return f"{start}{EN}{end}"


def format_doi(value: str) -> str:
    """A DOI keeps the https://doi.org/ prefix. Secs. 5.93 and 5.120."""
    rest = re.sub(r"^(https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I)
    return "https://doi.org/" + rest


def format_url(value: str) -> str:
    """Handbook examples drop https:// on ordinary URLs and keep it on DOIs."""
    text = value.strip()
    if re.match(r"https?://(?:dx\.)?doi\.org/|doi:\s*", text, flags=re.I):
        return format_doi(text)
    return re.sub(r"^https?://", "", text)


def join_seasons(first: str, second: str) -> str:
    """Sec. 5.121. A hyphen, not an en dash, joins two seasons or months."""
    return f"{first.strip().lower()}-{second.strip().lower()}"


def format_issue_range(start: str, end: str) -> str:
    """Sec. 5.121. Issue ranges take an en dash: nos. 3–4."""
    return "nos. " + shorten_range(f"{start}-{end}")


def supplied(text: str, *, uncertain: bool = False) -> str:
    """Sec. 5.122. Supplied information sits in square brackets; uncertainty adds ?."""
    body = text.strip()
    if uncertain and not body.endswith("?"):
        body += "?"
    return f"[{body}]"


def local_newspaper(name: str, city: str) -> str:
    """Sec. 5.122. The city follows the newspaper name in brackets and is not italicized."""
    return f"{name} [{city}]"


def format_works_cited_entry(entry: dict, *, byline: str | None = None, flags: list | None = None) -> str:
    """Secs. 5.120–5.122. Periods after the author, the title, and the entry; commas inside a container."""
    authors = byline if byline is not None else works_cited_authors(
        entry.get("authors") or [], entry.get("role"), et_al=bool(entry.get("et_al"))
    )
    title = entry.get("title") or ""
    if not entry.get("untitled"):
        title, title_flags = title_case_with_flags(title)
        if flags is not None:
            flags.extend(title_flags)
    if entry.get("type") == "book" or (not entry.get("container") and entry.get("publisher")):
        publisher = entry.get("publisher") or ""
        year = str(entry.get("year") or "")
        edition = str(entry.get("edition") or "")
        tail = ", ".join(part for part in (edition, publisher, year) if part)
        return f"{authors} {title}. {tail}."
    article = title if title[-1:] in "?!." else title + "."
    bits = []
    if entry.get("volume") and entry.get("volumes"):
        bits.append(f"vols. {entry['volume']} and {entry['volumes']}")
    elif entry.get("volume"):
        bits.append(f"vol. {entry['volume']}")
    if entry.get("issue_end"):
        bits.append(format_issue_range(str(entry["issue"]), str(entry["issue_end"])))
    elif entry.get("issue"):
        bits.append(f"no. {entry['issue']}")
    date = _date(entry)
    if date:
        bits.append(date)
    if entry.get("pages"):
        bits.append(format_pages(str(entry["pages"])))
    if entry.get("doi"):
        bits.append(format_doi(str(entry["doi"])))
    elif entry.get("url"):
        bits.append(format_url(str(entry["url"])))
    container = entry.get("container") or ""
    return f"{authors} \u201c{article}\u201d {container}, {', '.join(bits)}."


def repeat_byline(entry: dict, previous: tuple | None) -> tuple[str, tuple]:
    """Secs. 5.126–5.129. Dashes only when the names, and their order, match the previous entry."""
    signature = _signature(entry)
    role = entry.get("role")
    if previous == signature and signature and signature[0] != "etal-unlisted":
        if role:
            return f"{EM_DASHES}, {role}.", signature
        return f"{EM_DASHES}.", signature
    return works_cited_authors(entry.get("authors") or [], role, et_al=bool(entry.get("et_al"))), signature


def alphabetize_key(label: str) -> tuple[str, str]:
    """Secs. 5.123–5.124. Letter by letter, up to the first comma, ignoring articles, spaces, and accents."""
    text = label.strip()
    if "," in text:
        head, tail = text.split(",", 1)
        return _letters(head), _letters(tail)
    stripped = _strip_initial_article(text)
    return _letters(_spell_leading_numeral(stripped)), ""


def title_sort_parts(title: str) -> tuple[str, int, str]:
    """Sec. 5.130. Ignore an initial article, spell a leading numeral, keep a numbered sequence in order."""
    text = _strip_initial_article(title.strip())
    spelled = _spell_leading_numeral(text)
    if spelled != text:
        return _letters(spelled), 0, ""
    match = re.match(r"^(?P<stem>.+?)\s+(?P<roman>[IVXLCDM]+)\b(?P<rest>.*)$", text)
    if match and match.group("roman").upper() in _ROMAN_VALUES and re.search(r"[A-Za-z]", match.group("stem")):
        return (
            _letters(match.group("stem")),
            _ROMAN_VALUES[match.group("roman").upper()],
            _letters(match.group("rest")),
        )
    return _letters(text), 0, ""


def sort_entries(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    """Secs. 5.123–5.130. Solo works, then pairs, then et al.; same title goes earliest to latest."""
    families: dict[str, list[dict]] = {}
    loose: list[dict] = []
    for entry in entries:
        authors = entry.get("authors") or []
        if not authors:
            loose.append(entry)
            continue
        families.setdefault(_letters(authors[0]["family"]), []).append(entry)
    blocks: list[tuple[tuple, list[dict]]] = []
    for family, group in families.items():
        blocks.append(((family, 0, "", 0), sorted(group, key=_within_author_key)))
    for entry in loose:
        letters, seq, rest = title_sort_parts(entry.get("title") or "")
        blocks.append(((letters, seq, rest, _year_number(entry)), [entry]))
    blocks.sort(key=lambda block: block[0])
    return [entry for _, group in blocks for entry in group], []


def render_works_cited(entries: list[dict]) -> tuple[list[str], list[dict]]:
    """Sort and apply repeat-author dashes. Secs. 5.126–5.130."""
    ordered, flags = sort_entries(entries)
    lines = []
    previous = None
    for entry in ordered:
        byline, previous = repeat_byline(entry, previous)
        lines.append(format_works_cited_entry(entry, byline=byline, flags=flags))
    return lines, flags


def _date(entry: dict) -> str:
    year = str(entry.get("year") or "")
    if entry.get("season_end"):
        return f"{join_seasons(str(entry['season']), str(entry['season_end']))} {year}".strip()
    if entry.get("season"):
        return f"{str(entry['season']).lower()} {year}".strip()
    month = entry.get("month") or ""
    if month:
        return f"{month} {year}".strip()
    return year


def _inverted(person: dict) -> str:
    return f"{person['family'].strip()}, {person['given'].strip()}"


def _format_page_piece(piece: str) -> str:
    if re.search(r"[-–—]", piece):
        return shorten_range(piece)
    return piece


def _elide(start: str, end: str) -> str:
    if _roman(start) or _roman(end) or _mixed(start) or _mixed(end):
        return f"{start}{EN}{end}"
    start_n = _integer(start)
    end_n = _integer(end)
    if start_n is None or end_n is None or end_n < start_n:
        return f"{start}{EN}{end}"
    if end_n <= 99 or len(str(start_n)) != len(str(end_n)):
        return f"{start_n:,}{EN}{end_n:,}"
    sd, ed = str(start_n), str(end_n)
    i = 0
    while i < len(sd) - 2 and sd[i] == ed[i]:
        i += 1
    while True:
        short = ed[i:]
        implied = int(sd[:i] + short)
        if implied == end_n and int(short) > int(sd[i:]):
            return f"{start_n:,}{EN}{short}"
        if i == 0:
            return f"{start_n:,}{EN}{end_n:,}"
        i -= 1


def _integer(token: str) -> int | None:
    digits = token.replace(",", "")
    if digits.isdigit():
        return int(digits)
    return None


def _roman(token: str) -> bool:
    return bool(re.fullmatch(r"[ivxlcdm]+", token, flags=re.I))


def _mixed(token: str) -> bool:
    return bool(re.search(r"[A-Za-z]", token) and re.search(r"\d", token))


def _is_bce(value: str) -> bool:
    return bool(re.search(r"\bBCE\b|\bBC\b", value or "", flags=re.I))


def _letters(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    plain = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return "".join(ch for ch in plain.upper() if ch.isalpha())


def _signature(entry: dict) -> tuple:
    authors = tuple((person["family"], person["given"]) for person in entry.get("authors") or [])
    if _many_authors(entry):
        # Dashes need the same coauthors in the same order. An unlisted team is not that.
        if len(authors) <= 1:
            return ("etal-unlisted", id(entry))
        return authors
    return authors


def _many_authors(entry: dict) -> bool:
    return bool(entry.get("et_al") or len(entry.get("authors") or []) > 2)


def _within_author_key(entry: dict) -> tuple:
    """Solo, then two authors by the second surname, then three or more by title. Same title by year."""
    authors = entry.get("authors") or []
    title = title_sort_parts(entry.get("title") or "")
    year = _year_number(entry)
    if _many_authors(entry):
        return (2, title, year)
    if len(authors) == 2:
        return (1, _letters(authors[1]["family"]), title, year)
    given = _letters(authors[0]["given"]) if authors else ""
    return (0, given, title, year)


def _year_number(entry: dict) -> int:
    match = re.search(r"\d{1,4}", str(entry.get("year") or ""))
    return int(match.group(0)) if match else 0


def _strip_initial_article(title: str) -> str:
    # English A/An/The, plus Le, the foreign equivalent named in sec. 5.130.
    match = re.match(r"^(?:a|an|the|le)\b\s+", title, flags=re.I)
    return title[match.end() :] if match else title


def _spell_leading_numeral(text: str) -> str:
    match = re.match(r"^(\d+)\b", text)
    if not match:
        return text
    return _spell_number(int(match.group(1))) + text[match.end() :]


def _spell_number(number: int) -> str:
    if 1000 <= number <= 9999:
        high, low = divmod(number, 100)
        head = _spell_under_100(high)
        if low == 0:
            return f"{head} hundred"
        return f"{head} {_spell_under_100(low)}"
    if number < 100:
        return _spell_under_100(number)
    hundreds, rest = divmod(number, 100)
    words = f"{_ONES[hundreds]} hundred"
    if rest:
        words += " " + _spell_under_100(rest)
    return words


def _spell_under_100(number: int) -> str:
    if number < 20:
        return _ONES[number]
    ten, one = divmod(number, 10)
    if one == 0:
        return _TENS[ten]
    return f"{_TENS[ten]} {_ONES[one]}"


_ONES = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
)
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
_ROMAN_VALUES = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
}
