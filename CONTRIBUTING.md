# Contributing to Daily Berlin Jobs

Thanks for helping make Berlin tech jobs easier to discover. Contributions of
code, tests, documentation, accessibility improvements, scraper fixes, and
careful taxonomy proposals are welcome.

## Start locally without credentials

The public board has a committed sample-data mode so contributors never need
access to the production spreadsheet or service account.

```bash
cp .env.example web/.env.local
cd web
npm ci
npm run dev
```

Keep `USE_SAMPLE_DATA=true`. Open `http://localhost:3000`.

For Python changes:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## Project boundaries

- The public scope is Berlin tech engineering. Physical engineering fields are
  intentionally excluded.
- Python is the only classification authority. Do not add competing taxonomy
  regexes to the web application.
- The crawler does not run inside Vercel.
- Production credentials, tokens, private keys, raw exports, and local `.env`
  files must never be committed.
- Do not run or modify the production publishing workflow as part of a pull
  request. Maintainers perform live rollout verification after review.

Read `docs/ARCHITECTURE.md` before changing the data contract and
`docs/REFACTOR.md` before changing the migration boundary.

## Good first contributions

- accessibility and keyboard-navigation improvements;
- documentation and setup fixes;
- focused scraper test coverage;
- UI improvements that preserve the scan-first product shape;
- false-positive or false-negative taxonomy fixtures with evidence;
- German and English copy improvements.

## Pull requests

1. Create a focused branch from `main`.
2. Keep the change small enough to review.
3. Add or update tests for behavior changes.
4. Run the relevant Python and web checks.
5. Explain the user-facing effect and any data-contract impact in the PR.

Taxonomy changes must include positive and negative fixtures, increment the
classification version when the public boundary changes, and document the
expected migration. A green CI run does not authorize a production Sheets
write.

By contributing, you agree that your contribution is licensed under the MIT
License included in this repository.
