# Entity Data Utility Pack

Entity Data Utility Pack is a reusable **entity and dataset review** utility for
profiling tabular exports, catching data-quality problems, surfacing
entity-resolution QA issues, and producing analyst handoff reports.

## What This Is

A command-line and library utility that helps teams review tabular data and
entity-resolution outputs:

- Profile CSV columns before analysis, including typed numeric/date/currency
  summaries.
- Detect CSV hygiene issues before pandas ingest.
- Audit one-to-many mappings between IDs, sources, and clusters.
- Find possible duplicate records with blocked fuzzy matching.
- Score cluster size, low-score cluster risk, and candidate cluster-pair
  similarity.
- Compare two exports for persistent ID membership drift, with optional
  split/merge/reassignment narrative rows.
- Produce HTML, CSV, SVG, and optional Excel workbook report artifacts.

It is not a full entity-resolution engine, record-linkage platform, or automatic
merge/survivorship decision system. It surfaces review candidates; humans still
decide what to merge or fix.

## Folder Layout

- `src/er_reviewer/`: importable package and CLI implementation.
- `tests/`: unit and CLI smoke tests.
- `docs/`: design references and performance guidance.
- `examples/`: notebook-style analyst walkthroughs.
- `sample_data/`: synthetic CSVs for development and testing.
- `scripts/`: local benchmark and validation helpers.

## Install

For local development:

```bash
python3 -m pip install -e .
```

Optional extras:

```bash
python3 -m pip install -e '.[analysis]'  # pandas, scikit-learn, rapidfuzz
python3 -m pip install -e '.[tables]'    # pandas, openpyxl, pyarrow for xlsx/parquet input
python3 -m pip install -e '.[reports]'   # openpyxl, weasyprint
python3 -m pip install -e '.[dev]'       # pytest, ruff, mypy
```

## CLI Examples

```bash
er-review --version
er-review hygiene sample_data/bad_csv_example.csv
er-review profile sample_data/financial_extract.csv
er-review pair-profile sample_data/products.csv --threshold 0.5
er-review mappings sample_data/details.csv --left persistentId --right trusted_id
er-review duplicates sample_data/people_duplicates.csv --block "Date Of Birth" --match "Full Name" --id "Entity ID"
er-review duplicates sample_data/people_duplicates.csv --block "Date Of Birth" --match "Full Name" --id "Entity ID" --max-block-size 5000 --oversized-block-behavior sample --sample-rate 0.25
er-review clusters sample_data/details.csv --cluster persistentId --chart-out output/cluster_sizes.svg
er-review similarity sample_data/details.csv sample_data/similar.csv --cluster persistentId --compare company_name
er-review compare sample_data/export_old.csv sample_data/export_new.csv --id persistentId --member entityId --narrative
er-review lookup sample_data/details.csv --id entityId --value e001 --cluster persistentId
er-review report sample_data/details.csv --out-dir output/review --mapping persistentId:trusted_id --cluster persistentId
er-review report sample_data/details.csv --out-dir output/review --workbook-out output/review.xlsx --redact company_name --max-output-rows 5000
```

Most commands accept `--format auto|csv|tsv|xlsx|parquet`; Excel and Parquet
input require the optional `tables` extra. CSV remains the preferred path for
large exports because the main CSV readers avoid whole-file row-list loading.
Profiling still retains per-column values for exact typed stats; see
`docs/performance.md` before positioning profile as constant-memory.

Cluster outlier fields combine size and optional average match-score evidence.
When no match-score columns or prefix are supplied, outlier scoring is based on
cluster size only.

After installing the optional analysis extra, TF-IDF cluster-pair similarity is
available:

```bash
er-review similarity sample_data/details.csv sample_data/similar.csv --cluster persistentId --compare company_name --method tfidf
```

Report recipes can be supplied as JSON or TOML:

```toml
input = "sample_data/details.csv"
out_dir = "output/review"
title = "Configured Entity Review"
cluster = "persistentId"
redact = ["company_name"]

[[mappings]]
left = "persistentId"
right = "trusted_id"

[duplicates]
block = "Date Of Birth"
match = ["Full Name"]
id = "entityId"
threshold = 0.8
```

```bash
er-review report --config review.toml
```

## Python API

Notebook users can use a thin pandas-facing API after installing the analysis
extra:

```python
import pandas as pd
from er_reviewer import api

df = pd.read_csv("sample_data/details.csv")
profile = api.profile(df)
conflicts = api.mapping_conflicts(df, left="persistentId", right="trusted_id")
clusters = api.cluster_summary(df, cluster="persistentId")
```

Path-based profiling is available for CSV/TSV/XLSX/Parquet inputs:

```python
profile = api.profile_path("sample_data/details.csv")
```

## Package Modules

Most package modules are dependency-light and use the Python standard library:

- `er_reviewer.io.csv_hygiene`
- `er_reviewer.profiling.columns`
- `er_reviewer.profiling.pairs`
- `er_reviewer.checks.cardinality`
- `er_reviewer.checks.duplicates`
- `er_reviewer.checks.clusters`
- `er_reviewer.checks.lookup`
- `er_reviewer.checks.similarity`
- `er_reviewer.compare.exports`
- `er_reviewer.reporting.redaction`
- `er_reviewer.reporting.html_report`
- `er_reviewer.reporting.charts`
- `er_reviewer.reporting.workbook`
- `er_reviewer.api`

Duplicate scoring supports `--scorer auto|difflib|rapidfuzz`; `auto` uses
`rapidfuzz` when the optional analysis extra is installed and falls back to
stdlib `difflib`.

Reporting writes section CSVs plus one dependency-free `report.html`. Cluster
summaries can write dependency-free SVG bar charts, including an average
match-score distribution when match scores are present. Workbook and PDF output
use the optional `reports` extra. Use `--max-output-rows` to cap HTML previews
and workbook sheets while preserving full section CSV outputs.

## Performance Notes

Large-data guidance, current limits, and a synthetic benchmark harness are in
`docs/performance.md`. In short: use CSV for the largest inputs, guard duplicate
blocks, cap report previews, and treat TF-IDF/PDF/notebook workflows as
in-memory convenience paths rather than million-row defaults.

## Development

- The package code under `src/er_reviewer/` is the supported importable surface.
- Sample data is synthetic. Do not commit customer exports, generated reports,
  local notebooks with private outputs, credentials, API keys, or benchmark
  data.
- Generated analyst artifacts such as `.xlsx`, `.parquet`, `.pdf`, local report
  folders, coverage files, virtual environments, and caches are ignored by
  `.gitignore`.
- The repo-native validation gate is `make ci`; GitHub Actions runs the same
  command on push and pull request.

```bash
make ci
```

Development dependencies are declared in the `dev` optional extra and locked in
`uv.lock`. `make ci` runs Ruff format check, Ruff lint, syntax checks over the
package/test tree, mypy, and the sample-data test suite.
