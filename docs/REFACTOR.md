# Daily Berlin Jobs refactor record

## Decisions

- Product name: **Daily Berlin Jobs**.
- Current scope: Berlin tech-engineering jobs only; physical engineering disciplines are excluded.
- LinkedIn queries: Engineer-based searches across the included tech disciplines; generic Developer and unbounded Engineer searches are excluded.
- Classification: performed for each incoming job during publishing, not by a
  one-off raw-file analysis step.
- Source of truth: normalized PostgreSQL rows produced by Python. Supabase is
  the hosted provider; the contract remains portable PostgreSQL.
- Public UI: `All Jobs` and `New Today`, with search plus engineering area,
  level, and work-style filters.
- Legacy UI: frozen until Next.js parity is confirmed, then retired.

## Implementation sequence

1. Create `codex/daily-berlin-jobs-refactor` without dropping existing local
   changes.
2. Add the versioned engineering taxonomy and normalized public columns.
3. Remove duplicate classification rules from Next.js.
4. Simplify the public controls and job-row metadata.
5. Enforce the data contract in tests and the GitHub Actions verification step.
6. Run the pipeline without uploads, audit the generated output, and run the
   Python and Next.js checks.
7. Run the real GitHub Actions publisher before promoting the web deployment.
8. Retire the legacy UI only after public and admin parity checks pass.

## Guardrails

- Do not broaden into mechanical, electrical, civil, manufacturing, energy, or field/service engineering.
- Keep LinkedIn queries aligned with the included tech-engineering areas.
- Do not expose personal-fit data in the public UI.
- Do not run the crawler inside Vercel.
- Do not treat a workflow as successful when classification columns are absent.

## Local validation record

- The full dry-run processed 57,262 incoming rows without uploading data.
- The initial `engineering-v1` rules published 458 Berlin tech-engineering rows.
- The final `engineering-v2` dry-run processed 57,262 incoming rows and
  published 467 tech-engineering rows.
- `engineering-v2` added 11 embedded/firmware/robotics rows while publishing
  zero mechanical, electrical, civil, manufacturing, or field/service rows.
- All 467 `engineering-v2` rows had a non-empty role and the expected
  classification version.
- Sample review caught and removed two false positives: a founder-associate
  title mentioning a CTO office and a content role mentioning frontend.
- Python: 21 unit tests passed.
- Next.js: typecheck and production build passed.
- Desktop and 390 px mobile layouts were inspected; the mobile page had no
  horizontal overflow and the filters collapsed correctly.
- Browser inspection exposed a hydration-order mismatch caused by
  locale/runtime-dependent text and date sorting. The public list now uses
  deterministic text comparison and explicit date parsing.

The original Sheets rollout record above is historical. The current migration
and rollback procedure lives in `docs/DATABASE.md`.
