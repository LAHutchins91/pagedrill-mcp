# Paper & memo formatter by Ouroboros: research, recommendation, prototype

Prepared by Grok Bot for Lawrence, Sat Oct 10, 2026 (ET). **Research and prototype only. Nothing was deployed, no accounts or Stripe objects were created, nothing was posted.** Lawrence's scope (including the expansion to all school styles and military formats) is covered below.

## TL;DR

| | |
|---|---|
| **Recommendation** | A **separate plugin** that reuses Stetwise's .docx engine (propose → diff → apply → undo). Not a Stetwise tier, not a Papers add-on. One plugin, two storefronts: **Academic** (students, grad students, nursing) and **Military** (memos, PME papers). |
| **Proposed name** | **Galleyset by Ouroboros** (first-pass clear). Backups: **Pagedrill**, **Inkrule**. |
| **Price** | **$5.99/mo or $49.99/yr**, free "check-only" report. Cap: 60 documents, 120 preview renders, 25 MB/file per month. New house tier, so it needs Lawrence's OK. |
| **Cost per user** | $0.01 (light) · $0.05 (typical) · **$0.46 at the cap** per month (Stetwise cost model). Margin at the cap: $5.01/mo (84%) monthly, $3.53/mo (85%) annual. Uncapped abuser would cost $9.21 → cap is required. |
| **Closest competitors** | Veermat **$9/mo** (whole-document formatter, 1,000 pages) · PERRLA **$12.95/mo, $79.95/yr** (Word add-in; APA/MLA/Turabian) · NCO Kit **$10/mo or $97/yr** and EvalMe **$9.99/mo** (Army memos) · Scribbr human formatting **$2/page**. |
| **Samples** | APA 7 student paper: before.docx → after.docx, **28 pass / 0 fail / 5 flagged** against official APA pages. AR 25-50 memo: memo_before.docx → memo_after.docx, **20 pass / 0 fail / 4 flagged** against AR 25-50 paragraphs. |
| **v1 styles** | APA 7 (student + professional) and AR 25-50 memorandum (verified). MLA 9 next (partly verified). Everything paywalled or unreachable is marked "can't ship until licensed/verified" in sources.md. |

---

## 1. Demand and competitors

