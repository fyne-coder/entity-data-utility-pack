# Entity Resolution Engine — Similarity Function Reference

## Function-to-Column-Type Mapping

| Column Type | Similarity Function | Library | Why This One |
|-------------|-------------------|---------|-------------|
| `person_name` | `fuzzy_token_sort` | rapidfuzz | Handles word order ("Smith, John" vs "John Smith"). Levenshtein-based, good for typos. |
| `company_name` | `fuzzy_token_sort` | rapidfuzz | Handles word order ("Acme Corp International" vs "International Acme Corp"). |
| `address` | `fuzzy_ratio` | rapidfuzz | After normalization (abbreviation expansion), straight fuzzy catches remaining variation. Token sort is less useful here because address component order is usually consistent. |
| `email` | `email_composite` | custom | Domain should match exactly (0.5 weight). Local part can vary ("j.smith" vs "jsmith", 0.5 weight fuzzy). |
| `phone` | `exact_normalized` | built-in | After stripping formatting, phones either match or don't. Fuzzy matching on phone numbers creates false positives (one digit off = different person). |
| `date` | `exact_parsed` | dateutil | After parsing to ISO, dates either match or don't. Optional tolerance window (±N days) for known data quality issues. |
| `categorical` | `exact` | built-in | Categories match or they don't. Fuzzy matching "Male" to "Female" would be wrong. |
| `free_text` | `tfidf_cosine` | sklearn | For longer text, TF-IDF captures semantic overlap better than character-level fuzzy. Important: vectorizer must be fit on the full column globally, not per-cluster. |
| `numeric` | `normalized_distance` | custom | `1.0 - abs(a - b) / range`. Gives 1.0 for identical, 0.0 for max distance. Range = max - min across the full column. |

---

## Function Specifications

### `fuzzy_token_sort(a: str, b: str) -> float`

```
Input:  "John Michael Smith", "Smith, John M."
Step 1: Tokenize → ["john", "michael", "smith"], ["smith", "john", "m"]
Step 2: Sort tokens → "john michael smith", "john m smith"
Step 3: Levenshtein ratio on sorted strings
Output: 0.85 (approximate)
```

**Use `rapidfuzz` not `fuzzywuzzy`.** rapidfuzz is 10–100x faster (C++ implementation, no Python-level sequence matching). Drop-in compatible API.

```python
from rapidfuzz import fuzz
score = fuzz.token_sort_ratio(a, b) / 100.0  # returns 0–100, normalize to 0–1
```

**When it fails:** Very short strings ("Al" vs "Ali") get disproportionately penalized. Names with common prefixes/suffixes ("Dr. John Smith" vs "John Smith") need normalization first, not a different similarity function.

---

### `fuzzy_ratio(a: str, b: str) -> float`

```
Input:  "123 Main Street Apartment 4B", "123 Main St Apt 4b"
        (after normalization, both become "123 main street apartment 4b")
Output: 1.0
```

Simple Levenshtein ratio without token sorting. Better for addresses where component order is fixed.

```python
from rapidfuzz import fuzz
score = fuzz.ratio(a, b) / 100.0
```

---

### `email_composite(a: str, b: str) -> float`

```
Input:  "j.smith@acme.com", "jsmith@acme.com"
Step 1: Split → ("j.smith", "acme.com"), ("jsmith", "acme.com")
Step 2: Domain exact match → "acme.com" == "acme.com" → 1.0
Step 3: Local part fuzzy → fuzz.ratio("j.smith", "jsmith") / 100 → 0.86
Step 4: Weighted average → 0.5 * 1.0 + 0.5 * 0.86 = 0.93
Output: 0.93
```

**Edge cases:**
- If either value is null/empty → 0.0
- If domains differ → score is capped at 0.5 (different org, probably different entity)
- Gmail dots ("j.smith@gmail.com" = "jsmith@gmail.com"): normalization should strip dots before @ for gmail/googlemail domains

---

### `exact_normalized(a: str, b: str) -> float`

```
Input:  "+1 (555) 123-4567", "5551234567"
Step 1: Strip non-digits → "15551234567", "5551234567"
Step 2: Strip country code if matching → "5551234567", "5551234567"
Step 3: Exact match → True
Output: 1.0
```

Returns 1.0 or 0.0. No partial credit for phones — one digit off is a different number.

---

### `exact_parsed(a: str, b: str, tolerance_days: int = 0) -> float`

