"""Reformat a messy student paper to MLA 9 (profiles/mla9_paper.json). Format only: never rewrites sentences, never invents data.
usage: python3 src/format_mla.py mla_before.docx mla_after.docx profiles/mla9_paper.json refs_mla.json"""
import json, re, sys
sys.path.insert(0, "src")
from fmtlib import *
SRC, DST, PROFILE, REFS = sys.argv[1:5]
prof = json.load(open(PROFILE)); refs = json.load(open(REFS))["references"]; S = prof["sources"]
FONT, SIZE = prof["font"]["name"], prof["font"]["size_pt"]
L = Log()
src = Document(SRC)
paras = [(p.style.name, p.text.strip(), p) for p in src.paragraphs if p.text.strip()]

# ---------- 1. classify roles ----------
LABELS = {"student": "author", "name": "author", "author": "author", "instructor": "instructor", "professor": "instructor",
          "teacher": "instructor", "course": "course", "class": "course", "date": "date", "due": "date"}
meta, body, ref_texts, title, in_refs, wc_label = {}, [], [], None, False, None
for style, text, p in paras:
    m = re.match(r"^(\w+)\s*:\s*(.+)$", text)
    if not in_refs and title is None and m and m.group(1).lower() in LABELS:
        meta[LABELS[m.group(1).lower()]] = m.group(2).strip(); L.change("header-label-removed", text, m.group(2).strip(), S["ch1_3"]); continue
    if re.match(r"^(works cited|work cited|references?|bibliography|sources)\s*:?$", text, re.I):
        in_refs = True; wc_label = text; continue
    if in_refs: ref_texts.append(text); continue
    if title is None and not style.startswith("Heading"):
        title = text; title_runs = p.runs; continue
    lvl = int(style.split()[-1]) if style.startswith("Heading") and style.split()[-1].isdigit() else 0
    ital = [r.text for r in p.runs if r.italic and r.text.strip()]
    body.append({"level": lvl, "text": text, "italic": ital})
L.change("header-order", " / ".join(f"{k}" for k in meta), "author / instructor / course / date", S["ch1_3"])

# ---------- 2. title (1.3): no bold/italic/underline/quotes/all caps, no period; capitalization untouched ----------
t0 = title
if any(r.bold or r.underline for r in title_runs): L.change("title-style", "bold/underlined, 16 pt", "plain, 12 pt, centered", S["ch1_3"])
if re.search(r"[.]$", title): title = title[:-1]; L.change("title-period", t0, title, S["ch1_3"])
if title.strip("\u201c\u201d\"") != title: title = title.strip("\u201c\u201d\""); L.change("title-quotes", t0, title, S["ch1_3"])
if title.isupper(): L.flag("Title", "Typed in all capital letters. MLA 1.3 says not to; recasing needs the Handbook's capitalization rules (2.90, subscription-only), so the formatter leaves it for the writer.", S["ch1_3"])
L.flag("Title capitalization", "Kept exactly as typed. MLA 1.3 refers to section 2.90 for capitalization, which is subscription-only and was not read; the formatter does not recase titles.", S["ch1_3"])

# ---------- 3. headings (1.5) ----------
for b in body:
    if not b["level"]: continue
    t2 = re.sub(r"^\s*(\d+(\.\d+)*[.)]|[a-zA-Z][.)]|[IVXivx]+[.)])\s+", "", b["text"])
    if t2 != b["text"]:
        L.change("heading-numbering", b["text"], t2, S["ch1_5"])
        L.flag(f'Heading "{b["text"]}"', "Number removed: MLA 1.5 says generally avoid numbers/letters on headings unless your discipline uses them. Put them back if your instructor wants numbered sections.", S["ch1_5"])
        b["text"] = t2
    if b["text"].isupper(): L.flag(f'Heading "{b["text"]}"', "All capitals: MLA 1.5 says avoid them; recasing needs 2.90 (not read). Left for the writer.", S["ch1_5"])
