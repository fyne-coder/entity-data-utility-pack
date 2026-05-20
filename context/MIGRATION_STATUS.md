# Migration Status

This repo's reusable utility surface is `src/er_reviewer/`. The copied scripts
under `key_scripts/` are legacy source material and should not be treated as
package modules until their behavior has been moved behind configurable,
import-safe APIs with tests.

## Migrated To Generic Modules

| Legacy source | Generic module or command |
| --- | --- |
| `key_scripts/data_hygiene/csv_check.py` | `er_reviewer.io.csv_hygiene`, `er-review hygiene` |
| `key_scripts/data_hygiene/removeNulls_check.py` | `er_reviewer.io.csv_hygiene.strip_nul_bytes` |
| `key_scripts/common/data_profiler.py` | `er_reviewer.profiling.columns`, `er-review profile` |
| `key_scripts/common/data_pair_profile.py` | `er_reviewer.profiling.pairs`, `er-review pair-profile` |
| `key_scripts/mapping_checks/oneTomany_v1.py` | `er_reviewer.checks.cardinality`, `er-review mappings` |
| `key_scripts/mapping_checks/export_membership_compare.py` | `er_reviewer.compare.exports`, `er-review compare` |
| `key_scripts/common/recall.py` and `key_scripts/cluster_review/recall_analysis_v1.py` | `er_reviewer.checks.duplicates`, `er-review duplicates` |
| `key_scripts/cluster_review/AnalyzeClusters.py` | `er_reviewer.checks.clusters`, `er-review clusters` |
| `key_scripts/common/similarpairs.py` and `key_scripts/cluster_review/similar_entities_analysis_v1.py` | `er_reviewer.checks.similarity`, `er-review similarity` |

## Intentionally Not Package Surface

- LinkedIn-specific mapping checks remain legacy reference only.
- Vendor hyperlink generation should be represented by optional templates, not
  hardcoded URLs.
- `config.ini` is preserved only as an original-workflow example; generic code
  should accept function parameters or CLI arguments.
- Plot/PDF-heavy reporting should stay optional so the default install remains
  lightweight.

## Current Package Gate

`make ci` is the canonical local gate. It runs formatting, linting, typecheck,
legacy syntax checks, and tests over synthetic fixtures.
