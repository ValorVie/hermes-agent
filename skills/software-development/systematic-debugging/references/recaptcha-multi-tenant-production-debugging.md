# reCAPTCHA multi-tenant production debugging

Use this when a customer reports CAPTCHA failures on a specific tenant/domain in a shared PHP/OpenCart-style codebase.

## Pitfall

Do not reproduce only on a staging/demo tenant. In QDM, `rockstore.qdm.tw` was on a test ingress and already served newer keys, while the affected production domains (`correcta.tw`, `point.tw`) still served the old key. Testing the wrong tenant produced a false negative.

## Minimal evidence sequence

1. Normalize the exact reported hostnames:
   - Check bare domain redirect, `www` canonical URL, final URL, status code.
   - Record IP/ingress differences between affected domains and any control host.
2. Fetch the exact affected registration route, not a similar staging route:
   - `/register`
   - `/account/register`
3. Extract active reCAPTCHA configuration from returned HTML:
   - `data-sitekey="..."` for v2 checkbox.
   - `api.js?render=...` for v3 score.
   - `enterprise.js` vs `api.js` matters.
4. Compare affected domains to a known control page.
5. Probe the widget/key layer before debugging form validation:
   - Prefer a real browser whenever available. Inspect the actual `.g-recaptcha` element, the browser-created reCAPTCHA iframes, and the visible widget text.
   - Treat hand-built Google `api2/anchor` URLs as diagnostic only. They can produce false `Invalid site key` results when their parameters do not exactly match the browser-generated request.
   - If you must compare anchor calls, first capture the real iframe `src` from the loaded page and compare against that. Do not make the final conclusion from a manually assembled URL.
   - Record widget-side errors exactly, including quota/billing messages such as `這個網站已超出 reCAPTCHA Enterprise 免費配額。`, domain errors, or invalid-key errors.
   - A confirmed browser-visible `Invalid site key` or absent token source means the user cannot produce a valid `g-recaptcha-response`; an over-quota widget points to Google project quota/billing rather than a malformed page key.
6. Then trace backend failure mapping:
   - Missing `g-recaptcha-response` or failed `siteverify` often maps to the same user-facing language string.
   - Confirm the language string path so the reported message is tied to code.
7. Inspect the backend verifier for secret/key mismatch:
   - Frontend site key and backend secret must be paired.
   - Watch for dead variables, such as setting `$secretKey` but sending a literal placeholder in the `siteverify` URL.

## Durable findings from the QDM case

- A production tenant can serve a different reCAPTCHA key than staging even when code repos appear similar.
- Static HTML can prove which key the page attempts to use, but browser/widget probing is needed to prove whether Google accepts it.
- A hand-built Google anchor URL can misclassify a still-rendering key as `Invalid site key`; final widget-layer evidence must come from the real loaded page or its actual iframe `src`.
- `Invalid site key` at the widget layer means the user cannot produce a valid token; backend form errors are downstream symptoms.
- A visible over-quota / billing message means the next investigation target is Google project quota/billing and the deployed verifier response, not merely key-domain validity.
- If a backend uses `siteverify?secret=***`, fixing the frontend site key alone is insufficient.

## Post-rotation verification pitfall

When a stakeholder says only one tenant has been updated or only one tenant should be tested, narrow the probe to that exact tenant. Do not use still-unrotated production tenants as evidence for the rotated state.

For QDM-style shared storefronts, treat these as separate questions:

1. **Key / quota state** — Which site key is active on the exact tenant page, and does the widget show quota or key-domain errors?
2. **Registration validation failure** — Did the submitted form include `g-recaptcha-response`, and what did backend `siteverify` return?

A visible over-quota widget can coexist with unrelated registration failures. Do not tell merchants that quota is the cause of registration failure unless a failed submission is tied to backend `siteverify` evidence.

Minimal post-rotation checks:

- Fetch the exact updated tenant, e.g. `https://rockstore.qdm.tw/register`, and record final URL / redirect count.
- Extract `data-sitekey` and compare by fingerprint or equality to the expected deployed key without leaking the raw key.
- Confirm initial HTML does not already contain the user-facing captcha error.
- If safe, submit a probe without `g-recaptcha-response` to confirm the backend maps missing token to the same language string. This reproduces the error class without creating an account.
- To find root cause for real failures, add temporary safe logging around backend `siteverify`: token present yes/no, token length, HTTP status, `success`, `error-codes`, `hostname`, request host, and redacted/hashed client metadata. Never log the full token, secret, full IP, or personal data.

## Reporting format

Separate:

- **已確認**：exact host, redirect/final URL, active keys or key fingerprints, Google widget response, backend error string mapping.
- **推論**：why the user sees the error.
- **待確認**：actual deployed backend revision, actual secret source, whether the exact tenant under test has already rotated keys, and actual `siteverify` result for a failing submission.
