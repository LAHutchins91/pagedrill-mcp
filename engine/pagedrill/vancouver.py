"""Vancouver citations and reference list. Page layout stays as the author left it.

ICMJE numbers references in order of first mention and puts the number in parentheses.
Citing Medicine, 2nd ed., Chapter 1 (NBK7282) and Chapter 2 (NBK7271) supply the
reference-list rules. Separator style, list numbering, and page layout stay journal options.
"""

from __future__ import annotations

import re
from io import BytesIO

from docx import Document

from .errors import PagedrillRefusal
from .packageio import diff_parts
from .revisions import apply_tracked_changes
from .words import assert_vancouver_body_words
from .zippack import read_package, write_package

CH1 = "Citing Medicine 2nd ed., Chapter 1 Journals (NBK7282)"
CH2 = "Citing Medicine 2nd ed., Chapter 2 Books (NBK7271)"

# Finished forms named in Chapter 1, Location (Pagination), and the same procedure
# applied to the ranges the general rule describes. Inputs are the unshortened pages.
PAGE_EXAMPLES = {
    "123-125": "123-5",
    "284-287": "284-7",
    "40-46": "40-6",
    "1199-1201": "1199-201",
    "2257-2261": "2257-61",
    "98-101": "98-101",
    "124A-126A": "124A-126A",
    "660S-665S": "660S-665S",
    "41S-47S": "41S-47S",
    "387A-388A": "387A-388A",
    "S10-18": "S10-8",
    "S10-S18": "S10-8",
    "R837-R845": "R837-45",
    "H881-H886": "H881-6",
    "S221-S222": "S221-2",
    "F170-F171": "F170-1",
    "S47-S56": "S47-56",
    "xvii-xix": "xvii-xix",
    "vii-viii": "vii-viii",
    "X-XII": "X-XII",
    "V-VIII": "V-VIII",
    "16-20, 22, 24-29": "16-20, 22, 24-9",
    "a2752": "a2752",
}

OFFICIAL = {
    "Halpern": "Halpern SD, Ubel PA, Caplan AL. Solid-organ transplantation in HIV-infected patients. N Engl J Med. 2002 Jul 25;347(4):284-7.",
    "Rose": "Rose ME, Huerbin MB, Melick J, Marion DW, Palmer AM, Schiding JK, et al. Regulation of interstitial excitatory amino acid concentrations after cortical contusion injury. Brain Res. 2002;935(1-2):40-6.",
    "Zhang": "Zhang M, Holman CD, Price SD, Sanfilippo FM, Preen DB, Bulsara MK. Comorbidity and repeat admission to hospital for adverse drug reactions in older adults: retrospective cohort study. BMJ. 2009 Jan 7;338:a2752. doi: 10.1136/bmj.a2752.",
    "Murray": "Murray PR, Rosenthal KS, Kobayashi GS, Pfaller MA. Medical microbiology. 4th ed. St. Louis: Mosby; 2002.",
}

JOURNAL_RE = re.compile(
    r"^(?P<authors>.+?)\s+\((?P<year>\d{4})(?:,\s+(?P<month>[A-Za-z]+)(?:\s+(?P<day>\d{1,2}))?)?\)\.\s+"
    r"(?P<title>.+?)\.\s+(?P<journal>[^,]+),\s+(?P<volume>\d+)"
    r"(?:\((?P<issue>[^)]+)\))?,\s+(?P<pages>[^.]+)\."
    r"(?:\s+https?://doi\.org/(?P<doi>\S+))?\s*$"
)
BOOK_RE = re.compile(
    r"^(?P<authors>.+?)\s+\((?P<year>\d{4})\)\.\s+(?P<title>.+?)\s+\((?P<edition>\d+(?:st|nd|rd|th))\s+ed\.\)\.\s+"
    r"(?P<place>[^:]+):\s+(?P<publisher>.+?)\.\s*$"
)
CITE_RE = re.compile(r"\(((?:[^();]+?, \d{4}(?:; )?)+)\)")
HEADINGS = {"references", "reference list", "bibliography", "works cited"}


def elide_pages(pages: str) -> str:
    """Shorten a page range the way Citing Medicine Chapter 1 states it.

    123-125 becomes 123-5. A letter after the number blocks shortening (124A-126A).
    A letter before the number stays (S10-18 becomes S10-8). Roman numerals stay
    as found. Each span in a discontinuous list is shortened on its own.
    """
    if not pages or ("-" not in pages and "," not in pages):
        return pages
    parts = [part.strip() for part in pages.split(",")]
    return ", ".join(_elide_span(part) for part in parts)


