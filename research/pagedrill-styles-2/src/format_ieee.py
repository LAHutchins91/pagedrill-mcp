"""IEEE conference formatter. Usage: format_ieee.py before.docx after.docx profile.json refs.json
Layout comes from the official IEEE Word template (its styles, numbering, margins, columns are reused unchanged).
Words are never rewritten: only citation markers, heading numbers/labels, letter case of titles and reference entries change, and every change is logged."""
import sys, re, copy, csv, json
sys.path.insert(0, "src")
from fmtlib import *
src, out, prof_p, refs_p = sys.argv[1:5]
prof = json.load(open(prof_p)); R = json.load(open(refs_p))["references"]; L = Log(); S = prof["sources"]
B = Document(src); bp = [p for p in B.paragraphs if p.text.strip()]
# ---------- parse the draft ----------
title = bp[0].text.strip()
i = 1; authors = []
while not re.match(r"(?i)abstract\b", bp[i].text): authors.append(bp[i].text.strip()); i += 1
abstract = re.sub(r"(?i)^abstract\s*[:.\u2014-]\s*", "", bp[i].text.strip()); i += 1
keywords = None
if re.match(r"(?i)(keywords|index terms)\b", bp[i].text): keywords = re.sub(r"(?i)^(keywords|index terms)\s*[:.\u2014-]\s*", "", bp[i].text.strip()); i += 1
blocks = []                                   # (kind, text)
while i < len(bp):
    p = bp[i]; t = p.text.strip()
    if p.style.name.startswith("Heading"):
        label = re.sub(r"^\d+(\.\d+)*\.?\s+", "", t)
        comp = prof["text"]["component_heads"].get(label.lower())
        if comp: blocks.append(("comp", comp, t))
        else: blocks.append(("h2" if p.style.name == "Heading 2" else "h1", label, t))
        if comp == "References": i += 1; break
    else: blocks.append(("body", t, t))
    i += 1
typed_refs = [p.text.strip() for p in bp[i:]]
# ---------- grounding: extracted fields must occur in the typed entries ----------
for r, t in zip(R, typed_refs): ground(r, t, skip=("key", "type", "_note", "crossref", "cite", "article_no_note"))
# ---------- citations: author-year -> [n] in order of first citation ----------
order = []
def num(r):
    if r["key"] not in order: order.append(r["key"])
    return order.index(r["key"]) + 1
def find(name, year):
    for r in R:
        if r["cite"][0] == name.strip() and r["cite"][1] == year: return r
    raise SystemExit(f"citation '{name}, {year}' has no matching reference: flagging instead of guessing")
cite_re = re.compile(r"\(((?:[^();]+?, \d{4}(?:; )?)+)\)")
narr_re = re.compile(r"([A-Z][\w\u00C0-\u017F-]+(?: and [A-Z][\w\u00C0-\u017F-]+| et al\.)?) \((\d{4})\)")
new_blocks = []
for kind, text, orig in blocks:
    if kind != "body": new_blocks.append((kind, text, orig)); continue
    def par(m):
        nums = sorted({num(find(*c.rsplit(", ", 1))) for c in m.group(1).split("; ")})
        return ", ".join(f"[{n}]" for n in nums)
    def nar(m):
        n = num(find(m.group(1), m.group(2)))
        L.flag(f"'{m.group(1)} [{n}]'", "author name kept next to the number: ESM says drop it unless integral to the sentence (e.g. 'Smith [1] reduced ...'); removing words is the author's call", S["esm"] + " (References)")
        return f"{m.group(1)} [{n}]"
    # process left to right so numbering follows first appearance
    pieces, pos = [], 0
    for m in sorted(list(cite_re.finditer(text)) + list(narr_re.finditer(text)), key=lambda m: m.start()):
        if m.start() < pos: continue
        pieces.append(text[pos:m.start()]); pieces.append(par(m) if m.re is cite_re else nar(m)); pos = m.end()
    pieces.append(text[pos:]); nt = "".join(pieces)
    if re.search(r"\breference \[\d+\]", nt): L.flag("'in reference [n]'", "ESM: write 'in [1]', not 'in reference [1]'; wording left to the author", S["esm"] + " (References)")
    if nt != text: L.change("citation", text, nt, S["refguide"] + " (Citations: [n] on the line, inside punctuation; ranges written out); ESM (References: dates deleted in text)")
    new_blocks.append((kind, nt, orig))