```
Input:  "01/15/1990", "1990-01-15", tolerance=0
Step 1: Parse → date(1990,1,15), date(1990,1,15)
Step 2: abs(d1 - d2) = 0 days ≤ tolerance (0)
Output: 1.0

Input:  "01/15/1990", "01/16/1990", tolerance=1
Step 1: Parse → date(1990,1,15), date(1990,1,16)
Step 2: abs(d1 - d2) = 1 day ≤ tolerance (1)
Output: 1.0

Input:  "01/15/1990", "02/15/1990", tolerance=0
Output: 0.0
```

Tolerance is useful when dates are known to have entry errors (off-by-one day). Default to 0 (exact match).

---

### `exact(a: str, b: str) -> float`

```
Input:  "Male", "Male" → 1.0
Input:  "Male", "M"    → 0.0  (normalization should have handled this)
Input:  "Active", "active" → 1.0  (after universal lowercase normalization)
```

For categorical columns. If "M" vs "Male" is a known issue, handle it in normalization (map "M"→"male", "F"→"female") not in similarity.

---

### `tfidf_cosine(vectors_a, vectors_b) -> float`

```
Input:  Two pre-computed TF-IDF vectors (from a globally-fit vectorizer)
Step 1: cosine_similarity(vector_a, vector_b)
Output: 0.0–1.0
```

**Critical:** Do NOT fit a new vectorizer per comparison. The vectorizer must be fit once on the entire column across all records (via `fit_global_vectorizers()`). Pass the pre-computed vectors to this function.

For within-cluster similarity, compute pairwise cosine similarity matrix for all records in the cluster at once (vectorized, fast).

For cross-cluster similarity, compute centroid of each cluster's vectors, then cosine similarity between centroids.

---

### `normalized_distance(a: float, b: float, range_val: float) -> float`

```
Input:  a=50000, b=52000, range_val=200000 (salary column, range 0–200K)
Step 1: abs(50000 - 52000) / 200000 = 0.01
Step 2: 1.0 - 0.01 = 0.99
Output: 0.99

Input:  a=25, b=75, range_val=100
Output: 0.50
```

`range_val` = max(column) - min(column) across the full dataset. Computed once during setup.

If range is 0 (all values identical), return 1.0.

---

## Aggregate Scoring

### Per-record match score (within cluster)

For a record R in a cluster of size N:

```
For each other record R' in the same cluster:
    For each attribute column C:
        field_score[C] = compare_values(R[C], R'[C], method_for_C)
    pair_score = mean(field_score values)

record_score = mean(pair_score for all R')
```

### Per-cluster match score

```
cluster_score = mean(record_score for all records in cluster)
```

### Per-field average (global)

```
field_avg[C] = mean(all field_score[C] values across all pairs in all clusters)
```

This shows which fields are contributing to matches and which are dragging scores down.

---

## Performance Notes

| Dataset size | Strategy | Expected time |
|-------------|----------|---------------|
| < 1K rows | All-pairs, all functions | < 1 second |
| 1K – 10K rows | All-pairs, vectorized where possible | 1–10 seconds |
| 10K – 50K rows | Blocked pairwise, TF-IDF via sparse matrix ops | 10–60 seconds |
| > 50K rows | Out of scope for v1 upload app | N/A |

**Key optimization:** Use `rapidfuzz` instead of `fuzzywuzzy` for all fuzzy matching. Use `scipy.sparse` matrices for TF-IDF cosine similarity computation. Avoid Python-level loops over pairs — use vectorized operations wherever possible.

---

## Mapping to Existing Codebase

| Current script | Function used | Replacement |
|---------------|--------------|-------------|
| `PrecisionAnalysis_v1.py` | `fuzzywuzzy.fuzz.ratio` with DOB blocking | `fuzzy_token_sort` (for names) + configurable blocking |
| `recall_analysis_v1.py` | `fuzzywuzzy.fuzz.ratio` with configurable blocking | Same as above, generalized |
| `analyze_similar_clusters_v1.py` | `jaccard_similarity_v3` (token overlap) | `fuzzy_token_sort` for names, `tfidf_cosine` for text |
| `similar_entities_analysis_v1.py` | `TfidfVectorizer` per cluster pair | `tfidf_cosine` with global vectorizer |
| `uniformity_analysis_v1.py` | `TfidfVectorizer` per cluster per column | `tfidf_cosine` with global vectorizer |
| `AnalyzeClusters.py` | Pre-computed `ml_` match flags | `compare_values()` computed on the fly |