def _elide_span(span: str) -> str:
    span = span.replace("\u2013", "-").replace("\u2014", "-")
    if "-" not in span:
        return span
    left, right = span.split("-", 1)
    if _roman(left) and _roman(right):
        return f"{left}-{right}"
    if re.search(r"[A-Za-z]$", left) or re.search(r"[A-Za-z]$", right):
        return f"{left}-{right}"
    left_m = re.fullmatch(r"([A-Za-z]*)(\d+)", left)
    right_m = re.fullmatch(r"([A-Za-z]*)(\d+)", right)
    if not left_m or not right_m:
        return f"{left}-{right}"
    if left_m.group(1) == right_m.group(1) or (left_m.group(1) and not right_m.group(1)):
        prefix, start, end = left_m.group(1), left_m.group(2), right_m.group(2)
    else:
        return f"{left}-{right}"
    if len(start) != len(end):
        return f"{left}-{right}"
    index = 0
    while index < len(start) - 1 and start[index] == end[index]:
        index += 1
    return f"{prefix}{start}-{end[index:]}"


def _roman(value: str) -> bool:
    return bool(re.fullmatch(r"[IVXLCDMivxlcdm]+", value))


def sentence_case(title: str) -> tuple[str, list[str]]:
    """Capitalize only the first word, plus acronyms and tokens that contain a digit.

    A first word that is already lowercase stays lowercase (Citing Medicine example:
    c-jun, p53). Words after a colon are not re-capitalized.
    """
    rendered: list[str] = []
    changed: list[str] = []
    first = True
    for word in title.split(" "):
        parts = []
        for index, part in enumerate(word.split("-")):
            if _keep_token(part):
                parts.append(part)
            elif first and index == 0:
                parts.append(part)
            else:
                parts.append(part.lower())
        new = "-".join(parts)
        if new != word:
            changed.append(word)
        rendered.append(new)
        if word:
            first = False
    return " ".join(rendered), changed


def _keep_token(token: str) -> bool:
    core = re.sub(r"^[^\w]+|[^\w]+$", "", token, flags=re.UNICODE)
    if re.search(r"\d", core):
        return True
    return sum(1 for char in core if char.isupper()) >= 2


def parse_reference_line(line: str) -> dict | None:
    text = line.strip()
    if re.search(r"\d+(?:st|nd|rd|th)\s+ed\.", text):
        parsed = _parse_book(text)
        if parsed:
            return parsed
    return _parse_journal(text)


def _norm(value: str) -> str:
    return re.sub(r"[\W_]+", "", value or "", flags=re.UNICODE).lower()


def _ground(original: str, value: str | None, label: str) -> None:
    if not value:
        return
    if _norm(str(value)) not in _norm(original):
        raise PagedrillRefusal(
            f"A reference {label} was not in the author's entry. Pagedrill did not invent it.",
            "missing_field",
        )


def _authors(text: str) -> list[dict]:
    found = re.findall(r"([^,]+),\s*((?:[A-Z]\.\s*)+)", text.replace(" & ", ", ").replace(" and ", ", "))
    return [{"family": family.strip(), "initials": initials.strip()} for family, initials in found]


def _parse_journal(line: str) -> dict | None:
    match = JOURNAL_RE.match(line)
    if not match:
        return None
    authors = _authors(match.group("authors"))
    if not authors:
        return None
    parsed = {
        "type": "journal-article",
        "authors": authors,
        "year": match.group("year"),
        "month": match.group("month"),
        "day": match.group("day"),
        "title": match.group("title").strip(),
        "container": match.group("journal").strip(),
        "volume": match.group("volume"),
        "issue": match.group("issue"),
        "pages": match.group("pages").strip(),
        "doi": (match.group("doi") or "").rstrip("."),
        "typed": line,
    }
    _ground_people(line, authors)
    for key in ("year", "title", "container", "volume", "pages"):
        _ground(line, parsed[key], key)
    _ground(line, parsed["month"], "month")
    _ground(line, parsed["day"], "day")
    _ground(line, parsed["issue"], "issue")
    _ground(line, parsed["doi"] or None, "doi")
    parsed["key"] = authors[0]["family"].lower() + parsed["year"]
    return parsed