### Is there paid demand for whole-document formatting (not just citations)?
Yes, and it is paid for separately from citation tools:
- **Scribbr sells human "Paper Formatting" at $2 per page** (whole document only; title page, margins, spacing, headings, page numbers). (help.scribbr.com pricing article, updated Mar 2026)
- **Veermat** sells exactly this job ("Convert my essay to APA format… your words stay exactly as you wrote them") at **$9/mo for 1,000 downloaded pages**; the check is free, the download is paid. https://www.veermat.com/pricing
- **PERRLA** (paid, closest Word add-in) builds formatted APA/MLA/Turabian papers in Word and manages references: $12.95/mo, $79.95/yr, $129.95/2 yr; Pro $15.90/$99.90/$159.90; Unlimited $19.95/$124.90/$199.90; 50% off for military/veterans; schools $9.95/student/yr. https://www.perrla.com/pricing , PERRLA help-center price article (perrla.zendesk.com, updated Sep 21, 2026)
- **Military memo generators charge**: NCO Kit unlimited $10/mo or $97/yr (ncokit.com); EvalMe Pro $9.99/mo incl. AR 25-50 memos (evalmepro.com). Free ones exist too: Military Toolkit memo generator, Army Memo Maker (https://armymemomaker.com/), Prompt2Tool, the Navy "Yeomanizer" and jeranaias's naval letter generator (SECNAV format), and TongueToQuill for the Air Force (free for military, per search).
- **Student pain is visible but uncountable from the box.** Reddit returns 403 to the box, so only snippets: r/army "Memo builder" (https://www.reddit.com/r/army/comments/17vgy0y/memo_builder/), r/AirForce "Where is the memo template folder?" (https://www.reddit.com/r/AirForce/comments/1qjffca/where_is_the_memo_template_folder/), r/Professors "I honestly don't know what you mean by APA style" (thread found via search snippet; URL not recorded). No upvote counts available.
- **X** (search, Oct 2025–Oct 2026): steady low-volume complaints ("Why is the hanging indent so personal?" https://x.com/LMS_Tutor_US/status/2087523879900074280 ; "write the title 50 times" https://x.com/XennShen/status/2015845470967312663). One post is a useful positioning signal: a student says an essay was flagged 38% AI after using AI only to fix APA formatting (https://x.com/MuskSpeakFreely/status/2096961060641079718). A deterministic formatter that never touches the words is a selling point.
- **HN**: essentially no signal (Algolia: 18 stories for "APA format", none about this need). Not a developer product; don't use HN as a gauge.

### Citation-only tools (the crowded, mostly free part)
| Tool | Whole-document formatting? | Price (source) |
|---|---|---|
| Zotero | No (citations/bibliography in Word) | Free (zotero.org) |
| Mendeley | No | Free reference manager (search results; vendor page not fetched) |
| EndNote 2025 | No | $150 student one-time US (endnote.com/buy, via search) |
| MyBib | No | "100% free" (mybib.com) |
| Scribbr citation generator | No (formatting is the separate $2/page service) | Free (scribbr.com/citation/generator) |
| EasyBib / Citation Machine (Chegg) | No | Free generator; Plus $9.95/mo per third-party reviews (not confirmed on Chegg's own page) |
| Grammarly | No (citation finder/generator) | Pro $12/mo billed annually, $30 monthly (grammarly.com/plans, support article) |
| Paperpal | Submission checks, not student-paper layout | Prime $25/mo or $144/yr; Pro $59/mo or $348/yr (support.paperpal.com) |
| SciSpace (Typeset) | Journal-template formatting | Editor plans: Researcher $20/mo or $96/yr (per a 2026 review; SciSpace page not fetched) |
| APA Academic Writer | Yes (APA's own tool) | Institutional; individual price not public (apa.org, UW-Madison KB) |
| Microsoft Word built-in | Citations & bibliography only | Included. Microsoft's own page still documents an "APA 6th Edition citation style fix" and warns formats change (https://support.microsoft.com/en-us/word/apa-mla-chicago-automatically-format-bibliographies); PERRLA says Word's built-in references "are outdated". |

### MCP directories
What exists is citation tooling, not whole-document style compliance:
- zotero-mcp (Glama): inserts Zotero citation fields and bibliography into .docx; CSL APA/MLA/Chicago-AD/Harvard/IEEE/Vancouver. https://glama.ai/mcp/servers/Robernetes/zotero-mcp
- word-footnotes-bibliography-mcp (Glama): footnotes, citations, bibliography for APA 7/MLA 9/Chicago 17, local stdio. https://glama.ai/mcp/servers/Bravo111034/word-footnotes-bibliography-mcp/tree
- ReferenceMCP (GitHub): reference manager + CSL formatting. https://github.com/eduardofarina/ReferenceMCP
- Enhanced Word MCP (Glama): generic docx editing. https://glama.ai/mcp/servers/ildunari/enhanced-word
- Smithery registry: no server named or described as a paper-format/style-compliance tool in our searches. mcp.so and PulseMCP searches surfaced nothing relevant (search pages only partly parseable from the box).

**Gap:** no hosted MCP that takes a finished .docx and makes the *whole document* comply with a named style guide or military regulation, with a rule-by-rule report tied to the official source, and no rewriting of the author's words.

### Which assistants are missing it?
ChatGPT, Claude, Cursor and Grok have no listed tool for this. General-purpose assistants (in chat or inside Word) can be asked to "make it APA," but that's free-form LLM editing. It isn't checked against the rules, can change wording, and can invent citation data. ChatGPT is the main channel (students); Claude and Grok are secondary; Cursor matters only for LaTeX/Markdown users (out of v1 scope).

### Word add-in (Office.js / AppSource): in reach, but v2
- In reach technically: the formatting engine is server-side, so a Word task pane could call the same API on the open document. PERRLA already proves the add-in channel works (installed "through the Word Add-in Store").
- Out of v1 scope: it needs a Microsoft Partner Center publisher account (an account, so Lawrence's approval) plus AppSource certification. Office.js coverage of headers, fields and section properties also has to be checked against the requirement sets before committing. **v1 = MCP + hosted file upload/preview page; v2 = Word add-in.**

### Military caveat (important for marketing)
Official correspondence is often drafted on government systems, and personnel must not put CUI or classified content into commercial AI tools. Position the military side for **unclassified drafting on personal devices**: PME and ROTC papers, practice memos, and layout checks of unclassified drafts. Make no claims of DoD endorsement. Wording to be reviewed before any listing.

## 2. Feature or tier of Stetwise, add-on to Papers, or separate plugin?
**Separate plugin, built on Stetwise's engine.**
- **Audience:** Stetwise is for pros and agent users editing spreadsheets and documents outside Office. This one is for students (APA/MLA/Chicago), grad students (theses), nursing programs (strict APA) and service members (AR 25-50/SECNAV/Tongue and Quill, PME papers). Different search intent ("format my paper in APA", "AR 25-50 memo format"), different directories (ChatGPT for students).
- **Pricing fit:** students are price-sensitive and compare against PERRLA, Veermat and free generators. Stetwise is $7.99/$79.99, and its annual price is above PERRLA's $79.95. A $5.99/$49.99 plugin undercuts every paid competitor; a Stetwise tier can't.
- **Overlap:** Stetwise supplies the safe-edit core (diff, version token, undo); the formatter adds style profiles, a rule checker and the reference renderer. **Papers** stays academic search and citations. It's a natural cross-sell: when the formatter flags a missing DOI or date, Papers can look it up for the user to confirm (e.g., the sample's Sanchiz et al. DOI). Papers shouldn't absorb page layout, and the military side has nothing to do with Papers.
- **Marketing:** "Galleyset: your paper, in the exact format your assignment asks for. Your words untouched." It also gets its own landing pages per style (APA, MLA, AR 25-50…), which is where the search traffic is.

## 3. Pricing
- **Competitors (fetched today unless noted):** Veermat $9/mo · PERRLA $12.95/mo, $79.95/yr (military 50% off) · NCO Kit $10/mo, $97/yr · EvalMe $9.99/mo · Grammarly $12/mo annual, $30 monthly · Paperpal Prime $25/mo, $144/yr · Scribbr $2/page · EasyBib Plus $9.95/mo (third-party) · free: Zotero, Mendeley, MyBib, Scribbr generator, TongueToQuill, Yeomanizer, APD/AF templates.
- **Our cost** (src/cost_model.py reuses Stetwise's pricing_model.py unit prices: Cloud Run engine with LibreOffice renders, Supabase storage/egress, Vercel, Stripe 2.9% + 30¢ + 0.7% Billing; **no LLM cost**, since the user's assistant does the reading):

| Profile / month | Docs | Passes | Previews | Cost |
|---|---|---|---|---|
| Light student | 4 | 8 | 8 | $0.01 |
| Typical | 12 | 36 | 36 | $0.05 |
| Heavy at cap | 60 | 300 | 120 | **$0.46** |
| Uncapped abuser | 500 | 3,000 | 1,500 | $9.21 |

| Price | Net after Stripe (per mo) | Margin at cap |
|---|---|---|
| **$5.99/mo** | $5.47 | **$5.01 (84%)** |
| **$49.99/yr** | $3.99 | **$3.53 (85%)** |
| $4.99/mo (alt) | $4.51 | $4.05 |
| $7.99/mo (house tier, alt) | $7.40 | $6.94 |

- **Recommendation: $5.99/mo, $49.99/yr**, plus a free check-only report (like Veermat) so users see the issues before paying. Under every paid competitor monthly and annually (PERRLA's annual is $79.95, NCO Kit's $97). Above cost at every profile up to the cap.
- **Open choice for Lawrence:** PERRLA's military price is effectively $39.98/yr. To be under it for service members we'd need a verified-military annual at ≤ $39.97 (e.g., $34.99, still ~$2.33/mo margin at the cap). That needs a verification vendor (an account), so it isn't proposed for v1.
- This would be a **new house tier**; the existing ones are $7.99/$79.99 and $9.99/$99.99. No Stripe objects were created.

## 4. Name (first-pass only; not legal clearance)
| Check | **Galleyset** | Pagedrill | Inkrule |
|---|---|---|---|
| npm (bare, -mcp) | free / free | free / free | free / free |
| PyPI | free | free | free |
| GitHub repos named | 0 | 0 | 1 ("InkRules", unrelated) |
| Smithery registry | 0 | 0 | 0 |
| USPTO (via uspto.report mirror) | 0 results | 0 results | 0 results |
| Web | "Art-Galleyset", a French kitchenware shop (unrelated field) | No exact match found | Unrelated screen-printing use |
| .com | galleyset.com (and .app) don't resolve | pagedrill.com doesn't resolve | not checked |

Why Galleyset: a galley is the typesetter's proof, and "set" is what a compositor does. It covers academic and military without sounding like either. Pagedrill is the military-flavored backup ("drill" = done by the book).

**Not done yet (required before locking):** tmsearch.uspto.gov didn't load results in headless Chrome (even "grammarly" showed 0), so the USPTO check used a mirror without live/dead status or classes. Glama, PulseMCP and mcp.so search pages weren't reliably parseable from the box. ChatGPT/Claude directories weren't checked. Run the full check in a real browser. Names dropped: Quillset (an AI prompt-manager app at quillset.app), DressRight (Japanese Class 9 filing + a military uniform app), Squared Away (many USPTO marks), Quoinly (budgeting app), Margent, Rubricate, Formwise, Styleproof, Rubrica (taken or crowded).

## 5. Prototype (what's in this folder)
**Architecture shown by the prototype:**
1. The user's assistant reads the messy document and tags roles and reference fields (refs_extracted.json, memo_extracted.json).
2. The engine runs a **grounding check**: every extracted value must appear in the original text, or the job stops. That makes inventing a DOI, date or school impossible.
3. A **style profile** (profiles/*.json, every value tied to an official URL or paragraph) drives deterministic layout.
4. Output: the formatted .docx plus a change log (the diff the user approves, Stetwise-style), flags for anything user-dependent or missing, and a verifier that re-checks the saved file rule by rule.

**APA 7 student paper (fictional student/instructor; three real references taken from APA's own example pages, DOIs checked on Crossref):**
- Fixed automatically: title page (title 3 blank lines down, bold, centered; byline; course "PSY 201: …"; instructor; date), page number top right on every page, "Running head:" removed (student paper), Times New Roman 12, double spacing with 0 pt before/after, 0.5-in. first-line indents, ragged right, "Introduction" heading removed (the title acts as Level 1), headings re-leveled (L1 centered bold, L2 left bold, L3 left bold italic), numbers/letters stripped, ALL CAPS → APA title case, References on a new page with bold centered label, 0.5-in. hanging indent, alphabetized, authors inverted with initials and "&", italics on journal/volume and stand-alone titles, DOI as https://doi.org/, en-dash page ranges, in-text "and"→"&" in parentheses, "et al." for 3+ authors, multiple citations alphabetized with semicolons, missing parentheses around narrative years.
- Flagged, not guessed: missing affiliation (highlighted placeholder), course name as typed, a section with only one subsection, Toner news story with no date (URL says 2020/06/04, but APA's own example of the same story gives 2020, September 24, so URL dates aren't trusted), "(Toner)" citation with no year, Sanchiz et al. missing DOI/issue (Crossref shows DOI 10.1016/j.chb.2017.02.038 and no issue for vol. 72; the user adds it, or Papers looks it up).
- A word-level diff confirms the author's sentences are unchanged apart from citation punctuation and name lists.

**AR 25-50 memorandum (all units, names, office symbols, phone and email are fictional placeholders):**
- Fixed: civilian TO/FROM/Date layout → office symbol + date line, MEMORANDUM FOR on the 3rd line, SUBJECT: on the 2nd line below, text on the 3rd line below; single-spaced with a blank line between paragraphs; numbered 1./a./(1) with ¼ in. and ½ in. first-line indents and wrapped lines back at the margin (figure 2-1); two spaces after sentence periods (para 1-39b(9), changed back to two spaces in the 4 Oct 2024 revision); dates as "3 November 2026"; military time (0630, 1300); signature block at the page center on the 5th line below the text, NAME in caps, MAJ on line 2; salutation and "Sincerely," removed (not memo elements); 1-in. margins, no justification.
- Flagged: letterhead/DoD seal (must use the APD template), ARIMS record number, branch abbreviation (DA Pam 611-21 not fetched), authority line (user's call), postscript (para 1-29: no postscripts; held out pending the writer's OK), font face (para 1-19 leaves it to senior leaders; 12 pt recommended), date placed after signing (para 2-4a(3)(b)).

## 6. Phase plan (realistic)
| Phase | Scope | Size |
|---|---|---|
| **v1** | MCP tools: `list_styles`, `check_document` (free report), `propose_format` (diff + flags), `apply_format` (version token), `undo`, `render_preview`. Profiles: **APA 7 student + professional**, **AR 25-50 memorandum + MFR**, **MLA 9** (after finishing verification from MLA Style Center). Hosted upload/preview page. ChatGPT first, then Claude, Grok, MCP directories. | M (4–6 weeks on the Stetwise core) |
| v1.1 | IEEE (free official PDFs), Vancouver (ICMJE + NLM read from a browser), APA/MLA edge cases (tables, figures, block quotes, footnotes), Army Writing Style checks (BLUF, passive voice, paragraph length) as advisory flags. | S–M |
| v1.2 | **Profile importer:** a school's guide (thesis/dissertation, course rubric, "Harvard" variant) → draft profile with each rule linked to its sentence in the guide → human confirms → private profile. | M |
| v2 | After licensing/verification: Chicago 18 (and 17), Turabian, AMA, ASA, CSE, ACS, Bluebook, OSCOLA 5; SECNAV M-5216.5 + MCO 5216.20B, Tongue and Quill (after confirming current status), JSM 5711.01 (after confirming the number), USAWC and Air University paper formats. Word add-in (AppSource). | L |

## 7. Approvals needed (nothing done)
- Lawrence: the new $5.99/$49.99 tier; the name (after the full check); whether to buy licenses (CMOS Online, MLA Handbook Plus, AMA, Bluebook, etc.); a Microsoft Partner Center account for v2.
- Someone with a normal browser: download the SECNAV, MCO, e-Publishing, JCS, USAWC and AU documents (all blocked from the box).

## Files
- plan.md (this), sources.md (official source table), checklist.md (index), checklist_apa.md, checklist_memo.md
- before.docx / after.docx / before.pdf / after.pdf / before_pages.png / after_pages.png (+ per-page PNGs), after_changes.json
- memo_before.docx / memo_after.docx / memo_before.pdf / memo_after.pdf / memo_before_pages.png / memo_after_page-1.png, memo_after_changes.json
- profiles/apa7_student.json, profiles/ar25-50_memo.json; refs_extracted.json, memo_extracted.json
- src/make_before_apa.py, src/format_apa.py, src/verify_apa.py, src/make_before_memo.py, src/format_memo.py, src/verify_memo.py, src/cost_model.py
- apa_src/ (official APA page text as fetched), mil_src/ (AR 25-50 PDF + text, GPO Tongue and Quill PDF), style_src/, namecheck/
