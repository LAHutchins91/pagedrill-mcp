"""Import .bib and .ris references and render them with the active style.

Only fields present in the file are rendered. Missing fields are flagged.
"""

from __future__ import annotations

import re

from .errors import PagedrillRefusal
from .ieee import render_journal

MONTHS = {
    "jan": "January",
    "feb": "February",
    "mar": "March",
    "apr": "April",
    "may": "May",
    "jun": "June",
    "jul": "July",
    "aug": "August",
    "sep": "September",
    "oct": "October",
    "nov": "November",
    "dec": "December",
}


def render_imported(text: str, kind: str, profile: dict) -> dict:
    entries = parse_bib(text) if kind == "bib" else parse_ris(text) if kind == "ris" else None
    if entries is None:
        raise PagedrillRefusal("References can be imported from .bib or .ris text.", "bad_request")
    rendered = []
    for entry in entries:
        rendered.append(_render_entry(entry, profile))
    return {"style_id": profile.get("id"), "entries": rendered}


def parse_bib(text: str) -> list[dict]:
    blocks = re.split(r"(?=^@)", text.strip(), flags=re.M)
    entries = []
    for block in blocks:
        match = re.match(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*)\}\s*$", block.strip(), re.S)
        if not match:
            continue
        kind, key, body = match.group(1).lower(), match.group(2), match.group(3)
        fields = {"type": _bib_type(kind), "key": key}
        for match in re.finditer(r"(\w+)\s*=\s*(?:\{([^{}]*)\}|\"([^\"]*)\"|(\d+))", body, re.S):
            raw = match.group(2) or match.group(3) or match.group(4) or ""
            fields[match.group(1).lower()] = re.sub(r"\s+", " ", raw).strip()
        entries.append(fields)
    if not entries:
        raise PagedrillRefusal("No BibTeX entries were found. Nothing was invented.", "missing_field")
    return entries


def parse_ris(text: str) -> list[dict]:
    entries = []
    current: dict | None = None
    for line in text.splitlines():
        match = re.match(r"^([A-Z0-9]{2})  - (.*)$", line)
        if not match:
            continue
        tag, value = match.group(1), match.group(2).strip()
        if tag == "TY":
            current = {"type": "journal-article" if value.upper() == "JOUR" else value.lower(), "authors": []}
            entries.append(current)
        elif current is None:
            continue
        elif tag == "ER":
            current = None
        elif tag == "AU":
            current.setdefault("authors", []).append(value)
        elif tag == "TI":
            current["title"] = value
        elif tag in ("T2", "JO", "JF"):
            current["journal"] = value
        elif tag == "PY":
            current["year"] = value[:4]
        elif tag == "DA":
            current["date"] = value
        elif tag == "VL":
            current["volume"] = value
        elif tag == "IS":
            current["number"] = value
        elif tag == "SP":
            current["pages"] = value
        elif tag == "EP" and current.get("pages"):
            current["pages"] = current["pages"] + "-" + value
        elif tag == "DO":
            current["doi"] = value
    if not entries:
        raise PagedrillRefusal("No RIS entries were found. Nothing was invented.", "missing_field")
    return entries


def _bib_type(kind: str) -> str:
    return {"article": "journal-article", "book": "book", "inproceedings": "paper-conference"}.get(kind, kind)


def _initials(given: str) -> str:
    parts = re.findall(r"[A-Za-z]+", given)
    return " ".join(part[:1].upper() + "." for part in parts)


def _people(entry: dict) -> tuple[list[dict], list[str]]:
    missing = []
    authors = []
    raw = entry.get("author") or ""
    people = entry.get("authors") if isinstance(entry.get("authors"), list) else [part.strip() for part in re.split(r"\s+and\s+", raw) if part.strip()]
    if not people:
        missing.append("author")
        return [], missing
    for person in people:
        if "," in person:
            family, given = [part.strip() for part in person.split(",", 1)]
        else:
            bits = person.split()
            family, given = bits[-1], " ".join(bits[:-1])
        if not family:
            missing.append("author")
            continue
        authors.append({"family": family, "given": given, "initials": _initials(given) if given else ""})
        if not given:
            missing.append("given name")
    return authors, missing


