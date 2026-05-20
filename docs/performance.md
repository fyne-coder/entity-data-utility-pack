# Performance and Large Dataset Notes

This package is useful for large analyst exports, but it is not a distributed
entity-resolution engine. The v0.3 target is practical laptop-scale review:
hundreds of thousands to low millions of rows when commands use streaming
aggregators, bounded duplicate blocks, and capped report previews.

## Current Scaling Model

- `mappings`, `clusters`, and `compare` use streaming CSV wrappers for the main
  CSV path, then keep only the aggregate state needed for the result.
- `profile` uses a streaming CSV reader but keeps all normalized per-column
  values for exact typed inference, top values, and quantiles. It avoids
  materializing row dictionaries, but memory is still `O(rows * columns)`.
- `duplicates` is still quadratic inside each blocking group by design. Use
  `--max-block-size`, `--oversized-block-behavior sample`, `--sample-rate`, and
  `--workers` before running it on low-cardinality blocks.
- `pair-profile` now uses column fingerprints for identical-column detection,
  avoiding the prior per-pair full-column value comparison.
- `report` writes full section CSVs, but HTML previews and optional workbook
  sheets can be capped with `--max-output-rows`.
- Excel and Parquet input are convenience paths through optional pandas-backed
  readers. CSV remains the dependency-light and most scalable path.

## Recommended Large-Data Defaults

```bash
er-review profile export.csv --out output/profile.csv
er-review mappings export.csv --left persistent_id --right source_id --out output/mappings.csv
er-review clusters export.csv --cluster persistent_id --match-prefix ml_ --out output/clusters.csv
er-review duplicates export.csv \
  --block normalized_dob \
  --match full_name \
  --id entity_id \
  --max-block-size 5000 \
  --oversized-block-behavior sample \
  --sample-rate 0.25 \
  --workers 4 \
  --out output/duplicate_candidates.csv
er-review report export.csv --out-dir output/review --cluster persistent_id --max-output-rows 5000
```

## Benchmark Harness

Use the synthetic harness for repeatable local checks:

```bash
PYTHONPATH=src python3 scripts/benchmark_large_data.py --rows 100000 --work-dir output/benchmarks
PYTHONPATH=src python3 scripts/benchmark_large_data.py --rows 500000 --work-dir output/benchmarks
```

The script prints wall-clock time per command and child-process peak RSS. Keep
generated benchmark files under `output/` or `/tmp`; do not commit them.

## Known Limits

- Exact typed profiling stores all normalized per-column values for type and
  quantile calculations. It is lighter than holding every row dict, but it is
  not a constant-memory quantile engine.
- Similarity with `--method tfidf` is in-memory and scales with cluster count
  and vocabulary size.
- PDF output depends on WeasyPrint and should be used for concise handoff
  reports, not million-row previews.
- For repeated multi-million-row workflows, the next backend should be DuckDB,
  Polars, or Arrow rather than more Python row loops.
