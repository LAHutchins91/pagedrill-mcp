"""Shared helpers for the formatter prototypes (MLA 9, IEEE, Vancouver).
Rules: format only. Never rewrites the author's sentences, never invents reference data.
Every text-level change is logged (shown to the user as a diff before saving); anything the
style leaves to the user/instructor, or that our official sources don't settle, is FLAGGED, not guessed."""
import json, re, difflib
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

class Log:
    def __init__(self): self.changes, self.flags = [], []
    def change(self, kind, before, after, rule): self.changes.append({"kind": kind, "before": before, "after": after, "rule": rule})
    def flag(self, item, why, rule): self.flags.append({"item": item, "why": why, "rule": rule})
    def dump(self, path): json.dump({"changes": self.changes, "flags": self.flags}, open(path, "w"), indent=2, ensure_ascii=False)

def norm(s): return re.sub(r"[\W_]+", "", (s or "").lower())

def ground(ref, original, skip=("key", "type", "_note", "status")):
    """Every extracted value must literally occur in the user's original reference text (case/punctuation-insensitive).
    Values the user never typed stay null and get flagged. This makes invented DOIs/dates/pages impossible."""
    o = norm(original)
    for k, v in ref.items():
        if k in skip or v is None: continue
        if k == "authors":
            vals = []
            for a in v: vals += [a.get("family"), a.get("given"), a.get("initials")]
        elif isinstance(v, list): vals = v
        else: vals = [v]
        for x in vals:
            if x and norm(str(x)) not in o:
                raise SystemExit(f"GROUNDING FAIL: {k}={x!r} not found in the original reference text: {original[:120]}")

def ital_runs(p, segs, font=None, size=None):
    """segs = [(text, italic, highlight)]"""
    for text, it, hl in segs:
        r = p.add_run(text); r.italic = bool(it)
        if font: r.font.name = font
        if size: r.font.size = Pt(size)
        if hl: r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return p

def add_field(p, instr, font=None, size=None, placeholder="1"):
    r = p.add_run()
    if font: r.font.name = font
    if size: r.font.size = Pt(size)
    for tag, attr in (("w:fldChar", {"w:fldCharType": "begin"}), ("w:instrText", None), ("w:fldChar", {"w:fldCharType": "separate"})):
        e = OxmlElement(tag)
        if attr:
            for k, v in attr.items(): e.set(qn(k), v)
        else: e.set(qn("xml:space"), "preserve"); e.text = f" {instr} "
        r._r.append(e)
    t = OxmlElement("w:t"); t.text = placeholder; r._r.append(t)
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); r._r.append(e)
    return r

def set_font_everywhere(style, font):
    rpr = style.element.get_or_add_rPr(); rf = rpr.find(qn("w:rFonts"))
    if rf is None: rf = OxmlElement("w:rFonts"); rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"): rf.set(qn(a), font)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None: del rf.attrib[qn(a)]

def set_auto_hyphenation(doc, on):
    s = doc.settings.element; e = s.find(qn("w:autoHyphenation"))
    if e is None: e = OxmlElement("w:autoHyphenation"); s.append(e)
    e.set(qn("w:val"), "true" if on else "false")

def page_break_after(p): p.add_run().add_break(WD_BREAK.PAGE)

def words(text): return re.findall(r"[\w’'-]+|[^\w\s]", text)

def word_diff(before_text, after_text):
    return [x for x in difflib.ndiff(words(before_text), words(after_text)) if x[0] in "+-"]

def sentence_case(title, keep=(), cap_after_colon=True):
    """Lowercase every word except: the first word, the first word after a colon, ALL-CAPS tokens/acronyms
    (2+ capitals, e.g. HIV, MRI, BEM, TFT), and any word in `keep`. Returns (new, changed_words) so the change is logged and flagged:
    proper nouns cannot be detected reliably, so the user must confirm."""
    out, cap_next, changed = [], True, []
    acr = lambda p: bool(re.search(r"[A-Z].*[A-Z]", p)) or bool(re.search(r"\d", p))
    for w in title.split(" "):
        core = re.sub(r"^[^\w]+|[^\w]+$", "", w)
        if core in keep: nw = w
        else:
            parts = w.split("-"); np_ = []
            for k, p in enumerate(parts):
                pc = re.sub(r"^[^\w]+|[^\w]+$", "", p)
                if (cap_next and k == 0) or acr(pc) or pc in keep: np_.append(p)
                else: np_.append(p.lower())
            nw = "-".join(np_)
        if nw != w: changed.append(w)
        out.append(nw); cap_next = w.endswith(":") and cap_after_colon
    return " ".join(out), changed

def body_text(doc, start=0, stop=None):
    return " ".join(p.text for p in doc.paragraphs[start:stop] if p.text.strip())
