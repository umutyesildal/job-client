.PHONY: setup dev test doctor migrate catalog-check

setup:
	@test -f .env || cp .env.example .env
	@test -f web/.env.local || cp .env.example web/.env.local
	docker compose up -d postgres
	@test -x .venv/bin/python || python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/python scripts/db.py migrate
	npm --prefix web ci

dev:
	docker compose up -d postgres
	npm --prefix web run dev

migrate:
	.venv/bin/python scripts/db.py migrate

doctor:
	.venv/bin/python scripts/db.py doctor

catalog-check:
	.venv/bin/python -c "import sys; sys.path.insert(0, 'job_scraper/src'); from data_controller import DataController; print(f'Valid companies: {len(DataController().load_data_from_yaml(\"catalog/companies.yaml\"))}')"

test:
	.venv/bin/python -m unittest discover -s tests -v
	npm --prefix web test
	npm --prefix web run typecheck
	npm --prefix web run build
