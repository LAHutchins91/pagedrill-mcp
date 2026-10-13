"""Check after.docx against APA 7 student-paper rules; write checklist_apa.md. Every rule cites the official APA page it came from."""
import re, json, subprocess, difflib, sys
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml.ns import qn
D = Document("after.docx"); B = Document("before.docx"); prof = json.load(open("profiles/apa7_student.json"))
ch = json.load(open("after_changes.json"))
A = "https://apastyle.apa.org/style-grammar-guidelines/"
rows = []
def row(n, rule, url, ok, note=""):
    rows.append((n, rule, url, {True: "PASS", False: "FAIL"}.get(ok, ok), note))
ps = D.paragraphs
def is_break(p): return any(br.get(qn("w:type")) == "page" for br in p._p.iter(qn("w:br")))
ref_i = next(i for i, p in enumerate(ps) if p.text == "References")
text_start = 10
body = [p for p in ps[text_start:ref_i] if p.text and not p.style.name.startswith("Heading") and p.text != ps[3].text]
heads = [p for p in ps[text_start:ref_i] if p.style.name.startswith("Heading")]
refs = ps[ref_i+1:]
s = D.sections[0]
row(1, "1-inch margins on every side", A+"paper-format/margins",
    all(abs(getattr(s, f"{k}_margin") - Inches(1)) < 1000 for k in ("top","bottom","left","right")))
def eff_font(r, p):
    return (r.font.name or p.style.font.name or D.styles["Normal"].font.name, (r.font.size or p.style.font.size or D.styles["Normal"].font.size).pt)
fonts = {eff_font(r, p) for p in ps for r in p.runs if r.text.strip()}
row(2, "One permitted font used throughout (12-pt Times New Roman is a listed option)", A+"paper-format/font", fonts == {("Times New Roman", 12.0)}, f"fonts found: {sorted(fonts)}")
def ls(p): return p.paragraph_format.line_spacing or p.style.paragraph_format.line_spacing
allp = [p for p in ps]
row(3, "Double-space everything incl. title page and reference list; no extra space before/after paragraphs", A+"paper-format/line-spacing",
    all(ls(p) == 2.0 and (p.paragraph_format.space_after in (None, 0)) and (p.paragraph_format.space_before in (None, 0)) for p in allp))
row(4, "Text aligned left, ragged right (no full justification)", A+"paper-format/paragraph-format",
    all(p.alignment in (None, 0) for p in body + refs))
row(5, "First line of each body paragraph indented 0.5 in. (not with spaces)", A+"paper-format/paragraph-format",
    all(p.paragraph_format.first_line_indent == Inches(0.5) and not p.text.startswith(" ") for p in body))
hdr = s.header.paragraphs[0]; instr = "".join(t.text for t in hdr._p.iter(qn("w:instrText")))
row(6, "Page number (automatic field) in top-right of header on every page; title page is page 1", A+"paper-format/page-header",
    "PAGE" in instr and hdr.alignment == 2 and not s.different_first_page_header_footer, "PAGE field, right-aligned, same header on all pages")
row(7, "Student paper: no running head (and never a \"Running head:\" label)", A+"paper-format/page-header",
    "running head" not in hdr.text.lower() and hdr.text.strip() in ("", "1"))
tp = ps[:10]
row(8, "Title 3-4 lines down from top, centered, bold, title case", A+"paper-format/title-page",
    all(not p.text for p in tp[:3]) and tp[3].alignment == 1 and all(r.bold for r in tp[3].runs), "3 blank double-spaced lines, title on line 4")
row(9, "One double-spaced blank line between title and author name", A+"paper-format/title-page", tp[4].text == "")
row(10, "Byline, affiliation, course number: name, instructor, due date — each centered on its own double-spaced line", A+"paper-format/title-page",
    all(p.alignment == 1 for p in tp[5:10]) and re.match(r"^[A-Z]{2,5} ?\d+: ", tp[7].text) is not None)
row(11, "Affiliation = department + institution", A+"paper-format/title-page", "FLAG",
    "Not in the student's paper; highlighted placeholder left. User must supply. Never invented.")
row(12, "Course name as shown on instructional materials", A+"paper-format/title-page", "FLAG",
    "Kept as typed (\"Intro to Psychology\"); only the colon was added. User should confirm official course name.")
