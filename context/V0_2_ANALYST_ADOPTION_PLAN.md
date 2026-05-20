# v0.2 Analyst Adoption Plan

Date: 2026-05-19

Status: implemented on 2026-05-19. See
`context/ANALYST_ADOPTION_PLAN_AND_BACKLOG.md`, `CHECKPOINT.md`, and
`logs.md` for closeout evidence.

## Goal

Make `er-review` useful to financial analysts, data analysts, and
Python-capable business analysts who need quick, repeatable reviews of real
datasets, not only entity-resolution QA exports.

The v0.1 package already has useful ER review primitives: hygiene checks,
column profiling, one-to-many mapping checks, export comparison, duplicate
candidates, cluster summaries, token/TF-IDF similarity, and consolidated HTML
reporting. The adoption gap is that analyst workflows commonly start in Excel,
Parquet, notebooks, or warehouse extracts, and they need a shareable workbook
with richer profiling.

## Product Decision

Prioritize "installable analyst workflow + deeper profiling + multi-tab Excel
workbook report" for v0.2.

This is the lowest-schema-assumption slice: it improves value for any tabular
dataset while preserving the ER-specific commands already implemented. Defer
warehouse connectors, single-entity lookup, and richer entity-drift narratives
until after the tool has a stronger analyst-facing artifact.

Implementation note: the 2026-05-19 execution pulled a few originally deferred
items forward because they were low-churn once the CLI/report surface was open:
single-entity lookup, optional drift narrative rows, report redaction,
similarity verdict bands, duplicate normalization, cluster outlier flags, and
JSON/TOML report recipes.

Claude's review correctly identified the workbook artifact as the fastest path
to analyst adoption. My added constraint is that v0.2 should also remove the
"prototype CLI" feel: the install path, package positioning, and a minimal
DataFrame API need to be visible enough that Python-capable analysts can use the
library from notebooks without waiting for a later major slice.

## Positioning

Keep the package/module name as `er_reviewer` and the CLI as `er-review` for
now, but describe the tool as "entity and dataset review" rather than a full
entity-resolution engine. The repo should not promise automatic matching,
survivorship, or merge decisions. Its strongest wedge is repeatable review:
profile a dataset, flag mapping conflicts, find duplicate candidates, compare
exports, and produce a shareable report.

## Target Users

- Financial analysts reviewing customer, account, product, transaction, or
  vendor extracts.
- Data analysts doing first-pass QA before loading a dataset into pandas,
  notebooks, dashboards, or a warehouse.
- Python-capable business analysts who can run a CLI but expect Excel-friendly
  outputs.
- ER QA reviewers who need a handoff artifact for mapping conflicts,
  duplicates, cluster summaries, and export-to-export drift.

## Acceptance Criteria

- README has an install-first quickstart using the package entrypoint:
  `er-review`, not only `PYTHONPATH=src python3 -m er_reviewer.cli`.
- README clearly says what the tool is and is not: dataset/ER review and QA,
  not a full ER matching platform.
- `er-review profile` returns richer typed profiling for CSV input:
  inferred type, numeric parse rate, datetime parse rate, min, max, selected
  quantiles, currency-like detection, and sampled invalid parse examples where
  applicable.
- `er-review report` can write a multi-tab `.xlsx` workbook alongside the
  existing HTML, section CSVs, and SVG output.
- Workbook tabs map cleanly to existing report sections: profile, hygiene,
  mappings, duplicates, clusters, similarity, compare, and a summary tab.
- A thin public Python API exposes the highest-value functions for notebook
  users without making them shell out to the CLI.
- Optional Excel dependencies are behind an extra, not required for the
  dependency-free core path.
- Existing report output and exit-code behavior remain backward-compatible.
- `make ci` passes, including tests for richer profiling and workbook output.

## Non-Goals for v0.2

