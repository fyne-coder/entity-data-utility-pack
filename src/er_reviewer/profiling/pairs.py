from __future__ import annotations

import csv
from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from er_reviewer._csv_utils import read_dict_rows


@dataclass(frozen=True)
class GroupingCandidate:
    column: str
    most_common_value: str
    most_common_count: int
    total_rows: int
    dominance_ratio: float

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["dominance_ratio"] = round(self.dominance_ratio, 4)
        return data


@dataclass(frozen=True)
class IdenticalColumnPair:
    left_column: str
    right_column: str
    compared_rows: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def find_grouping_candidates(
    rows: list[dict[str, str]],
    *,
    threshold: float = 0.5,
) -> list[GroupingCandidate]:
    """Find columns dominated by one value, useful for pre-grouping or partitioning."""
    if not rows:
        return []
    total_rows = len(rows)
    candidates: list[GroupingCandidate] = []
    for column in rows[0]:
        counts = Counter((row.get(column) or "").strip() for row in rows)
        most_common_value, most_common_count = counts.most_common(1)[0]
        dominance_ratio = most_common_count / total_rows
        if dominance_ratio >= threshold:
            candidates.append(
                GroupingCandidate(
                    column=column,
                    most_common_value=most_common_value,
                    most_common_count=most_common_count,
                    total_rows=total_rows,
                    dominance_ratio=dominance_ratio,
                )
            )
    return sorted(candidates, key=lambda candidate: (-candidate.dominance_ratio, candidate.column))


def find_identical_column_pairs(rows: list[dict[str, str]]) -> list[IdenticalColumnPair]:
    """Find columns with exactly identical values across all rows."""
    if not rows:
        return []
    columns = list(rows[0])
    fingerprints = {column: sha256() for column in columns}
    for row in rows:
        for column in columns:
            _update_fingerprint(fingerprints[column], row.get(column, ""))
    return _pairs_from_fingerprints(
        {column: digest.digest() for column, digest in fingerprints.items()},
        compared_rows=len(rows),
    )


def _update_fingerprint(digest: Any, value: str) -> None:
    encoded = value.encode("utf-8", errors="surrogatepass")
    digest.update(len(encoded).to_bytes(8, "big"))
    digest.update(b"\0")
    digest.update(encoded)
    digest.update(b"\0")


def _pairs_from_fingerprints(
    fingerprints: dict[str, bytes],
    *,
    compared_rows: int,
) -> list[IdenticalColumnPair]:
    columns = list(fingerprints)
    pairs: list[IdenticalColumnPair] = []
    for left_index, left_column in enumerate(columns):
        for right_column in columns[left_index + 1 :]:
            if fingerprints[left_column] == fingerprints[right_column]:
                pairs.append(
                    IdenticalColumnPair(
                        left_column=left_column,
                        right_column=right_column,
                        compared_rows=compared_rows,
                    )
                )
    return pairs


def find_grouping_candidates_in_csv(
    path: str | Path,
    *,
    threshold: float = 0.5,
) -> list[GroupingCandidate]:
    return find_grouping_candidates(read_dict_rows(path), threshold=threshold)


def find_identical_column_pairs_in_csv(path: str | Path) -> list[IdenticalColumnPair]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        fingerprints = {column: sha256() for column in columns}
        compared_rows = 0
        for row in reader:
            compared_rows += 1
            for column in columns:
                _update_fingerprint(fingerprints[column], row.get(column, ""))
    if compared_rows == 0:
        return []
    return _pairs_from_fingerprints(
        {column: digest.digest() for column, digest in fingerprints.items()},
        compared_rows=compared_rows,
    )
