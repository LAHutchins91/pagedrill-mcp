"""Vancouver (ICMJE + NLM) formatter: citations and reference list only. Page layout is left exactly as the user had it
(ICMJE sets none; the target journal decides). Usage: format_vancouver.py before.docx after.docx profile.json refs.json"""
import sys, re, json
sys.path.insert(0, "src")
from fmtlib import *
src, out, prof_p, refs_p = sys.argv[1:5]
prof = json.load(open(prof_p)); R = json.load(open(refs_p))["references"]; S = prof["sources"]; L = Log()
D = Document(src); ps = D.paragraphs
ri = next(i for i, p in enumerate(ps) if p.style.name.startswith("Heading") and p.text.strip().lower() in ("references", "reference list", "bibliography", "works cited"))
refps = [p for p in ps[ri + 1:] if p.text.strip()]
for r, p in zip(R, refps): ground(r, p.text, skip=("key", "type", "_note", "cite", "lookup", "verified"))
order = []
def num(r):
    if r["key"] not in order: order.append(r["key"])
    return order.index(r["key"]) + 1
def find(name, year):
    for r in R:
        if r["cite"][0] == name.strip() and r["cite"][1] == year: return r
    raise SystemExit(f"no reference matches '{name}, {year}'")
cite_re = re.compile(r"\(((?:[^();]+?, \d{4}(?:; )?)+)\)")
multi = False
for p in ps[:ri]:
    t = p.text
    def rep(m):
        global multi
        ns = sorted({num(find(*c.rsplit(", ", 1))) for c in m.group(1).split("; ")})
        if len(ns) > 1: multi = True
        return "(" + ", ".join(map(str, ns)) + ")"
    nt = cite_re.sub(rep, t)
    if nt != t:
        for r in p.runs[1:]: r._r.getparent().remove(r._r)
        p.runs[0].text = nt
        L.change("citation", t, nt, S["icmje"] + " ('numbered consecutively in the order in which they are first mentioned'; 'Arabic numerals in parentheses')")
if multi: L.flag("multiple citations", "written as (1, 4); ICMJE does not say whether to use commas, spaces or ranges (e.g. 1,4 or 1-3). Check the journal's instructions", S["icmje"])
L.flag("citation placement", "numbers left exactly where the author put them (before the period); ICMJE does not specify, journals differ", S["icmje"])
for k in [r["key"] for r in R if r["key"] not in order]:
    order.append(k); L.flag(k, "listed but never cited; placed last", S["icmje"])
M = prof["months"]
def elide(pg):
    if "-" not in pg: return pg
    a, b = pg.split("-"); i = 0
    while i < min(len(a), len(b)) - 1 and len(a) == len(b) and a[i] == b[i]: i += 1
    return f"{a}-{b[i:]}"
def authors(au):
    n = [f'{a["family"]} {a["initials"].replace(".", "").replace(" ", "")}' for a in au]
    return ", ".join(n[:6]) + (", et al" if len(n) > 6 else "") + ". "
rendered = {}
for r in R:
    s = authors(r["authors"])
    t, ch = sentence_case(r["title"], (), cap_after_colon=False)
    if ch: L.flag(r["key"] + " title", "sentence case applied (NLM examples); proper nouns cannot be detected automatically, confirm", S["nlm_samples"])
    if r["type"] == "book":
        s += f"{t}. {r['edition']} ed. {r['place']}: {r['publisher']}; {r['year']}."
        L.flag(r["key"], "book: not on Crossref/PubMed; matches NLM Sample Reference #19 word for word. Book rules beyond that example are in Citing Medicine (not read)", S["nlm_samples"])
    else:
        j = r["lookup"]["journal_abbrev"]
        if j != r["container"]: L.change("journal abbreviation (lookup)", r["container"], j, f"MEDLINE abbreviation from {r['lookup']['from']} (ICMJE: abbreviate per MEDLINE)")
        date = r["year"] + (f" {M[r['month']]}" if r.get("month") else "") + (f" {r['day']}" if r.get("day") else "")
        pg = elide(r["pages"])
        if pg != r["pages"]: L.change("page elision", r["pages"], pg, S["nlm_samples"] + " (examples 284-7, 40-6; rule text in Citing Medicine, not read)")
        s += f"{t}. {j}. {date};{r['volume']}" + (f"({r['issue']})" if r.get("issue") else "") + f":{pg}."
        if r.get("doi"): s += f" doi: {r['doi']}."
    if len(r["authors"]) > 6: L.change("authors", f"{len(r['authors'])} authors", "first six + et al.", S["nlm_samples"] + " ('List the first six authors, followed by et al.')")
    if len(r["authors"]) == 6: L.flag(r["key"], "exactly six authors: all six listed (rule says more than six -> et al.)", S["nlm_samples"])
    if r["key"] == "rose": L.flag("rose", "PubMed holds two records with this title and author list (Brain Res 935(1-2):40-6, PMID 12062471, and 943(1):15-22, PMID 12088834). Confirm which one you read", S["pubmed"])
    rendered[r["key"]] = s
L.flag("reference list numbering", "written as '1. ' with a hanging indent; neither ICMJE nor NLM's Sample References shows how the list is numbered. Check the journal", S["icmje"])
L.flag("page layout", "font, spacing, margins and title page left as they were: ICMJE sets none and defers to the journal's instructions", S["icmje"])
for i, (p, k) in enumerate(zip(refps, order)):
    before = p.text; new = f"{i + 1}. {rendered[k]}"
    for r in p.runs[1:]: r._r.getparent().remove(r._r)
    p.runs[0].text = new; p.runs[0].italic = False
    L.change("reference", before, new, S["nlm_samples"])
if [r["key"] for r in R] != order: L.change("reference order", ", ".join(r["key"] for r in R), ", ".join(order), S["icmje"])
D.save(out); L.dump(out.replace(".docx", "_changes.json"))
print(f"wrote {out}: {len(L.changes)} changes, {len(L.flags)} flags; order {order}")
