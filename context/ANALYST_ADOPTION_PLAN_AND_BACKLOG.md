# Analyst Adoption Plan and Backlog

Date: 2026-05-19

## Purpose

Turn `entity_data_utility_pack` into a practical analyst-facing utility for
dataset review and entity-resolution QA, with two complementary surfaces:

- `er-review`: the reusable Python package and CLI engine.
- `entity-data-review`: a local Codex skill that guides agents through review
  workflow, command selection, interpretation, and analyst summaries.

The package does the work. The skill teaches agents how to use the package
safely and consistently.

## Current State

Implemented package surface:

- CSV hygiene checks with explicit encoding and delimiter flags.
- Column profiling and pair profiling.
- Richer typed profiling for numeric, date, currency, and categorical fields.
- One-to-many mapping checks.
- Export membership comparison with optional split/merge/reassignment narrative
  rows.
- Blocked duplicate candidate detection with configurable normalization.
- Cluster summaries with outlier score/reason fields.
- Token and optional TF-IDF similarity with verdict bands and recommendations.
- Single-entity lookup with optional cluster siblings.
- Consolidated HTML report with section CSVs and SVG cluster-size chart.
- Optional multi-tab `.xlsx` workbook report.
- JSON/TOML report recipes.
- Report/lookup redaction.
- Thin pandas-facing API wrappers.
- `make ci` gate with formatter, lint, typecheck, and tests.

Implemented skill surface:

- Local skill at `/Users/arthurlee/.codex/skills/entity-data-review/`.
- `SKILL.md` plus references for workflow, report interpretation, and
  thresholds.
- No datasets or legacy scripts bundled into the skill.

Remaining adoption gaps:

- Current implementation is correctness-first, not large-data optimized.
  Practical sweet spot is roughly 100k-250k rows by about 50 columns on a
  workstation; larger files need guardrails and streaming/chunked paths.
- Excel/Parquet input remains future work.
- Warehouse-source input remains future work.
- Larger worked examples and notebook walkthroughs remain future work.
- Workbook formatting can be improved for business-user polish.
- Interactive report filtering/search remains future work.

## Product Positioning

Describe the tool as **entity and dataset review**.

Do not position it as:

- A full entity-resolution engine.
- A record-linkage platform.
- An automatic merge/survivorship decision system.
- A replacement for human review of duplicate or cluster candidates.

Best wedge:

- "Run repeatable QA on tabular exports: profile fields, catch hygiene issues,
  flag mapping conflicts, find duplicate candidates, compare exports, and
  produce a shareable analyst report."

## Phase 1: v0.2 Package Adoption Slice

Status: implemented on 2026-05-19.

Delivered:

- [x] README install-first quickstart using `er-review`.
- [x] Clear README positioning: review/QA utility, not full ER automation.
- [x] `er-review --version`.
- [x] Richer typed profiling:
  - inferred type
  - numeric parse rate
  - datetime parse rate
  - min/max
  - selected quantiles
  - currency-like detection
  - categorical/top-value summary
  - capped invalid parse examples
- [x] Optional multi-tab `.xlsx` workbook output from `er-review report`.
- [x] Thin DataFrame API for notebook use:
  - `profile(...)`
  - `find_duplicates(...)`
  - `mapping_conflicts(...)`
  - `compare_exports(...)`
  - `cluster_summary(...)`
- [x] Tests for richer profiling, workbook generation when optional
  dependencies are available, and API wrappers.
- [x] `lookup` CLI for single-entity plus cluster-sibling review.
- [x] Report and lookup redaction.
- [x] Optional compare narrative rows for member reassignments, splits, and
  merges.
- [x] Similarity verdict bands and recommendations.
- [x] Duplicate normalization profile.
- [x] Cluster outlier score/reason fields.
- [x] JSON/TOML report config recipes.

Final acceptance:

- `make ci` passed on 2026-05-19: 32 tests passed and 3 optional-dependency
  skips.
- Optional reports-extra path passed on 2026-05-19:
  `tests/test_workbook.py tests/test_analyst_adoption.py` reported 10 passed
  and 1 optional pandas skip.

## Phase 2: Codex Skill MVP

Status: implemented locally on 2026-05-19.

Path:

```text
/Users/arthurlee/.codex/skills/entity-data-review/
├── SKILL.md
└── references/
    ├── workflow.md
    ├── report_interpretation.md
    └── thresholds.md
```

Delivered:

- [x] Natural-language trigger and negative trigger.
- [x] Command decision tree.
- [x] Install/version precedence.
- [x] Analyst summary contract.
- [x] Data-locality and PII guardrails.
- [x] Workflow, interpretation, and threshold references.
- [x] No shell wrapper; the MVP did not need one.

Remaining skill work:

- Validate against realistic prompts.
- Add `agents/openai.yaml` metadata only if the skill should appear in UI skill
  lists.

## Phase 3: v0.3 Product Expansion

Remaining candidate deliverables:

- Large-dataset/performance slice:
  - chunked row source abstraction
  - streaming-friendly aggregators
  - duplicate block guardrails
  - output row caps
  - manual benchmark harness
- Excel and Parquet input support behind optional dependencies.
- Expanded DataFrame API beyond the thin wrappers.
- Single-entity lookup expansion:
  - mapping conflicts
  - duplicate candidates
  - export membership changes
