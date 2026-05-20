# Sample Data

These CSVs are synthetic. They are designed to exercise the reusable utility ideas without
copying large or sensitive source exports.

- `details.csv`: entity details with `record_id`, `entity_id`,
  `suggested_entity_id`, source fields, rule fields, `profile_url`, and
  `normalized_` comparison fields.
- `master.csv`: compact entity-level review-status fixture.
- `similar.csv`: candidate cluster-pair similarities.
- `people_duplicates.csv`: small people/contact duplicate-detection fixture.
- `export_old.csv` and `export_new.csv`: two-export drift comparison fixture.
- `bad_csv_example.csv`: intentionally malformed CSV rows for hygiene checker testing.
- `products.csv`: non-company product fixture for generic profiling, grouping, and ID analysis tests.
- `financial_extract.csv`: finance-style fixture for numeric, date, currency, and categorical profiling.
