# Sample Data

These CSVs are synthetic. They are designed to show common review scenarios
without copying large or sensitive source exports.

Use them to learn the commands before pointing the package at private business
data.

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

## Suggested Practice Runs

```bash
er-review report sample_data/details.csv --out-dir output/sample_review --mapping entity_id:reference_id --cluster entity_id
er-review profile sample_data/financial_extract.csv --out output/financial_profile.csv
er-review duplicates sample_data/people_duplicates.csv --block "Date Of Birth" --match "Full Name" --id "Entity ID"
er-review compare sample_data/export_old.csv sample_data/export_new.csv --id entity_id --member record_id --narrative
```

The generated files go under `output/`, which is ignored by git.
