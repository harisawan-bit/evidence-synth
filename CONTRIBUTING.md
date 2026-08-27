# Contributing to evidence-synth

Thanks for your interest in improving `evidence-synth`! This document covers
how to get set up, run the tests, and open a pull request.

## Getting started

```bash
# 1. Fork and clone
git clone https://github.com/harisawan-bit/evidence-synth.git
cd evidence-synth

# 2. Create a feature branch off master
git checkout -b feat/my-improvement master

# 3. Editable install with dev extras (pytest + ruff)
pip install -e ".[dev]"
```

> Note: the default branch is `master` (not `main`).

## Running the tests

The test suite is **fully offline and deterministic** — it uses the bundled
sample corpus and pure-logic unit tests (novelty scoring, dedup).

```bash
pytest -q
```

Run a single file if you prefer:

```bash
pytest tests/test_dedup.py -q
```

## Linting

```bash
ruff check .
```

Fix trivial issues automatically with `ruff check . --fix`. Please keep new
code lint-clean; do **not** change behavior to satisfy the linter.

## Guidelines

- **Offline-first.** New unit tests must not require network access. Mock any
  external service (e.g. PubMed) and assert on pure logic.
- **Reproducibility.** The dedup `merged` map and PRISMA flow must stay
  deterministic across runs.
- **Scope.** Keep changes focused. A PR should do one thing well.
- **Evidence quality.** This tool automates review *mechanics*; changes must
  not imply it replaces protocol registration (PROSPERO), peer review, or
  methodological judgment.

## Commit & PR conventions

- Write clear, imperative commit messages (`add ruff lint workflow`).
- Open PRs against `master`.
- Ensure CI is **green** before requesting review/merge.
- Keep PR descriptions concise: what changed, why, and how it was verified.

## Releasing

Maintainers bump the version in `pyproject.toml` and `evidence_synth/__init__.py`,
then tag `vX.Y.Z` and create a GitHub release. See the CI workflow for the
automated test/lint matrix (Python 3.9 / 3.11 / 3.12).
