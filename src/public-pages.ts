const MILITARY =
  "Army memorandum formatting is an unclassified drafting aid. Pagedrill is not endorsed by the Department of Defense, does not display the DoD seal, and must not be used for classified information or controlled unclassified information.";

export function page(title: string, body: string): string {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title>
<style>body{margin:0;background:#0b1020;color:#edf1ff;font:17px/1.6 system-ui}main{max-width:760px;margin:0 auto;padding:32px 20px 64px}a{color:#b8adff}</style></head><body><main>${body}</main></body></html>`;
}

export function homePage(billingReady: boolean): string {
  return page(
    "Pagedrill by Ouroboros",
    `<p>Pagedrill by Ouroboros</p><h1>Official style, author's words.</h1>
<p>Format a .docx paper or memo to a verified style from ChatGPT, Claude, Cursor, or Grok. Every rule cites its official source. Missing affiliation, DOI, date, letterhead, and record numbers are flagged, not invented.</p>
<p>${MILITARY}</p>
<p>${billingReady ? "A 14-day trial does not require a card. Stripe shows the amount before you pay. After the trial, Pro continues only if a payment method is on file." : "Billing is not configured on this host yet. Stripe Checkout is used once STRIPE_PRODUCT_ID, STRIPE_PRICE_MONTHLY, and STRIPE_PRICE_YEARLY are set. Pagedrill does not create those objects."}</p>
<p>Without a trial or Pro subscription, check_document stays available and one fully formatted download is included each month. Pro includes 60 formatted documents and 120 previews each month, with files up to 25 MB. The same caps apply during the trial. Files are deleted 24 hours after last use. File contents are not written to logs and are not used for training.</p>
<p><a href="/privacy">Privacy</a> · <a href="/terms">Terms</a> · <a href="/support">Support</a> · <a href="mailto:ouroborosplugins@gmail.com">ouroborosplugins@gmail.com</a></p>`
  );
}

export function privacyPage(): string {
  return page(
    "Privacy",
    `<h1>Privacy</h1><p>Files are deleted 24 hours after last use. Logs store the operation name, a status code, a hash, and a size. They do not store document text. Document text is not used to train models.</p><p>${MILITARY}</p><p><a href="/">Back</a></p>`
  );
}

export function termsPage(): string {
  return page(
    "Terms",
    `<h1>Terms</h1><p>Pagedrill formats layout. It does not rewrite the author's sentences except for citation punctuation and name-list mechanics on APA papers, and the date and time forms required by AR 25-50. A style without a fully verified checklist cannot be selected.</p><p>${MILITARY}</p><p>Support: <a href="mailto:ouroborosplugins@gmail.com">ouroborosplugins@gmail.com</a></p><p><a href="/">Back</a></p>`
  );
}

export function supportPage(): string {
  return page(
    "Support",
    `<h1>Support</h1><p>Email <a href="mailto:ouroborosplugins@gmail.com">ouroborosplugins@gmail.com</a>.</p><p>${MILITARY}</p><p><a href="/">Back</a></p>`
  );
}