def _parse_book(line: str) -> dict | None:
    match = BOOK_RE.match(line)
    if not match:
        return None
    authors = _authors(match.group("authors"))
    if not authors:
        return None
    parsed = {
        "type": "book",
        "authors": authors,
        "year": match.group("year"),
        "month": None,
        "day": None,
        "title": match.group("title").strip(),
        "edition": match.group("edition"),
        "place": match.group("place").strip(),
        "publisher": match.group("publisher").strip(),
        "typed": line,
    }
    _ground_people(line, authors)
    for key in ("year", "title", "edition", "place", "publisher"):
        _ground(line, parsed[key], key)
    parsed["key"] = authors[0]["family"].lower() + parsed["year"]
    return parsed


def _ground_people(line: str, authors: list[dict]) -> None:
    for author in authors:
        _ground(line, author["family"], "author")
        _ground(line, author["initials"].replace(" ", ""), "initials")


def format_vancouver(original: bytes, profile: dict, supplied: dict | None = None) -> dict:
    supplied = supplied or {}
    document = Document(BytesIO(original))
    paragraphs = list(document.paragraphs)
    ref_at = next((index for index, paragraph in enumerate(paragraphs) if paragraph.text.strip().lower() in HEADINGS), None)
    if ref_at is None:
        raise PagedrillRefusal("No References heading was in the draft. Pagedrill did not invent one.", "missing_field")
    sources = profile.get("source_keys") or {}
    icmje = sources.get("icmje", "ICMJE g. References")
    samples = sources.get("nlm_samples", "NLM Sample References")
    changes: list[dict] = []
    flags: list[dict] = []

    def log(kind: str, before: str, after: str, rule: str) -> None:
        changes.append({"kind": kind, "before": before, "after": after, "rule": rule})

    def flag(item: str, why: str, rule: str) -> None:
        flags.append({"item": item, "why": why, "rule": rule})

    multiple = _option(profile, supplied, "multiple_citation", "comma-space")
    numbering = _option(profile, supplied, "list_numbering", "period-space")
    layout = _option(profile, supplied, "page_layout", "unchanged")
    if layout != "unchanged":
        raise PagedrillRefusal(
            "No journal page layout was supplied. Pagedrill did not invent font, spacing, or margins.",
            "missing_field",
        )

    parsed: list[dict] = []
    for paragraph in paragraphs[ref_at + 1 :]:
        line = paragraph.text.strip()
        if not line:
            continue
        item = parse_reference_line(line)
        if item is None:
            parsed.append({"type": "other", "typed": line, "key": line[:40], "authors": []})
            flag(line[:80], "This reference is not an entire book or a journal article in the typed pattern. It was kept as typed.", samples)
        else:
            parsed.append(item)
    if not any(item["type"] in ("journal-article", "book") for item in parsed):
        raise PagedrillRefusal("No journal article or book reference could be read. Nothing was invented.", "missing_field")

    order: list[str] = []

    def number_for(item: dict) -> int:
        if item["key"] not in order:
            order.append(item["key"])
        return order.index(item["key"]) + 1

    def find(name: str, year: str) -> dict | None:
        family = name.strip().split()[0]
        matches = [item for item in parsed if item["type"] != "other" and item["authors"][0]["family"] == family and item["year"] == year]
        return matches[0] if matches else None

    multi = False
    before_body = [paragraph.text for paragraph in paragraphs[:ref_at]]
    for paragraph in paragraphs[:ref_at]:
        original_text = paragraph.text

        def replace(match: re.Match) -> str:
            nonlocal multi
            numbers = []
            for piece in match.group(1).split("; "):
                if ", " not in piece:
                    return match.group(0)
                name, year = piece.rsplit(", ", 1)
                item = find(name, year)
                if item is None:
                    flag(piece, "No reference matches this citation. It was left as typed.", icmje)
                    return match.group(0)
                numbers.append(number_for(item))
            if len(numbers) > 1:
                multi = True
            return _format_numbers(numbers, multiple)

        updated = CITE_RE.sub(replace, original_text)
        if updated != original_text:
            paragraph.text = updated
            log("citation", original_text, updated, icmje + " (Arabic numerals in parentheses, order of first mention)")
    if multi:
        flag(
            "multiple citations",
            f"Written with the journal option '{multiple}' ({_format_numbers([1, 4], multiple)}). ICMJE does not specify commas, spaces, or ranges. Citing Medicine chapters 1 and 2 are reference-list rules.",
            icmje,
        )
    flag(
        "citation placement",
        "Numbers stay where the author typed the citation. ICMJE does not specify the position relative to punctuation.",
        icmje,
    )

    for item in parsed:
        if item["type"] != "other" and item["key"] not in order:
            order.append(item["key"])
            flag(item["authors"][0]["family"], "Listed but never cited; placed last.", icmje)

    rendered: dict[str, str] = {}
    for item in parsed:
        if item["type"] == "other":
            rendered[item["key"]] = item["typed"]
        elif item["type"] == "book":
            rendered[item["key"]] = _render_book(item, profile, log, flag)
        else:
            rendered[item["key"]] = _render_journal(item, profile, supplied, log, flag)

    flag(
        "reference list numbering",
        f"Written with the journal option '{numbering}' ({_list_prefix(1, numbering)!r}). Neither ICMJE nor NLM Sample References shows the list number. Citing Medicine examples are unnumbered.",
        icmje,
    )
    flag(
        "page layout",
        "Font, spacing, margins, and the title page were left as the author had them. The journal option is 'unchanged'. ICMJE says to consult the journal.",
        icmje,
    )

    sequence = [item for key in order for item in parsed if item["key"] == key]
    others = [item for item in parsed if item["type"] == "other"]
    sequence.extend(item for item in others if item not in sequence)
    targets = [paragraph for paragraph in paragraphs[ref_at + 1 :] if paragraph.text.strip()]
    if len(targets) != len(sequence):
        raise PagedrillRefusal("The reference list could not be rewritten without adding or removing a paragraph.", "engine_error")
    for index, (paragraph, item) in enumerate(zip(targets, sequence)):
        before = paragraph.text
        after = _list_prefix(index + 1, numbering) + rendered[item["key"]]
        paragraph.text = after
        log("reference", before, after, samples if item["type"] != "other" else icmje)
    if [item["key"] for item in parsed if item["type"] != "other"] != [item["key"] for item in sequence if item["type"] != "other"]:
        log("reference order", ", ".join(item["key"] for item in parsed if item["type"] != "other"), ", ".join(order), icmje)

    after_body = [paragraph.text for paragraph in paragraphs[:ref_at]]
    surnames = {author["family"] for item in parsed for author in item.get("authors") or []}
    years = {str(item.get("year")) for item in parsed if item.get("year")}
    years |= set(re.findall(r"\b(?:19|20)\d\d\b", "\n".join(before_body)))
    assert_vancouver_body_words("\n".join(before_body), "\n".join(after_body), surnames, years)
    if supplied.get("track_changes"):
        apply_tracked_changes(document, changes)
    data, verification = _save_document_only(original, document)
    verification["basis"] = "in-place"
    title = next((paragraph.text.strip() for paragraph in paragraphs if paragraph.text.strip()), None)
    return {"docx": data, "changes": changes, "flags": flags, "verification": verification, "title": title}


