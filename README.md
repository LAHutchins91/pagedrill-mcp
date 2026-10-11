# Pagedrill by Ouroboros

Pagedrill formats a `.docx` paper or memorandum to an official style from ChatGPT, Claude, Cursor, or Grok. The checklists in `research/pagedrill-seed/` are the spec. A rule is applied only when it traces to the cited official source.

Support: [ouroborosplugins@gmail.com](mailto:ouroborosplugins@gmail.com)

## What v1 will format

| Style | Selectable | Result on the sample |
|---|---|---|
| APA 7 student paper | yes | 28 pass, 0 fail, 5 flagged |
| APA 7 professional paper | yes | running head, author note, and abstract flagged when missing |
| Army memorandum, AR 25-50 | yes | 20 pass, 0 fail, 4 flagged |
| IEEE conference paper, US letter | yes | 28 pass, 0 fail, 7 flagged |
| Vancouver (ICMJE + NLM) | yes | 12 pass, 0 fail, 5 flagged |
| MLA 9 | no | loaded, hidden, and refused until a checklist is fully verified |

Flagged on the APA student sample, by design: affiliation, course name, a single subsection, Toner's missing date, Sanchiz's missing DOI and issue, and the Toner citation without a year. Nothing in those fields is looked up or invented.

Flagged on the memorandum, by design: letterhead and DoD seal, ARIMS record number, authority line, and the postscript (held out of the layout). Branch abbreviations are not guessed.

Flagged on the IEEE conference sample, by design: an all-capitals title, an author block without email or ORCID, a short abstract, an author name left beside a citation number, "in reference [n]", proper nouns in reference titles, and a combined issue number. Only journal articles are rendered. Any other reference type is kept as typed and flagged. Journal abbreviations are limited to titles attested in the profile. IEEE is rebuilt on the conference template (`profiles/assets/ieee_conference_letter.docx`); the original file stays as version 1 so undo can restore it.

Flagged on the Vancouver sample, by design: grouped citation punctuation, where the number sits relative to the punctuation, reference-list numbering, and page layout. ICMJE and Citing Medicine leave those to the journal, so they are profile options (`comma-space`, `1. `, and `unchanged` on the sample), not guessed rules. The formatter also asks the author to confirm proper nouns, Rose's second PubMed record, and a book place that was typed without a state. Journal abbreviations are the attested MEDLINE forms in the profile, or an abbreviation the user supplies. A missing month, day, or DOI is omitted.

Army copy is an unclassified drafting aid. Pagedrill is not endorsed by the Department of Defense, does not display the DoD seal, and is not for classified information or controlled unclassified information.

## Tools

`check_document` is free, rate-limited, and does not change the file. It does not count against the monthly caps. An account without a trial or Pro subscription can check a document and gets one fully formatted download a month.

`propose_format` returns the change list, flags, and checklist. `apply_format` needs the `proposal_id` and `base_version` from that proposal. Pass `supplied.track_changes` when the user wants the wording edits written as Word revisions (`w:ins` / `w:del`, author Pagedrill). Pass `supplied.table_of_contents` when the user wants a TOC field for a thesis or long paper. Word fills that field from heading styles. Pagedrill does not type the entries. `undo` restores an earlier version, including the imported bytes. `import_file` takes a ChatGPT attachment download URL. Other clients use `start_upload` and the signed PUT link.

`import_references` reads `.bib` or `.ris` text and renders journal articles in the active style. Other types stay as typed. Missing fields are flagged and omitted. It does not use a formatted download. `create_memorandum` builds a new AR 25-50 memo from organization, office symbol, memorandum for, subject, paragraphs, signature block, and an optional point of contact. Letterhead and the ARIMS number are flagged when the user did not supply them. Creating a memo uses one file slot and one formatted download. Undo of that file restores the created bytes.

The author's words stay. APA may change citation punctuation and name-list mechanics. AR 25-50 may change date and time forms. IEEE may change citation brackets and journal-article reference punctuation. Vancouver may change parenthetical citation numbers and reference-list punctuation. Any other wording change is refused and the file is not saved. For APA and AR 25-50, only `word/document.xml`, `word/styles.xml`, and an existing `word/header1.xml` may change. Vancouver rewrites `word/document.xml` only, so the author's font and margins stay. Every other package part keeps its original bytes. IEEE is the template exception above.

## Caps and billing

Without a trial or Pro subscription, the free tier is the check report plus one fully formatted download a month (and two previews, so that download can be proposed first). Trial and Pro both allow 60 formatted documents and 120 previews a month, and files up to 25 MB. A separate file-count cap of 120 a month limits storage on those plans. The free file cap is 5. Free usage is counted separately, so time already spent on a trial does not spend the free download. Past a cap, the call is blocked. There is no overage charge.

Checkout uses `STRIPE_PRODUCT_ID`, `STRIPE_PRICE_MONTHLY`, and `STRIPE_PRICE_YEARLY`. Those objects are not created here. If any of them is unset, checkout returns 503. The trial is 14 days, a card is not required to start, and a missing payment method at the end of the trial cancels the subscription. Stripe shows the amount before anyone pays.

Files are deleted 24 hours after last use. Logs store the operation, a status code, a hash, and a size. They do not store document text. Document text is not used for training.

## Run locally

```bash
npm install
pip install 'python-docx>=1.1,<2'
cp .env.example .env
npm test
npm run test:engine
npm run dev
```

`PAGEDRILL_DEV_AUTH=1` accepts `Authorization: Bearer dev-pagedrill`. Set `PAGEDRILL_STORE=local` to use the JSON adapter in `.data/`. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, and leave `PAGEDRILL_STORE` unset, to use Supabase. Apply `supabase/schema.sql` in the SQL editor first.

The container image is `Dockerfile`. It is not deployed by this repository's tests.

## Research

`research/pagedrill-seed/` is the preserved seed archive: checklists, `sources.md`, profiles, prototype scripts, and samples. `research/pagedrill-styles-2/` is the follow-up archive, including the IEEE and Vancouver checklists and `comparison.md`. Citing Medicine Chapter 1 (NBK7282) and Chapter 2 (NBK7271) are the browser print-PDFs in `research/vanc_src/citing_medicine/`. `research/archives/` holds the archive files themselves. MLA 9 stays hidden until its checklist is fully verified.