- Direct Snowflake, BigQuery, Postgres, or other warehouse connectors.
- Single-entity lookup/drilldown workflows.
- Interactive HTML sorting/filtering/search.
- Full entity-resolution automation or merge recommendations.
- PDF export.
- Full config-file driven review recipes.
- Large fixture generation beyond what is needed to prove workbook/report
  behavior.

## Implementation Plan

1. Documentation and CLI surface
   - Add install instructions for editable local use and extras.
   - Rewrite command examples to use `er-review`.
   - Add a short "Analyst workflow" path: profile, report, inspect workbook.
   - Add `er-review --version` if low-churn with current package metadata.
   - Add positioning copy that frames `er-review` as an audit/review utility,
     not an auto-resolution engine.

2. Richer profiling
   - Extend `src/er_reviewer/profiling/columns.py` without breaking existing
     output fields.
   - Add typed metrics for numeric, datetime, categorical, and currency-like
     columns.
   - Keep parsing conservative and deterministic; report parse rates instead
     of silently coercing the user's data.
   - Include small invalid-example samples, capped to avoid leaking too many
     raw values into reports.

3. Workbook reporting
   - Add a workbook writer module under `src/er_reviewer/reporting/`.
   - Add `--workbook-out` to `er-review report`.
   - Write one tab per section plus a summary/index tab.
   - Keep HTML/CSV/SVG output unchanged unless the user opts into the workbook.
   - Use an optional dependency such as `openpyxl` or `xlsxwriter` behind a
     package extra.

4. Thin Python API
   - Add `src/er_reviewer/api.py` or package-level exports for stable analyst
     entrypoints.
   - Prioritize wrappers for `profile`, `find_duplicates`, `mapping_conflicts`,
     `compare_exports`, and `cluster_summary`.
   - Accept `pd.DataFrame` where pandas is installed, while keeping core CLI
     behavior file-based and dependency-light.
   - Return `pd.DataFrame` objects for analyst ergonomics; do not introduce a
     new object model in v0.2.

5. Tests and fixtures
   - Add sample rows that exercise numeric strings, currency strings, dates,
     invalid dates, blanks, and categorical columns.
   - Unit-test profiling metrics directly.
   - CLI-test workbook generation when the optional dependency is available.
   - API-test at least the profile and mapping/duplicate wrappers.
   - Ensure tests do not require local-only files or client-sensitive data.

6. Durable closeout
   - Update `CHECKPOINT.md`, `logs.md`, and this plan with the final v0.2
     evidence.
   - Run `make ci`.
   - Clean generated workbooks/reports unless they are intentionally checked in
     as docs artifacts.

## Failure Cases

- The README still makes users run through `PYTHONPATH=src`.
- Workbook output requires heavy dependencies for every install.
- Rich profiling changes existing CSV schemas without documentation.
- Public API wrappers drift from CLI behavior or duplicate core logic.
- The report path writes raw PII unexpectedly beyond the user's requested
  output files.
- Large/wide datasets produce unusably huge workbooks without row caps or
  summary-first tabs.
- `make ci` passes only when optional Excel dependencies happen to be installed
  locally.
- The package name or README implies full entity resolution when the code only
  provides review and QA checks.

## v0.3 Backlog

- `er-review report --config er-review.yaml` for repeatable review recipes.
- Excel, Parquet, delimiter, and encoding input support across commands.
- Expanded DataFrame API beyond the thin v0.2 wrappers.
- Single-entity lookup view by ID.
- Drift narrative categories for export comparison: added, removed, split,
  merged, and reassigned.
- PII redaction/masking options for reports and workbooks.
- Larger worked example fixture and notebook walkthrough.

## Prioritized Delivery Order

1. README/install/positioning update. This fixes the current discoverability
   problem immediately and gives testers the right mental model.
2. Richer profiling metrics. This creates value for every analyst dataset,
   including non-ER data.
3. Workbook output. This creates the artifact analysts actually circulate.
4. Thin Python API. This prevents the package from being CLI-only for notebook
   users without expanding scope into warehouse or interactive-app work.
5. Fixture/test expansion and closeout evidence.