def render_parsed(parsed: dict, profile: dict, supplied: dict | None = None) -> tuple[str | None, list[dict], list[str]]:
    """Render one already-parsed reference. Used by the bibliography importer."""
    supplied = supplied or {}
    changes: list[dict] = []
    flags: list[dict] = []

    def log(kind: str, before: str, after: str, rule: str) -> None:
        changes.append({"kind": kind, "before": before, "after": after, "rule": rule})

    def flag(item: str, why: str, rule: str) -> None:
        flags.append({"item": item, "why": why, "rule": rule})

    if parsed.get("type") == "book":
        if not (parsed.get("authors") and parsed.get("title") and parsed.get("year") and parsed.get("place") and parsed.get("publisher")):
            return None, flags, []
        return _render_book(parsed, profile, log, flag), flags, []
    if parsed.get("type") != "journal-article":
        return None, flags, []
    if not (parsed.get("authors") and parsed.get("title") and parsed.get("year") and parsed.get("container")):
        return None, flags, []
    return _render_journal(parsed, profile, supplied, log, flag), flags, []


def _render_journal(parsed: dict, profile: dict, supplied: dict, log, flag) -> str:
    references = profile.get("references") or {}
    samples = (profile.get("source_keys") or {}).get("nlm_samples", "NLM Sample References")
    who = _people(parsed["authors"], 6, parsed.get("key") or parsed["authors"][0]["family"], flag, samples)
    title, changed = sentence_case(parsed["title"])
    if changed:
        log("reference title case", parsed["title"], title, CH1 + ", Article Title, General Rules")
        flag(
            str(parsed.get("key") or title) + " title",
            "Sentence case applied (first word, acronyms, and initialisms). Proper nouns cannot be detected, so confirm none was lowercased.",
            CH1 + ", Article Title for Journal Articles, General Rules",
        )
    journal, how = _abbrev(parsed["container"], profile, supplied, flag)
    if journal != parsed["container"]:
        log("journal abbreviation (lookup)", parsed["container"], journal, how)
    date = _date(parsed, profile, flag)
    pages = elide_pages(parsed.get("pages") or "")
    if parsed.get("pages") and pages != parsed["pages"]:
        log("page elision", parsed["pages"], pages, CH1 + ", Location (Pagination), General Rules")
    issue = f"({parsed['issue']})" if parsed.get("issue") else ""
    volume = parsed.get("volume") or ""
    if volume or issue:
        locator = f"{date};{volume}{issue}:{pages}." if pages else f"{date};{volume}{issue}."
    elif pages:
        locator = f"{date}:{pages}."
    else:
        locator = f"{date}."
    text = f"{who}{title}. {journal}. {locator}"
    if parsed.get("doi"):
        text += f" doi: {parsed['doi']}."
    if _rose_conflict(parsed):
        flag(
            "rose",
            "PubMed holds two records with this title and author list (Brain Res 935(1-2):40-6, PMID 12062471, and 943(1):15-22, PMID 12088834). Confirm which one you read.",
            (profile.get("source_keys") or {}).get("pubmed", "PubMed"),
        )
    return text


