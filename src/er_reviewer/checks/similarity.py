from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from er_reviewer._csv_utils import read_dict_rows, require_columns

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


@dataclass(frozen=True)
class ClusterPairSimilarity:
    left_cluster_id: str
    right_cluster_id: str
    similarity: float
    compared_columns: tuple[str, ...]
    band: str = ""
    recommendation: str = ""

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["similarity"] = round(self.similarity, 4)
        data["compared_columns"] = "|".join(self.compared_columns)
        return data


def tokenize(value: str) -> set[str]:
    return {token.casefold() for token in TOKEN_RE.findall(value)}


def jaccard_similarity(left: str, right: str) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def compare_cluster_pairs(
    detail_rows: list[dict[str, str]],
    pair_rows: list[dict[str, str]],
    *,
    cluster_column: str,
    left_pair_column: str,
    right_pair_column: str,
    compare_columns: Iterable[str],
    method: str = "jaccard",
    review_threshold: float = 0.65,
    likely_match_threshold: float = 0.85,
) -> list[ClusterPairSimilarity]:
    compare_columns = list(compare_columns)
    require_columns(
        detail_rows[0].keys() if detail_rows else [], [cluster_column, *compare_columns]
    )
    require_columns(pair_rows[0].keys() if pair_rows else [], [left_pair_column, right_pair_column])

    cluster_text: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for row in detail_rows:
        cluster_id = (row.get(cluster_column) or "").strip()
        if not cluster_id:
            continue
        for column in compare_columns:
            cluster_text[cluster_id][column].append(row.get(column, ""))

    pairs = [
        (
            (pair.get(left_pair_column) or "").strip(),
            (pair.get(right_pair_column) or "").strip(),
        )
        for pair in pair_rows
    ]
    if method == "tfidf":
        return _compare_cluster_pairs_tfidf(
            cluster_text,
            pairs,
            compare_columns,
            review_threshold=review_threshold,
            likely_match_threshold=likely_match_threshold,
        )
    if method != "jaccard":
        raise ValueError(f"Unknown similarity method: {method}")

    similarities: list[ClusterPairSimilarity] = []
    for left_id, right_id in pairs:
        column_scores: list[float] = []
        for column in compare_columns:
            left_text = " ".join(cluster_text[left_id][column])
            right_text = " ".join(cluster_text[right_id][column])
            column_scores.append(jaccard_similarity(left_text, right_text))
        score = sum(column_scores) / len(column_scores) if column_scores else 0.0
        similarities.append(
            ClusterPairSimilarity(
                left_cluster_id=left_id,
                right_cluster_id=right_id,
                similarity=score,
                compared_columns=tuple(compare_columns),
                band=similarity_band(
                    score,
                    review_threshold=review_threshold,
                    likely_match_threshold=likely_match_threshold,
                ),
                recommendation=similarity_recommendation(
                    score,
                    review_threshold=review_threshold,
                    likely_match_threshold=likely_match_threshold,
                ),
            )
        )
    return sorted(
        similarities,
        key=lambda item: (
            -item.similarity,
            item.left_cluster_id,
            item.right_cluster_id,
        ),
    )


def _compare_cluster_pairs_tfidf(
    cluster_text: dict[str, dict[str, list[str]]],
    pairs: list[tuple[str, str]],
    compare_columns: list[str],
    review_threshold: float,
    likely_match_threshold: float,
) -> list[ClusterPairSimilarity]:
    try:
        feature_extraction = import_module("sklearn.feature_extraction.text")
        pairwise = import_module("sklearn.metrics.pairwise")
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn is not installed. Install the analysis extra or use jaccard."
        ) from exc
    tfidf_vectorizer = cast(Any, feature_extraction).TfidfVectorizer
    cosine_similarity = cast(Any, cast(Any, pairwise).cosine_similarity)

    cluster_docs = {
        cluster_id: " ".join(
            " ".join(values) for column, values in columns.items() if column in compare_columns
        )
        for cluster_id, columns in cluster_text.items()
    }
    ordered_ids = sorted(cluster_docs)
    if not ordered_ids:
        return []
    vectorizer = tfidf_vectorizer(lowercase=True)
    vectors = vectorizer.fit_transform([cluster_docs[cluster_id] for cluster_id in ordered_ids])
    index_by_cluster = {cluster_id: index for index, cluster_id in enumerate(ordered_ids)}

    similarities: list[ClusterPairSimilarity] = []
    for left_id, right_id in pairs:
        if left_id not in index_by_cluster or right_id not in index_by_cluster:
            score = 0.0
        else:
            left_vector = vectors[index_by_cluster[left_id]]
            right_vector = vectors[index_by_cluster[right_id]]
            score = float(cosine_similarity(left_vector, right_vector)[0, 0])
        similarities.append(
            ClusterPairSimilarity(
                left_cluster_id=left_id,
                right_cluster_id=right_id,
                similarity=score,
                compared_columns=tuple(compare_columns),
                band=similarity_band(
                    score,
                    review_threshold=review_threshold,
                    likely_match_threshold=likely_match_threshold,
                ),
                recommendation=similarity_recommendation(
                    score,
                    review_threshold=review_threshold,
                    likely_match_threshold=likely_match_threshold,
                ),
            )
        )
    return sorted(
        similarities,
        key=lambda item: (
            -item.similarity,
            item.left_cluster_id,
            item.right_cluster_id,
        ),
    )


def compare_cluster_pairs_csv(
    details_path: str | Path,
    pairs_path: str | Path,
    *,
    cluster_column: str,
    left_pair_column: str,
    right_pair_column: str,
    compare_columns: Iterable[str],
    method: str = "jaccard",
    review_threshold: float = 0.65,
    likely_match_threshold: float = 0.85,
    details_encoding: str = "utf-8",
    pairs_encoding: str = "utf-8",
    details_delimiter: str = ",",
    pairs_delimiter: str = ",",
) -> list[ClusterPairSimilarity]:
    return compare_cluster_pairs(
        read_dict_rows(details_path, encoding=details_encoding, delimiter=details_delimiter),
        read_dict_rows(pairs_path, encoding=pairs_encoding, delimiter=pairs_delimiter),
        cluster_column=cluster_column,
        left_pair_column=left_pair_column,
        right_pair_column=right_pair_column,
        compare_columns=compare_columns,
        method=method,
        review_threshold=review_threshold,
        likely_match_threshold=likely_match_threshold,
    )


def similarity_band(
    score: float,
    *,
    review_threshold: float = 0.65,
    likely_match_threshold: float = 0.85,
) -> str:
    _validate_thresholds(
        review_threshold=review_threshold,
        likely_match_threshold=likely_match_threshold,
    )
    if score >= likely_match_threshold:
        return "likely_match"
    if score >= review_threshold:
        return "review"
    return "low_similarity"


def similarity_recommendation(
    score: float,
    *,
    review_threshold: float = 0.65,
    likely_match_threshold: float = 0.85,
) -> str:
    band = similarity_band(
        score,
        review_threshold=review_threshold,
        likely_match_threshold=likely_match_threshold,
    )
    if band == "likely_match":
        return "prioritize_review"
    if band == "review":
        return "review_if_relevant"
    return "ignore_unless_context_requires"


def _validate_thresholds(
    *,
    review_threshold: float,
    likely_match_threshold: float,
) -> None:
    if review_threshold > likely_match_threshold:
        raise ValueError("review_threshold must be less than or equal to likely_match_threshold.")
