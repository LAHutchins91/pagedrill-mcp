"""Word tracked changes for text-level edits.

Accepted text stays recoverable by unwrapping w:ins and dropping w:del.
Layout changes are listed in the change log; they are not fake wording revisions.
The markup follows the w:ins / w:del shape used by stetwise, with author Pagedrill.
"""

from __future__ import annotations

import difflib
import re
from datetime import datetime, timezone

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

AUTHOR = "Pagedrill"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def apply_tracked_changes(document, changes: list[dict]) -> None:
    """Rewrite paragraphs whose full text is a logged text change."""
    pending = []
    for change in changes:
        before = change.get("before")
        after = change.get("after")
        if not isinstance(before, str) or not isinstance(after, str):
            continue
        if before == after or after.startswith("(") or "\n" in after:
            continue
        pending.append((before, after))
    used: set[int] = set()
    xml = document.element.xml
    next_id = max((int(item) for item in re.findall(r'w:id="(\d+)"', xml)), default=0) + 1
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for paragraph in document.paragraphs:
        text = paragraph.text
        match_at = next((index for index, (_before, after) in enumerate(pending) if after == text and index not in used), None)
        if match_at is None:
            continue
        before, after = pending[match_at]
        used.add(match_at)
        next_id = _mark(paragraph, before, after, next_id, when)


def _mark(paragraph, before: str, after: str, next_id: int, when: str) -> int:
    runs = [run for run in paragraph.runs if run.text]
    # Direct font overrides are written only when the paragraph already had them.
    # IEEE conference styles fail if a tracked change adds rFonts or sz.
    font = next((run.font.name for run in runs if run.font.name), None)
    sized = next((run.font.size for run in runs if run.font.size is not None), None)
    size = int(sized.pt * 2) if sized is not None else None
    italic_spans = _spans(paragraph, lambda run: bool(run.italic))
    bold_spans = _spans(paragraph, lambda run: bool(run.bold))
    element = paragraph._p
    preserved = []
    for child in list(element):
        if child.tag != qn("w:r"):
            continue
        # Page breaks and fields are not wording. Keep them so a rewrite cannot drop them.
        if child.find(qn("w:br")) is not None or child.find(qn("w:fldChar")) is not None or child.find(qn("w:instrText")) is not None:
            preserved.append(child)
            continue
        element.remove(child)
    anchor = preserved[0] if preserved else None

    def place(node) -> None:
        if anchor is not None:
            anchor.addprevious(node)
        else:
            element.append(node)
    def place_kept(text: str, start: int) -> None:
        for piece, bold, italic in _format_groups(text, start, bold_spans, italic_spans):
            place(_run(piece, font, size, bold, italic))

    def place_inserted(text: str, start: int) -> int:
        nonlocal next_id
        groups = _format_groups(text, start, bold_spans, italic_spans)
        if not groups:
            return next_id
        wrapper = OxmlElement("w:ins")
        wrapper.set(qn("w:id"), str(next_id))
        wrapper.set(qn("w:author"), AUTHOR)
        wrapper.set(qn("w:date"), when)
        for piece, bold, italic in groups:
            wrapper.append(_run(piece, font, size, bold, italic))
        place(wrapper)
        next_id += 1
        return next_id

    pending: list[tuple[str, int]] = []

    def flush_kept() -> None:
        if not pending:
            return
        place_kept("".join(item[0] for item in pending), pending[0][1])
        pending.clear()

    pieces_a = _pieces(before)
    pieces_b = _pieces(after)
    matcher = difflib.SequenceMatcher(a=[piece[0] for piece in pieces_a], b=[piece[0] for piece in pieces_b], autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            pending.extend(pieces_b[j1:j2])
            continue
        flush_kept()
        if tag == "delete":
            deleted = "".join(piece[0] for piece in pieces_a[i1:i2])
            if deleted:
                place(_revision("w:del", next_id, _run(deleted, font, size, False, False, tag="w:delText"), when))
                next_id += 1
        elif tag == "insert":
            for text, start, _end in pieces_b[j1:j2]:
                place_inserted(text, start)
        else:
            deleted = "".join(piece[0] for piece in pieces_a[i1:i2])
            if deleted:
                place(_revision("w:del", next_id, _run(deleted, font, size, False, False, tag="w:delText"), when))
                next_id += 1
            for text, start, _end in pieces_b[j1:j2]:
                place_inserted(text, start)
    flush_kept()
    return next_id


def _pieces(text: str) -> list[tuple[str, int, int]]:
    return [(match.group(), match.start(), match.end()) for match in re.finditer(r"\s+|\S+", text)]


def _spans(paragraph, predicate) -> list[tuple[int, int]]:
    spans = []
    cursor = 0
    for run in paragraph.runs:
        text = run.text or ""
        if text and predicate(run):
            spans.append((cursor, cursor + len(text)))
        cursor += len(text)
    return spans


def _covers(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(span_start < end and start < span_end for span_start, span_end in spans)


def _format_groups(text: str, start: int, bold_spans, italic_spans) -> list[tuple[str, bool, bool]]:
    """Split one token where bold or italic changes, so volume stays italic and the issue does not."""
    groups: list[tuple[str, bool, bool]] = []
    for offset, character in enumerate(text):
        position = start + offset
        bold = _covers(bold_spans, position, position + 1)
        italic = _covers(italic_spans, position, position + 1)
        if groups and groups[-1][1] is bold and groups[-1][2] is italic:
            previous, _, _ = groups[-1]
            groups[-1] = (previous + character, bold, italic)
        else:
            groups.append((character, bold, italic))
    return groups


def _run(text: str, font: str, size_half_points: int, bold: bool, italic: bool, tag: str = "w:t"):
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    if bold:
        props.append(OxmlElement("w:b"))
    if italic:
        props.append(OxmlElement("w:i"))
    if font:
        fonts = OxmlElement("w:rFonts")
        fonts.set(qn("w:ascii"), font)
        fonts.set(qn("w:hAnsi"), font)
        props.append(fonts)
    if size_half_points:
        size = OxmlElement("w:sz")
        size.set(qn("w:val"), str(size_half_points))
        props.append(size)
    if len(props):
        run.append(props)
    node = OxmlElement(tag)
    if text[:1].isspace() or text[-1:].isspace():
        node.set(qn("xml:space"), "preserve")
    node.text = text
    run.append(node)
    return run


def _revision(kind: str, rev_id: int, run, when: str):
    wrapper = OxmlElement(kind)
    wrapper.set(qn("w:id"), str(rev_id))
    wrapper.set(qn("w:author"), AUTHOR)
    wrapper.set(qn("w:date"), when)
    wrapper.append(run)
    return wrapper


def accepted_document_xml(xml: bytes) -> bytes:
    """Drop deletions and promote insertions so a checklist sees the accepted text."""
    if b"w:ins" not in xml and b"w:del" not in xml:
        return xml
    from lxml import etree

    root = etree.fromstring(xml)
    ns = {"w": W}
    for deleted in root.xpath(".//w:del", namespaces=ns):
        parent = deleted.getparent()
        if parent is not None:
            parent.remove(deleted)
    for inserted in list(root.xpath(".//w:ins", namespaces=ns)):
        parent = inserted.getparent()
        if parent is None:
            continue
        index = parent.index(inserted)
        for child in list(inserted):
            parent.insert(index, child)
            index += 1
        parent.remove(inserted)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
