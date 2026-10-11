"""AR 25-50 memorandum. Missing letterhead, ARIMS, and branch codes are flagged, never invented."""

from __future__ import annotations

import re
from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from .errors import PagedrillRefusal
from .packageio import splice_allowed
from .revisions import apply_tracked_changes

MONTHS = "January February March April May June July August September October November December".split()
DATE_RE = re.compile(r"(%s)\s+(\d{1,2})(?:st|nd|rd|th)?,\s*(\d{4})" % "|".join(MONTHS))
TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?", re.I)
MINOR = {"to", "of", "and", "the", "a", "for", "in", "on"}
MILITARY_NOTICE = (
    "Unclassified drafting aid only. Pagedrill is not endorsed by the Department of Defense "
    "and does not display the DoD seal. Do not upload classified information or controlled unclassified information."
)


def _norm(value: str) -> str:
    return re.sub(r"\W+", "", value.lower())


def military_date(value: str) -> str:
    return DATE_RE.sub(lambda match: f"{int(match.group(2))} {match.group(1)} {match.group(3)}", value)


def fix_body(text: str) -> tuple[str, list[tuple[str, str, str]]]:
    """Return regulation date and time forms. The author's other words stay."""
    logs: list[tuple[str, str, str]] = []
    dated = military_date(text)
    if dated != text:
        logs.append(("date-format", text, dated))
    previous = dated

    def clock(match: re.Match) -> str:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3).lower()
        hour = (hour % 12) + (12 if meridiem.startswith("p") else 0)
        tail = match.string[match.end() :]
        keep_period = match.group(0).endswith(".") and (tail == "" or re.match(r"\s+[A-Z]", tail) is not None)
        return f"{hour:02d}{minute:02d}" + ("." if keep_period else "")

    timed = TIME_RE.sub(clock, dated)
    if timed != previous:
        logs.append(("military-time", previous, timed))
    spaced = re.sub(r"(?<!\b[A-Z])([.?])\s+(?=[A-Z(])", r"\1  ", timed)
    if spaced != timed:
        logs.append(("sentence-spacing", timed, spaced))
    return spaced, logs


def subject_case(value: str) -> str:
    words = value.split(" ")
    rendered = []
    for index, word in enumerate(words):
        if index and word.lower() in MINOR:
            rendered.append(word.lower())
        else:
            rendered.append(word[:1].upper() + word[1:])
    return " ".join(rendered)


def _classify_body(text: str) -> tuple[int, str]:
    lettered = re.match(r"^([a-z])\s*-\s+(.+)$", text)
    if lettered:
        return 2, lettered.group(2)
    roman = re.match(r"^((?:i|ii|iii|iv|v|vi|vii|viii|ix|x))\.\s+(.+)$", text)
    if roman:
        return 3, roman.group(2)
    return 1, text


def _ground(blob: str, value: str, label: str) -> None:
    if value and _norm(value) not in blob:
        raise PagedrillRefusal(
            f"The {label} was not in the author's text. Pagedrill did not invent it.",
            "grounding_failed",
        )