from collections import Counter
cnt = Counter(b["level"] for b in body if b["level"])
for lvl, n in cnt.items():
    if n == 1: L.flag(f"Heading level {lvl}", "Only one heading at this level. MLA 1.5: no internal heading level should have only one instance. Writer's call; not changed.", S["ch1_5"])
L.flag("Space around headings", "MLA 1.5 says 'include a line space above and below a heading'. In a fully double-spaced paper it is unclear whether an extra blank line is meant, so the formatter adds none. Confirm with the instructor.", S["ch1_5"])

# ---------- 4. references: grounding + render ----------
orig_for = {}
for r in refs:
    hit = [t for t in ref_texts if norm(r["authors"][0]["family"]) in norm(t)]
    if len(hit) != 1: raise SystemExit(f"cannot match reference {r['key']}")
    orig_for[r["key"]] = hit[0]; ground({k: v for k, v in r.items() if k not in ("crossref", "et_al")}, hit[0])
MON = prof["entries"]["month_abbrev_over_four_letters"]["map"]
SEEN9 = {"January", "September"}
def dash(p, key):
    a, _, b = p.partition("-")
    if a.isdigit() and b.isdigit() and int(a) > 99 and len(a) == len(b) and a[:-2] == b[:-2]:
        L.flag(f"Pages {p} ({key})", "MLA shortens the second number of some ranges (Handbook 2.139, subscription-only, not read). Kept in full.", "MLA Handbook 2.139 (not verified)")
    return p.replace("-", "\u2013")
def end_title(t): return t if t[-1] in "?!" else t + "."
rendered = []
for r in refs:
    a = r["authors"][0]
    au = f'{a["family"]}, {a["given"]}' + (", et al." if r.get("et_al") else ("" if a["given"].endswith(".") else "."))
    if len(r["authors"]) == 2:
        au = f'{a["family"]}, {a["given"]}, and {r["authors"][1]["given"]} {r["authors"][1]["family"]}.'
        L.flag(f"Authors ({r['key']})", "Two-author pattern taken from an MLA post written for the 8th edition (not verified for the 9th).", S["two_authors_8th"])
    if r.get("et_al"): L.flag(f"Authors ({r['key']})", "'et al.' after the first author: matches the 9th-ed. example 'Adams, Peter, et al.' (Closer Look); the rule text itself (Handbook 5.3-5.22) is subscription-only.", S["closer_look"])
    if r["type"] == "book":
        segs = [(au + " ", False, False), (r["title"], True, False), (". " + r["publisher"] + ", " + r["year"] + ".", False, False)]
    else:
        date = r["year"]
        if r.get("month"):
            mm = MON[r["month"]]; date = f"{mm} {r['year']}"
            if r["month"] not in SEEN9: L.flag(f"Month ({r['key']})", f"Abbreviated '{r['month']}' as '{mm}'; the 9th-ed. rule (abbreviate months longer than four letters) is verified, but this exact abbreviation was not seen in a 9th-ed. source.", S["closer_look"])
        if r.get("season"): date = f"{r['season'].lower()} {r['year']}"
        tail = f", vol. {r['volume']}" + (f", no. {r['issue']}" if r.get("issue") else "") + f", {date}, pp. {dash(r['pages'], r['key'])}"
        if r.get("doi"): tail += f", https://doi.org/{re.sub(r'^(https?://(dx\.)?doi\.org/|doi:\s*)', '', r['doi'], flags=re.I)}"
        segs = [(au + " \u201c" + end_title(r["title"]) + "\u201d ", False, False), (r["container"], True, False), (tail + ".", False, False)]
    txt = "".join(s[0] for s in segs)
    L.change("works-cited-entry", orig_for[r["key"]], txt, S["closer_look"])
    rendered.append((norm(a["family"]) + norm(r.get("title", "")), segs, r))
    if r["key"] == "berman": L.flag("Berman entry", "Crossref has this DOI but no author, volume or issue; those came from the student's entry (and match MLA's own example). Confirm against the article.", "crossref/crossref_results.json")
    if r["key"] == "baron": L.flag("Baron entry", "No DOI in the student's entry. MLA 5.84 prefers a DOI for works consulted online; if read online, add https://doi.org/10.1632/pmla.2013.128.1.193 (Crossref). Not added automatically.", S["doi_post"])
