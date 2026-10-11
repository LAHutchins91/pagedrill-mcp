# Checklists

- **APA 7 student paper** → [checklist_apa.md](checklist_apa.md): 33 rules, each with the official apastyle.apa.org URL. after.docx: **28 pass, 0 fail, 5 flagged** (user-dependent or missing data; nothing guessed).
- **AR 25-50 memorandum** → [checklist_memo.md](checklist_memo.md): 24 rules, each with its AR 25-50 paragraph (10 Oct 2020, admin rev 007, 4 Oct 2024). memo_after.docx: **20 pass, 0 fail, 4 flagged**.
- **MLA 9 student paper** → [checklist_mla.md](checklist_mla.md): 40 rules. mla_after.docx: **36 pass, 0 fail, 3 flagged, 1 not verified**. Status: **NOT fully verified**. Still unread: secs. 2.89–2.125. The profile stays hidden.
- **IEEE conference paper (US letter)** → [checklist_ieee.md](checklist_ieee.md): 35 rules from the official template, Editorial Style Manual and Reference Style Guide (V 3.28.2025). ieee_after.docx: **28 pass, 0 fail, 7 flagged, 0 not verified**. Status: **FULLY VERIFIED** for journal-article references (other reference types kept as typed + flagged).
- **Vancouver (ICMJE + NLM)** → [checklist_vancouver.md](checklist_vancouver.md): 17 rules. vanc_after.docx: **12 pass, 0 fail, 5 flagged, 0 not verified**. Status: **fully verified** against Citing Medicine Chapter 1 (NBK7282) and Chapter 2 (NBK7271). Grouped citations, list numbering, and page layout stay journal options.
- Competitor comparison and free-rival kill check → [comparison.md](comparison.md).
- Official source status for every requested style → [sources.md](sources.md).

Re-run: `python3 src/make_before_apa.py before.docx && python3 src/format_apa.py before.docx after.docx profiles/apa7_student.json refs_extracted.json && python3 src/verify_apa.py` and `python3 src/make_before_memo.py && python3 src/format_memo.py && python3 src/verify_memo.py` (memo scripts use fixed file names in this folder) (from this folder).

MLA/IEEE/Vancouver: `python3 src/make_before_mla.py mla_before.docx && python3 src/format_mla.py mla_before.docx mla_after.docx profiles/mla9_paper.json refs_mla.json && python3 src/verify_mla.py`; `python3 src/make_before_ieee.py && python3 src/format_ieee.py ieee_before.docx ieee_after.docx profiles/ieee_conference.json refs_ieee.json && python3 src/verify_ieee.py`; `python3 src/make_before_vancouver.py && python3 src/format_vancouver.py vanc_before.docx vanc_after.docx profiles/vancouver_icmje_nlm.json refs_vancouver.json && python3 src/verify_vancouver.py`.
