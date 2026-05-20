# Entity Resolution Engine — Technical Architecture

## Module Overview

The engine is organized into six modules. Each module has a single responsibility, clear inputs/outputs, and no platform-specific dependencies.

```
┌─────────────────────────────────────────────────┐
│                   App Entry Point                │
│           (upload handler, orchestrator)          │
└──────────┬──────────────────────────┬────────────┘
           │                          │
    ┌──────▼──────┐           ┌───────▼───────┐
    │   Profiler   │           │  LLM Client   │
    │  (Step 2,4)  │           │  (Step 3,6,   │
    │              │           │   8B,10)       │
    └──────┬──────┘           └───────┬───────┘
           │                          │
    ┌──────▼──────────────────────────▼────────┐
    │            Column Mapper (Step 5)         │
    │   (merges profile + LLM + user overrides) │
    └──────────────────┬───────────────────────┘
                       │
              ┌────────▼────────┐
              │   Normalizer    │
              │    (Step 6)     │
              └────────┬────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
    ┌──────▼──────┐        ┌───────▼───────┐
    │  Clustered   │        │  Unclustered  │
    │   Analyzer   │        │   Analyzer    │
    │  (Step 8A)   │        │  (Step 8B)    │
    └──────┬──────┘        └───────┬───────┘
           │                       │
           └───────────┬───────────┘
                       │
              ┌────────▼────────┐
              │    Reporter     │
              │  (Step 9, 10)   │
              └─────────────────┘
```

---

## Module 1: Profiler

**File:** `profiler.py`

### `profile_columns(df: pd.DataFrame) -> dict[str, ColumnProfile]`

```python
@dataclass
class ColumnProfile:
    name: str
    dtype: str                    # pandas dtype
    cardinality: int              # unique non-null values
    cardinality_ratio: float      # cardinality / total rows
    null_rate: float              # fraction of null/empty values
    min_length: int               # min string length (non-null)
    max_length: int               # max string length (non-null)
    sample_values: list[str]      # 5 non-null values (stratified)
    date_parseable_pct: float     # % that dateutil can parse
    has_leading_zeros: bool       # numeric-looking but has leading zeros
    has_repeated_values: bool     # same value appears in multiple rows
    has_business_suffixes: bool   # contains Inc, LLC, Corp, & in >10% of values
    is_unique_per_row: bool       # cardinality_ratio > 0.95
```

### `validate_classification(llm_result: dict, profiles: dict[str, ColumnProfile]) -> tuple[dict, list[str]]`

Takes the LLM's classification and the deterministic profile. Returns a corrected column map and a list of correction log entries.

Validation rules (exhaustive):

```python
VALIDATION_RULES = {
    "cluster_id": lambda p: not p.is_unique_per_row and p.has_repeated_values,
    "date": lambda p: p.date_parseable_pct >= 0.9,
    "person_name": lambda p: not p.has_business_suffixes,
    "phone": lambda p: 7 <= avg_digit_length(p) <= 15,
    "email": lambda p: pct_containing(p, "@") >= 0.9,
    "numeric": lambda p: pct_numeric(p) >= 0.9,
    "categorical": lambda p: p.cardinality < 50 or p.cardinality_ratio < 0.05,
}
```

---

## Module 2: LLM Client

**File:** `llm_client.py`

Thin wrapper around the LLM API. All LLM interactions go through this module so they can be logged, cached, and mocked for testing.

### `classify_columns(column_names: list[str], sample_rows: list[dict], profiles: dict[str, ColumnProfile], preset: str) -> dict`

Returns structured JSON with column classifications. See prompt template in `03_llm_prompts.md`.

### `diagnose_parse_failures(column_name: str, failing_values: list[str], column_type: str) -> str`

Returns a format string (e.g., "DD/MM/YYYY") that can be used to configure the parser.

### `suggest_blocking_keys(column_map: dict[str, str], sample_rows: list[dict]) -> list[str]`

Returns suggested blocking column name(s) with plain-English explanation.

### `curate_threshold_pairs(candidate_pairs: pd.DataFrame, column_map: dict[str, str]) -> pd.DataFrame`

Selects 10–15 informative pairs at varying similarity levels. Returns a subset of candidate_pairs.

### `narrate_results(summary_stats: dict) -> str`

Returns a 3–5 sentence plain-English summary of the analysis results.

---

## Module 3: Column Mapper

**File:** `column_mapper.py`

### `build_column_map(profiles: dict, llm_classification: dict, user_overrides: dict | None) -> ColumnMap`

```python
@dataclass
class ColumnMap:
    cluster_id_column: str | None
    attribute_columns: dict[str, ColumnConfig]
    skipped_columns: list[str]

@dataclass
class ColumnConfig:
    name: str
    column_type: str              # person_name, company_name, address, etc.
    similarity_function: str      # fuzzy_token_sort, exact, tfidf_cosine, etc.
    normalize_function: str       # person_name_norm, address_norm, phone_norm, etc.
    confidence: str               # high, medium, low
    source: str                   # "llm", "validation_override", "user_override"
```

