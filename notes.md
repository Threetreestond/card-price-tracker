# database.py notes
duplicate deck names allowed (deliberate)
N+1 in two functions (Phase 3)
cascade delete pending (schema migration later)

# 19/04/2026 Todo:
1. Baseline tasks for today
Task A: Finish type-hinting database.py and context_manager.py.
Concrete output: every function signature annotated, python -m mypy src/database.py src/context_manager.py runs with zero errors.

Task B: Fix whatever mypy finds.
Concrete output: a clean mypy run, or a documented list in notes.md of any errors you're deliberately ignoring and why.

Task C: Write tests for get_prices and get_latest_price.
Concrete output: at least 4 new passing tests covering no-filter, single-filter, date-range, and the "no results" case. Run python -m pytest src/test_database.py -v with all tests green.

Task D: Commit everything.
Concrete output: a single clean commit with a message like "refactor: database.py context manager, type hints, tests". Your GitHub should reflect today's work by end of day.


2. Stretch tasks
Stretch A: Add type hints to models.py. This forces you to confront the broken callers — every method in Deck needs conn now. You don't have to fix them today, but annotating them will surface every break point clearly.

Stretch B: Configure Ruff. pip install ruff, add a [tool.ruff] section to pyproject.toml (or create one), run ruff check src/. Fix whatever it flags. This is 15 minutes of work that pays off permanently — Ruff catches style issues on every future commit.

Stretch C: Replace os.path / os.makedirs with pathlib in context_manager.py. You discussed this during the session but left os.path.dirname in place. Small change, checks a Phase 1 box.


# For Phase 2

1. The progression I described regarding dashboard refresh (manual now → Fabric lakehouse → automated pipelines → agentic mapping resolution) maps directly onto Phases 2-4 of the roadmap.