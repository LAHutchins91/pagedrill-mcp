"""Check mla_after.docx against MLA 9 rules; write checklist_mla.md. Every rule cites the official MLA source it came from.
Results: PASS / FAIL / FLAG (user-dependent or missing data) / NOT VERIFIED (official rule text not readable from free sources)."""
import re, json, sys
sys.path.insert(0, "src")
from fmtlib import *
D = Document("mla_after.docx"); B = Document("mla_before.docx"); prof = json.load(open("profiles/mla9_paper.json")); S = prof["sources"]
ch = json.load(open("mla_after_changes.json"))
rows = []
def row(rule, src, ok, note=""): rows.append((len(rows) + 1, rule, src, {True: "PASS", False: "FAIL"}.get(ok, ok), note))
ps = D.paragraphs; s = D.sections[0]
wc = next(i for i, p in enumerate(ps) if p.text in ("Works Cited", "Work Cited"))
hdr, title_p = ps[0:4], ps[4]
heads = [p for p in ps[5:wc] if p.style.name.startswith("Heading")]
body = [p for p in ps[5:wc] if not p.style.name.startswith("Heading") and p.text]
refs = ps[wc + 1:]
def eff(r, p): return (r.font.name or p.style.font.name or D.styles["Normal"].font.name, (r.font.size or p.style.font.size or D.styles["Normal"].font.size).pt)
def ls(p): return p.paragraph_format.line_spacing or p.style.paragraph_format.line_spacing
def is_break(p): return any(br.get(qn("w:type")) == "page" for br in p._p.iter(qn("w:br")))
U = "https://mlahandbookplus.org/books/book/5/chapter/"
row("1-inch margins top, bottom, both sides (1.1)", S["ch1_1"], all(abs(getattr(s, f"{k}_margin") - Inches(1)) < 1000 for k in ("top", "bottom", "left", "right")))
fonts = {eff(r, p) for p in ps for r in p.runs if r.text.strip()} | {eff(r, p) for p in s.header.paragraphs for r in p.runs if r.text.strip()}
row("Readable typeface with clear italics, 11-13 pt; same typeface and size throughout (1.2)", S["ch1_1"], len(fonts) == 1 and 11 <= list(fonts)[0][1] <= 13, f"fonts found: {sorted(fonts)}; Times New Roman is the Handbook's own example (instructor may specify another)")
row("Double-space the entire paper, including the works-cited list; no extra space between paragraphs (1.2, 1.6)", S["ch1_1"], all(ls(p) == 2.0 and p.paragraph_format.space_after in (None, 0) and p.paragraph_format.space_before in (None, 0) for p in ps))
row("Do not justify lines at the right margin (1.2)", S["ch1_1"], all(p.alignment in (None, 0, 1) for p in ps) and all(p.alignment in (None, 0) for p in body + refs))
hy = D.settings.element.find(qn("w:autoHyphenation"))
row("Automatic hyphenation turned off (1.2)", S["ch1_1"], hy is not None and hy.get(qn("w:val")) == "false")
row("First line of each paragraph indented 0.5 in. (1.2)", S["ch1_1"], all(p.paragraph_format.first_line_indent == Inches(0.5) for p in body))
row("One space after a period, unless the instructor prefers two (1.2)", S["ch1_1"], "FLAG" if not any(re.search(r"[.?!][\u201d\"]?  ", p.text) for p in ps) else False,
    "one space applied (two spaces existed in the original); instructor may prefer two")
hp = s.header.paragraphs[0]; instr = "".join(t.text for t in hp._p.iter(qn("w:instrText")))
row("Running head: surname, a space, page number; upper right, flush right, 0.5 in. from top, every page (1.4)", S["ch1_4"],
    hp.alignment == 2 and "PAGE" in instr and hp.text.startswith("Example ") and abs(s.header_distance - Inches(0.5)) < 1000 and not s.different_first_page_header_footer,
    f'header text "{hp.text}" + PAGE field; header distance {s.header_distance.inches:.2f} in.')
row("No \"p.\", period, hyphen or other mark with the page number (1.4)", S["ch1_4"], not re.search(r"p\.|page|-|\.", hp.text, re.I))
row("Name, instructor's name, course name and number, date on separate double-spaced lines, flush left, from the top of page 1; no title page (1.3)", S["ch1_3"],
    [p.text for p in hdr] == ["Riley Example", "Professor Dana Placeholder", "ENGL 102: Academic Writing", "14 October 2026"] and all(p.alignment in (None, 0) and p.paragraph_format.first_line_indent == Inches(0) for p in hdr),
    "labels (Student:, Date:...) removed and order fixed")
row("Title centered on a new double-spaced line; not italic, underlined, bold, in quotation marks, or all capitals (1.3)", S["ch1_3"],
    title_p.alignment == 1 and not any(r.bold or r.italic or r.underline for r in title_p.runs) and not title_p.text.isupper() and not title_p.text.startswith(("\u201c", '"')))
