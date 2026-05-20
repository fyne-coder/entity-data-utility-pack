# Entity Resolution Engine — LLM Prompt Templates

## Overview

These are the exact prompts sent to the LLM at each step. Each prompt is designed to return structured output that can be parsed programmatically. The prompts include the deterministic profile data so the LLM has context, and use the preset selection as a prior.

---

## Prompt 1: Column Classification (Step 3)

**When:** Always (every file upload)
**Expected response time:** 2–3 seconds

```
You are analyzing a CSV file that a user uploaded for entity resolution analysis.
Your job is to classify each column by its semantic type.

PRESET: {preset}
(If "people", expect person names, DOBs, addresses, emails, phones.
 If "companies", expect company names, domains, industries, addresses.
 If "auto-detect", make no assumptions.)

COLUMN PROFILES:
{for each column}
- Column: "{column_name}"
  dtype: {dtype}
  cardinality: {cardinality} unique values out of {total_rows} rows (ratio: {ratio})
  null_rate: {null_rate}
  string_length: min={min_length}, max={max_length}
  has_repeated_values: {true/false}
  sample_values: {5 sample values}
{end for}

SAMPLE ROWS (showing first 25 rows):
{formatted table of 25 sample rows}

For each column, classify it as ONE of these types:
- cluster_id: Groups records into entities/clusters. MUST have repeated values.
- person_name: Individual human name
- company_name: Organization/business name
- address: Street or mailing address
- email: Email address
- phone: Phone number (any format)
- date: Date value (any format)
- categorical: Low-cardinality label (gender, status, region, source system)
- free_text: Longer descriptive text
- numeric: Numeric value meaningful for comparison (age, score, amount)
- id: Unique row-level identifier — NOT useful for similarity comparison
- irrelevant: Row numbers, timestamps, internal metadata — skip in analysis

Return ONLY valid JSON in this exact format:
{
  "cluster_id_column": "<column_name>" or null,
  "columns": {
    "<column_name>": {
      "type": "<one of the types above>",
      "confidence": "high" | "medium" | "low",
      "reasoning": "<one sentence explaining why>"
    }
  }
}

Rules:
- At most ONE column can be cluster_id.
- If no column clearly groups records into clusters, set cluster_id_column to null.
- A column with cardinality_ratio > 0.95 is almost certainly NOT a cluster_id.
- Columns with business suffixes (Inc, LLC, Corp, &) are company_name, not person_name.
- Numeric-looking columns with leading zeros (zip codes) should be categorical or address, not numeric.
- When in doubt between id and cluster_id, prefer id (safer default).
```

---

## Prompt 2: Normalization Failure Diagnosis (Step 6)

**When:** Only if >20% of values in a column fail normalization
**Expected response time:** 1–2 seconds

```
I'm trying to parse a column classified as "{column_type}" but {failure_rate}% of
values failed to parse.

Column name: "{column_name}"

Here are 10 values that FAILED to parse:
{10 failing values, one per line}

Here are 5 values that SUCCEEDED:
{5 successful values, one per line}

What format are the failing values in? Return ONLY valid JSON:
{
  "detected_format": "<format string, e.g., DD/MM/YYYY, or MM-DD-YY, or epoch_seconds>",
  "explanation": "<one sentence>",
  "suggestion": "<how to parse these, e.g., 'use dayfirst=True' or 'divide by 1000 for epoch ms'>"
}
```

---

## Prompt 3: Blocking Key Suggestion (Step 8B.1)

**When:** Only for unclustered files with >10K rows
**Expected response time:** 1–2 seconds

```
I have an unclustered dataset with {row_count} rows that I need to deduplicate.
Computing all-pairs similarity is too expensive, so I need to choose blocking key(s)
to reduce the comparison space.

COLUMN MAP:
{for each attribute column}
- "{column_name}" (type: {column_type}, cardinality: {cardinality}, null_rate: {null_rate})
{end for}

SAMPLE ROWS (10 rows):
{formatted table}

A good blocking key:
- Creates groups small enough to compare pairwise (ideally <100 records per block)
- Keeps true duplicates in the same block (records that are the same entity should share the blocking key value)
- Has a low null rate (records with null blocking key can't be matched)

Suggest 1–2 blocking strategies. Return ONLY valid JSON:
{
  "strategies": [
    {
      "blocking_columns": ["<col1>", "<col2 if composite>"],
      "description": "<plain English: what this blocks on and why>",
      "estimated_max_block_size": <number>,
      "risk": "<what true duplicates might this miss?>"
    }
  ],
  "recommended": 0
}

If the data has a date column, consider blocking on a coarsened version
(e.g., birth year, not full DOB). If person names, consider first letter of
last name. Prefer strategies that are robust to data quality issues.
```

---

