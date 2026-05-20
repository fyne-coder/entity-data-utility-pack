# Packaging Review

## Best MVP

Package this first as a CLI/library for CSV and entity-resolution data review.

### 1. Column/Data Profiler

Source:

- `key_scripts/common/data_profiler.py`
- `docs/01_flow_specification.md`

Reusable value:

- Row counts.
- Cardinality and cardinality ratio.
- Null and blank rates.
- Top values.
- Dummy-value detection.
- Likely ID/category/date fields.

### 2. CSV Hygiene Checker

Source:

- `key_scripts/data_hygiene/csv_check.py`
- `key_scripts/data_hygiene/removeNulls_check.py`

Reusable value:

- Inconsistent column counts.
- Embedded newlines.
- Invalid UTF-8.
- NUL bytes.
- Quote issues.

This should run before pandas ingest.

### 3. Cardinality and One-to-Many Audits

Source:

- `key_scripts/mapping_checks/oneTomany_v1.py`
- `key_scripts/mapping_checks/source_analysis_v1.py`
- `key_scripts/mapping_checks/id_analysis_v1.py`

Reusable value:

- Detect when one customer ID maps to multiple source IDs.
- Detect when one persistent ID maps to multiple trusted IDs.
- Summarize source-level conflicts.

### 4. Duplicate Candidate Finder

Source:

- `key_scripts/common/recall.py`
- `key_scripts/cluster_review/entity_basic_analysis_v1.py`

Reusable value:

- Blocked fuzzy duplicate detection.
- Especially useful for people/contact datasets using DOB, name, and address.

### 5. Cluster Quality Audit

Source:

- `key_scripts/cluster_review/AnalyzeClusters.py`
- `key_scripts/common/uniformity.py`

Reusable value:

- Cluster size distribution.
- Suspiciously large clusters.
- Low internal similarity.
- Per-field match scores.

### 6. Similar-Cluster Collision Audit

Source:

- `key_scripts/common/similarpairs.py`

Reusable value:

- Find clusters that look similar enough to need review or merging.
- Report per-column similarity.

### 7. Two-Export Drift Comparison

Source:

- `key_scripts/mapping_checks/export_membership_compare.py`

Reusable value:

- Compare two exports.
- Report persistent IDs that disappeared, appeared, or changed entity membership.

### 8. Rule Explanation / Cluster Forensics

Source:

- `key_scripts/mapping_checks/cluster_rule_analysis.py`

Reusable value:

- Explain which rule columns appear to connect records inside a suggested cluster.
- More domain-specific than the other utilities, so package later or keep optional.

## Recommended Package Shape

```text
er_reviewer/
  cli.py
  io/csv_hygiene.py
  profiling/columns.py
  checks/cardinality.py
  checks/duplicates.py
  checks/clusters.py
  checks/cluster_similarity.py
  compare/exports.py
  reporting/html_report.py
  config.py
```

## Main Refactor Needed

- Move all script execution under `if __name__ == "__main__"` or CLI commands.
- Turn hardcoded paths into function parameters.
- Turn hardcoded tenant URLs into optional hyperlink templates.
- Turn hardcoded column names into config.
- Remove diagnostic prints from library functions.
- Return DataFrames or typed result objects from core functions.
- Keep file writing in CLI/reporting layers.
- Add unit tests around the synthetic files in `sample_data/`.
