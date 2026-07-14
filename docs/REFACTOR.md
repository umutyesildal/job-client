# Daily Berlin Jobs refactor record

## Decisions

- Product name: **Daily Berlin Jobs**.
- Current scope: Berlin engineering jobs only.
- LinkedIn queries: unchanged and engineering-focused.
- Classification: performed for each incoming job during publishing, not by a
  one-off raw-file analysis step.
- Source of truth: normalized Google Sheets rows produced by Python.
- Public UI: `All Jobs` and `New Today`, with search plus engineering area,
  level, and work-style filters.
- Legacy UI: frozen until Next.js parity is confirmed, then retired.

## Implementation sequence

1. Create `codex/daily-berlin-jobs-refactor` without dropping existing local
   changes.
2. Add the versioned engineering taxonomy and normalized Sheets columns.
3. Remove duplicate classification rules from Next.js.
4. Simplify the public controls and job-row metadata.
5. Enforce the data contract in tests and the GitHub Actions verification step.
6. Run the pipeline without uploads, audit the generated output, and run the
   Python and Next.js checks.
7. Run the real GitHub Actions publisher before promoting the web deployment.
8. Retire the legacy UI only after public and admin parity checks pass.

## Guardrails

- Do not broaden beyond engineering in this refactor.
- Do not change the default LinkedIn query list.
- Do not expose personal-fit data in the public UI.
- Do not run the crawler inside Vercel.
- Do not treat a workflow as successful when classification columns are absent.

## Local validation record

- The full dry-run processed 57,262 incoming rows without uploading data.
- The tightened `engineering-v1` rules published 458 Berlin engineering rows.
- All 458 published rows had a non-empty role and the expected classification
  version.
- Sample review caught and removed two false positives: a founder-associate
  title mentioning a CTO office and a content role mentioning frontend.
- Python: 18 unit tests passed.
- Next.js: typecheck and production build passed.
- Desktop and 390 px mobile layouts were inspected; the mobile page had no
  horizontal overflow and the filters collapsed correctly.
- Browser inspection exposed a hydration-order mismatch caused by
  locale/runtime-dependent text and date sorting. The public list now uses
  deterministic text comparison and explicit date parsing.

The currently published worksheets predate `engineering-v1`. Run the branch
workflow once before promoting the matching web build so filter options are
populated from normalized Sheets columns.
