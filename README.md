# Pagedrill by Ouroboros

Pagedrill formats a `.docx` paper or memorandum to an official style from ChatGPT, Claude, Cursor, or Grok. The checklists in `research/pagedrill-seed/` are the spec. A rule is applied only when it traces to the cited official source.

Support: [ouroborosplugins@gmail.com](mailto:ouroborosplugins@gmail.com)

## What v1 will format

| Style | Selectable | Result on the sample |
|---|---|---|
| APA 7 student paper | yes | 28 pass, 0 fail, 5 flagged |
| APA 7 professional paper | yes | running head, author note, and abstract flagged when missing |
| Army memorandum, AR 25-50 | yes | 20 pass, 0 fail, 4 flagged |
| MLA 9, IEEE, Vancouver | no | refused until a checklist is fully verified |

Flagged on the APA student sample, by design: affiliation, course name, a single subsection, Toner's missing date, Sanchiz's missing DOI and issue, and the Toner citation without a year. Nothing in those fields is looked up or invented.

Flagged on the memorandum, by design: letterhead and DoD seal, ARIMS record number, authority line, and the postscript (held out of the layout). Branch abbreviations are not guessed.

Army copy is an unclassified drafting aid. Pagedrill is not endorsed by the Department of Defense, does not display the DoD seal, and is not for classified information or controlled unclassified information.

## Tools

`check_document` is free, rate-limited, and does not change the file. It does not count against the monthly caps. An account without a trial or Pro subscription can still check a file it already imported.

`propose_format` returns the change list, flags, and checklist. `apply_format` needs the `proposal_id` and `base_version` from that proposal. `undo` restores an earlier version, including the imported bytes. `import_file` takes a ChatGPT attachment download URL. Other clients use `start_upload` and the signed PUT link.

The author's words stay. APA may change citation punctuation and name-list mechanics. AR 25-50 may change date and time forms. Any other wording change is refused and the file is not saved. Only `word/document.xml`, `word/styles.xml`, and an existing `word/header1.xml` may change. Every other package part keeps its original bytes.

## Caps and billing

Trial and Pro both allow 60 formatted documents and 120 previews a month, and files up to 25 MB. A separate file-count cap of 120 a month limits storage. Past a cap, the call is blocked. There is no overage charge.

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

`research/pagedrill-seed/` is the preserved seed archive: checklists, `sources.md`, profiles, prototype scripts, and samples. `research/archives/pagedrill-seed.tar.gz` is the archive itself. The styles follow-up archive was not in the upload set when this branch was built, so MLA, IEEE, and Vancouver stay unselectable.