row(13, "Title page ends; text starts on a new page (start each section on a new page)", A+"paper-format/order-pages", is_break(tp[9]))
row(14, "Paper title repeated at top of first page of text (acts as de facto Level 1 heading); no \"Introduction\" heading", A+"paper-format/headings",
    ps[10].text == tp[3].text and ps[10].alignment == 1 and all(r.bold for r in ps[10].runs) and not any(h.text.lower() == "introduction" for h in heads))
def hfmt(h):
    L = int(h.style.name[-1]); r = h.runs[0]
    return L, h.alignment, bool(r.bold), bool(r.italic)
exp = {1: (1, True, False), 2: (0, True, False), 3: (0, True, True)}
row(15, "Heading levels: L1 centered bold; L2 flush left bold; L3 flush left bold italic (L4/L5 inline, supported in code, not used in sample)", A+"paper-format/headings",
    all((hfmt(h)[1] or 0, hfmt(h)[2], hfmt(h)[3]) == exp[hfmt(h)[0]] for h in heads), "; ".join(f"L{hfmt(h)[0]} {h.text}" for h in heads))
MINOR = {"a","an","the","and","as","but","for","if","nor","or","so","yet","at","by","in","of","off","on","per","to","up","via"}
def is_title_case(t):
    w = t.split(); return all(x[0].isupper() or (x.lower() in MINOR and i) for i, x in enumerate(w))
row(16, "Headings in title case, not numbered/lettered", A+"capitalization/title-case",
    all(is_title_case(h.text) and not re.match(r"^(\d+|[a-z])[.)]", h.text) for h in heads + [ps[3]]))
row(17, "No blank lines above or below headings", A+"paper-format/headings",
    all(ps[i-1].text and (i+1 >= len(ps) or ps[i+1].text) for i, p in enumerate(ps) if p.style.name.startswith("Heading")))
row(18, "Avoid a single subsection within a section", A+"paper-format/headings", "FLAG",
    "\"Shopping Online\" has one Level 3 subsection (\"Help From the Community\"). Writer's call; not changed.")
row(19, "Reference list starts on a new page; label \"References\" bold and centered (not \"Works Cited\")", A+"paper-format/reference-list",
    is_break(ps[ref_i-1]) and ps[ref_i].alignment == 1 and all(r.bold for r in ps[ref_i].runs))
row(20, "0.5-in. hanging indent; double-spaced; no extra space between entries", A+"paper-format/reference-list",
    all(p.paragraph_format.left_indent == Inches(0.5) and p.paragraph_format.first_line_indent == -Inches(0.5) for p in refs))
row(21, "Entries alphabetized by first author surname", A+"paper-format/reference-list",
    [p.text.split(",")[0] for p in refs] == sorted(p.text.split(",")[0] for p in refs), " < ".join(p.text.split(",")[0] for p in refs))
row(22, "Authors inverted (Surname, Initials.), comma before &, ampersand before final author", A+"references/elements-list-entry",
    all(re.match(r"^[A-Z][\w-]+, ([A-Z]\. ?)+(, (& )?[A-Z][\w-]+, ([A-Z]\. ?)+)*", p.text) for p in refs) and "Rybaczewska, M., & Sparks, L." in refs[0].text)
def ital(p, s): return any(r.italic and s in r.text for r in p.runs)
def notital(p, s): return all(not r.italic for r in p.runs if s in r.text)
row(23, "Article title sentence case, not italic; journal name and volume italic; issue in parentheses not italic", A+"references/elements-list-entry",
    ital(refs[0], "Ageing and Society") and ital(refs[0], "42") and notital(refs[0], "Ageing consumers") and notital(refs[0], "(8)") and ital(refs[1], "Computers in Human Behavior") and ital(refs[1], "72"),
    "volume/journal italics as shown in APA journal-article examples: " + A + "references/examples/journal-article-references")
