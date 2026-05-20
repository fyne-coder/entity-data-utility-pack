# Using This Repo in Codex or Cowork

This is the recommended way to use Entity Data Utility Pack for most business
users and analysts.

Codex, Cowork, or any similar coding-agent workspace can use this repo as a
repeatable data-review tool. The key is to give the agent the local file path,
the business question, the expected output, and clear rules about private data.

## One-Time Setup For Analysis

Clone the repo and install the extras used for reports, Excel/Parquet files,
and faster similarity scoring:

```bash
git clone https://github.com/fyne-coder/entity-data-utility-pack.git
cd entity-data-utility-pack
python3 -m pip install -e '.[reports,tables,analysis]'
```

If the agent is only running analysis on a data file, it should run the relevant
`er-review` command and report the output paths.

## Contributor Setup

If the agent will modify package code, tests, or docs, install the development
extra and run the validation gate:

```bash
python3 -m pip install -e '.[reports,tables,analysis,dev]'
make ci
```

Use `make ci` as the validation command after code changes.

## Where To Put Data

Put private exports in a local ignored folder such as:

```text
input/
data/
```

Put generated reports in:

```text
output/
reports/
```

Those folders are ignored by git. The agent should not commit customer data,
workbooks, PDFs, credentials, or generated private reports.

## What To Tell The Agent

Give the agent:

- The local path to the file.
- The business goal.
- The key columns, if you know them.
- Whether generated outputs can be written under `output/`.
- Any sensitive columns to redact from HTML, Excel, or PDF outputs.

Example:

```text
Use this repo to review input/customer_export.csv.
Goal: identify data quality issues before a CRM migration.
Known columns: Customer ID is the entity group, Source ID is the source-system reference, Account Name is sensitive.
Write outputs under output/customer_review.
Redact Account Name from shareable outputs.
Explain the findings in business terms and list the files created.
Do not commit the input file or generated reports.
```

## Good Starter Prompts

Broad business review:

```text
Inspect the headers in input/accounts.csv, choose the right er-review commands,
and create a business-readable review package under output/accounts_review.
Summarize the highest-risk findings and include the exact output files.
```

Column quality review:

```text
Run a profile on input/vendor_master.csv and explain which columns are risky for
reporting, joining, matching, or migration.
```

Mapping consistency review:

```text
Check whether Account ID maps cleanly to Source System ID in input/accounts.csv.
Create a CSV of exceptions and explain what the exceptions mean for operations.
```

Duplicate review:

```text
Find possible duplicate contacts in input/contacts.csv. Block by Date Of Birth,
match on Full Name, and use Contact ID as the row identifier. Use large-block
guards so the command does not explode on common dates.
```

Old-vs-new export review:

```text
Compare input/export_old.csv and input/export_new.csv using entity_id as the
group ID and record_id as the row ID. Produce a narrative summary of added,
removed, reassigned, split, and merged groups.
```

## Agent Operating Rules

Ask the agent to follow this checklist:

1. Inspect file headers before choosing column options.
2. Use `er-review --help` and command-specific help instead of guessing flags.
3. Write analysis outputs under `output/` or `reports/`.
4. Keep private inputs and generated outputs out of commits.
5. Explain findings in business terms first, with technical details second.
6. Run `make ci` after changing package code or docs.
7. Report exact commands run and exact output paths created.

## Useful Commands

```bash
er-review --help
er-review report --help
er-review profile input/file.csv --out output/profile.csv
er-review report input/file.csv --out-dir output/review --max-output-rows 5000
make ci
```

## Expected Closeout From An Agent

A good final response should include:

- The goal it handled.
- The commands it ran.
- The output files it created.
- The most important business findings.
- Any columns it could not confidently identify.
- Any limits, such as large duplicate blocks or missing optional dependencies.
