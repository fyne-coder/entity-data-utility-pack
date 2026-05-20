# Entity Resolution Engine — Flow Specification

## Overview

This document describes the complete processing flow for a generalized entity resolution and deduplication analysis app. The app takes an uploaded CSV file and produces an actionable quality report with minimal user effort. The design principle is: the app picks good defaults, the user corrects only what's wrong.

---

## Step 1: Upload + Preset Selection

**Type:** User decision
**User involvement:** Required

The user uploads a CSV file and selects one of three starting profiles:

- **People/Contacts** — preconfigures expected column types (name, DOB, address, email, phone), similarity functions (fuzzy for names, exact for DOB, fuzzy for addresses), and normalization rules (strip titles, expand address abbreviations).
- **Companies/Organizations** — preconfigures for company name, domain, industry, address. Uses token-sort fuzzy matching for company names to handle word-order variation ("Acme Corp International" vs "International Acme Corp").
- **Auto-detect** — no priors. Falls back entirely to LLM classification + deterministic profiling.

Presets solve the cold start problem. They mean the LLM classification in Step 3 has a strong prior for the two most common use cases, reducing hallucination risk.

### Input
- CSV file (any delimiter — auto-detected via `csv.Sniffer`)
- Preset selection (people / companies / auto-detect)

### Output
- Raw DataFrame loaded into memory
- Preset configuration object (expected column types, similarity defaults)

---

## Step 2: Deterministic Column Profiling

**Type:** Automated (deterministic)
**User involvement:** None

For each column in the uploaded file, compute:

| Metric | Purpose |
|--------|---------|
| **Cardinality** | Number of unique values. Helps distinguish IDs from attributes. |
| **Cardinality ratio** | Unique values / total rows. Ratio near 1.0 = likely unique ID. Ratio near 0.0 = likely categorical. |
| **Null rate** | Fraction of missing/empty values. High null rate = less useful for matching. |
| **Dtype** | Pandas inferred dtype. Numeric, object, datetime. |
| **Min/max string length** | Helps distinguish short codes from free text. |
| **Sample values** | 5 non-null values for display and LLM input. |
| **Date parseable %** | Try `dateutil.parser.parse` on a sample. If >90% parse, flag as likely date. |
| **Leading zeros** | If numeric-looking but has leading zeros (zip codes, IDs), flag as string. |
| **Repeats** | Does the column have repeated values? A cluster ID must repeat. A row-level unique ID won't. |
| **Contains business suffixes** | Check for "Inc", "LLC", "Corp", "Ltd", "&" — suggests company names. |

### Input
- Raw DataFrame

### Output
- `column_profile`: dict mapping column name → profile metrics
- This feeds into both the LLM classification (Step 3) and the validation gate (Step 4)

---

## Step 3: LLM Column Classification

**Type:** LLM-assisted
**User involvement:** None (happens automatically)
**LLM calls:** 1

Send to the LLM:
- Column names
- 20–30 sample rows (stratified: include rows with nulls, rows with unusual values, not just the first 20)
- The deterministic profile summary from Step 2
- The selected preset (as a prior)

Ask the LLM to return structured JSON:

```json
{
  "cluster_id_column": "group_id" | null,
  "columns": {
    "full_name": {
      "type": "person_name",
      "confidence": "high",
      "reasoning": "Values contain first/last name patterns, no business suffixes"
    },
    "addr": {
      "type": "address",
      "confidence": "medium",
      "reasoning": "Contains street numbers and abbreviations like St, Ave"
    }
  }
}
```

### Supported column types

| Type | Description | Example values |
|------|-------------|---------------|
| `cluster_id` | Groups records into entities | "C-001", "entity_42" |
| `person_name` | Individual human name | "John Smith", "Smith, Jane" |
| `company_name` | Organization name | "Acme Corp", "Johnson & Associates" |
| `address` | Street/mailing address | "123 Main St, Apt 4B" |
| `email` | Email address | "john@example.com" |
| `phone` | Phone number | "+1 (555) 123-4567" |
| `date` | Date value | "01/02/2024", "2024-02-01" |
| `categorical` | Low-cardinality label | "M", "F", "Active", "Region-East" |
| `free_text` | Longer descriptive text | "Senior engineer with 10 years..." |
| `numeric` | Numeric value meaningful for comparison | 45000, 3.7 |
| `id` | Unique identifier (not for similarity) | "EMP-0042", "ROW-1" |
| `irrelevant` | Row numbers, timestamps, internal metadata | 1, 2, 3... |