blocks = new_blocks
missing = [r["key"] for r in R if r["key"] not in order]
for k in missing: L.flag(k, "listed but never cited; IEEE numbers by citation order, so it is placed last; confirm", S["template"])
order += missing
# ---------- paper title: headline case per ESM ----------
low = set(prof["text"]["lowercase_words"])
def headline(t):
    ws = t.split(" "); outw = []
    for k, w in enumerate(ws):
        parts = []
        for part in w.split("-"):
            lw = part.lower()
            parts.append(lw if (lw in low and 0 < k < len(ws) - 1) else lw[:1].upper() + lw[1:])
        outw.append("-".join(parts))
    return " ".join(outw)
new_title = headline(title) if title.isupper() or title.islower() else title
if new_title != title:
    L.change("title case", title, new_title, S["esm"] + " (Title)")
    L.flag("paper title", "typed in all capitals: acronyms and proper nouns cannot be told apart, and ESM's 'most short prepositions' is not a closed list; confirm the capitalization", S["esm"] + " (Title)")
# ---------- references ----------
abbr_sheet = {}
for row in csv.reader(open("ieee_src/ieee_journal_abbreviations.csv")):
    if len(row) >= 3 and row[2].startswith("IEEE"):
        name = row[0].strip('"* ')
        if ", IEEE" in name: name = "IEEE " + name.replace(", IEEE", "").replace("IEEE ", "")
        abbr_sheet[name.lower()] = row[2].split("(")[0].strip()
words_tbl = json.load(open("ieee_src/ieee_word_abbreviations.json"))
wt = {}
for k, v in words_tbl.items():
    for form in re.sub(r"\((\w+)\)", r"|\1", k).split("|"):
        pass
    base = re.sub(r"\(.*?\)", "", k); wt[base.lower()] = v
    m = re.search(r"\((\w+)\)", k)
    if m: wt[(base + m.group(1)).lower()] = v
def journal(name):
    if name.lower() in abbr_sheet: return abbr_sheet[name.lower()], "IEEE abbreviation sheet"
    t2 = re.sub(r"^IEEE ", "", name)
    for k, v in abbr_sheet.items():
        if k == ("ieee " + t2).lower(): return v, "IEEE abbreviation sheet"
    if name in prof["references"]["guide_attested_titles"]: return prof["references"]["guide_attested_titles"][name], "abbreviated exactly as in the Reference Guide's own examples"
    if " " not in name: return name, "one-word title, not abbreviated"
    outw = []
    for w in name.split():
        if w.lower() in ("of", "and", "the", "on", "in", "for"): continue
        if w.isupper(): outw.append(w); continue
        if w.lower() not in wt: return name, "NOT abbreviated: word '" + w + "' is not in the IEEE word table"
        outw.append(wt[w.lower()])
    return " ".join(outw), "built from the IEEE word table"
keep = set(prof["references"]["proper_noun_keep"])
def pages(p):
    a, b = p.split("-")
    if len(b) < len(a): b = a[:len(a) - len(b)] + b
    return f"{a}\u2013{b}"
rendered = {}
for r in R:
    if r["type"] != "journal-article":                      # other types are in the guide but not rendered yet: never guess
        typed = next(x for x, rr in zip(typed_refs, R) if rr is r)
        rendered[r["key"]] = [(typed, False)]
        L.flag(r["key"], f"reference type '{r['type']}' not rendered yet; kept exactly as typed", S["refguide"]); continue
    au = r["authors"]
    names = [f'{a["initials"]} {a["family"]}' for a in au]
    if len(names) > 6: who = names[0] + " et al."
    elif len(names) == 1: who = names[0]
    elif len(names) == 2: who = f"{names[0]} and {names[1]}"
    else: who = ", ".join(names[:-1]) + ", and " + names[-1]
    if len(names) == 6: L.flag(r["key"], "exactly six authors: the Reference Guide lists all six, the conference template text says 'Unless there are six authors or more give all authors' names'; we list all six", S["refguide"])
    t, ch = sentence_case(r["title"], keep)
    if ch: L.change("reference title case", r["title"], t, S["refguide"] + " (examples) and template ('Capitalize only the first word in a paper title, except for proper nouns')")
    hits = [w for w in t.split() if re.sub(r"\W", "", w) in keep]
    if ch or hits: L.flag(r["key"] + " title", "sentence case applied; proper nouns kept: " + (", ".join(hits) or "none detected") + ". Confirm no other proper noun was lowercased", S["refguide"])
    j, how = journal(r["container"])
    if how.startswith("NOT"): L.flag(r["key"], how, S["refguide"] + " (Common Abbreviations of Words in References)")
    mon = prof["references"]["months"].get(r["month"] or "", None)
    date = f"{mon} {r['year']}" if mon else r["year"]
    segs = [(f"{who}, \u201c{t},\u201d ", False), (j, True)]
    tail = f", vol. {r['volume']}" + (f", no. {r['issue']}" if r["issue"] else "")
    if r["pages"]:
        pg = pages(r["pages"]); tail += f", pp. {pg}, {date}"
        if pg.replace("\u2013", "-") != r["pages"]: L.change("page range", r["pages"], pg, S["refguide"] + " (examples print full page numbers with an en dash)")
    elif r["article_no"]: tail += f", {date}, Art. no. {r['article_no']}"
    else: tail += f", {date}"; L.flag(r["key"], "no page range or article number in the typed entry", S["refguide"])
    if r["issue"] and "-" in r["issue"]: L.flag(r["key"] + " issue", f"combined issue '{r['issue']}' kept as typed: the guide has no rule for issue ranges", S["refguide"])
    tail += f", doi: {r['doi']}." if r["doi"] else "."
    segs.append((tail, False)); rendered[r["key"]] = segs
    L.change("reference", next(x for x, rr in zip(typed_refs, R) if rr is r), "".join(s for s, _ in segs), S["refguide"] + f" (Periodicals; journal: {how})")