def _render_entry(entry: dict, profile: dict) -> dict:
    flags = []
    missing = []
    engine = profile.get("engine")
    if entry.get("type") != "journal-article":
        echoed = {key: value for key, value in entry.items() if key != "authors" and value}
        flags.append({"item": entry.get("key") or entry.get("title") or "reference", "why": f"Reference type '{entry.get('type')}' is not rendered. Only the fields in the file are listed.", "rule": "import"})
        return {"rendered": None, "fields": echoed, "missing": [], "flags": flags}
    authors, author_gaps = _people(entry)
    missing.extend(author_gaps)
    title = entry.get("title") or ""
    journal = entry.get("journal") or ""
    year = str(entry.get("year") or "")
    if not title:
        missing.append("title")
    if not journal:
        missing.append("journal")
    if not year:
        missing.append("year")
    volume = entry.get("volume") or ""
    issue = entry.get("number") or entry.get("issue") or ""
    pages = entry.get("pages") or ""
    doi = entry.get("doi") or ""
    month = entry.get("month") or ""
    if month.lower()[:3] in MONTHS and month.lower() not in {name.lower() for name in MONTHS.values()}:
        month = MONTHS[month.lower()[:3]]
    for field, present in (("volume", volume), ("issue", issue), ("pages", pages), ("doi", doi), ("month", month)):
        if not present:
            missing.append(field)
    if engine == "ieee-conference" and authors and title and journal and year and volume:
        parsed = {
            "type": "journal-article",
            "authors": authors,
            "cite": authors[0]["family"],
            "year": year,
            "month": month or "May",
            "title": title,
            "container": journal,
            "volume": volume,
            "issue": issue or None,
            "pages": pages if "-" in pages else (pages or None),
            "article_no": None if (not pages or "-" in pages) else pages,
            "doi": doi or None,
            "typed": title,
        }
        if not month:
            parsed["month"] = ""
        changes: list[dict] = []
        local_flags: list[dict] = []

        def log(kind: str, before: str, after: str, rule: str) -> None:
            changes.append({"kind": kind, "before": before, "after": after, "rule": rule})

        def flag(item: str, why: str, rule: str) -> None:
            local_flags.append({"item": item, "why": why, "rule": rule})

        if not month:
            flag("month", "No month was in the file. None was invented.", "import")
            parsed["month"] = "May"
            # Do not keep the placeholder month in the rendered date.
            parsed_month_missing = True
        else:
            parsed_month_missing = False
        if parsed_month_missing:
            profile = _without_month(profile)
            parsed["month"] = ""
        try:
            segments = render_journal(parsed, profile, log, flag)
        except PagedrillRefusal:
            segments = []
        text = "".join(piece for piece, _italic in segments) if segments else None
        if parsed_month_missing and text:
            text = re.sub(r", (?:Jan\.|Feb\.|Mar\.|Apr\.|May|Jun\.|Jul\.|Aug\.|Sep\.|Oct\.|Nov\.|Dec\.) (\d{4})", r", \1", text)
        flags.extend(local_flags)
        flags.extend({"item": name, "why": "Not in the imported file. It was not invented.", "rule": "import"} for name in missing)
        return {"rendered": text, "missing": missing, "flags": flags}
    if engine == "apa-author-date" and authors and title and year:
        names = []
        for author in authors:
            given = author["initials"] or "[INITIALS NEEDED]"
            names.append(f"{author['family']}, {given}")
        if len(names) == 1:
            who = names[0]
        else:
            who = ", ".join(names[:-1]) + ", & " + names[-1]
        date = year if year else "[DATE NEEDED]"
        tail = f"{journal}" if journal else "[JOURNAL NEEDED]"
        if volume:
            tail += f", {volume}"
            if issue:
                tail += f"({issue})"
        if pages:
            tail += f", {pages.replace('-', '\u2013')}"
        sentence = f"{who} ({date}). {title}. {tail}."
        if doi:
            sentence += f" https://doi.org/{doi.removeprefix('https://doi.org/')}"
        flags.extend({"item": name, "why": "Not in the imported file. It was not invented.", "rule": "import"} for name in missing)
        return {"rendered": sentence, "missing": missing, "flags": flags}
    flags.extend({"item": name, "why": "Not in the imported file. It was not invented.", "rule": "import"} for name in missing)
    return {"rendered": None, "missing": missing, "flags": flags, "fields": {key: value for key, value in entry.items() if key != "authors"}}


def _without_month(profile: dict) -> dict:
    copied = dict(profile)
    references = dict(profile.get("references") or {})
    references["months"] = {}
    copied["references"] = references
    copied["source_keys"] = profile.get("source_keys") or {"refguide": "IEEE Reference Style Guide"}
    return copied
