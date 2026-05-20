# Source Directory Catalog

Reviewed source: internal analysis workspace

## High-Level Inventory

- Total source directory size: about `625M`.
- Project-owned files excluding virtualenvs: about `130`.
- Python code excluding virtualenvs: `55` files, about `4,711` lines.
- Environment artifacts excluded from this pack:
  - `myenv`: Python 3.12 virtualenv.
  - `untitled folder/venv_check`: second virtualenv-style folder.
- Large exports excluded from this pack:
  - `common/files/output-*.csv`: 13 large source-platform CSV shards, about `393M`.
  - large ad-hoc outputs under `untitled folder/`.

## Main Purpose

The source directory is centered on entity-resolution data review:

- Cluster quality checks.
- Duplicate detection.
- Recall and precision checks.
- Within-cluster uniformity.
- Similar-cluster detection.
- Platform ID and persistent ID inspection.
- Address parsing and normalization experiments.

## Strongest Reusable Areas

- `common/data_profiler.py`: column-level data profiling and report generation.
- `common/recall.py`: blocked fuzzy duplicate detection.
- `common/uniformity.py`: within-cluster similarity scoring.
- `common/similarpairs.py`: per-field similarity between candidate cluster pairs.
- `AnalyzeClusters.py`: cluster size distribution, field match scores, and chart outputs.
- `oneTomany_v1.py`, `source_analysis_v1.py`, `id_analysis_v1.py`: mapping cardinality checks.
- `untitled folder/csv_check.py`, `removeNulls_check.py`: CSV hygiene checks.
- `untitled folder/export_membership_compare.py`: export-to-export persistent ID comparison.
- `untitled folder/cluster_rule_analysis.py`: rule-based cluster explanation helpers.

## Excluded Areas

Address OpenAI parser scripts, BigQuery scripts, Snowflake scripts, Postgres scripts, D&B API scripts,
and cache update scripts were not copied because they are integration-specific and some contain
hardcoded credentials or tenant-specific details in the original source tree.
