# Key Script Manifest

Status: legacy source material only. These scripts are preserved to show where
the reusable ideas came from, but package code should live under `src/er_reviewer/`.
Many files here still contain hardcoded filenames, import-time execution,
tenant/platform assumptions, or old dependency choices. Do not import these
modules from the package.

These scripts are included as working source material for a reusable data review utility.
They are not yet polished package modules.

## `common/`

- `data_profiler.py`: column profiling and HTML/PDF report generation.
- `data_pair_profile.py`: column relationship and grouping analysis ideas.
- `recall.py`: blocked fuzzy duplicate detection from configurable columns.
- `uniformity.py`: within-cluster TF-IDF cosine similarity.
- `similarpairs.py`: per-field similarity for candidate cluster pairs.
- `combine.py`: combine split CSV files and diagnose parsing problems.
- `encoding.py`: log decoding issues.
- `compare.py`: detect decoding issues.
- `config.ini`: sample config from the original common workflow.
- `requirements.txt`: original dependency list.

## `cluster_review/`

- `AnalyzeClusters.py`: cluster size distribution, match score histograms, and field averages.
- `entity_basic_analysis_v1.py`: duplicate detection with parameter validation ideas.
- `recall_analysis_v1.py`: earlier recall duplicate finder.
- `uniformity_analysis_v1.py`: earlier cluster uniformity scoring.
- `similar_entities_analysis_v1.py`: earlier similar-cluster analysis.

## `data_hygiene/`

- `csv_check.py`: detects inconsistent CSV row widths and embedded line breaks.
- `removeNulls_check.py`: detects/removes NUL bytes and logs encoding/line-break issues.

## `mapping_checks/`

- `oneTomany_v1.py`: reports one-to-many mappings between two columns.
- `source_analysis_v1.py`: source-specific mapping analysis with hyperlink output.
- `id_analysis_v1.py`: group/aggregate/pivot utility for ID analysis.
- `linkedin_persistent_id_count.py`: legacy domain-specific count check; not package surface.
- `linkedin_cluster_id_filter.py`: legacy domain-specific filtering helper; not package surface.
- `export_membership_compare.py`: compares persistent ID membership across two exports.
- `cluster_rule_analysis.py`: explains likely rule connections inside suggested clusters.

## Known Packaging Work

- Many scripts execute work at import time.
- Several scripts hardcode file names, column names, and URLs.
- Library functions should return DataFrames; file writes should move to CLI/reporting layers.
- Use synthetic data in `../sample_data/` for initial tests.