def format_memo(original: bytes, profile: dict, supplied: dict | None = None) -> dict:
    supplied = supplied or {}
    source = Document(BytesIO(original))
    lines = [paragraph.text.strip() for paragraph in source.paragraphs if paragraph.text.strip()]
    if any(text.startswith("MEMORANDUM FOR") for text in lines):
        return _reformat_structured(original, profile, supplied)
    blob = _norm(" ".join(lines))
    changes: list[dict] = []
    flags: list[dict] = []

    def log(kind: str, before: str, after: str, ref: str) -> None:
        changes.append({"kind": kind, "before": before, "after": after, "ref": ref})

    def flag(item: str, why: str, ref: str) -> None:
        flags.append({"item": item, "why": why, "ref": ref})

    organization = None
    meta: dict[str, str] = {}
    body: list[dict] = []
    signature_lines: list[str] = []
    salutation = None
    close = None
    postscript = None
    phase = "head"
    for text in lines:
        if phase == "signature":
            if re.match(r"^p\.?\s*s\.?", text, re.I):
                postscript = text
                phase = "done"
            else:
                signature_lines.append(text)
            continue
        if re.match(r"^p\.?\s*s\.?", text, re.I):
            postscript = text
            continue
        if re.match(r"^sincerely\b", text, re.I):
            close = text
            phase = "signature"
            continue
        dated = re.match(r"^date\s*:\s*(.+)$", text, re.I)
        if dated and "date" not in meta:
            meta["date"] = dated.group(1).strip()
            continue
        addressed = re.match(r"^to\s*:\s*(.+)$", text, re.I)
        if addressed and "memo_for" not in meta:
            meta["memo_for"] = addressed.group(1).strip()
            continue
        office = re.match(r"^from\s*:\s*(.+)$", text, re.I)
        if office and "office_symbol" not in meta:
            symbol = re.search(r"\b([A-Z]{2,}(?:-[A-Z0-9]+)+)\b", office.group(1))
            if symbol:
                meta["office_symbol"] = symbol.group(1)
                meta["from_line"] = text
            continue
        subject = re.match(r"^subject\s*[-:]\s*(.+)$", text, re.I)
        if subject and "subject" not in meta:
            meta["subject"] = subject.group(1).strip()
            continue
        if re.match(r"^dear\b", text, re.I):
            salutation = text
            continue
        if organization is None and not body:
            organization = text
            continue
        level, bare = _classify_body(text)
        body.append({"level": level, "text": bare, "original": text})

    for key in ("date", "memo_for", "office_symbol", "subject"):
        if key not in meta:
            raise PagedrillRefusal(
                f"The memorandum is missing {key.replace('_', ' ')}. Pagedrill did not invent it.",
                "missing_field",
            )
        _ground(blob, meta[key], key.replace("_", " "))
    if not organization:
        raise PagedrillRefusal("The memorandum is missing the organization line. Pagedrill did not invent it.", "missing_field")
    _ground(blob, organization, "organization")
    if supplied.get("organization"):
        organization = str(supplied["organization"]).strip()
        _ground(blob, organization, "organization")
    for key in ("office_symbol", "memo_for", "subject", "date"):
        if supplied.get(key):
            meta[key] = str(supplied[key]).strip()
            _ground(blob, meta[key], key.replace("_", " "))
    if supplied.get("arims"):
        meta["arims"] = str(supplied["arims"]).strip()
    if supplied.get("branch_abbrev"):
        meta["branch_abbrev"] = str(supplied["branch_abbrev"]).strip()

    for item in body:
        _ground(blob, item["text"], "paragraph")
        rendered, logs = fix_body(item["text"])
        item["rendered"] = rendered
        for kind, before, after in logs:
            ref = {"date-format": profile["date_ref"], "military-time": profile["time_ref"], "sentence-spacing": profile["spaces_ref"]}[kind]
            log(kind, before, after, ref)
    for item in body:
        expected, _logs = fix_body(item["text"])
        if re.sub(r"\s+", " ", expected).strip() != re.sub(r"\s+", " ", item["rendered"]).strip():
            raise PagedrillRefusal("The format would change the author's words. Pagedrill refused it and did not save.", "word_change")

    ranks = {key: value for key, value in profile.get("rank_abbreviations", {}).items() if key != "ref"}
    signature = _signature(signature_lines, ranks, blob)
    date = military_date(meta["date"])
    log("date-format", meta["date"], date, profile["date_ref"])
    subject = subject_case(meta["subject"])
    if len(subject.split()) > 10:
        flag(
            "Subject length",
            "AR 25-50 limits the subject to 10 words or fewer. It was not shortened, because shortening would drop the author's words.",
            "para 2-4a(6)",
        )

    document = Document(BytesIO(original))
    _prepare(document, profile)
    _clear_body(document)
    _write(document, profile, organization, meta, date, subject, body, signature, salutation, close, postscript, log, flag)
    if supplied.get("track_changes"):
        apply_tracked_changes(document, changes)
    fresh = BytesIO()
    document.save(fresh)
    data, verification = splice_allowed(original, fresh.getvalue())
    return {
        "docx": data,
        "changes": changes,
        "flags": flags,
        "verification": verification,
        "title": subject,
        "notice": MILITARY_NOTICE,
    }


def _signature(lines: list[str], ranks: dict, blob: str) -> dict:
    if len(lines) < 3:
        raise PagedrillRefusal(
            "The signature block is missing a name, rank, or title. Pagedrill did not invent them.",
            "missing_field",
        )
    name, rank_line, title = lines[0], lines[1], lines[2]
    _ground(blob, name, "signature name")
    _ground(blob, rank_line, "rank line")
    _ground(blob, title, "title")
    match = re.match(r"^([A-Za-z ]+?),\s+(.+)$", rank_line)
    if not match:
        raise PagedrillRefusal("The rank line could not be read. Pagedrill did not guess a rank or branch.", "missing_field")
    rank, branch = match.group(1).strip(), match.group(2).strip()
    abbrev = ranks.get(rank)
    if not abbrev:
        raise PagedrillRefusal(
            "That rank is not in the AR 25-50 abbreviation table loaded with this profile. It was not guessed.",
            "missing_field",
        )
    return {"name": name, "rank": rank, "abbrev": abbrev, "branch": branch, "title": title}