def _render_book(parsed: dict, profile: dict, log, flag) -> str:
    samples = (profile.get("source_keys") or {}).get("nlm_samples", "NLM Sample References")
    who = _people(parsed["authors"], None, parsed.get("key") or parsed["authors"][0]["family"], flag, samples)
    title, changed = sentence_case(parsed["title"])
    if changed:
        log("reference title case", parsed["title"], title, CH2 + ", Title for Entire Books, General Rules")
        flag(
            str(parsed.get("key") or title) + " title",
            "Sentence case applied. Proper nouns cannot be detected, so confirm none was lowercased.",
            CH2 + ", Title for Entire Books, General Rules",
        )
    edition = f"{parsed['edition']} ed. " if parsed.get("edition") else ""
    text = f"{who}{title}. {edition}{parsed['place']}: {parsed['publisher']}; {parsed['year']}."
    if not re.search(r"\([^)]+\)", parsed.get("place") or ""):
        flag(
            parsed.get("key") or parsed["authors"][0]["family"],
            "Place left as typed. Citing Medicine adds a state or country only for a lesser-known or ambiguous city. No qualifier was in the typed entry, and none was invented. NLM sample #19 prints St. Louis without one.",
            CH2 + ", Place of Publication for Entire Books, General Rules",
        )
    flag(
        parsed.get("key") or "book",
        "Entire book rendered from Chapter 2A (authors, title, edition, place, publisher, year). Not looked up in PubMed or Crossref.",
        samples,
    )
    return text


def _people(authors: list[dict], limit: int | None, label: str, flag, source: str) -> str:
    names = []
    for author in authors:
        letters = re.findall(r"[A-Za-z]", author.get("initials") or "")
        if len(letters) > 2:
            flag(label, "Citing Medicine allows at most two initials. Extra initials were dropped.", CH1 + ", Author, General Rules")
            letters = letters[:2]
        names.append(f"{author['family']} {''.join(letters)}".strip())
    if limit is not None and len(names) > limit:
        return ", ".join(names[:limit]) + ", et al. "
    if limit is not None and len(names) == limit:
        flag(label, "Exactly six authors: all six are listed. More than six would be followed by et al.", source)
    return ", ".join(names) + ". "


