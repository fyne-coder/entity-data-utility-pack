from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from er_reviewer._csv_utils import open_dict_row_source, require_columns


@dataclass(frozen=True)
class ClusterSummary:
    cluster_id: str
    size: int
    size_bucket: str
    average_match_score: float | None = None
    outlier_score: float = 0.0
    outlier_reason: str = ""

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["average_match_score"] = (
            "" if self.average_match_score is None else round(self.average_match_score, 4)
        )
        data["outlier_score"] = round(self.outlier_score, 4)
        return data


def size_bucket(size: int) -> str:
    if size == 1:
        return "1"
    if size <= 5:
        return "2-5"
    if size <= 10:
        return "6-10"
    if size <= 25:
        return "11-25"
    if size <= 50:
        return "26-50"
    if size <= 100:
        return "51-100"
    if size <= 250:
        return "101-250"
    if size <= 500:
        return "251-500"
    return "500+"


def summarize_clusters(
    rows: list[dict[str, str]],
    *,
    cluster_column: str,
    match_columns: Iterable[str] | None = None,
    match_prefix: str | None = None,
    large_cluster_size: int = 10,
    low_match_score: float = 0.85,
) -> list[ClusterSummary]:
    require_columns(rows[0].keys() if rows else [], [cluster_column])
    columns = list(rows[0].keys()) if rows else []
    return _summarize_cluster_rows(
        rows,
        fieldnames=columns,
        cluster_column=cluster_column,
        match_columns=match_columns,
        match_prefix=match_prefix,
        large_cluster_size=large_cluster_size,
        low_match_score=low_match_score,
    )


def _summarize_cluster_rows(
    rows: Iterable[dict[str, str]],
    *,
    fieldnames: Iterable[str],
    cluster_column: str,
    match_columns: Iterable[str] | None = None,
    match_prefix: str | None = None,
    large_cluster_size: int,
    low_match_score: float,
) -> list[ClusterSummary]:
    require_columns(fieldnames, [cluster_column])
    columns = list(fieldnames)
    if match_columns is None and match_prefix:
        match_columns = [column for column in columns if column.startswith(match_prefix)]
    match_columns = list(match_columns or [])

    cluster_sizes: dict[str, int] = defaultdict(int)
    score_sums: dict[str, float] = defaultdict(float)
    score_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        cluster_id = (row.get(cluster_column) or "").strip()
        if cluster_id:
            cluster_sizes[cluster_id] += 1
            for column in match_columns:
                raw_value = (row.get(column) or "").strip()
                try:
                    score_sums[cluster_id] += float(raw_value)
                except ValueError:
                    continue
                score_counts[cluster_id] += 1

    summaries: list[ClusterSummary] = []
    for cluster_id, size in cluster_sizes.items():
        average_score = (
            score_sums[cluster_id] / score_counts[cluster_id] if score_counts[cluster_id] else None
        )
        outlier_score, outlier_reason = _cluster_outlier(
            size=size,
            average_match_score=average_score,
            large_cluster_size=large_cluster_size,
            low_match_score=low_match_score,
        )
        summaries.append(
            ClusterSummary(
                cluster_id=cluster_id,
                size=size,
                size_bucket=size_bucket(size),
                average_match_score=average_score,
                outlier_score=outlier_score,
                outlier_reason=outlier_reason,
            )
        )
    return sorted(summaries, key=lambda summary: (-summary.size, summary.cluster_id))


def summarize_clusters_in_csv(
    path: str | Path,
    *,
    cluster_column: str,
    match_columns: Iterable[str] | None = None,
    match_prefix: str | None = None,
    large_cluster_size: int = 10,
    low_match_score: float = 0.85,
    encoding: str = "utf-8",
    delimiter: str = ",",
) -> list[ClusterSummary]:
    with open_dict_row_source(path, encoding=encoding, delimiter=delimiter) as source:
        return _summarize_cluster_rows(
            source.rows,
            fieldnames=source.fieldnames,
            cluster_column=cluster_column,
            match_columns=match_columns,
            match_prefix=match_prefix,
            large_cluster_size=large_cluster_size,
            low_match_score=low_match_score,
        )


def _cluster_outlier(
    *,
    size: int,
    average_match_score: float | None,
    large_cluster_size: int,
    low_match_score: float,
) -> tuple[float, str]:
    reasons: list[str] = []
    score = 0.0
    if size >= large_cluster_size:
        reasons.append("large_cluster")
        score += min(1.0, size / max(large_cluster_size, 1)) * 0.5
    if average_match_score is not None and average_match_score < low_match_score:
        reasons.append("low_match_score")
        score += min(1.0, low_match_score - average_match_score + 0.5) * 0.5
    return min(score, 1.0), "|".join(reasons)