def _prepare(document: Document, profile: dict) -> None:
    font_name = profile["font"]["name"]
    normal = document.styles["Normal"]
    normal.font.name = font_name
    normal.font.size = Pt(profile["font"]["size_pt"])
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    paragraph = normal.paragraph_format
    paragraph.space_before = Pt(0)
    paragraph.space_after = Pt(0)
    paragraph.line_spacing = 1.0
    section = document.sections[0]
    section.page_width = Inches(profile["page"]["size_in"][0])
    section.page_height = Inches(profile["page"]["size_in"][1])
    for side, value in profile["page"]["margins_in"].items():
        setattr(section, f"{side}_margin", Inches(value))


def _clear_body(document: Document) -> None:
    body = document.element.body
    for child in list(body):
        if child.tag.endswith("sectPr"):
            continue
        body.remove(child)


def _run(paragraph, text: str, profile: dict, bold: bool = False, size: int | None = None, highlight: bool = False):
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.name = profile["font"]["name"]
    run.font.size = Pt(size or profile["font"]["size_pt"])
    if highlight:
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return run


def _paragraph(document, profile, text="", align="left", left=0.0, first=0.0, bold=False, size=None, highlight=False):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if align == "center" else WD_ALIGN_PARAGRAPH.LEFT
    fmt = paragraph.paragraph_format
    fmt.left_indent = Inches(left)
    fmt.first_line_indent = Inches(first)
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.line_spacing = 1.0
    if text:
        _run(paragraph, text, profile, bold=bold, size=size, highlight=highlight)
    return paragraph


def _blanks(document, profile, count: int) -> None:
    for _ in range(count):
        _paragraph(document, profile)


