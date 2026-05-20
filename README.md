# Entity Data Utility Pack

Entity Data Utility Pack helps analysts and data teams turn messy tabular
exports into a clear review package: what looks healthy, what needs attention,
and which records or entity groups should be checked before downstream
reporting, migration, or matching work continues.

## What This Is

A lightweight review toolkit for teams that need confidence in customer,
account, vendor, product, or other entity data. It is designed for the common
handoff moment when someone has a CSV, Excel, or Parquet export and needs to
answer practical questions quickly:

- Are the key fields complete, consistent, and usable?
- Do IDs or reference values map cleanly, or do they point to conflicting
  records?
- Which records look like possible duplicates?
- Which entity groups are unusually large, low-confidence, or worth reviewing?
- What changed between two exports, and can the changes be explained?
- Can the findings be shared as a simple report or workbook?

It is not a full entity-resolution platform or an automatic merge decision
system. It produces review candidates, summaries, and artifacts that help people
make better decisions before data is loaded, matched, migrated, or reported.

## Common Use Cases

- Pre-migration data quality review.
- Customer/account/vendor/product master-data cleanup.
- Entity-resolution QA after a matching or clustering run.
- Duplicate review before outreach, billing, analytics, or CRM sync.
- Comparing old and new exports to explain adds, removals, splits, and merges.
- Packaging findings for business users in CSV, HTML, SVG, Excel, or PDF.

## Folder Layout

- `src/er_reviewer/`: importable package and CLI implementation.
- `tests/`: unit and CLI smoke tests.
- `docs/`: business guide, agent usage guide, design references, and
  performance guidance.
- `examples/`: notebook-style analyst walkthroughs.
- `sample_data/`: synthetic CSVs for development and testing.
- `scripts/`: local benchmark and validation helpers.

## Start Here

- [Business User Guide](docs/business_user_guide.md): plain-language workflow
  for analysts and business users.
- [Using This Repo in Codex or Cowork](docs/codex_cowork_usage.md): prompts and
  operating rules for agent workspaces.
- [Performance and Large Dataset Notes](docs/performance.md): scaling guidance
  and large-export defaults.

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

## Quick Start

```bash
er-review --version
er-review hygiene sample_data/bad_csv_example.csv
er-review profile sample_data/financial_extract.csv
er-review pair-profile sample_data/products.csv --threshold 0.5
er-review mappings sample_data/details.csv --left entity_id --right reference_id
er-review duplicates sample_data/people_duplicates.csv --block "Date Of Birth" --match "Full Name" --id "Entity ID"
er-review duplicates sample_data/people_duplicates.csv --block "Date Of Birth" --match "Full Name" --id "Entity ID" --max-block-size 5000 --oversized-block-behavior sample --sample-rate 0.25
er-review clusters sample_data/details.csv --cluster entity_id --chart-out output/cluster_sizes.svg
er-review similarity sample_data/details.csv sample_data/similar.csv --cluster entity_id --compare company_name
er-review compare sample_data/export_old.csv sample_data/export_new.csv --id entity_id --member record_id --narrative
er-review lookup sample_data/details.csv --id record_id --value e001 --cluster entity_id
er-review report sample_data/details.csv --out-dir output/review --mapping entity_id:reference_id --cluster entity_id
er-review report sample_data/details.csv --out-dir output/review --workbook-out output/review.xlsx --redact company_name --max-output-rows 5000
```

The report command is the easiest starting point for non-developers: it writes
section CSVs plus a consolidated HTML report, and can optionally create a
multi-tab Excel workbook for stakeholder review.

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
er-review similarity sample_data/details.csv sample_data/similar.csv --cluster entity_id --compare company_name --method tfidf
```

Report recipes can be supplied as JSON or TOML:

```toml
input = "sample_data/details.csv"
out_dir = "output/review"
title = "Configured Entity Review"
cluster = "entity_id"
redact = ["company_name"]

[[mappings]]
left = "entity_id"
right = "reference_id"

[duplicates]
block = "Date Of Birth"
match = ["Full Name"]
id = "record_id"
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
conflicts = api.mapping_conflicts(df, left="entity_id", right="reference_id")
clusters = api.cluster_summary(df, cluster="entity_id")
```

Path-based profiling is available for CSV/TSV/XLSX/Parquet inputs:

```python
profile = api.profile_path("sample_data/details.csv")
```

## Outputs

- Column profiles with completeness, uniqueness, type, and common-value
  summaries.
- CSV hygiene checks for malformed rows, NUL bytes, and embedded line breaks.
- One-to-many mapping exceptions for IDs, source systems, and reference values.
- Duplicate candidate lists with configurable blocking and fuzzy scoring.
- Entity/group summaries with size buckets, match-score averages, and outlier
  reasons.
- Export comparison narratives for adds, removals, reassignment, splits, and
  merges.
- HTML reports, section CSVs, SVG charts, and optional Excel/PDF handoff
  artifacts.

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
  folders, local `input/` and `data/` folders, coverage files, virtual
  environments, and caches are ignored by `.gitignore`.
- The repo-native validation gate is `make ci`; GitHub Actions runs the same
  command on push and pull request.

```bash
make ci
```

Development dependencies are declared in the `dev` optional extra and locked in
`uv.lock`. `make ci` runs Ruff format check, Ruff lint, syntax checks over the
package/test tree, mypy, and the sample-data test suite.