The mapper merges three sources with priority: user override > validation correction > LLM classification.

Similarity function assignment (lookup table):

```python
SIMILARITY_FUNCTION_MAP = {
    "person_name":    "fuzzy_token_sort",
    "company_name":   "fuzzy_token_sort",
    "address":        "fuzzy_ratio",
    "email":          "email_composite",    # exact domain + fuzzy local
    "phone":          "exact_normalized",
    "date":           "exact_parsed",       # or within_n_days(tolerance)
    "categorical":    "exact",
    "free_text":      "tfidf_cosine",
    "numeric":        "normalized_distance",
}
```

---

## Module 4: Normalizer

**File:** `normalizer.py`

### `normalize_dataframe(df: pd.DataFrame, column_map: ColumnMap, llm_client: LLMClient | None) -> tuple[pd.DataFrame, NormalizationReport]`

```python
@dataclass
class NormalizationReport:
    per_column: dict[str, ColumnNormReport]

@dataclass
class ColumnNormReport:
    column_name: str
    column_type: str
    records_processed: int
    records_changed: int
    records_failed: int
    failure_rate: float
    before_after_samples: list[tuple[str, str]]  # 5 (original, normalized) pairs
    llm_assist_used: bool
    llm_format_detected: str | None               # e.g., "DD/MM/YYYY"
```

### Individual normalizers (all are pure functions, deterministic)

```python
def normalize_universal(value: str) -> str:
    """Lowercase, strip whitespace, collapse spaces, unify nulls."""

def normalize_person_name(value: str) -> str:
    """Strip titles/suffixes, normalize Last,First → First Last."""

def normalize_company_name(value: str) -> str:
    """Strip Inc/LLC/Corp/Ltd/Co, normalize & → and."""

def normalize_address(value: str) -> str:
    """Expand abbreviations, normalize directionals."""

def normalize_phone(value: str) -> str:
    """Strip non-digits except leading +."""

def normalize_date(value: str, format_hint: str | None = None) -> str:
    """Parse to ISO 8601. Use format_hint if provided by LLM."""

def normalize_email(value: str) -> str:
    """Lowercase, strip mailto: prefix."""
```

---

## Module 5: Analyzers

### 5A: Clustered Analyzer

**File:** `clustered_analyzer.py`

```python
@dataclass
class ClusteredAnalysisResult:
    cluster_distribution: pd.DataFrame      # cluster_id, size, bucket
    match_scores: pd.DataFrame              # cluster_id, record_id, per-field scores, aggregate
    field_averages: pd.DataFrame            # field_name, avg_score across all clusters
    flagged_clusters: pd.DataFrame          # cluster_id, size, score, per-field, worst_pair
    cross_cluster_collisions: pd.DataFrame  # col_name, value, cluster_id_1, cluster_id_2
```

Key functions:

```python
def analyze_clusters(df: pd.DataFrame, column_map: ColumnMap) -> ClusteredAnalysisResult:
    """Main entry point. Orchestrates all sub-analyses."""

def compute_cluster_distribution(df: pd.DataFrame, cluster_col: str) -> pd.DataFrame:
    """Count records per cluster, assign to size buckets."""

def compute_within_cluster_similarity(
    df: pd.DataFrame,
    cluster_col: str,
    attribute_configs: dict[str, ColumnConfig],
    global_vectorizers: dict[str, TfidfVectorizer]   # <-- fit once on full dataset
) -> pd.DataFrame:
    """Pairwise similarity per attribute within each cluster."""

def flag_problem_clusters(
    match_scores: pd.DataFrame,
    cluster_distribution: pd.DataFrame,
    score_threshold: float = 0.8
) -> pd.DataFrame:
    """Large clusters with low match scores, ranked."""

def find_cross_cluster_collisions(
    df: pd.DataFrame,
    cluster_col: str,
    check_cols: list[str]
) -> pd.DataFrame:
    """Records sharing same value in check_col but different clusters."""
```

**Important implementation detail:** TF-IDF vectorizers for `free_text` columns must be fit once on the entire column across all records, then used to transform individual clusters. This ensures IDF weights are global and similarity scores are comparable across clusters.

```python
def fit_global_vectorizers(df: pd.DataFrame, column_map: ColumnMap) -> dict[str, TfidfVectorizer]:
    """Fit one TfidfVectorizer per free_text column on the full dataset."""
    vectorizers = {}
    for col_name, config in column_map.attribute_columns.items():
        if config.similarity_function == "tfidf_cosine":
            texts = df[col_name].fillna("").astype(str).values
            vectorizers[col_name] = TfidfVectorizer().fit(texts)
    return vectorizers
```

### 5B: Unclustered Analyzer

**File:** `unclustered_analyzer.py`

```python
@dataclass
class UnclusteredAnalysisResult:
    candidate_pairs: pd.DataFrame           # record_id_1, record_id_2, per-field scores, aggregate
    calibration_pairs: pd.DataFrame         # subset for user labeling
    matched_pairs: pd.DataFrame             # filtered by threshold
    pair_quality_summary: pd.DataFrame      # score distribution, field contributions
    threshold_used: float
```

