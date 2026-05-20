from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from er_reviewer._csv_utils import open_dict_row_source, require_columns


@dataclass(frozen=True)
class OneToManyIssue:
    left_column: str
    left_value: str
    right_column: str
    distinct_right_count: int
    right_values: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["right_values"] = "|".join(self.right_values)
        return data


def find_one_to_many_mappings(
    rows: list[dict[str, str]],
    *,
    left_column: str,
    right_column: str,
    ignore_blank: bool = True,
) -> list[OneToManyIssue]:
    """Find values in one column that map to multiple distinct values in another."""
    require_columns(rows[0].keys() if rows else [], [left_column, right_column])
    return _find_one_to_many_mappings_from_rows(
        rows,
        left_column=left_column,
        right_column=right_column,
        ignore_blank=ignore_blank,
    )


def _find_one_to_many_mappings_from_rows(
    rows: Iterable[dict[str, str]],
    *,
    left_column: str,
    right_column: str,
    ignore_blank: bool,
) -> list[OneToManyIssue]:
    """Find one-to-many mappings from an already validated row stream."""

    mappings: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        left_value = (row.get(left_column) or "").strip()
        right_value = (row.get(right_column) or "").strip()
        if ignore_blank and (not left_value or not right_value):
            continue
        mappings[left_value].add(right_value)

    issues = [
        OneToManyIssue(
            left_column=left_column,
            left_value=left_value,
            right_column=right_column,
            distinct_right_count=len(right_values),
            right_values=tuple(sorted(right_values)),
        )
        for left_value, right_values in mappings.items()
        if len(right_values) > 1
    ]
    return sorted(issues, key=lambda issue: (-issue.distinct_right_count, issue.left_value))


def find_one_to_many_mappings_in_csv(
    path: str | Path,
    *,
    left_column: str,
    right_column: str,
    ignore_blank: bool = True,
    encoding: str = "utf-8",
    delimiter: str = ",",
) -> list[OneToManyIssue]:
    with open_dict_row_source(path, encoding=encoding, delimiter=delimiter) as source:
        require_columns(source.fieldnames, [left_column, right_column])
        return _find_one_to_many_mappings_from_rows(
            source.rows,
            left_column=left_column,
            right_column=right_column,
            ignore_blank=ignore_blank,
        )