if [r["key"] for r in R] != order: L.change("reference order", ", ".join(r["key"] for r in R), ", ".join(order), "references numbered in order of first citation (template)")
# ---------- build on the official template ----------
D = Document(prof["layout"]["base_document"]); body = D.element.body
final_sect = body.find(qn("w:sectPr"))
for el in list(body):
    if el is not final_sect: body.remove(el)
STY = prof["layout"]["styles"]
def para(style, segs):
    p = D.add_paragraph(style=STY[style])
    for t, it in segs:
        r = p.add_run(t)
        if it: r.italic = True
    return p
para("title", [(new_title, False)])
for k, a in enumerate(authors):
    p = para("author", [(a, False)])
    if k: p.paragraph_format.space_before = Pt(0)
if not any("@" in a or "orcid" in a.lower() for a in authors):
    L.flag("author block", "template line 5 'email address or ORCID' is missing; nothing invented", S["template"])
# section break: title/author block single column, then the body in the template's two columns
last = D.paragraphs[-1]._p.get_or_add_pPr()
s1 = copy.deepcopy(final_sect)
for c in s1.findall(qn("w:cols")): s1.remove(c)
for c in s1.findall(qn("w:type")): s1.remove(c)
last.append(s1)
cols = final_sect.find(qn("w:cols"))
if cols is None: cols = OxmlElement("w:cols"); final_sect.insert(len(final_sect) - 1, cols)
cols.set(qn("w:num"), "2"); cols.set(qn("w:space"), str(prof["layout"]["body_column_space_twips"]))
ty = final_sect.find(qn("w:type"))
if ty is None: ty = OxmlElement("w:type"); final_sect.insert(0, ty)
ty.set(qn("w:val"), "continuous")
for fr in final_sect.findall(qn("w:footerReference")) + final_sect.findall(qn("w:headerReference")) + s1.findall(qn("w:footerReference")) + s1.findall(qn("w:headerReference")): pass
wc = len(abstract.split())
para("abstract", [("Abstract", True), ("\u2014" + abstract, False)])
L.change("label", "Abstract: ", "Abstract\u2014", S["template"])
if not 150 <= wc <= 250: L.flag("abstract", f"{wc} words; the ESM asks for 150-250 words (Transactions rule; the conference template sets no length). Text not changed", S["esm"] + " (Abstract)")
if keywords:
    para("keywords", [("Keywords\u2014" + keywords, False)]); L.change("label", "Keywords: ", "Keywords\u2014", S["template"])
for kind, text, orig in blocks:
    if kind in ("h1", "h2"):
        para(kind, [(text, False)])
        if text != orig: L.change("heading number removed", orig, text, S["template"] + " ('Do not number text heads-the template will do that for you')")
    elif kind == "comp":
        para("component_head", [(text, False)])
        if text != orig: L.change("component heading", orig, text, S["esm"] + " (Acknowledgment: 'always singular, with no \"e\"'; Reference and Acknowledgment heads never enumerated)")
    else: para("body", [(text, False)])
for k in order: para("reference", rendered[k])
L.flag("footer page numbers", "removed: template says 'Do not add any kind of pagination anywhere in the paper'", S["template"])
D.save(out); L.dump(out.replace(".docx", "_changes.json"))
print(f"wrote {out}: {len(L.changes)} changes, {len(L.flags)} flags; citation order {order}")