---

## Step 4: Cross-Validate LLM Against Profile

**Type:** Validation gate (deterministic)
**User involvement:** None

Programmatic checks that catch LLM hallucinations:

| LLM says | Validation check | Action if fails |
|----------|-----------------|-----------------|
| `cluster_id` | Column must have repeated values (cardinality ratio < 0.9) | Reclassify as `id` |
| `date` | dateutil must parse ≥90% of non-null values | Reclassify as `free_text` |
| `person_name` | Must NOT contain business suffixes (Inc, LLC, Corp, &) in >10% of values | Reclassify as `company_name` |
| `phone` | After stripping non-digits, values should be 7–15 chars | Reclassify as `id` or `free_text` |
| `email` | Must contain "@" in >90% of non-null values | Reclassify as `free_text` |
| `numeric` | Must be parseable as float for >90% of non-null values | Reclassify as `id` or `categorical` |
| `categorical` | Cardinality should be < 50 or cardinality ratio < 0.05 | Reclassify as `free_text` or `id` |
| Any column marked `irrelevant` | If cardinality ratio is low and values are meaningful strings | Flag for user review |

Every correction is logged with the reason, so the user can see what the system changed and why.

### Input
- LLM classification from Step 3
- Deterministic profile from Step 2

### Output
- Validated `column_map`: dict mapping column name → confirmed type
- `validation_log`: list of corrections made

---

## Step 5: User Reviews Column Map

**Type:** User decision point
**User involvement:** Optional (can accept defaults)

Present the validated column map as an editable table:

```
Column Name     | Detected Type   | Confidence | Sample Values           | [Override ▼]
----------------|-----------------|------------|-------------------------|-------------
group_id        | cluster_id      | high       | C-001, C-002, C-001     | [cluster_id ▼]
full_name       | person_name     | high       | John Smith, Jane Doe    | [person_name ▼]
zip             | categorical     | medium     | 10001, 90210, 60601     | [categorical ▼]  ← user might change to "address_component"
field_7         | free_text       | low        | misc values...          | [free_text ▼]
```

If the validation log contains corrections, show them: "LLM classified 'zip' as numeric, but it has leading zeros — reclassified as categorical."

The user can:
- Change any column's type via dropdown
- Mark columns as "skip" (exclude from analysis)
- Confirm and proceed

**For most files, users will accept defaults and click "Continue."**

---

## Step 6: Deterministic Normalization

**Type:** Automated (deterministic)
**User involvement:** None
**LLM calls:** 0–1 (only if normalizer failures exceed 20%)

Normalization rules by column type:

