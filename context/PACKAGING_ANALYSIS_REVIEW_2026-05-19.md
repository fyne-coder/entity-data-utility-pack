# Packaging Analysis Review - 2026-05-19

## Conclusion

The proposed analysis is directionally right but overstates "ready to package."
This repository is a curated utility pack, not the full original analysis
workspace. Most copied scripts are useful source material but still need
import-safety, parameterization, test fixtures, and a real `make ci` gate before
they should be treated as package modules.

## Corrections

- The pack contains 23 copied source-material files under `key_scripts/`, not
  the full original 65-script workspace.
- Tier 3 items such as address parsing, BigQuery, Postgres, D&B, and cache
  update scripts are mostly excluded already per `context/CATALOG.md`; they are
  not active packaging candidates in this repo.
- `data_quality_toolkit` conflicts with the repo's existing naming direction:
  `er-review` CLI and `er_reviewer/` package.
- The proposed flat module layout conflicts with the existing package shape in
  `context/PACKAGING_REVIEW.md` and `notes/NEXT_STEPS.md`.
- "Replace fuzzywuzzy with rapidfuzz" is valid, but already captured in
  `notes/NEXT_STEPS.md`.

## Recommended MVP Order

1. `io.csv_hygiene` from `key_scripts/data_hygiene/csv_check.py` and
   `key_scripts/data_hygiene/removeNulls_check.py`.
2. `profiling.columns` from `key_scripts/common/data_profiler.py`, with PDF
   generation moved behind an optional extra and report generation separated.
3. `checks.cardinality` from `key_scripts/mapping_checks/oneTomany_v1.py`, then
   selected ideas from `source_analysis_v1.py` and `id_analysis_v1.py`.
4. `compare.exports` from `key_scripts/mapping_checks/export_membership_compare.py`.
5. `checks.duplicates` from `key_scripts/common/recall.py`, replacing
   `fuzzywuzzy` with `rapidfuzz` and removing `config.ini` coupling.
6. Cluster and similarity modules after the simpler checks: `AnalyzeClusters.py`,
   `similarpairs.py`, and `uniformity.py`.
7. One consolidated `reporting/html_report.py` rather than scattered CSV, PNG,
   and PDF outputs.

## Main Risks

- Several modules execute work at import time, including `data_profiler.py`,
  `csv_check.py`, `removeNulls_check.py`, `recall.py`, `uniformity.py`,
  `similarpairs.py`, and `export_membership_compare.py`.
- `make ci` currently fails intentionally because lint/test targets are
  placeholders.
- There are no tests yet. MVP extraction should use existing fixtures in
  `sample_data/`.
- `weasyprint` adds native system dependencies and should not be a default
  dependency.
- `key_scripts/common/requirements.txt` lists `sklearn`; packaging should use
  `scikit-learn`.
- There are overlapping versions of recall, uniformity, and similarity scripts;
  the package should choose canonical sources rather than carrying duplicates.

## Verification

- `find key_scripts -name '*.py' -print0 | xargs -0 python3 -m py_compile`
  passed.
- `make ci` failed at the placeholder lint target, as documented in
  `CHECKPOINT.md`.
- Claude was asked through tmux session `cc_tmux` after `/clear`; its review
  agreed that the Tier 1 label is overstated and recommended the same MVP order:
  hygiene, profiling, cardinality, export comparison, duplicates, then cluster
  and similarity work.