order_before = [k for t in ref_texts for k, v in orig_for.items() if v == t]
rendered.sort(key=lambda x: x[0])
L.change("works-cited-order", ", ".join(order_before), ", ".join(x[2]["key"] for x in rendered), S["ch1_6"])
L.flag("Alphabetizing detail", "Order is by author surname (1.6 says the list is alphabetic). Letter-by-letter and article-skipping rules come from an 8th-ed. post (Handbook 5.124-5.130 not read); no ties in this list.", S["alpha_8th"])
L.change("works-cited-label", wc_label, "Works Cited" if len(rendered) > 1 else "Work Cited", S["ch1_6"])

# ---------- 5. in-text citations (QG 2024; Closer Look 6.30) ----------
FAM = {r["authors"][0]["family"]: r for r in refs}
def fix_cites(text):
    orig = text
    def repl(m):
        inner = m.group(1)
        items = re.split(r";\s*|,\s+(?=(?:%s)\b)" % "|".join(map(re.escape, FAM)), inner)
        out = []
        for it in items:
            fam = next((f for f in FAM if re.match(rf"^{re.escape(f)}\b", it)), None)
            if not fam: return m.group(0)
            etal = " et al." if re.search(r"\bet al\.?", it) else ""
            rest = re.sub(rf"^{re.escape(fam)}(\s+et al\.?)?,?\s*", "", it)
            rest = re.sub(r"^(19|20)\d\d[a-z]?\b,?\s*", "", rest)            # MLA in-text: no year
            rest = re.sub(r"^pp?\.\s*", "", rest)                              # no "p." before location
            # author already named in the same sentence (outside these parentheses) -> location only
            sent_start, inq = 0, False                                          # sentence start, ignoring periods inside quotations
            for i_, ch in enumerate(text[:m.start()]):
                if ch in "\u201c\u201d\"": inq = (ch == "\u201c") or (ch == '"' and not inq)
                elif ch in ".?!" and not inq and text[i_ + 1:i_ + 2] == " ": sent_start = i_ + 1
            in_prose = re.search(rf"\b{re.escape(fam)}\b", text[sent_start:m.start()])
            if in_prose and len(items) == 1 and rest: out.append(rest)
            else: out.append((fam + etal + (" " + rest if rest else "")).strip())
            if etal: L.flag(f"Citation ({fam} et al.)", "'et al.' kept as typed; the 9th-ed. rule for 3+ authors in parentheses is in Handbook 6.5 (subscription-only). An 8th-ed. post shows '(Burdick et al. 42)'.", S["et_al_8th"])
        return "(" + "; ".join(out) + ")"
    text = re.sub(r"\(([^()]*)\)", repl, text)
    if text != orig: L.change("in-text-citation", orig, text, S["intext_qg"])
    return text
def fix_spaces(text):
    t2 = re.sub(r"([.?!][\u201d\"]?)  +(?=\S)", r"\1 ", text)
    if t2 != text:
        L.change("sentence-spacing", text, t2, S["ch1_1"])
        L.flag("Two spaces after periods", "Changed to one space (MLA 1.2 default). MLA allows two if your instructor prefers.", S["ch1_1"])
    return t2
for b in body:
    if not b["level"]: b["text"] = fix_spaces(fix_cites(b["text"]))