| Column type | Normalization steps |
|-------------|-------------------|
| **All types** | Lowercase, strip leading/trailing whitespace, collapse multiple spaces to one, unify null representations (N/A, null, -, None, empty → NaN) |
| **person_name** | Strip titles (Mr, Mrs, Dr, Prof), strip suffixes (Jr, Sr, III, PhD), normalize "Last, First" → "First Last" |
| **company_name** | Strip common suffixes (Inc, LLC, Corp, Ltd, Co), normalize "&" → "and" |
| **address** | Expand abbreviations (St→Street, Ave→Avenue, Apt→Apartment, Blvd→Boulevard, Dr→Drive, Ln→Lane, Rd→Road, Ste→Suite, #→Apt), normalize directionals (N→North, S→South, E→East, W→West) |
| **email** | Lowercase (already covered), strip mailto: prefix if present |
| **phone** | Strip all non-digit characters except leading +, remove country code if all values are same country |
| **date** | Parse with dateutil.parser → ISO 8601 format (YYYY-MM-DD). If ambiguous (01/02/2024), use dayfirst=False as default (US convention), allow user override. |
| **categorical** | Lowercase, strip whitespace (already covered) |
| **free_text** | Lowercase, strip whitespace, optionally remove stopwords (configurable) |

### Normalizer failure handling

If >20% of values in a column fail normalization (e.g., date parsing failures), send a sample of 10 failing values to the LLM and ask: "What format are these in?" Use the LLM's answer to configure the parser (e.g., "these are DD/MM/YYYY European-format dates"), then retry. This is 0–1 LLM calls, only on failure.

### Output
- Normalized DataFrame
- `normalization_report`: per-column before/after samples (5 examples each), failure count, any LLM-assisted format detection

---

## Step 7: Branch — Clustered vs. Unclustered

**Type:** Automated
**User involvement:** None

If `column_map` contains a `cluster_id` column → **Clustered Path** (Step 8A)
If no `cluster_id` column → **Unclustered Path** (Step 8B)

---

## Step 8A: Clustered Path

### 8A.1: Cluster Size Distribution

**Type:** Automated

Count records per cluster ID. Bucket into size ranges:

| Bucket | Range |
|--------|-------|
| Singletons | 1 record |
| Small | 2–5 records |
| Medium | 6–10 records |
| Large | 11–25 records |
| Very large | 26–50 records |
| Oversized | 51–100 records |
| Extreme | 100+ records |

Generate horizontal bar chart (log scale on x-axis, matching existing `plot_distribution` logic).

**Output:** `cluster_distribution.csv`, `cluster_distribution.png`

### 8A.2: Within-Cluster Similarity Scoring

**Type:** Automated

**Critical design decision:** Fit TF-IDF vectorizers ONCE on the full dataset's column, not per-cluster. This gives comparable scores across clusters.

For each cluster with >1 record, compute pairwise similarity between all records within the cluster, per attribute column, using type-appropriate similarity functions (see Similarity Function Reference).

Aggregate into:
- **Per-record match score:** average similarity of this record to all other records in its cluster, across all attribute columns
- **Per-cluster match score:** average of all per-record scores in the cluster
- **Per-field average:** across all clusters, which fields have the highest/lowest agreement

**Output:** `match_scores.csv`, `field_averages.png`, `match_score_histogram.png`

### 8A.3: Flag Problem Clusters

**Type:** Automated

Identify clusters where: `cluster_size > average_cluster_size AND cluster_match_score < 0.8`

Sort by cluster size descending (largest problem clusters first).

For each flagged cluster, include:
- Cluster ID
- Cluster size
- Overall match score
- Per-field scores (which fields disagree?)
- Actual record values for the worst-matching pair

**Output:** `clusters_to_review.csv`

### 8A.4: Cross-Cluster Collision Detection

**Type:** Automated (with user input on which columns to check)

The reusable primitive: `find_cross_cluster_collisions(df, cluster_col, match_cols)`

For each column in `match_cols`, find records that share the same value in that column but belong to different clusters. These are potential recall failures — entities that should have been merged.

The app suggests which columns to check based on column type (dates, IDs, and emails are good candidates — names and addresses are too noisy). User can add/remove columns.

**Output:** `cross_cluster_collisions.csv`

---

## Step 8B: Unclustered Path

### 8B.1: Compute Pairwise Similarities

**Type:** Automated

**Size-dependent strategy:**

| Row count | Strategy |
|-----------|----------|
| < 10,000 | All-pairs. Build TF-IDF matrix for text columns, matrix multiply for cosine similarities. Fuzzy match for name columns (vectorized with rapidfuzz). No blocking needed. |
| 10,000 – 50,000 | LLM suggests blocking key(s) based on column types. User confirms. Compute pairwise similarity only within blocks. **1 LLM call.** |
| > 50,000 | Out of scope for v1 upload-based app. Show message: "File too large for browser-based analysis. Consider sampling or using the CLI version." |

**Output:** `candidate_pairs.csv` (all pairs with similarity > minimum threshold, e.g., 0.3)

### 8B.2: Threshold Calibration

**Type:** User decision (LLM-assisted curation)
**LLM calls:** 1

From the candidate pairs, the LLM selects 10–15 pairs that are maximally informative for threshold calibration:
- 3–4 pairs at similarity 0.9+ (likely matches — sanity check)
- 3–4 pairs at similarity 0.7–0.85 (borderline — this is where the threshold usually falls)
- 3–4 pairs at similarity 0.5–0.65 (likely non-matches — sanity check)
- 2–3 pairs where fields disagree (high name similarity but low address similarity)

Present these to the user as cards: "Are these the same entity? Yes / No / Not sure"

The user's labels set the threshold: the midpoint between the lowest "Yes" score and the highest "No" score. If the user labels everything, the system has a calibrated threshold. If they skip, use 0.7 as a default.

**The LLM's role is choosing WHICH pairs to show, not deciding same/different.**

**Output:** Calibrated similarity threshold

### 8B.3: Ranked Candidate Pairs

**Type:** Automated

Filter `candidate_pairs.csv` to pairs above the calibrated threshold. Rank by similarity score descending. Include per-field breakdown so the user can see why each pair matched.

**No automatic clustering in v1.** Connected components has the chaining problem (one weak edge merges unrelated groups). Scored pairs are immediately actionable — the user can review and merge manually.

**Output:** `matched_pairs.csv`

### 8B.4: Pair Quality Summary

**Type:** Automated

- Distribution of pair similarity scores (histogram)
- Which fields contribute most/least to matches
- How many pairs at each confidence level (high/medium/low)
- Count of pairs per blocking key (if blocking was used)

**Output:** `pair_quality_summary.csv`, `pair_score_histogram.png`

---

## Step 9: Sanity Check Results

**Type:** Validation gate (deterministic)
**User involvement:** Only if triggered

Check for degenerate cases before showing results:

| Condition | Likely cause | Warning message |
|-----------|-------------|-----------------|
| >90% of clusters flagged as problematic | Similarity function wrong for one or more column types | "Almost all clusters were flagged. Check if column types are correctly classified — a mismatch between column type and similarity function can cause this." |
| All match scores near 0 | Normalization failed or column types misclassified | "Match scores are uniformly low. This usually means the data wasn't normalized correctly or column types are wrong. Check the normalization report." |
| All match scores near 1.0 | Threshold too permissive or data is trivially clean | "All clusters look perfect. Either your data is very clean (great!) or the similarity threshold is too low to catch real issues." |
| One field has dramatically lower avg score | That field's similarity function may be wrong | "The '{field}' column is dragging down match scores. All other fields look good. You may want to check if '{field}' is classified correctly." |
| >50% of candidate pairs above threshold (unclustered) | Threshold too low or blocking key too broad | "Over half of all compared pairs matched. The threshold may be too low, or the blocking key is grouping unrelated records together." |

If any condition triggers, show a yellow warning banner with the message, a link to the relevant step's artifact (column map, normalization report, etc.), and a "Re-run with changes" button.

---

## Step 10: Output — Summary + Drilldown

### 10.1: Summary Report (LLM-Narrated)

**Type:** LLM-assisted
**LLM calls:** 1

Send summary statistics to the LLM:
- Total records, total clusters (or total candidate pairs)
- Cluster size distribution summary
- % of clusters flagged
- Top problem fields
- Number of cross-cluster collisions (or matched pairs)

Ask for a 3–5 sentence plain-English summary. The LLM is translating numbers into narrative — it's not making analytical decisions.

### 10.2: Detail Drilldown

**Type:** Output (user explores)

Everything produced in prior steps is available for inspection:

| Artifact | From step | Purpose |
|----------|-----------|---------|
| Column map + validation log | Steps 3–5 | See what was classified and any corrections |
| Normalization report (before/after) | Step 6 | Verify normalization worked correctly |
| Cluster distribution chart | Step 8A.1 | Overview of cluster sizes |
| Match scores + histogram | Step 8A.2 | Field-level quality breakdown |
| Problem clusters (ranked) | Step 8A.3 | Prioritized review list with actual record values |
| Cross-cluster collisions | Step 8A.4 | Potential recall failures |
| Matched pairs (ranked) | Step 8B.3 | Candidate duplicates with per-field scores |
| Pair quality summary | Step 8B.4 | Overview of match confidence levels |
| Sanity check warnings | Step 9 | Any red flags about the configuration |

The user starts at the summary, drills into whichever section is relevant. Analysts go deep into the per-field breakdowns. Executives read the summary and forward it.

---

## LLM Call Budget Summary

| Call | When | Purpose | Required? |
|------|------|---------|-----------|
| 1 | Step 3 | Column classification | Always |
| 2 | Step 6 | Normalization failure diagnosis | Only if >20% parse failures |
| 3 | Step 8B.1 | Blocking key suggestion | Only if unclustered + >10K rows |
| 4 | Step 8B.2 | Threshold pair curation | Only if unclustered |
| 5 | Step 10.1 | Result narration | Always |

**Typical clustered file: 2 LLM calls**
**Typical unclustered file: 3–4 LLM calls**
**Worst case: 5 LLM calls**