def _write(document, profile, organization, meta, date, subject, body, signature, salutation, close, postscript, log, flag) -> None:
    lines = profile["lines"]
    _paragraph(document, profile, "[DoD SEAL — use APD letterhead template]", "center", size=8, highlight=True)
    _paragraph(document, profile, "DEPARTMENT OF THE ARMY", "center", bold=True, size=10)
    _paragraph(document, profile, organization.upper(), "center", bold=True, size=8)
    address = str(meta.get("street") or "")
    city = str(meta.get("city_line") or "")
    if not address:
        _paragraph(document, profile, "[STANDARDIZED STREET ADDRESS]", "center", bold=True, size=8, highlight=True)
    else:
        _paragraph(document, profile, address, "center", bold=True, size=8)
    if not city:
        _paragraph(document, profile, "[CITY STATE ZIP+4]", "center", bold=True, size=8, highlight=True)
    else:
        _paragraph(document, profile, city, "center", bold=True, size=8)
    flag(
        "Letterhead",
        "AR 25-50 para 1-16 requires the computer-generated APD letterhead with the DoD seal and a complete standardized address. Pagedrill left a highlighted text placeholder and did not draw a seal.",
        "para 1-16, 1-35",
    )
    _blanks(document, profile, lines["office_symbol_after_seal"] - 1)
    office = _paragraph(document, profile)
    office.paragraph_format.tab_stops.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.RIGHT)
    _run(office, meta["office_symbol"] + " ", profile)
    arims = meta.get("arims")
    if arims:
        _run(office, f"({arims})", profile)
    else:
        _run(office, "([ARIMS record no.])", profile, highlight=True)
        flag(
            "ARIMS record number",
            "Required after the office symbol. It depends on the record type and was not in the original, so a highlighted placeholder was left.",
            "para 2-4a(2)",
        )
    _run(office, "\t" + date, profile)
    log(
        "office-symbol-line",
        meta.get("from_line", meta["office_symbol"]),
        f"{meta['office_symbol']} ([ARIMS record no.])\t{date}",
        "para 2-4a(1)-(3)",
    )
    flag(
        "Date",
        "The date on a memorandum is added after signing, or in a text box for a digital signature. The typed date was kept and reformatted. It was not treated as the date of signature.",
        "para 2-4a(3)",
    )
    _blanks(document, profile, lines["memo_for_after_office_symbol"] - 1)
    _paragraph(document, profile, "MEMORANDUM FOR " + meta["memo_for"])
    log("memo-for", "TO: " + meta["memo_for"], "MEMORANDUM FOR " + meta["memo_for"], "para 2-4a(5)(a)")
    _blanks(document, profile, lines["subject_after_address"] - 1)
    _paragraph(document, profile, "SUBJECT: " + subject)
    log("subject", "Subject - " + meta["subject"], "SUBJECT: " + subject, "para 2-4a(6)")
    flag(
        "Subject capitalization",
        'The regulation requires "SUBJECT:" in capitals and 10 words or fewer. It does not state a rule for the subject words. Figures show initial capitals, so the subject was cased to match the figures.',
        "para 2-4a(6), figure 2-1",
    )
    _blanks(document, profile, lines["text_after_subject"] - 1)
    if salutation:
        log("removed", salutation, "(removed: a memorandum has no salutation)", "para 2-4, 3-4a")
    counts = {1: 0, 2: 0, 3: 0}
    indents = {1: 0.0, 2: profile["body"]["first_indent_in"], 3: profile["body"]["second_indent_in"]}
    for index, item in enumerate(body):
        level = item["level"]
        counts[level] += 1
        for deeper in range(level + 1, 4):
            counts[deeper] = 0
        if level == 1:
            label = f"{counts[1]}."
        elif level == 2:
            label = f"{chr(ord('a') + counts[2] - 1)}."
        else:
            label = f"({counts[3]})"
        rendered_line = f"{label}  {item['rendered']}"
        log("paragraph", item.get("original", item["rendered"]), rendered_line, profile["body"]["ref"])
        _paragraph(document, profile, rendered_line, left=0.0, first=indents[level])
        if index < len(body) - 1:
            _paragraph(document, profile)
    log("numbering", "unnumbered / lettered / roman", "1. / a. / (1)", profile["body"]["ref"])
    flag(
        "References paragraph",
        "References belong in the first paragraph. The original already led with the reference, so it stayed paragraph 1.",
        "para 1-30, 2-4b(1)(a)",
    )
    flag(
        "POC",
        "The point of contact stays in the last paragraph. Contact details were not invented.",
        "para 1-23, 2-4b(1)(e)",
    )
    if close:
        log("removed", close, "(removed: a memorandum closes with the authority line and signature block)", "para 2-4c")
    _blanks(document, profile, lines["signature_after_authority_or_text"] - 1)
    flag(
        "Authority line",
        "None was added. An authority line is used only when someone signs for the commander. The signature block is on the 5th line below the text.",
        "para 2-4c(1), 6-4b",
    )
    left = profile["signature"]["start_from_left_margin_in"]
    fictional = re.search(r"\(fictional\)", signature["name"], re.I)
    name = re.sub(r"\s*\(fictional\)", "", signature["name"], flags=re.I).upper()
    if fictional:
        name += " (FICTIONAL)"
    _paragraph(document, profile, name, left=left)
    rank = _paragraph(document, profile, left=left)
    _run(rank, signature["abbrev"] + ", ", profile)
    if meta.get("branch_abbrev"):
        _run(rank, meta["branch_abbrev"], profile)
    else:
        _run(rank, f"[branch abbrev.: {signature['branch']}]", profile, highlight=True)
        flag(
            "Branch abbreviation",
            "Para 6-4c says the branch is abbreviated per DA Pam 611-21. That code was not in the original, so it was not guessed.",
            "para 6-4c, 6-4f",
        )
    _paragraph(document, profile, signature["title"], left=left)
    log(
        "signature-block",
        f"{signature['name']} / {signature['rank']}, {signature['branch']} / {signature['title']}",
        f"{name} / {signature['abbrev']}, [branch abbrev.] / {signature['title']}",
        "para 6-4a-c, table 6-1",
    )
    if postscript:
        flag(
            "Postscript",
            f'"{postscript}" is the writer\'s content. Para 1-29 says not to use postscripts, so it was held out of the layout and listed here.',
            "para 1-29",
        )
        log("held-out", postscript, "(held out of the memo: no postscripts)", "para 1-29")
    flag(
        "Font",
        "Para 1-19 leaves the font face to Army senior leaders and recommends 12 point. Arial 12 is the profile setting, not a DoD-mandated face.",
        "para 1-19",
    )