row("No period after the title or any heading (1.3)", S["ch1_3"], not title_p.text.endswith(".") and not any(h.text.endswith(".") for h in heads) and not ps[wc].text.endswith("."))
row("Text begins on the next double-spaced line after the title, first line indented 0.5 in. (1.3)", S["ch1_3"], ps[5].text and ps[5].paragraph_format.first_line_indent == Inches(0.5))
row("Title capitalization per Handbook 2.90", "MLA Handbook 2.90 (subscription-only; not read)", "NOT VERIFIED", "formatter keeps the typed capitalization; it never recases titles under this profile")
row("Headings flush left, not indented or centered (1.5)", S["ch1_5"], all(h.alignment in (None, 0) and h.paragraph_format.first_line_indent in (None, 0) for h in heads))
row("Each heading level styled consistently; same typeface/size as text; bold used for prominence (1.5, 1.2)", S["ch1_5"], len({(h.style.name, bool(h.runs[0].bold), eff(h.runs[0], h)) for h in heads}) == 1)
row("Headings not numbered/lettered (\"generally avoid\") (1.5)", S["ch1_5"], not any(re.match(r"^\d+[.)]", h.text) for h in heads), "numbers removed and flagged: discipline/instructor may want them")
row("No heading level with only one instance (1.5)", S["ch1_5"], len(heads) != 1, f"{len(heads)} level-1 headings")
row("\"Include a line space above and below a heading\" (1.5)", S["ch1_5"], "FLAG", "ambiguous in a fully double-spaced paper; no extra blank line added; instructor to confirm")
row("Works Cited at the end, new page, heading \"Works Cited\" centered 1 in. from top, no period (1.6, 1.3)", S["ch1_6"], is_break(ps[wc - 1]) and ps[wc].alignment == 1 and ps[wc].text == "Works Cited")
row("Works-cited heading weight (bold vs plain)", S["ch1_6"], "FLAG", "1.6 text doesn't say; plain, as in MLA's published sample essays")
row("Entries flush left with 0.5-in. hanging indent; list double-spaced (1.6)", S["ch1_6"], all(p.paragraph_format.left_indent == Inches(0.5) and p.paragraph_format.first_line_indent == -Inches(0.5) for p in refs))
row("List is alphabetical (1.6)", S["ch1_6"], [p.text.split(",")[0] for p in refs] == sorted(p.text.split(",")[0] for p in refs), " < ".join(p.text.split(",")[0] for p in refs) + "; letter-by-letter/article rules are 8th-ed. only (" + S["alpha_8th"] + ")")
OFFICIAL = {
 "Adams": ("Adams, Peter, et al. \u201cThe Accelerated Learning Program: Throwing Open the Gates.\u201d Journal of Basic Writing, vol. 28, no. 2, fall 2009, pp. 50\u201369.", S["closer_look"]),
 "Baron": ("Baron, Naomi S. \u201cRedefining Reading: The Impact of Digital Communication Media.\u201d PMLA, vol. 128, no. 1, Jan. 2013, pp. 193\u2013200.", S["intext_qg"]),
 "Berman": ("Berman, Russell A. \u201cThe Necessity of Second-Language Learning.\u201d ADFL Bulletin, vol. 43, no. 2, 2015, pp. 11\u201314, https://doi.org/10.1632/adfl.43.2.11.", S["closer_look"]),
 "Mantel": ("Mantel, Hilary. Wolf Hall. Picador, 2010.", "https://style.mla.org/ (Citations by Format quick guide; copy in mla_src/citations-quick.txt)")}
got = {p.text.split(",")[0]: p.text for p in refs}
row("Each entry identical, character for character, to the MLA's own 9th-ed. published example of the same work", "; ".join(sorted({v[1] for v in OFFICIAL.values()})),
    all(got.get(k) == v[0] for k, v in OFFICIAL.items()), "; ".join(f"{k}: {'match' if got.get(k) == v[0] else 'DIFF'}" for k, v in OFFICIAL.items()))
def ital(p, sub): return any(r.italic and sub in r.text for r in p.runs)
ref = {p.text.split(",")[0]: p for p in refs}
row("Container (journal) and book titles italic; article titles in quotation marks, not italic (template examples)", S["intext_qg"],
    ital(ref["Baron"], "PMLA") and ital(ref["Mantel"], "Wolf Hall") and ital(ref["Adams"], "Journal of Basic Writing") and not any(r.italic and "Redefining" in r.text for r in ref["Baron"].runs), "grade E9: shown in 9th-ed. examples; rule text in Handbook 5.23-5.37")