# ---------- 6. build ----------
out = Document()
st = out.styles["Normal"]; st.font.name = FONT; st.font.size = Pt(SIZE); set_font_everywhere(st, FONT)
pf = st.paragraph_format; pf.line_spacing = 2.0; pf.space_before = Pt(0); pf.space_after = Pt(0)
hs = out.styles["Heading 1"]; set_font_everywhere(hs, FONT); hs.font.size = Pt(SIZE); hs.font.bold = True; hs.font.italic = False
hs.font.color.rgb = RGBColor(0, 0, 0); hp = hs.paragraph_format; hp.space_before = Pt(0); hp.space_after = Pt(0); hp.line_spacing = 2.0; hp.keep_with_next = True
set_auto_hyphenation(out, False)
sec = out.sections[0]; sec.page_width, sec.page_height = Inches(8.5), Inches(11)
for k, v in prof["page"]["margins_in"].items(): setattr(sec, f"{k}_margin", Inches(v))
sec.header_distance = Inches(prof["running_head"]["header_distance_in"])
surname = meta["author"].split()[-1]
hpara = sec.header.paragraphs[0]; hpara.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = hpara.add_run(surname + " "); r.font.name = FONT; r.font.size = Pt(SIZE); add_field(hpara, "PAGE", FONT, SIZE)
L.change("running-head", src.sections[0].header.paragraphs[0].text.strip(), f"{surname} [page number], top right, 0.5 in. from top", S["ch1_4"])
L.flag("Running head on page 1", "Kept on every page (MLA 1.4). Some teachers prefer none on the first page; follow the instructor.", S["ch1_4"])
L.flag("Surname in running head", f'Took "{surname}" as the surname (last word of the name). Confirm for compound or family-name-first names.', S["ch1_4"])
def P(text="", align="left", bold=False, indent=True, style=None, hanging=None, italic_spans=()):
    p = out.add_paragraph(style=style)
    p.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER}[align]
    f = p.paragraph_format; f.line_spacing = 2.0; f.space_before = Pt(0); f.space_after = Pt(0)
    f.first_line_indent = Inches(prof["text"]["first_line_indent_in"]) if indent else Inches(0)
    if hanging: f.left_indent = Inches(hanging); f.first_line_indent = Inches(-hanging)
    pos = 0
    for span in italic_spans:
        i = text.find(span, pos)
        if i < 0: continue
        if i > pos: p.add_run(text[pos:i]).bold = bold
        rr = p.add_run(span); rr.italic = True; rr.bold = bold; pos = i + len(span)
    if text[pos:]: p.add_run(text[pos:]).bold = bold
    return p
for k in prof["first_page_header"]["order"]:
    if meta.get(k): P(meta[k], indent=False)
    else:
        p = P("", indent=False); rr = p.add_run(f"[{k.upper()} NEEDED]"); rr.font.highlight_color = WD_COLOR_INDEX.YELLOW
        L.flag(f"Header: {k}", "Missing from the paper; highlighted placeholder left (never invented).", S["ch1_3"])
L.flag("Date format", f'Kept as typed ("{meta.get("date")}"). The 9th-ed. 1.3 text does not prescribe a date format.', S["ch1_3"])
L.flag("Course line", f'Kept as typed ("{meta.get("course")}"). MLA 1.3 asks for the course name and number; confirm against the syllabus.', S["ch1_3"])
P(title, "center", indent=False)
for b in body:
    if b["level"]: P(b["text"], "left", bold=True, indent=False, style="Heading 1")
    else: P(b["text"], "left", indent=True, italic_spans=b["italic"])
page_break_after(out.paragraphs[-1])
P("Works Cited" if len(rendered) > 1 else "Work Cited", "center", indent=False)
L.flag("Works Cited heading style", "Centered, no period (1.3, 1.6). The 1.6 text doesn't say bold or plain; set plain as in MLA's published sample essays.", S["ch1_6"])
for _, segs, r in rendered:
    p = P("", indent=False, hanging=prof["works_cited"]["hanging_indent_in"]); ital_runs(p, segs)
out.core_properties.author = "Riley Example (fictional)"; out.core_properties.title = title
out.core_properties.comments = "SAMPLE DOCUMENT: student, instructor and course are fictional. References are real works."
out.save(DST); L.dump(DST.replace(".docx", "_changes.json"))
print(f"wrote {DST}: {len(L.changes)} changes, {len(L.flags)} flags")
