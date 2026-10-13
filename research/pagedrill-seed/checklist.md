# Checklists

- **APA 7 student paper** → [checklist_apa.md](checklist_apa.md): 33 rules, each with the official apastyle.apa.org URL. after.docx: **28 pass, 0 fail, 5 flagged** (user-dependent or missing data; nothing guessed).
- **AR 25-50 memorandum** → [checklist_memo.md](checklist_memo.md): 24 rules, each with its AR 25-50 paragraph (10 Oct 2020, admin rev 007, 4 Oct 2024). memo_after.docx: **20 pass, 0 fail, 4 flagged**.
- Official source status for every requested style → [sources.md](sources.md).

Re-run: `python3 src/make_before_apa.py before.docx && python3 src/format_apa.py before.docx after.docx profiles/apa7_student.json refs_extracted.json && python3 src/verify_apa.py` and `python3 src/make_before_memo.py && python3 src/format_memo.py && python3 src/verify_memo.py` (memo scripts use fixed file names in this folder) (from this folder).