row(24, "Stand-alone works (webpages, news stories) have italic titles", A+"references/elements-list-entry", ital(refs[2], "When Covid-19 hit"))
row(25, "DOIs as https://doi.org/xxxxx (doi: prefix standardized)", A+"references/dois-urls", "https://doi.org/10.1017/S0144686X20001932" in refs[0].text and "doi:" not in " ".join(p.text for p in refs))
row(26, "Page ranges with en dash (as in APA examples)", A+"references/examples/journal-article-references", "1879\u20131898" in refs[0].text and "67\u201378" in refs[1].text)
row(27, "Missing reference info handled, not invented (Toner date; Sanchiz DOI/issue)", A+"references/missing-information", "FLAG",
    "Toner: highlighted [DATE NEEDED] (URL date 2020/06/04 ≠ APA's example date 2020, September 24, so not guessed). Sanchiz: no DOI/issue in the student's text; Crossref (checked separately by us, not by the formatter) lists DOI 10.1016/j.chb.2017.02.038 and no issue for vol. 72, so the user should add the DOI.")
alltext = " ".join(p.text for p in body)
row(28, "Parenthetical: & for two authors; Surname et al. for 3+ (even first citation); comma before year", A+"citations/basic-principles/author-date",
    "(Rybaczewska & Sparks, 2022)" in alltext and "Sanchiz et al., 2017" in alltext and "Chevalier" not in alltext and " and Sparks 2022)" not in alltext)
row(29, "Narrative: spell out \"and\"; year in parentheses right after names", A+"citations/basic-principles/parenthetical-versus-narrative",
    "Rybaczewska and Sparks (2022) examined" in alltext and "Sanchiz et al. (2017) compared" in alltext)
row(30, "Multiple works in one parenthesis: alphabetical, separated by semicolons", A+"citations/basic-principles/multiple-works",
    "(Rybaczewska & Sparks, 2022; Sanchiz et al., 2017)" in alltext)
row(31, "Every citation has author + year and matches a reference", A+"citations/basic-principles/author-date", "FLAG",
    "\"(Toner)\" has no year and the reference has no date. Left as typed; user must add the date (or n.d. if the page truly has none).")
row(32, "Student paper: no abstract/author note required (none added)", A+"paper-format/order-pages", not any(p.text.lower() in ("abstract", "author note") for p in ps))
# words-preserved check
def words(doc, skip):
    t = " ".join(p.text for p in doc.paragraphs if p.text and not skip(p)); return re.findall(r"[\w’'-]+|[^\w\s]", t)
bw = words(B, lambda p: p.text.startswith(("Name:", "Class:", "Professor:", "Due:", "Works Cited")) or p.style.name.startswith("Heading") or "Toner, K." in p.text or p.text.startswith(("Maria", "Sanchiz, M.", "older adults, information")))
aw = re.findall(r"[\w’'-]+|[^\w\s]", " ".join(p.text for p in ps[11:ref_i] if p.text and not p.style.name.startswith("Heading")))
dif = [x for x in difflib.ndiff(bw, aw) if x[0] in "+-"]
row(33, "Author's sentences unchanged (only citation punctuation/name-list changes)", "(Lawrence's rule: format only)", 
    set(x[2:] for x in dif) <= {"and", "&", ",", "Chevalier", "Amadieu", "et", "al", ".", "(", ")", "2022", "2017", "Rybaczewska", "Sparks", "Sanchiz", ";"},
    "word-level diff of body text: " + " ".join(dif))
with open("checklist_apa.md", "w") as f:
    f.write("# APA 7 student paper — rule checklist for after.docx\n\nGenerated by `src/verify_apa.py` (programmatic checks on the .docx XML). Rules come from official APA Style pages fetched 2026-10-10 (copies in `apa_src/`). FLAG = user-dependent or missing data: the formatter refused to guess.\n\n")
    f.write("| # | Rule | Official source | Result | Note |\n|---|---|---|---|---|\n")
    for r in rows: f.write(f"| {r[0]} | {r[1]} | {r[2]} | **{r[3]}** | {r[4]} |\n")
    c = {k: sum(1 for r in rows if r[3] == k) for k in ("PASS", "FAIL", "FLAG")}
    f.write(f"\n**Totals:** {c['PASS']} pass, {c['FAIL']} fail, {c['FLAG']} flagged for the user.\n\n## Flags from the formatter\n")
    for fl in ch["flags"]: f.write(f"- **{fl['item']}**: {fl['why']} ({fl['rule']})\n")
    f.write("\n## Logged changes (what the user would see as a diff before saving)\n")
    for x in ch["changes"]: f.write(f"- `{x['kind']}`: “{x['before'][:140]}” → “{x['after'][:160]}”\n")
for r in rows: print(r[0], r[3], r[1][:60], "|", r[4][:100])