def _date(parsed: dict, profile: dict, flag) -> str:
    year = str(parsed.get("year") or "")
    month = parsed.get("month")
    day = parsed.get("day")
    if not month and not day:
        if parsed.get("type") != "book":
            flag(
                parsed.get("key") or year,
                "No month or day was in the typed entry. Citing Medicine includes year, month, and day when they are present. None was invented.",
                CH1 + ", Date of Publication for Journal Articles, General Rules",
            )
        return year
    months = (profile.get("references") or {}).get("months") or profile.get("months") or {}
    abbrev = months.get(month) if month else None
    if month and not abbrev:
        flag(parsed.get("key") or year, f"Month '{month}' is not in the three-letter list. It was not abbreviated by guess.", CH1)
        return year
    date = year + (f" {abbrev}" if abbrev else "")
    if day:
        date += f" {int(day)}"
    return date


def _abbrev(name: str, profile: dict, supplied: dict, flag) -> tuple[str, str]:
    references = profile.get("references") or {}
    attested = dict(references.get("medline_attested_titles") or {})
    extra = supplied.get("journal_abbreviations") if isinstance(supplied.get("journal_abbreviations"), dict) else {}
    supplied_keys = set()
    for key, value in extra.items():
        if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
            attested[key.strip()] = value.strip()
            supplied_keys.add(key.strip())
    if name in attested:
        how = "abbreviation supplied for this format" if name in supplied_keys else references.get("medline_attested_note", "attested MEDLINE abbreviation")
        return attested[name], how
    flag(
        name,
        "Journal title left in full. It is not in the attested MEDLINE list and no abbreviation was supplied. None was invented.",
        (profile.get("source_keys") or {}).get("icmje", "ICMJE"),
    )
    return name, "not abbreviated"


def _rose_conflict(parsed: dict) -> bool:
    if not parsed.get("authors"):
        return False
    return parsed["authors"][0]["family"] == "Rose" and "contusion" in (parsed.get("title") or "").lower()


def _option(profile: dict, supplied: dict, key: str, default: str) -> str:
    spec = ((profile.get("journal_options") or {}).get(key) or {})
    choices = spec.get("choices") or {}
    selected = spec.get("selected") or default
    override = None
    options = supplied.get("journal_options")
    if isinstance(options, dict):
        override = options.get(key)
    if override is None:
        if selected not in choices and choices:
            raise PagedrillRefusal(f"The profile option '{selected}' is not one of the journal choices for {key}.", "bad_request")
        return selected
    if override not in choices:
        raise PagedrillRefusal(
            f"'{override}' is not a journal option for {key}. Pagedrill did not guess one.",
            "bad_request",
        )
    return str(override)


def _format_numbers(numbers: list[int], style: str) -> str:
    ordered = sorted(set(numbers))
    if style == "range":
        parts: list[str] = []
        start = previous = ordered[0]
        for number in ordered[1:]:
            if number == previous + 1:
                previous = number
                continue
            parts.append(f"{start}-{previous}" if previous != start else str(start))
            start = previous = number
        parts.append(f"{start}-{previous}" if previous != start else str(start))
        inner = ", ".join(parts)
    elif style == "comma":
        inner = ",".join(str(number) for number in ordered)
    else:
        inner = ", ".join(str(number) for number in ordered)
    return f"({inner})"


def _list_prefix(number: int, style: str) -> str:
    if style == "space":
        return f"{number} "
    if style == "paren":
        return f"({number}) "
    return f"{number}. "


def _save_document_only(original: bytes, document: Document) -> tuple[bytes, dict]:
    """Replace word/document.xml only, so font and section layout cannot move."""
    fresh = BytesIO()
    document.save(fresh)
    old = read_package(original)
    new = read_package(fresh.getvalue())
    old_map = old.by_name()
    new_map = new.by_name()
    if "word/document.xml" not in new_map or "word/document.xml" not in old_map:
        raise PagedrillRefusal("The document part was missing. Pagedrill did not save the file.", "verification_failed")
    updated = new_map["word/document.xml"].data
    if updated == old_map["word/document.xml"].data:
        report = diff_parts(original, original)
        return original, report
    out = write_package(old, {"word/document.xml": updated})
    report = diff_parts(original, out)
    if report["changed_parts"] != ["word/document.xml"] or report["removed_parts"] or report["added_parts"] or not report["untouched_identical"]:
        raise PagedrillRefusal("Untouched-part verification failed. Pagedrill did not save the file.", "verification_failed")
    return out, report
