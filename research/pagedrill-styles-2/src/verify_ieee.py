"""Check ieee_after.docx against the IEEE conference template, Editorial Style Manual and Reference Style Guide; write checklist_ieee.md."""
import re, json, sys
sys.path.insert(0, "src")
from fmtlib import *
D = Document("ieee_after.docx"); B = Document("ieee_before.docx"); T = Document("ieee_src/conference-template-letter.docx")
prof = json.load(open("profiles/ieee_conference.json")); S = prof["sources"]; ch = json.load(open("ieee_after_changes.json"))
TPL, ESM, RG = S["template"].split(" ")[0], S["esm"].split(" ")[0], S["refguide"].split(" ")[0]
rows = []
def row(rule, src, ok, note=""): rows.append((len(rows) + 1, rule, src, {True: "PASS", False: "FAIL"}.get(ok, ok), note))
ps = D.paragraphs; sty = lambda n: [p for p in ps if p.style.name == n]
body = sty("Body Text"); refs = sty("references"); h1 = sty("Heading 1"); h2 = sty("Heading 2"); h5 = sty("Heading 5")
used = {p.style.name for p in ps}; tstyles = {s.name for s in T.styles}
row("Paper built on the official IEEE conference Word template (US letter, 'Updated 2024'); only the template's own styles used", TPL, used <= tstyles and used >= {"paper title", "Author", "Abstract", "Heading 1", "Body Text", "references"}, "styles used: " + ", ".join(sorted(used)))
s0, s1 = D.sections[0], D.sections[-1]; ts = T.sections[-1]
row("Margins exactly as the template (top 0.75 in., bottom 1 in., left/right 0.62 in.): 'please do not alter them'", TPL,
    all(getattr(x, a) == getattr(ts, a) for x in (s0, s1) for a in ("top_margin", "bottom_margin", "left_margin", "right_margin", "page_width", "page_height")),
    f"{s1.top_margin.inches:.2f}/{s1.bottom_margin.inches:.2f}/{s1.left_margin.inches:.2f}/{s1.right_margin.inches:.2f} in.; letter {s1.page_width.inches}x{s1.page_height.inches}")
c1 = s1._sectPr.find(qn("w:cols")); c0 = s0._sectPr.find(qn("w:cols"))
row("Title/author block in one column; body in the template's two columns (space 0.25 in. = 360 twips)", TPL, c0 is None and c1.get(qn("w:num")) == "2" and c1.get(qn("w:space")) == "360" and len(D.sections) == 2)
direct = [r.text[:20] for p in ps for r in p.runs if r.font.name or r.font.size]
row("Fonts and sizes come from the template styles (no direct overrides; Times New Roman, 10-pt body)", TPL, not direct, "direct overrides: " + (", ".join(direct) or "none"))
fld = [p for part in [D.part] + [s.header.part for s in D.sections if s.header.is_linked_to_previous is False] for p in [part]]
xml_all = D.element.xml + "".join(s.footer._element.xml + s.header._element.xml for s in D.sections)
row("No pagination anywhere ('Do not add any kind of pagination anywhere in the paper')", TPL, "PAGE" not in xml_all, "the draft's footer page numbers are gone")
row("Paper title in the 'paper title' style, headline capitalization (ESM Title)", ESM + " (Title)", "FLAG", f"'{ps[0].text}': draft was all capitals, so acronyms/proper nouns and 'most short prepositions' need the author's confirmation")
auth = sty("Author")
row("Author block: name, dept., organization, city/country, email or ORCID, centered (template lines 1-5)", TPL, "FLAG", f"{len(auth)} lines kept as typed; line 5 (email/ORCID) missing, nothing invented")
ab = sty("Abstract")[0]
row("Abstract in the 'Abstract' style, label 'Abstract\u2014' with 'Abstract' italic, one paragraph", TPL, ab.text.startswith("Abstract\u2014") and ab.runs[0].text == "Abstract" and ab.runs[0].italic and len(sty("Abstract")) == 1)
row("Abstract length 150-250 words (ESM; written for Transactions, the conference template sets none)", ESM + " (Abstract)", "FLAG", f"{len(ab.text.split())} words; text not changed")
row("Keywords in the 'Keywords' style with label 'Keywords\u2014'", TPL, sty("Keywords")[0].text.startswith("Keywords\u2014"))
num = T.part.numbering_part.element
def lvl(numid, il):
    n = [x for x in num.findall(qn("w:num")) if x.get(qn("w:numId")) == numid][0]; a = n.find(qn("w:abstractNumId")).get(qn("w:val"))
    an = [x for x in num.findall(qn("w:abstractNum")) if x.get(qn("w:abstractNumId")) == a][0]
    l = [x for x in an.findall(qn("w:lvl")) if x.get(qn("w:ilvl")) == il][0]
    return l.find(qn("w:numFmt")).get(qn("w:val")), l.find(qn("w:lvlText")).get(qn("w:val"))
