# Sample Data

These CSVs are synthetic. They are designed to exercise the reusable utility ideas without
copying large or sensitive source exports.

- `details.csv`: source-platform-like entity details with `entityId`, `persistentId`, `suggestedClusterId`,
  source fields, rule fields, `profile_url`, and `ml_` normalized fields.
- `master.csv`: compact cluster-level input used by the common uniformity workflow.
- `similar.csv`: candidate cluster-pair similarities.
- `people_duplicates.csv`: small people/contact duplicate-detection fixture.
- `export_old.csv` and `export_new.csv`: two-export drift comparison fixture.
- `bad_csv_example.csv`: intentionally malformed CSV rows for hygiene checker testing.
- `products.csv`: non-company product fixture for generic profiling, grouping, and ID analysis tests.
- `financial_extract.csv`: finance-style fixture for numeric, date, currency, and categorical profiling.

The original `common/config.ini` expects names like `master.csv`, `details.csv`, and `similar.csv`.
For quick experiments, copy or symlink this directory as the script working `input` directory,
or refactor the scripts to accept paths directly.
