.PHONY: bootstrap backend frontend test-backend test-frontend demo verify

# --- S-01 run commands (see tasks.md §1.3) ---
# Dependency installation needs the package registries ONCE at bootstrap.
# After that every target below works with networking disabled.

bootstrap:  ## create python venv, install backend deps, npm ci in frontend/
	python3 -m venv backend/.venv
	backend/.venv/bin/pip install --upgrade pip
	backend/.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm ci

backend:  ## uvicorn app.main:app --reload --port 8000 (cwd: backend)
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:  ## npm run dev -- --port 5173 (cwd: frontend)
	cd frontend && npm run dev -- --port 5173

test-backend:  ## pytest -q (cwd: backend)
	cd backend && .venv/bin/python -m pytest -q

test-frontend:  ## npm test -- --run (cwd: frontend)
	cd frontend && npm test -- --run

demo:  ## python -m app.demo --print (cwd: backend, offline E2E in terminal)
	cd backend && .venv/bin/python -m app.demo --print

verify:  ## ruff + pytest + typecheck + lint + test + build
	cd backend && .venv/bin/ruff check app tests
	$(MAKE) test-backend
	cd frontend && npm run typecheck
	cd frontend && npm run lint
	$(MAKE) test-frontend
	cd frontend && npm run build
