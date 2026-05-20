# Business User Guide

Entity Data Utility Pack helps you inspect business data before you rely on it
for reporting, migration, matching, billing, outreach, or operational cleanup.
It is most useful when you have an export from a CRM, ERP, billing system,
product catalog, vendor file, account master, or matching process and need to
know what deserves review.

The package does not decide which records should be merged. It produces evidence
and review lists so analysts and business owners can make cleaner decisions.

## Questions It Helps Answer

- Can this file be loaded and read reliably?
- Which columns are incomplete, inconsistent, mostly blank, or filled with
  placeholder values?
- Do IDs and reference values map cleanly, or does one value point to multiple
  values?
- Which records look like possible duplicates?
- Which entity groups are unusually large or low-confidence?
- What changed between two exports?
- Which rows should be reviewed first before a migration, dashboard, or sync?

## Recommended First Workflow

Use the combined report command first. It creates section CSVs and a readable
HTML report, with an optional Excel workbook for business review.

```bash
python3 -m pip install -e '.[reports,tables]'

er-review report input/customers.csv \
  --out-dir output/customer_review \
  --cluster entity_id \
  --mapping entity_id:reference_id \
  --workbook-out output/customer_review.xlsx \
  --max-output-rows 5000
```

Use the column names from your own file. If you do not know the columns yet,
start with:

```bash
er-review profile input/customers.csv --out output/profile.csv
```

## Which Command To Use

| Situation | Command | Business outcome |
| --- | --- | --- |
| You want a broad first-pass review | `er-review report` | Creates a shareable package of findings. |
| You only need column quality | `er-review profile` | Shows completeness, uniqueness, common values, and likely data types. |
| You suspect broken CSV formatting | `er-review hygiene` | Finds malformed rows, embedded line breaks, NUL bytes, and parsing issues. |
| You need to check ID consistency | `er-review mappings` | Finds one-to-many mapping exceptions such as one customer ID tied to many source IDs. |
| You need duplicate candidates | `er-review duplicates` | Produces rows that look similar within a blocking group such as date of birth, email domain, or account region. |
| You have grouped or matched records | `er-review clusters` | Summarizes entity groups and highlights unusually large groups. |
| You have old and new exports | `er-review compare` | Explains added, removed, reassigned, split, and merged groups. |
| You need to inspect one record or group | `er-review lookup` | Pulls the row and related group context. |

## Column Names To Look For

The package is intentionally generic. You can use your own column names, but
these names are used in sample data and examples:

- `record_id`: the row-level record identifier.
- `entity_id`: the group or resolved entity identifier.
- `reference_id`: another business or source-system identifier to compare
  against.
- `suggested_entity_id`: a candidate group or match suggestion from another
  system.
- `normalized_*`: cleaned comparison fields such as `normalized_name` or
  `normalized_address`.

If your export uses names like customer ID, account ID, vendor number, source
system ID, master ID, or match group, pass those actual column names in the CLI
options.

## How To Read The Outputs

Start with `report.html`. It gives you the summary sections and links the
detail files written under the output folder.

Then review the detail CSVs:

- Profile findings identify columns that may be unreliable for joins, filters,
  matching, or reporting.
- Mapping findings identify places where business keys do not behave as clean
  one-to-one relationships.
- Duplicate findings are candidates, not final decisions.
- Cluster findings show which groups need review because they are large,
  unusual, or supported by weak match evidence.
- Compare findings explain how entity assignments changed across exports.

For stakeholder review, use the Excel workbook if you generated one. It is often
the easiest artifact for business users to sort, filter, annotate, and share.

## Analyst Guidance

Use business-safe columns for blocking duplicate searches. For example, date of
birth, postal code, email domain, country, account type, or source system can
reduce the number of comparisons. Avoid running duplicate detection across a
large file without a block column.

For large exports, prefer CSV input and cap report previews:

```bash
er-review report input/accounts.csv \
  --out-dir output/account_review \
  --cluster entity_id \
  --max-output-rows 5000
```

See [Performance and Large Dataset Notes](performance.md) before running
duplicate or TF-IDF similarity workflows on very large files.

## Data Safety

Keep private files out of git. This repo ignores `input/`, `data/`, `output/`,
and `reports/`, which are safe places for local working files and generated
review artifacts.

Do not commit customer exports, generated workbooks, PDFs, local notebooks with
private outputs, credentials, or API keys.