- Broader PII redaction/masking coverage if future subcommands add new output
  surfaces.
- Larger worked example fixture and notebook walkthrough.
- Workbook polish:
  - frozen header rows
  - column widths
  - filters
  - summary formulas
  - issue-priority tabs
- Match-score distribution charts.
- Optional PDF export if stakeholders need static handoff artifacts.
- Interactive HTML report enhancements only if workbook output is insufficient.

## Backlog

### P0: Skill Validation

- Status: implemented on 2026-05-19.
- Validated the skill against three realistic prompts:
  - "Review this customer export for data quality."
  - "Find likely duplicates in this file."
  - "Compare these two exports and summarize what changed."
- Added notebook/API routing guidance after validation exposed that gap.
- Added local `agents/openai.yaml` metadata because the skill has stable
  implicit-invocation triggers.

### P0: v0.3 Large-Dataset / Performance Slice

Status: implemented as a pragmatic v0.3 baseline on 2026-05-19. The package now
has streaming CSV row sources, streaming-friendly CSV wrappers for the main
aggregate checks, duplicate block guardrails, fingerprint-based identical-column
detection, report output caps, benchmark docs, and a synthetic benchmark
harness. It is not yet a columnar/DuckDB/Polars engine.

Target envelope:

- 500k-5M rows.
- 50-200 columns.
- Duplicate blocks up to about 50k rows when guarded/sampled.
- Runnable on a 16 GB laptop without swapping.

Current limits to address:

- Done: `_csv_utils.py` has lazy row-source helpers:
  `open_dict_row_source`, `iter_dict_rows`, `chunked_rows`, and
  `iter_dict_row_chunks`.
- Done: `io/csv_hygiene.py` scans NUL bytes and parses CSV structure without
  holding raw bytes, decoded text, and all parsed rows at once.
- Done: `checks/duplicates.py` has opt-in `max_block_size`,
  `oversized_block_behavior`, deterministic sampling, pair sampling, and
  `workers`.
- Done: `profiling/pairs.py` identical-column detection uses per-column SHA-256
  fingerprints.
- Done: `reporting/html_report.py` and `reporting/workbook.py` have row caps;
  CLI report exposes `--max-output-rows`.
- Done: `api.py` has an `engine=` placeholder and path-based profiling.
- Remaining scale caveat: `profile_columns` still stores per-column values for
  exact typed stats/quantiles, compare still keeps membership sets in memory,
  and Excel/Parquet input is convenience-oriented rather than streaming.

Implementation order:

1. Done: Add a chunked row-source abstraction in `_csv_utils.py`, such as
   `iter_dict_rows(...)` / `read_dict_rows_chunked(...)`. Keep
   `read_dict_rows()` as the compatibility wrapper.
2. Done: Migrate streaming-friendly aggregators to chunked input:
   `profiling/columns.py`, `checks/clusters.py`, `checks/cardinality.py`, and
   `compare/exports.py`.
3. Done: Replace identical-column detection in `profiling/pairs.py` with per-column
   fingerprints instead of pairwise full-list comparisons.
4. Done: Add duplicate guardrails in `checks/duplicates.py` and `cli.py`:
   `--max-block-size`, `--sample-rate`, and clear fail/warn behavior when a
   blocking key is too broad.
5. Done: Add `--workers` for duplicate block scoring after the block-size contract is
   settled.
6. Done: Add `--max-output-rows` where it prevents
   runaway report/profile/detail output.
7. Done: Add a benchmark harness and `docs/performance.md` covering synthetic
   runs with wall time and peak RSS.
8. Done: Add manual large-data benchmark entrypoint:
   `scripts/benchmark_large_data.py`.
9. Done: Add an `engine=` API placeholder for future DuckDB/Polars/Arrow support, but
   defer actual backend wiring until after the streaming/guardrail work lands.

Non-goals for this slice:

- Do not add automatic encoding detection.
- Do not make optional dependencies mandatory.
- Do not implement Excel/Parquet input in the same slice.
- Do not rewrite everything around Spark/Dask.
- Do not emit uncapped million-row HTML or workbook outputs.

### P1: v0.3 Input and Repeatability

- Done: Add Excel/Parquet input support behind optional `tables`
  dependencies.
- Add richer config schema validation and examples.
- Add warehouse-source input only after file-based adoption is stable.

### P2: Analyst Experience

- Done: Add notebook walkthrough in `examples/analyst_walkthrough.ipynb`.
- Done: Improve workbook formatting with freeze panes, filters, capped summary
  metadata, and safer sheet names.
- Future: Add richer single-entity lookup joins.
- Future: Add larger persisted demo fixture; current large fixture is generated
  by the benchmark harness to avoid committing bulky files.
- Add interactive HTML only if the static workbook path is insufficient.

### P2: Advanced ER Review

- Done: Add match-score distribution charts.
- Done: Add optional PDF export if stakeholders need static handoff artifacts.
- Expand cluster outlier scoring beyond size/average-score heuristics.

## Decision Log

- Keep `er_reviewer` / `er-review` naming for now.
- Build package capabilities before skill workflow where possible.
- Keep the skill as a thin local playbook, not a second implementation.
- Treat workbook output as the most important analyst adoption artifact.
- Treat report interpretation and thresholds as the highest-value skill
  references.
- Keep optional dependencies lazy-loaded and non-mandatory for `make ci`.
