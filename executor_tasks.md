# Executor Tasks

Use this file for bounded implementation slices that need durable task state.

## Project Contract

- Acceptance criteria: define a package layout for the reusable CSV/entity-resolution utility; wire a real local check command; prove at least one sample-data workflow under test.
- Failure cases: scripts still require hardcoded local paths, tenant-specific columns are not parameterized, package imports execute top-level analysis code, or `make ci` remains a placeholder.
- Evaluator inputs: synthetic CSVs in `sample_data/` and the reusable scripts under `key_scripts/`.
- Verification commands: `make ci` after replacing placeholder lint/test targets.
- Evidence paths: `CHECKPOINT.md`, `logs.md`, test output, and any generated sample reports.

## Tasks

- [x] Package bootstrap: choose the Python package shape, migrate one or two reusable scripts behind import-safe command functions, add tests using `sample_data/`, and replace the placeholder `make ci` targets with real lint/test commands.
- [x] Next generic extraction: migrate duplicate detection with configurable columns and dependency-free scoring, then cluster distribution/similarity checks with plotting/reporting separated from core analysis.
- [x] Reporting and richer scoring: add optional `rapidfuzz` scorer support, optional numeric chart outputs, and a consolidated HTML report.
- [x] Heavier optional analysis: add TF-IDF cluster similarity behind analysis extras.
- [x] Packaging hardening: add CI config that runs `make ci`.
- [x] Packaging hardening: add formatter config, lockfile/dependency strategy, and broader non-company product fixture coverage.
- [x] Legacy pattern migration: extract `key_scripts/common/data_pair_profile.py` ideas into generic stdlib pair profiling.
- [x] Packaging hardening: add typecheck strategy and make readiness scan report `ready`.
- [x] v0.2 analyst adoption: improve install/positioning docs, implement deeper typed profiling, optional multi-tab `.xlsx` report output, and a thin DataFrame API while preserving the current HTML/CSV/SVG report contract.
- [x] Skill MVP: create a local `entity-data-review` Codex skill that wraps `er-review` with command-selection, report-interpretation, threshold, and data-safety guidance.
- [x] v0.3 large-dataset/performance: add chunked row sources, streaming-friendly aggregators, duplicate block guardrails, output caps, and a benchmark harness before advertising million-row workflows.
- [x] v0.3 candidate: add Excel/Parquet input support, expanded DataFrame API, richer lookup joins, broader PII redaction coverage, larger examples/notebooks, workbook polish, and optional advanced reporting.

## v0.2 Analyst Adoption Contract

- Acceptance criteria: `er-review profile` exposes richer typed column metrics; `er-review report` can emit a multi-tab workbook; README shows install-first `er-review` workflows and honest review/QA positioning; a thin Python API supports notebook use for the main checks; existing HTML/CSV/SVG outputs and exit-code behavior remain compatible; `make ci` passes.
- Failure cases: users still need `PYTHONPATH=src`; README implies a full entity-resolution engine; workbook dependencies become mandatory for core installs; profiling silently coerces data without reporting parse quality; API wrappers duplicate or drift from core logic; optional workbook tests fail when extras are absent; generated workbooks expose more raw data than the requested report sections.
- Evaluator inputs: `sample_data/details.csv`, `sample_data/products.csv`, a fixture with numeric/date/currency/categorical edge cases, and existing report smoke commands.
- Verification commands: `make ci`; `er-review profile ...`; `er-review report ... --workbook-out ...` with cleanup afterward.
- Evidence paths: `context/V0_2_ANALYST_ADOPTION_PLAN.md`, `CHECKPOINT.md`, `logs.md`, tests, and any intentionally retained sample report artifacts.

## Completed v0.2 Evidence

- Package files: `src/er_reviewer/profiling/columns.py`, `src/er_reviewer/reporting/workbook.py`, `src/er_reviewer/api.py`, `src/er_reviewer/checks/lookup.py`, `src/er_reviewer/reporting/redaction.py`, `src/er_reviewer/cli.py`.
- Tests: `tests/test_analyst_adoption.py`, `tests/test_workbook.py`.
- Skill files: `/Users/arthurlee/.codex/skills/entity-data-review/SKILL.md` and references.
- Verification: `make ci` passed with 32 tests passed and 3 optional-dependency skips; `uv run --extra reports --extra dev pytest -q -p no:cacheprovider tests/test_workbook.py tests/test_analyst_adoption.py` passed with 10 tests passed and 1 optional pandas skip.

## Analyst Adoption Roadmap

- Source of truth: `context/ANALYST_ADOPTION_PLAN_AND_BACKLOG.md`.
- Package principle: `er-review` remains the analysis engine.
- Skill principle: `entity-data-review` should guide workflow and
  interpretation, not reimplement analysis or store datasets.
- Performance principle: v0.2 is correctness-first; v0.3 must add streaming,
  caps, and duplicate guardrails before positioning this as large-data ready.

## Completed v0.3 Evidence

- Performance files: `src/er_reviewer/_csv_utils.py`,
  `src/er_reviewer/io/csv_hygiene.py`, `src/er_reviewer/profiling/columns.py`,
  `src/er_reviewer/profiling/pairs.py`, `src/er_reviewer/checks/duplicates.py`,
  `src/er_reviewer/checks/cardinality.py`, `src/er_reviewer/checks/clusters.py`,
  and `src/er_reviewer/compare/exports.py`.
- Input/API/reporting files: `src/er_reviewer/io/table.py`,
  `src/er_reviewer/api.py`, `src/er_reviewer/cli.py`,
  `src/er_reviewer/reporting/html_report.py`,
  `src/er_reviewer/reporting/workbook.py`,
  `src/er_reviewer/reporting/charts.py`, and
  `src/er_reviewer/reporting/pdf_report.py`.
- Documentation and examples: `docs/performance.md`,
  `scripts/benchmark_large_data.py`, `examples/analyst_walkthrough.ipynb`,
  `README.md`, and `context/ANALYST_ADOPTION_PLAN_AND_BACKLOG.md`.
- Skill files: `/Users/arthurlee/.codex/skills/entity-data-review/SKILL.md`,
  `/Users/arthurlee/.codex/skills/entity-data-review/references/workflow.md`,
  and `/Users/arthurlee/.codex/skills/entity-data-review/agents/openai.yaml`.
- Verification: `make ci` passed with 56 tests passed and 7 optional-dependency
  skips; `uv run --extra analysis --extra reports --extra tables --extra dev
  pytest -q -p no:cacheprovider` passed with 63 tests passed; small synthetic
  benchmark smoke ran at 1,000 rows with profile/clusters/mappings all exiting
  0 and peak child RSS about 28 MB.
- Known limits retained in docs: profile exact typed stats still keep
  per-column values, compare keeps membership sets in memory, Excel/Parquet
  input is pandas-backed convenience, and true columnar backend support remains
  future DuckDB/Polars/Arrow work.
