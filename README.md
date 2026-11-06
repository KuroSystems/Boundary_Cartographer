# Boundary_Cartographer

Maps an AI agent's identities, tools, and data scopes, then proves with a deterministic policy gate outside the model when individually permitted tools chain into an unauthorized data flow. Offline MVP: seeded prompt-injection replay, least-privilege fix, human approval queue — no real exports.

## Offline rule

Dependency installation needs the package registries **once** at bootstrap. After `make bootstrap` completes, `make backend`, `make frontend`, `make demo`, `make test-backend`, `make test-frontend`, and `make verify` all work **with networking disabled**. The demo itself is fully offline: mock tools run in-process, no sockets, no hosted models on the authorization path.

## Run commands (task S-01)

```
make bootstrap           # python venv + pip install -r backend/requirements.txt; npm ci in frontend/
make backend             # uvicorn app.main:app --reload --port 8000  (cwd: backend)
make frontend            # npm run dev -- --port 5173                 (cwd: frontend)
make test-backend        # pytest -q                                  (cwd: backend)
make test-frontend       # npm test -- --run                          (cwd: frontend)
make demo                # python -m app.demo --print                 (cwd: backend, offline E2E in terminal)
make verify              # ruff + pytest + npm run typecheck + lint + test + build
```

The frontend dev server proxies `/api/*` to the backend on `http://localhost:8000`.

## Toolchain and installed versions (verified 2026-11-06)

- Python **3.11.2**, Node **v22.22.3**, npm **10.9.8**

Backend (`backend/.venv`, from `backend/requirements.txt`):

| package | installed |
| --- | --- |
| fastapi | 0.162.0 |
| uvicorn | 0.54.0 |
| pydantic | 2.14.3 |
| networkx | 3.6.1 |
| langgraph | 1.2.20 |
| PyYAML | 6.0.3 |
| pytest | 9.2.0 |
| httpx | 0.28.1 |
| ruff | 0.17.4 |

Frontend (`frontend/`, from `package-lock.json`):

| package | installed |
| --- | --- |
| react / react-dom | 18.3.1 |
| react-router-dom | 6.30.6 |
| @tanstack/react-query | 5.106.1 |
| @xyflow/react | 12.12.1 |
| zod | 3.25.76 |
| vite | 5.4.21 |
| vitest | 2.1.9 |
| typescript | 5.9.3 |
| eslint (+ eslint-plugin-react 7.37.5, `react/no-danger` enforced) | 8.57.1 |
| msw | 2.15.0 |
| openapi-typescript | 7.13.0 |
| @testing-library/react | 16.3.3 |
| @testing-library/jest-dom | 6.9.1 |
| jsdom | 25.0.1 |
| @vitejs/plugin-react | 4.7.0 |

## Layout

```
/README.md                    this file (run commands, offline rule, demo script)
/Makefile                     make bootstrap | backend | frontend | test | demo | verify
/backend/app/…                FastAPI app (placeholder /api/v1/health for now)
/backend/tests/…              pytest suite (placeholder smoke test)
/frontend/src/…               React 18 + TS + Vite app (placeholder page)
/tasks.md                     MVP task plan
```