def create_memo(profile: dict, fields: dict) -> dict:
    """Build a new AR 25-50 memorandum from fields the user filled in."""
    required = ("organization", "office_symbol", "memo_for", "subject", "paragraphs", "signature")
    for key in required:
        if not fields.get(key):
            raise PagedrillRefusal(f"The memorandum needs {key.replace('_', ' ')}. Pagedrill did not invent it.", "missing_field")
    signature_in = fields["signature"] if isinstance(fields["signature"], dict) else {}
    for key in ("name", "rank", "title"):
        if not str(signature_in.get(key) or "").strip():
            raise PagedrillRefusal(f"The signature block needs a {key}. Pagedrill did not invent it.", "missing_field")
    paragraphs = fields["paragraphs"]
    if not isinstance(paragraphs, list) or not all(isinstance(item, str) and item.strip() for item in paragraphs):
        raise PagedrillRefusal("Each paragraph must be text you supply. Pagedrill did not invent one.", "missing_field")
    ranks = {key: value for key, value in profile.get("rank_abbreviations", {}).items() if key != "ref"}
    rank = str(signature_in["rank"]).strip()
    abbrev = ranks.get(rank)
    if not abbrev:
        raise PagedrillRefusal(
            "That rank is not in the AR 25-50 abbreviation table loaded with this profile. It was not guessed.",
            "missing_field",
        )
    changes: list[dict] = []
    flags: list[dict] = []

    def log(kind: str, before: str, after: str, ref: str) -> None:
        changes.append({"kind": kind, "before": before, "after": after, "ref": ref})

    def flag(item: str, why: str, ref: str) -> None:
        flags.append({"item": item, "why": why, "ref": ref})

    body = []
    for text in paragraphs:
        level, bare = _classify_body(text.strip())
        rendered, logs = fix_body(bare)
        for kind, before, after in logs:
            ref = {"date-format": profile["date_ref"], "military-time": profile["time_ref"], "sentence-spacing": profile["spaces_ref"]}[kind]
            log(kind, before, after, ref)
        if re.sub(r"\s+", " ", rendered).strip() != re.sub(r"\s+", " ", fix_body(bare)[0]).strip():
            raise PagedrillRefusal("The format would change the author's words. Pagedrill refused it and did not save.", "word_change")
        body.append({"level": level, "text": bare, "rendered": rendered, "original": text.strip()})
    poc = str(fields.get("poc") or "").strip()
    if poc:
        rendered, logs = fix_body(poc)
        for kind, before, after in logs:
            ref = {"date-format": profile["date_ref"], "military-time": profile["time_ref"], "sentence-spacing": profile["spaces_ref"]}[kind]
            log(kind, before, after, ref)
        body.append({"level": 1, "text": poc, "rendered": rendered, "original": poc})
    date = str(fields.get("date") or "").strip()
    if date:
        dated = military_date(date)
        log("date-format", date, dated, profile["date_ref"])
        date = dated
    else:
        date = "[date of signature]"
        flag("Date", "No date was supplied. The date is added after signing, so none was invented.", "para 2-4a(3)")
    subject = subject_case(str(fields["subject"]).strip())
    meta = {
        "office_symbol": str(fields["office_symbol"]).strip(),
        "memo_for": str(fields["memo_for"]).strip(),
        "subject": str(fields["subject"]).strip(),
        "from_line": str(fields["office_symbol"]).strip(),
    }
    if fields.get("arims"):
        meta["arims"] = str(fields["arims"]).strip()
    if fields.get("branch_abbrev"):
        meta["branch_abbrev"] = str(fields["branch_abbrev"]).strip()
    if fields.get("street"):
        meta["street"] = str(fields["street"]).strip()
    if fields.get("city_line"):
        meta["city_line"] = str(fields["city_line"]).strip()
    signature = {
        "name": str(signature_in["name"]).strip(),
        "rank": rank,
        "abbrev": abbrev,
        "branch": str(signature_in.get("branch") or "").strip() or "[branch needed]",
        "title": str(signature_in["title"]).strip(),
    }
    if signature["branch"] == "[branch needed]":
        flag("Branch", "No branch was supplied, so none was abbreviated.", "para 6-4c")
    document = Document()
    _prepare(document, profile)
    _clear_body(document)
    _write(document, profile, str(fields["organization"]).strip(), meta, date, subject, body, signature, None, None, None, log, flag)
    if fields.get("track_changes"):
        apply_tracked_changes(document, changes)
    fresh = BytesIO()
    document.save(fresh)
    return {
        "docx": fresh.getvalue(),
        "changes": changes,
        "flags": flags,
        "verification": {
            "changed_parts": ["word/document.xml"],
            "removed_parts": [],
            "added_parts": [],
            "untouched_part_count": 0,
            "untouched_identical": True,
            "basis": "new-memorandum",
        },
        "title": subject,
        "notice": MILITARY_NOTICE,
    }