row("DOI written as https://doi.org/... (5.93)", S["closer_look"], "https://doi.org/10.1632/adfl.43.2.11" in ref["Berman"].text and "doi:" not in " ".join(p.text for p in refs))
row("Months longer than four letters abbreviated in entries (Appendix 1)", S["closer_look"], "Jan. 2013" in ref["Baron"].text)
row("Season in a publication date lowercased (5.79)", S["closer_look"], "fall 2009" in ref["Adams"].text)
row("Page ranges with en dash; \"pp.\" before the range (9th-ed. examples)", S["intext_qg"], all("\u2013" in p.text and "pp." in p.text for p in refs if "vol." in p.text), "grade E9")
row("Shortening of page/number ranges (Handbook 2.139)", "MLA Handbook 2.139 (subscription-only; not read)", "NOT VERIFIED", "kept in full; no range in this sample would be shortened (193\u2013200, 11\u201314, 50\u201369), so output is unaffected")
row("Three or more authors: first author, then \"et al.\" (Handbook 5.3-5.22)", S["closer_look"], "NOT VERIFIED", "output matches the 9th-ed. example 'Adams, Peter, et al.'; rule text only in an 8th-ed. post (" + S["et_al_8th"] + ")")
row("Two authors: \"Surname, Given, and Given Surname.\" (Handbook 5.3-5.22)", S["two_authors_8th"], "NOT VERIFIED", "not used in this sample; implemented from an 8th-ed. post and flagged whenever it fires")
txt = " ".join(p.text for p in body)
row("In-text citation = first element of the entry (author) + location; no year; no \"p.\" (Quick Guide 2024)", S["intext_qg"],
    "(Mantel)" in txt and "(Baron)" in txt and "2010)" not in txt and "p. " not in txt and "(Berman 12; Baron 196)" in txt)
row("Author named in the prose: location only in parentheses; never the name in both (Quick Guide 2024; overview)", S["intext_overview"], "writing\u201d (194)." in txt)
row("More than one source in one parenthesis separated by semicolons (6.30)", S["closer_look"], "(Berman 12; Baron 196)" in txt)
row("\"et al.\" in parenthetical citations (Handbook 6.5)", S["et_al_8th"], "NOT VERIFIED", "'(Adams et al.)' kept as the student typed it; 9th-ed. rule text not read")
row("Titles of works italicized in prose (Handbook 2.89-2.125)", "MLA Handbook 2.89-2.125 (subscription-only)", "NOT VERIFIED", "italics kept exactly as typed (Wolf Hall was already italic)")
# words-preserved check (body sentences only)
bb = " ".join(p.text for p in B.paragraphs if p.text and not p.style.name.startswith("Heading") and not re.match(r"^(Date|Student|Course|Instructor):", p.text)
             and p.text not in ("Reading, Writing, and the Screen.", "Bibliography") and not p.text.startswith(("Hilary", "Baron, Naomi", "Berman, R", "Peter Adams")))
ab = " ".join(p.text for p in body)
dif = word_diff(bb, ab)
row("Author's sentences unchanged (only citation contents and spacing change)", "(Lawrence's rule: format only)",
    {x[2:] for x in dif} <= {",", "p", ".", "2010", "2013", "2009", "Baron", ";"}, "word-level diff: " + " ".join(dif))
with open("checklist_mla.md", "w") as f:
    f.write("# MLA 9 student research paper — rule checklist for mla_after.docx\n\nGenerated by `src/verify_mla.py` (programmatic checks on the .docx XML). Sources fetched 2026-10-10; copies in `mla_src/` (chapter 1 of the MLA Handbook is MLA's free sample chapter on mlahandbookplus.org, read via the fetch tool; the box itself gets a Cloudflare challenge there).\n\n"
            "FLAG = user/instructor-dependent: the formatter refused to guess. NOT VERIFIED = the official 9th-ed. rule text is subscription-only (MLA Handbook Plus) or only exists in an MLA post written for the 8th edition.\n\n")
    f.write("| # | Rule | Official source | Result | Note |\n|---|---|---|---|---|\n")
    for r in rows: f.write(f"| {r[0]} | {r[1]} | {r[2]} | **{r[3]}** | {r[4]} |\n")
    c = {k: sum(1 for r in rows if r[3] == k) for k in ("PASS", "FAIL", "FLAG", "NOT VERIFIED")}
    f.write(f"\n**Totals:** {c['PASS']} pass, {c['FAIL']} fail, {c['FLAG']} flagged, {c['NOT VERIFIED']} not verified.\n\n")
    f.write("**Status: NOT FULLY VERIFIED (not shippable as full MLA 9).** Page layout (Handbook ch. 1) is fully verified. Still missing, all subscription-only: 2.90 (title capitalization), 2.89-2.125 (titles in prose), 2.139 (number ranges), 5.3-5.22 (author element: two authors, et al.), 5.120-5.130 (entry punctuation, alphabetizing), 6.3-6.30 (in-text details: coauthors, corporate authors, same surname). Fix: buy the MLA Handbook 9th ed. (print/e-book) or an MLA Handbook Plus login and re-run this checklist.\n\n## Flags from the formatter\n")
    for fl in ch["flags"]: f.write(f"- **{fl['item']}**: {fl['why']} ({fl['rule']})\n")
    f.write("\n## Logged changes (the diff the user approves before saving)\n")
    for x in ch["changes"]: f.write(f"- `{x['kind']}`: \u201c{x['before'][:150]}\u201d \u2192 \u201c{x['after'][:170]}\u201d\n")
for r in rows: print(r[0], r[3], r[1][:70], "|", r[4][:110])