## Prompt 4: Threshold Pair Curation (Step 8B.2)

**When:** Only for unclustered files (during threshold calibration)
**Expected response time:** 2–3 seconds

```
I computed pairwise similarity scores for candidate duplicate pairs.
I need to select 12–15 pairs to show a human reviewer for threshold calibration.

The pairs should be MAXIMALLY INFORMATIVE — spread across different similarity
levels so the reviewer's labels clearly indicate where the match/non-match
boundary falls.

COLUMN MAP:
{for each attribute column}
- "{column_name}" (type: {column_type})
{end for}

CANDIDATE PAIRS (showing 100 representative pairs, sorted by aggregate score):
{table: record_id_1, record_id_2, per-field scores, aggregate_score}

Select 12–15 pairs following this distribution:
- 3–4 pairs with aggregate score 0.90–1.00 (likely matches, sanity check)
- 4–5 pairs with aggregate score 0.65–0.89 (borderline, most informative)
- 3–4 pairs with aggregate score 0.40–0.64 (likely non-matches, sanity check)
- 2–3 pairs where fields DISAGREE (e.g., high name score but low address score)

Return ONLY a JSON array of the selected pair indices (0-based row numbers
from the table above):
{
  "selected_indices": [0, 5, 12, 18, ...],
  "reasoning": "<one sentence on selection strategy>"
}

Prioritize pairs that are ambiguous and would genuinely help distinguish
matches from non-matches. Avoid pairs that are obviously the same or
obviously different unless needed for the sanity check slots.
```

---

## Prompt 5: Result Narration (Step 10.1)

**When:** Always (every analysis run)
**Expected response time:** 1–2 seconds

### Clustered path variant:

```
Summarize these entity resolution analysis results in 3–5 sentences of
plain English. Write for a non-technical reader who wants to know:
is my data clean, what should I worry about, and where should I look first.

ANALYSIS RESULTS:
- Total records: {total_records}
- Total clusters: {total_clusters}
- Singleton clusters (1 record): {singleton_count} ({singleton_pct}%)
- Cluster size distribution:
  {bucket: count for each bucket}
- Average within-cluster match score: {avg_score}
- Clusters flagged for review: {flagged_count} ({flagged_pct}%)
- Per-field average scores:
  {field_name: avg_score for each field}
- Lowest-scoring field: {worst_field} (avg: {worst_score})
- Cross-cluster collisions found: {collision_count}
  (records sharing same value in {collision_fields} but in different clusters)

{if sanity_warnings}
WARNINGS:
{warning messages}
{end if}

Rules:
- Do NOT list every statistic. Highlight what matters.
- If flagged clusters are <5% of total, lead with "data looks mostly clean."
- If one field is dragging scores down, call it out by name.
- If there are sanity warnings, mention them prominently.
- End with a clear recommendation: what the user should look at first.
```

### Unclustered path variant:

```
Summarize these deduplication analysis results in 3–5 sentences of
plain English. Write for a non-technical reader who wants to know:
how many potential duplicates were found and how confident are we.

ANALYSIS RESULTS:
- Total records: {total_records}
- Total candidate pairs evaluated: {total_pairs}
- Similarity threshold used: {threshold}
- Pairs above threshold (potential duplicates): {match_count}
- Score distribution of matched pairs:
  High confidence (>0.9): {high_count}
  Medium confidence (0.7–0.9): {medium_count}
  Lower confidence ({threshold}–0.7): {low_count}
- Per-field contribution to matches:
  {field_name: avg_score for matched pairs}
- Field most often disagreeing in matched pairs: {worst_field}

{if sanity_warnings}
WARNINGS:
{warning messages}
{end if}

Rules:
- Lead with the headline number: how many potential duplicates.
- Distinguish high-confidence from borderline matches.
- If one field is weak, call it out.
- If warnings exist, mention them.
- End with recommendation: review high-confidence pairs first, then borderline.
```

---

## Prompt Design Principles

1. **Always request structured JSON output.** Unstructured text responses are harder to parse reliably and introduce fragility.

2. **Include deterministic profile data in every prompt.** The LLM makes better decisions when it has the statistical summary, not just sample values.

3. **Use the preset as a prior, not a constraint.** "If people, expect names and DOBs" guides the LLM but doesn't prevent it from classifying something differently if the data doesn't match.

4. **Constrain the output vocabulary.** Explicit lists of valid types, confidence levels, and formats prevent the LLM from inventing categories.

5. **One task per prompt.** Each LLM call has a single clear objective. No multi-part requests that could partially fail.

6. **Every prompt output is validated downstream.** The classification prompt output goes through `validate_classification()`. The blocking suggestion goes to the user for confirmation. The threshold curation is just selecting indices — the user makes the actual same/different judgment. The narration is presentation-only. No LLM output directly drives computation without a check.