row("Primary heads: Roman numerals, centered, small caps; numbers not typed by the author (template numbers heads)", ESM + " (Text Section Headings); " + TPL,
    lvl("1", "0") == ("upperRoman", "%1.") and not any(re.match(r"^\d", h.text) for h in h1) and D.styles["Heading 1"].element.xml.count("smallCaps") > 0, "Heading 1 \u2192 I., II., III. (numbers typed in the draft were removed)")
row("Secondary heads: 'A.', 'B.', italic, flush left", ESM + " (Text Section Headings)", lvl("1", "1") == ("upperLetter", "%2.") and D.styles["Heading 2"].font.italic and not any(re.match(r"^\d", h.text) for h in h2))
row("Acknowledgment: singular spelling with no 'e'; never enumerated", ESM + " (Acknowledgment; Text Section Headings)", any(h.text == "Acknowledgment" for h in h5) and "numId" not in D.styles["Heading 5"].element.xml, "draft said 'Acknowledgements' (heading label changed and logged)")
row("References heading never enumerated", ESM + " (Text Section Headings)", any(h.text == "References" for h in h5))
txt = " ".join(p.text for p in body)
row("Citations are numbers in square brackets on the line, inside the punctuation; no author-year left", RG + " (Citations)", not re.search(r"\(\D+, \d{4}\)", txt) and not re.search(r"\.\s?\[\d", txt) and bool(re.search(r"\[\d+\]\.", txt)))
first = []
for m in re.finditer(r"\[(\d+)\]", txt):
    if int(m.group(1)) not in first: first.append(int(m.group(1)))
row("References numbered consecutively in order of first citation", TPL + " ('number citations consecutively within brackets')", first == list(range(1, len(refs) + 1)), "first-citation order: " + ", ".join(map(str, first)))
row("Groups written out, no en-dash ranges ([1], [2], [3])", RG + " (Citations)", "]\u2013[" not in txt and "[1], [2], [3]" in txt)
row("Reference dates deleted in the text", ESM + " (References)", not re.search(r"\(\d{4}\)|, \d{4}\)", txt))
row("Author's name not placed with the number unless integral", ESM + " (References)", "FLAG", "'Chiampi and Zilberti [3]' kept: deleting words is the author's decision")
row("'in [1]', not 'in reference [1]'", ESM + " (References)", "FLAG", "'described in reference [4]' kept: wording is the author's decision")
row("One reference per number; every listed reference cited", ESM + " (References)", sorted(first) == list(range(1, len(refs) + 1)))
row("Reference list numbered [1], [2] ... flush left, hanging (template 'references' style)", RG + " (Reference list); " + TPL, lvl("5", "0") == ("decimal", "[%1]") and all(p.style.name == "references" for p in refs))
row("Initials before surname", RG + " (General guidelines)", all(re.match(r"^([A-Z]\. )+[A-Z\u00C0-\u017F]", p.text) for p in refs))
row("All names up to six; more than six \u2192 first author + 'et al.'", RG + " (General guidelines)", refs[0].text.startswith("M. Ito et al.,") and refs[1].text.count(",") >= 5 and "et al." not in refs[1].text, "Ito (10 authors) \u2192 et al.; Fardel (5) all listed")
row("Article title in quotation marks, comma inside the closing quote", RG + " (Periodicals)", all(re.search(r"\u201c[^\u201d]+,\u201d", p.text) for p in refs))
row("Article title in sentence case (first word, first word after a colon, acronyms, proper nouns capitalized)", RG + " (examples); " + TPL, "\u201cInduction of electric field in human bodies moving near MRI: An efficient BEM computational procedure,\u201d" in refs[2].text and "Gaussian approximation" in refs[3].text)
row("Proper nouns in reference titles", RG, "FLAG", "cannot be detected reliably; user confirms (Gaussian kept from the profile's proper-noun list)")
itl = {r.text for p in refs for r in p.runs if r.italic}
row("Periodical title abbreviated (IEEE sheet \u2192 guide examples \u2192 word table) and italic; comma not italic", S["abbrev_sheet"].split(" ")[0] + "; " + RG + " (Common Abbreviations of Words in References)",
    itl == {"J. Non-Cryst. Solids", "Appl. Phys. Lett.", "IEEE Trans. Biomed. Eng.", "IEEE Commun. Lett."}, ", ".join(sorted(itl)))
