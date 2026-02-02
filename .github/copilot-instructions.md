# Copilot / AI Agent Instructions for fastapi-blog ✅

Purpose: Help an AI or human contributor get immediately productive in this small FastAPI tutorial repo by describing the minimal, discoverable architecture and the concrete, repeatable workflows used here.

## Quick repo facts 📌
- Project root files: `main.py`, `pyproject.toml`, `README.md` (empty).
- Python requirement: `>=3.12` (see `pyproject.toml`).
- Dependency: `fastapi[standard]>=0.128.0` (declared in `pyproject.toml`).
- Current app entrypoint: `main.py` defines `app = FastAPI()` at module level.

## Big picture / architecture 🔧
- This is a minimal tutorial-style FastAPI app: a single module exposes an ASGI `app` object.
- The module-level `app` variable name is important: tools and servers expect `module:app` (e.g., `uvicorn main:app`).
- There are currently no routers, models, or DB code; expect features to be added incrementally (routers, services, tests).

## Where to add code and patterns to follow 🛠
- New HTTP endpoints: either add to `main.py` for tiny examples or create a `routers/` package and register via `app.include_router(...)` for feature separation.
- If adding a database or business layer, create top-level packages like `db/`, `models/`, `services/` and import them from `main.py` (keep `main.py` responsible for wiring, not detailed logic).
- Keep `app` as the ASGI entrypoint (module-level `app` variable). Example: `# main.py\nfrom fastapi import FastAPI\napp = FastAPI()`

## Running, debugging & local dev ▶️
- Install the project into a venv: `python -m venv .venv` then Windows activate: `.\.venv\Scripts\activate` and `python -m pip install -e .`
- Run dev server: `python -m uvicorn main:app --reload --port 8000` (if `uvicorn` is not present, install via `pip install "uvicorn[standard]"`).
- Debugging: use an IDE (VS Code) attach configuration that points at `main:app` or run `uvicorn` with `--reload` and use breakpoints.

## Tests & CI 🔁
- There are no tests now. When adding tests, place them under `tests/` and use `pytest` (standard convention). Example command: `pytest -q`.
- For GitHub Actions CI, run `pip install -e .` then `pytest` and optionally `ruff`/`black` for lint/format.

## Packaging & dependencies 📦
- `pyproject.toml` declares runtime deps. Edit dependency versions there (no lockfile included).

## Conventions & caveats ⚠️
- Minimal project: prefer explicit, small changes over heavyweight scaffolding.
- Keep `main.py` simple and use routers/services for complexity.
- Avoid assumptions about testing/linting tools — add config files and dev deps when you introduce them.

## Example tasks you can ask the agent to do (concrete prompts) 💡
- "Add a `routers/posts.py` router with CRUD endpoints and include it in `main.py` under the prefix `/posts`."
- "Add `pytest` and a sample test `tests/test_root.py` that verifies a GET `/` endpoint returns 200." 
- "Add GitHub Action workflow `ci.yml` that installs deps and runs `pytest`."

## Files to consult 🔍
- `main.py` — entrypoint exposing ASGI `app`
- `pyproject.toml` — Python version + declared dependencies

---

If anything here is unclear or you want me to expand a section (for example, add a recommended `tests/` layout or CI sample), tell me which part and I will update this file.