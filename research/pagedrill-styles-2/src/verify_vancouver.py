"""Check vanc_after.docx against ICMJE + NLM Sample References; write checklist_vancouver.md."""
import re, json, sys
sys.path.insert(0, "src")
from fmtlib import *
D = Document("vanc_after.docx"); B = Document("vanc_before.docx"); prof = json.load(open("profiles/vancouver_icmje_nlm.json")); S = prof["sources"]
ch = json.load(open("vanc_after_changes.json"))
IC, NLM, CM = S["icmje"].split(" ")[0], S["nlm_samples"].split(" ")[0], S["citing_medicine"].split(" ")[0]
rows = []
def row(rule, src, ok, note=""): rows.append((len(rows) + 1, rule, src, {True: "PASS", False: "FAIL"}.get(ok, ok), note))
ps = D.paragraphs; ri = next(i for i, p in enumerate(ps) if p.text == "References")
txt = " ".join(p.text for p in ps[:ri]); refs = [p.text for p in ps[ri + 1:] if p.text]
row("Citations identified by Arabic numerals in parentheses; no author-year left", IC + " (g. References)", not re.search(r"\(\D+, \d{4}\)", txt) and all(re.fullmatch(r"\d+(, \d+)*", m) for m in re.findall(r"\(([\d, ]+)\)", txt)))
first = []
for m in re.findall(r"\(([\d, ]+)\)", txt):
    for n in map(int, m.split(", ")):
        if n not in first: first.append(n)
row("References numbered consecutively in order of first mention", IC + " (g. References)", first == list(range(1, len(refs) + 1)), "first-mention order: " + ", ".join(map(str, first)))
row("Several references in one citation: separator/range style", IC, "FLAG", "'(1, 4)' used; ICMJE doesn't specify (journals use 1,4 / 1, 4 / superscripts / ranges)")
row("Placement of the citation number relative to punctuation", IC, "FLAG", "left where the author typed it; not specified")
row("Every listed reference cited; one reference per number", IC, sorted(first) == list(range(1, len(refs) + 1)))
row("Reference list numbering format ('1.')", IC + "; " + NLM, "FLAG", "not shown by ICMJE or the Sample References page")
OFF = {"Halpern": ("Halpern SD, Ubel PA, Caplan AL. Solid-organ transplantation in HIV-infected patients. N Engl J Med. 2002 Jul 25;347(4):284-7.", "#1 Standard journal article"),
       "Rose": ("Rose ME, Huerbin MB, Melick J, Marion DW, Palmer AM, Schiding JK, et al. Regulation of interstitial excitatory amino acid concentrations after cortical contusion injury. Brain Res. 2002;935(1-2):40-6.", "#1, more than six authors"),
       "Zhang": ("Zhang M, Holman CD, Price SD, Sanfilippo FM, Preen DB, Bulsara MK. Comorbidity and repeat admission to hospital for adverse drug reactions in older adults: retrospective cohort study. BMJ. 2009 Jan 7;338:a2752. doi: 10.1136/bmj.a2752.", "Article with a DOI (PubMed PMID/PMCID omitted: optional and not in the user's entry)"),
       "Murray": ("Murray PR, Rosenthal KS, Kobayashi GS, Pfaller MA. Medical microbiology. 4th ed. St. Louis: Mosby; 2002.", "#19 Personal author(s)")}
