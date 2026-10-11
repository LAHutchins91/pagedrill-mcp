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
if multi: L.flag("multiple citations", "written as (1, 4), the selected journal option. ICMJE does not say whether to use commas, spaces or ranges. Citing Medicine chapters 1 and 2 do not set in-text punctuation.", S["icmje"])
L.flag("citation placement", "numbers left exactly where the author put them (before the period); ICMJE does not specify, journals differ", S["icmje"])
for k in [r["key"] for r in R if r["key"] not in order]:
    order.append(k); L.flag(k, "listed but never cited; placed last", S["icmje"])
M = prof["months"]
def elide(pg):
    """Citing Medicine Ch 1, Location (Pagination): 123-125 -> 123-5; do not shorten 124A-126A; keep a leading letter (S10-8); keep roman numerals."""
    if not pg or ("-" not in pg and "," not in pg): return pg
    def roman(v): return bool(re.fullmatch(r"[IVXLCDMivxlcdm]+", v))
    def span(raw):
        raw = raw.replace("\u2013", "-")
        if "-" not in raw: return raw
        left, right = raw.split("-", 1)
        if roman(left) and roman(right): return f"{left}-{right}"
        if re.search(r"[A-Za-z]$", left) or re.search(r"[A-Za-z]$", right): return f"{left}-{right}"
        lm, rm = re.fullmatch(r"([A-Za-z]*)(\d+)", left), re.fullmatch(r"([A-Za-z]*)(\d+)", right)
        if not lm or not rm: return f"{left}-{right}"
        if lm.group(1) == rm.group(1) or (lm.group(1) and not rm.group(1)):
            prefix, a, b = lm.group(1), lm.group(2), rm.group(2)
        else:
            return f"{left}-{right}"
        if len(a) != len(b): return f"{left}-{right}"
        i = 0
        while i < len(a) - 1 and a[i] == b[i]: i += 1
        return f"{prefix}{a}-{b[i:]}"
    return ", ".join(span(part.strip()) for part in pg.split(","))
def authors(au):
    n = [f'{a["family"]} {a["initials"].replace(".", "").replace(" ", "")}' for a in au]
    return ", ".join(n[:6]) + (", et al" if len(n) > 6 else "") + ". "
rendered = {}
for r in R:
    s = authors(r["authors"])
    t, ch = sentence_case(r["title"], (), cap_after_colon=False)
    if ch: L.flag(r["key"] + " title", "sentence case applied (Citing Medicine: first word, proper nouns, proper adjectives, acronyms, and initialisms). Proper nouns cannot be detected automatically; confirm.", S["citing_medicine"])
    if r["type"] == "book":
        s += f"{t}. {r['edition']} ed. {r['place']}: {r['publisher']}; {r['year']}."
        L.flag(r["key"], "book: not on Crossref/PubMed. Entire-book form is Citing Medicine Ch 2A (Author/Editor, Title, Edition, Place of Publication, Publisher, Date). Place left as typed; no state was invented.", S["nlm_samples"])
    else:
        j = r["lookup"]["journal_abbrev"]
        if j != r["container"]: L.change("journal abbreviation (lookup)", r["container"], j, f"MEDLINE abbreviation from {r['lookup']['from']} (ICMJE: abbreviate per MEDLINE)")
        date = r["year"] + (f" {M[r['month']]}" if r.get("month") else "") + (f" {r['day']}" if r.get("day") else "")
        pg = elide(r["pages"])
        if pg != r["pages"]: L.change("page elision", r["pages"], pg, "Citing Medicine Ch 1, Location (Pagination), General Rules (123-125 becomes 123-5)")
        s += f"{t}. {j}. {date};{r['volume']}" + (f"({r['issue']})" if r.get("issue") else "") + f":{pg}."
        if r.get("doi"): s += f" doi: {r['doi']}."
    if len(r["authors"]) > 6: L.change("authors", f"{len(r['authors'])} authors", "first six + et al.", S["nlm_samples"] + " ('List the first six authors, followed by et al.')")
    if len(r["authors"]) == 6: L.flag(r["key"], "exactly six authors: all six listed (rule says more than six -> et al.)", S["nlm_samples"])
    if r["key"] == "rose": L.flag("rose", "PubMed holds two records with this title and author list (Brain Res 935(1-2):40-6, PMID 12062471, and 943(1):15-22, PMID 12088834). Confirm which one you read", S["pubmed"])
    rendered[r["key"]] = s
L.flag("reference list numbering", "written as '1. ', the selected journal option. Neither ICMJE nor NLM's Sample References shows the list number. Citing Medicine examples are unnumbered.", S["icmje"])
L.flag("page layout", "font, spacing, margins and title page left as they were. The journal option is unchanged: ICMJE sets none and defers to the journal.", S["icmje"])
for i, (p, k) in enumerate(zip(refps, order)):
    before = p.text; new = f"{i + 1}. {rendered[k]}"
    for r in p.runs[1:]: r._r.getparent().remove(r._r)
    p.runs[0].text = new; p.runs[0].italic = False
    L.change("reference", before, new, S["nlm_samples"])
if [r["key"] for r in R] != order: L.change("reference order", ", ".join(r["key"] for r in R), ", ".join(order), S["icmje"])
D.save(out); L.dump(out.replace(".docx", "_changes.json"))
print(f"wrote {out}: {len(L.changes)} changes, {len(L.flags)} flags; order {order}")