Key functions:

```python
def find_candidate_pairs(
    df: pd.DataFrame,
    column_map: ColumnMap,
    blocking_cols: list[str] | None = None,
    min_similarity: float = 0.3
) -> pd.DataFrame:
    """All-pairs or blocked pairwise similarity computation."""

def calibrate_threshold(
    candidate_pairs: pd.DataFrame,
    user_labels: dict[tuple, bool],          # (id1, id2) → same_entity?
    default_threshold: float = 0.7
) -> float:
    """Derive threshold from user labels on curated pairs."""

def filter_and_rank_pairs(
    candidate_pairs: pd.DataFrame,
    threshold: float
) -> pd.DataFrame:
    """Filter to pairs above threshold, sort by score descending."""
```

### 5C: Similarity Functions (shared)

**File:** `similarity.py`

```python
def compare_values(val_a: str, val_b: str, method: str, **kwargs) -> float:
    """Dispatch to appropriate similarity function. Returns 0.0–1.0."""

def fuzzy_token_sort(a: str, b: str) -> float:
    """Token-sort fuzzy ratio. Handles word order variation."""

def fuzzy_ratio(a: str, b: str) -> float:
    """Simple Levenshtein-based fuzzy ratio."""

def exact(a: str, b: str) -> float:
    """1.0 if equal, 0.0 otherwise."""

def exact_normalized(a: str, b: str) -> float:
    """Exact match after stripping formatting (phone, ID)."""

def exact_parsed(a: str, b: str, tolerance_days: int = 0) -> float:
    """Parse both as dates, compare. Optionally allow N-day tolerance."""

def email_composite(a: str, b: str) -> float:
    """Split at @. Exact match domain (0.5 weight), fuzzy local part (0.5 weight)."""

def tfidf_cosine(vectors_a, vectors_b) -> float:
    """Cosine similarity on pre-computed TF-IDF vectors."""

def normalized_distance(a: float, b: float, range_val: float) -> float:
    """1.0 - |a-b|/range. Normalized to 0.0–1.0."""

def compare_groups(
    group_a: pd.DataFrame,
    group_b: pd.DataFrame,
    column_configs: dict[str, ColumnConfig],
    global_vectorizers: dict[str, TfidfVectorizer] | None = None
) -> dict[str, float]:
    """Unified function: within-cluster (a==b) or cross-cluster (a!=b) similarity."""
```

---

## Module 6: Reporter

**File:** `reporter.py`

### `run_sanity_checks(result: ClusteredAnalysisResult | UnclusteredAnalysisResult) -> list[SanityWarning]`

```python
@dataclass
class SanityWarning:
    severity: str                # "warning" | "error"
    condition: str               # what was detected
    likely_cause: str            # what probably went wrong
    message: str                 # user-facing message
    related_step: str            # which step's artifact to inspect
```

### `generate_summary(result, llm_client: LLMClient) -> str`

Extracts summary statistics from the analysis result, sends to LLM for narration.

### `compile_report(result, warnings: list, summary: str, normalization_report) -> AnalysisReport`

```python
@dataclass
class AnalysisReport:
    summary_text: str                              # LLM-narrated
    warnings: list[SanityWarning]                  # sanity check results
    normalization_report: NormalizationReport       # before/after samples
    cluster_distribution: pd.DataFrame | None       # clustered path
    match_scores: pd.DataFrame | None               # clustered path
    field_averages: pd.DataFrame | None             # clustered path
    flagged_clusters: pd.DataFrame | None           # clustered path
    cross_cluster_collisions: pd.DataFrame | None   # clustered path
    matched_pairs: pd.DataFrame | None              # unclustered path
    pair_quality_summary: pd.DataFrame | None       # unclustered path
    threshold_used: float | None                    # unclustered path
    charts: dict[str, bytes]                        # name → PNG bytes
```

---

## Data Flow Summary

```
CSV File
  │
  ▼
profile_columns()          → ColumnProfile per column
  │
  ▼
classify_columns() [LLM]   → Raw classification
  │
  ▼
validate_classification()   → Corrected classification + log
  │
  ▼
build_column_map()          → ColumnMap (+ user overrides)
  │
  ▼
normalize_dataframe()       → Normalized DataFrame + NormalizationReport
  │
  ├── cluster_id exists ──► analyze_clusters() → ClusteredAnalysisResult
  │                              │
  │                              ├── compute_cluster_distribution()
  │                              ├── fit_global_vectorizers()
  │                              ├── compute_within_cluster_similarity()
  │                              ├── flag_problem_clusters()
  │                              └── find_cross_cluster_collisions()
  │
  └── no cluster_id ──────► find_candidate_pairs() → candidate pairs
                                 │
                                 ├── curate_threshold_pairs() [LLM]
                                 ├── [user labels pairs]
                                 ├── calibrate_threshold()
                                 └── filter_and_rank_pairs()
                                      │
                                      ▼
                            run_sanity_checks()
                                      │
                                      ▼
                            generate_summary() [LLM]
                                      │
                                      ▼
                            compile_report() → AnalysisReport
```