got = {re.sub(r"^\d+\. ", "", r).split(" ")[0]: re.sub(r"^\d+\. ", "", r) for r in refs}
row("Each entry identical, character for character, to NLM's own Sample Reference for the same work", NLM, all(got.get(k) == v[0] for k, v in OFF.items()), "; ".join(f"{k} ({v[1]}): {'match' if got.get(k) == v[0] else 'DIFF'}" for k, v in OFF.items()))
row("Authors: surname + initials, no periods; first six then 'et al.' when more than six", NLM + " (#1: 'List the first six authors, followed by et al.')", got["Rose"].startswith("Rose ME, Huerbin MB, Melick J, Marion DW, Palmer AM, Schiding JK, et al.") and "et al" not in got["Zhang"], "Rose (8 authors) \u2192 6 + et al.; Zhang (exactly 6) all listed")
row("Journal titles abbreviated per MEDLINE (looked up in PubMed, not guessed)", IC + " ('abbreviated according to the style used for MEDLINE'); " + S["pubmed"].split(" ")[0], "N Engl J Med." in got["Halpern"] and "Brain Res." in got["Rose"], "N Engl J Med (PMID 12140307), Brain Res (PMID 12062471), BMJ (PMID 19129307)")
row("Article titles in sentence case, lowercase after a colon", NLM + " (examples) / " + CM, "NOT VERIFIED", "output matches NLM's examples; the rule text (and proper-noun handling) is in Citing Medicine, which could not be read")
row("Date as 'year Mon day' with three-letter month, no period", NLM + " (examples) / " + CM, "NOT VERIFIED", "'2002 Jul 25', '2009 Jan 7' match NLM examples; rule text in Citing Medicine")
row("Page ranges elided (284-7, 40-6)", NLM + " (examples) / " + CM, "NOT VERIFIED", "matches NLM examples here; edge cases (e.g. 1199-1201, letters, roman numerals) need Citing Medicine")
row("DOI after the pagination as 'doi: 10.xxxx.'", NLM + " (Article with a Digital Object Identifier)", got["Zhang"].endswith("doi: 10.1136/bmj.a2752."))
row("Book: Authors. Title. Edition. Place: Publisher; year.", NLM + " (#19) / " + CM, "NOT VERIFIED", "matches NLM #19 exactly; other book cases (editors, chapters, place with state) need Citing Medicine")
row("Page layout (font, spacing, margins, title page)", IC, "FLAG", "ICMJE sets none ('consult with the journal'); left as the author had it")
row("Reference data checked against PubMed/Crossref", S["pubmed"].split(" ")[0], "FLAG", "Halpern, Zhang, Rose verified in PubMed; Rose also exists as a second PubMed record (943(1):15-22): author must confirm; Murray (book) not in Crossref/PubMed")
bps = B.paragraphs; bri = [p.text for p in bps].index("References"); bb = " ".join(p.text for p in bps[:bri])
dif = word_diff(bb, txt)
row("Author's sentences unchanged (only citation markers change)", "(Lawrence's rule: format only)", {x[2:] for x in dif} <= {"Halpern", "Zhang", "Rose", "Murray", "et", "al", ".", ",", ";", "2002", "2009", "1", "2", "3", "4"}, "word-level diff: " + " ".join(dif))
with open("checklist_vancouver.md", "w") as f:
    f.write("# Vancouver (ICMJE + NLM) — rule checklist for vanc_after.docx\n\nGenerated by `src/verify_vancouver.py`. Sources (fetched 2026-10-10, copies in `vanc_src/`):\n"
            f"- ICMJE Recommendations, Preparing a Manuscript for Submission, g. References: {S['icmje']}\n- NLM Samples of Formatted References for Authors of Journal Articles: {S['nlm_samples']}\n- NLM Citing Medicine, 2nd ed.: {S['citing_medicine']}\n- PubMed E-utilities (data checks): {S['pubmed']}\n\n"
            "FLAG = journal/author decision (not specified by ICMJE/NLM, or data needs confirming). NOT VERIFIED = output matches NLM's own examples, but the rule text lives in Citing Medicine, which we could not read.\n\n")
    f.write("| # | Rule | Official source | Result | Note |\n|---|---|---|---|---|\n")
    for r in rows: f.write(f"| {r[0]} | {r[1]} | {r[2]} | **{r[3]}** | {r[4]} |\n")
    c = {k: sum(1 for r in rows if r[3] == k) for k in ("PASS", "FAIL", "FLAG", "NOT VERIFIED")}
    f.write(f"\n**Totals:** {c['PASS']} pass, {c['FAIL']} fail, {c['FLAG']} flagged, {c['NOT VERIFIED']} not verified.\n\n"
            "**Status: NOT FULLY VERIFIED.** Citations and the four sample entries are correct (all four match NLM's own examples character for character), but the general rules for titles, dates, page elision and books are only example-attested: the rule text is in Citing Medicine 2nd ed. (free on NCBI Bookshelf, NBK7256), which returned a reCAPTCHA to the box. To finish: open NBK7256 in a normal browser (Lawrence's machine, or the box browser with a human solving the CAPTCHA), save chapters 1 (Journals) and 2 (Books), and re-run this checklist. Vancouver has no official page layout; that stays journal-dependent by design.\n\n## Flags from the formatter\n")
    for fl in ch["flags"]: f.write(f"- **{fl['item']}**: {fl['why']}\n")
    f.write("\n## Logged changes\n")
    for x in ch["changes"]: f.write(f"- `{x['kind']}`: \u201c{x['before'][:200]}\u201d \u2192 \u201c{x['after'][:220]}\u201d\n")
for r in rows: print(r[0], r[3], r[1][:70], "|", r[4][:140])
