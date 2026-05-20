# Next Steps

## Step 1: Create a Real Package Skeleton

Create:

```text
pyproject.toml
src/er_reviewer/
tests/
```

Use `pandas`, `scikit-learn`, `rapidfuzz`, `tqdm`, and optionally `dask`.
Prefer `rapidfuzz` over `fuzzywuzzy` for licensing and performance.

## Step 2: Start With Import-Safe Modules

First modules to extract:

- `io.csv_hygiene`
- `profiling.columns`
- `checks.cardinality`
- `compare.exports`

These are less coupled to source-platform cluster assumptions and easiest to test.

## Step 3: Add Cluster Review

Then extract:

- `checks.duplicates`
- `checks.clusters`
- `checks.cluster_similarity`

These need more careful config because current scripts assume columns such as
`persistentId`, `suggestedClusterId`, and `ml_` prefixes.

## Step 4: Build One HTML Report

Instead of producing many one-off CSVs and PNGs, produce:

- `profile.csv`
- `hygiene.csv`
- `mapping_issues.csv`
- `duplicate_candidates.csv`
- `cluster_quality.csv`
- `report.html`

## Step 5: Preserve Platform Conveniences as Optional Features

Platform hyperlinks are useful, but the package should not depend on one vendor.
Represent them as:

```bash
--hyperlink-template "https://example.com/entities/{id}?tab=details"
```