def _reformat_structured(original: bytes, profile: dict, supplied: dict) -> dict:
    """Rewrite a memorandum that is already in AR 25-50 layout. Words stay."""
    source = Document(BytesIO(original))
    paragraphs = list(source.paragraphs)
    texts = [paragraph.text for paragraph in paragraphs]
    changes: list[dict] = []
    flags: list[dict] = []

    def log(kind: str, before: str, after: str, ref: str) -> None:
        changes.append({"kind": kind, "before": before, "after": after, "ref": ref})

    def flag(item: str, why: str, ref: str) -> None:
        flags.append({"item": item, "why": why, "ref": ref})

    try:
        office = next(text for text in texts if "([ARIMS" in text or re.match(r"^[A-Z]{2,}(?:-[A-Z0-9]+)+ ", text))
        memo_for = next(text for text in texts if text.startswith("MEMORANDUM FOR "))[len("MEMORANDUM FOR ") :]
        subject = next(text for text in texts if text.startswith("SUBJECT: "))[len("SUBJECT: ") :]
    except StopIteration as exc:
        raise PagedrillRefusal("The memorandum layout is incomplete. Pagedrill did not invent the missing line.", "missing_field") from exc
    match = re.match(r"^(\S+) \((.*)\)\t(.+)$", office)
    if not match:
        raise PagedrillRefusal("The office-symbol line could not be read. Pagedrill did not rebuild it from a guess.", "missing_field")
    organization = next((text for text in texts if text.isupper() and text not in {"DEPARTMENT OF THE ARMY"} and not text.startswith("[") and "," not in text and len(text.split()) <= 8), "")
    if not organization:
        raise PagedrillRefusal("The organization line was not in the memorandum. Pagedrill did not invent it.", "missing_field")
    body = []
    for text in texts:
        labeled = re.match(r"^(?:\d+\.|[a-z]\.|\(\d+\))  (.+)$", text)
        if not labeled:
            continue
        level, _bare = _classify_body(text)
        prose = labeled.group(1)
        body.append({"level": level, "text": prose, "rendered": prose, "original": text})
    signature_lines = [paragraph.text for paragraph in paragraphs if paragraph.text.strip() and abs((paragraph.paragraph_format.left_indent or 0) - Inches(3.25)) < 20000]
    if len(signature_lines) < 3:
        raise PagedrillRefusal("The signature block was not in the memorandum. Pagedrill did not invent it.", "missing_field")
    rank_line = signature_lines[1]
    rank_match = re.match(r"^([^,]+),\s*(.*)$", rank_line)
    if not rank_match:
        raise PagedrillRefusal("The rank line could not be read. Pagedrill did not guess a rank.", "missing_field")
    branch_text = rank_match.group(2)
    branch_abbrev = None
    branch = branch_text
    placeholder = re.match(r"\[branch abbrev\.: (.+)\]", branch_text)
    if placeholder:
        branch = placeholder.group(1)
        branch_abbrev = None
    else:
        branch_abbrev = branch_text
        branch = branch_text
    arims = match.group(2)
    meta = {"office_symbol": match.group(1), "memo_for": memo_for, "subject": subject, "from_line": office}
    if "ARIMS record no." not in arims:
        meta["arims"] = arims
    if branch_abbrev:
        meta["branch_abbrev"] = branch_abbrev
    signature = {
        "name": signature_lines[0],
        "rank": rank_match.group(1),
        "abbrev": rank_match.group(1),
        "branch": branch,
        "title": signature_lines[2],
    }
    document = Document(BytesIO(original))
    _prepare(document, profile)
    _clear_body(document)
    _write(document, profile, organization, meta, match.group(3), subject_case(subject), body, signature, None, None, None, log, flag)
    if supplied.get("track_changes"):
        apply_tracked_changes(document, changes)
    fresh = BytesIO()
    document.save(fresh)
    data, verification = splice_allowed(original, fresh.getvalue())
    return {"docx": data, "changes": changes, "flags": flags, "verification": verification, "title": subject, "notice": MILITARY_NOTICE}