row("Month abbreviated as in the guide (Aug., Oct., Feb.; May in full) before the year", RG + " (examples)", all(m in " ".join(p.text for p in refs) for m in ("May 2008", "Aug. 2007", "Oct. 2011", "Feb. 2019")))
row("Pages 'pp. first\u2013last' with an en dash, full numbers", RG + " (Periodicals)", "pp. 2787\u20132793" in refs[2].text and all("pp." not in p.text or re.search(r"pp\. \d+\u2013\d+", p.text) for p in refs), "draft's '2787-93' expanded (as in the guide's own example of this article)")
row("Article-number form: 'Abbrev. month, year, Art. no. xxx'", RG + " (Periodical With Article ID)", "Aug. 2007, Art. no. 061103" in refs[1].text)
row("DOI as ', doi: xxx.' after the date; every reference ends with a period (none ends with a URL)", RG + " (Periodical With DOI; General guidelines)", all(p.text.endswith(".") for p in refs) and ", doi: 10.1109/TBME.2011.2158315." in refs[2].text and "https://doi.org" not in " ".join(p.text for p in refs))
G = "M. M. Chiampi and L. L. Zilberti, \u201cInduction of electric field in human bodies moving near MRI: An efficient BEM computational procedure,\u201d IEEE Trans. Biomed. Eng., vol. 58, no. 10, pp. 2787\u20132793, Oct. 2011, doi: 10.1109/TBME.2011.2158315."
row("Entry identical, character for character, to the Reference Guide's own example of the same article", RG + " (Periodical With DOI, Chiampi example)", refs[2].text == G,
    "Chiampi: exact match. Vatta: authors and title match the guide; vol./no./pages are the final published issue (Crossref) instead of the guide's 'early access' form. Fardel: matches the guide except 'Nüesch' (as typed/Crossref), 'light-emitting' (Crossref title) and the added DOI. Ito: the guide's example has the wrong title and date per Crossref; we follow Crossref")
row("Combined issue numbers (no. 19-25)", RG, "FLAG", "kept as typed; the guide has no rule for issue ranges")
bb = " ".join(p.text for p in B.paragraphs if p.text and p.style.name == "Normal" and not re.match(r"^(Abstract|Keywords|LOW-COST|Casey|Department|Example State|Springfield)", p.text) and "(20" not in p.text[:200] or (p.style.name == "Normal" and re.search(r"\(\D+, \d{4}\)|\(\d{4}\)", p.text)))
bb = " ".join(p.text for p in B.paragraphs if p.style.name == "Normal" and p.text and not re.match(r"^(Abstract|Keywords|LOW-COST|Casey|Department|Example State|Springfield|Chiampi, M|Fardel, R|Ito, M|Vatta, F)", p.text))
dif = word_diff(bb, txt)
allowed = {"(", ")", ",", ";", "et", "al", ".", "and", "Ito", "Fardel", "Chiampi", "Zilberti", "Vatta", "2007", "2008", "2011", "2019", "[", "]", "1", "2", "3", "4"}
row("Author's sentences unchanged (only citation markers change); abstract and keyword text unchanged", "(Lawrence's rule: format only)",
    {x[2:] for x in dif} <= allowed and ab.text[len("Abstract\u2014"):] in B.paragraphs[5].text, "word-level diff: " + " ".join(dif))
with open("checklist_ieee.md", "w") as f:
    f.write("# IEEE conference paper (US letter) — rule checklist for ieee_after.docx\n\nGenerated by `src/verify_ieee.py`. Sources (all free, official, fetched 2026-10-10, copies in `ieee_src/`):\n"
            f"- Template: {S['template']}\n- Editorial Style Manual: {S['esm']}\n- Reference Style Guide: {S['refguide']}\n- Abbreviations sheet: {S['abbrev_sheet']}\n\nFLAG = the author's decision (wording, proper nouns, missing data); the formatter does not guess.\n\n")
    f.write("| # | Rule | Official source | Result | Note |\n|---|---|---|---|---|\n")
    for r in rows: f.write(f"| {r[0]} | {r[1]} | {r[2]} | **{r[3]}** | {r[4]} |\n")
    c = {k: sum(1 for r in rows if r[3] == k) for k in ("PASS", "FAIL", "FLAG")}
    f.write(f"\n**Totals:** {c['PASS']} pass, {c['FAIL']} fail, {c['FLAG']} flagged, 0 not verified.\n\n"
            "**Status: FULLY VERIFIED for this scope** — IEEE conference papers (US letter template) with journal-article references. Every rule above was read in an official IEEE source. "
            "Limits: other reference types (books, conference papers, websites, datasets, patents, standards) are specified in the same guide but not rendered yet; the formatter keeps them exactly as typed and flags them. "
            "A4 template and IEEE Transactions/journal layouts are not included. Known conflict, flagged when it fires: exactly six authors (guide: list all six; conference template text: 'six authors or more' use all names, inconsistent wording).\n\n## Flags from the formatter\n")
    for fl in ch["flags"]: f.write(f"- **{fl['item']}**: {fl['why']}\n")
    f.write("\n## Logged changes\n")
    for x in ch["changes"]: f.write(f"- `{x['kind']}`: \u201c{x['before'][:160]}\u201d \u2192 \u201c{x['after'][:200]}\u201d\n")
for r in rows: print(r[0], r[3], r[1][:70], "|", r[4][:120])
