from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import cast

from er_reviewer._csv_utils import open_dict_row_source

DEFAULT_DUMMY_VALUES = {
    "",
    "0",
    "-1",
    "1900-01-01",
    "9999-12-31",
    "n/a",
    "na",
    "none",
    "null",
    "sample",
    "test",
    "undefined",
    "unknown",
}


@dataclass(frozen=True)
class ColumnProfile:
    column: str
    total_rows: int
    blank_count: int
    null_like_count: int
    unique_count: int
    unique_ratio: float
    top_values: dict[str, int] = field(default_factory=dict)
    likely_unique_id: bool = False
    inferred_type: str = "empty"
    numeric_parse_rate: float = 0.0
    datetime_parse_rate: float = 0.0
    min_value: str = ""
    max_value: str = ""
    q1: str = ""
    median: str = ""
    q3: str = ""
    currency_like: bool = False
    invalid_examples: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["top_values"] = "; ".join(
            f"{value}={count}" for value, count in self.top_values.items()
        )
        data["invalid_examples"] = "|".join(self.invalid_examples)
        return data


def profile_csv_columns(
    path: str | Path,
    *,
    dummy_values: set[str] | None = None,
    top_n: int = 10,
    encoding: str = "utf-8",
    delimiter: str = ",",
) -> list[ColumnProfile]:
    """Return generic column-level profile statistics for a CSV file."""
    with open_dict_row_source(path, encoding=encoding, delimiter=delimiter) as source:
        return profile_columns(
            source.rows,
            fieldnames=source.fieldnames,
            dummy_values=dummy_values,
            top_n=top_n,
        )


def profile_columns(
    rows: Iterable[dict[str, str]],
    *,
    fieldnames: list[str] | None = None,
    dummy_values: set[str] | None = None,
    top_n: int = 10,
) -> list[ColumnProfile]:
    """Return column-level profile statistics for in-memory rows."""
    dummy_values = {value.lower() for value in (dummy_values or DEFAULT_DUMMY_VALUES)}
    columns = list(fieldnames or [])
    counters: dict[str, Counter[str]] = {column: Counter() for column in columns}
    blank_counts = {column: 0 for column in columns}
    null_like_counts = {column: 0 for column in columns}
    values_by_column: dict[str, list[str]] = {column: [] for column in columns}
    total_rows = 0

    for row in rows:
        total_rows += 1
        if fieldnames is None:
            for column in row:
                if column not in counters:
                    columns.append(column)
                    counters[column] = (
                        Counter({"": total_rows - 1}) if total_rows > 1 else Counter()
                    )
                    blank_counts[column] = total_rows - 1
                    null_like_counts[column] = total_rows - 1 if "" in dummy_values else 0
                    values_by_column[column] = [""] * (total_rows - 1)
        for column in columns:
            value = row.get(column) or ""
            normalized = value.strip()
            if not normalized:
                blank_counts[column] += 1
            if normalized.lower() in dummy_values:
                null_like_counts[column] += 1
            counters[column][normalized] += 1
            values_by_column[column].append(normalized)

    profiles: list[ColumnProfile] = []
    for column in columns:
        unique_count = len(counters[column])
        unique_ratio = unique_count / total_rows if total_rows else 0.0
        non_blank_rows = total_rows - blank_counts[column]
        column_name = column.lower()
        looks_identifier_like = "id" in column_name or column_name.endswith("_key")
        likely_unique_id = bool(
            looks_identifier_like
            and non_blank_rows
            and unique_count == non_blank_rows
            and total_rows > 1
        )
        type_stats = _profile_type(values_by_column[column], dummy_values)
        profiles.append(
            ColumnProfile(
                column=column,
                total_rows=total_rows,
                blank_count=blank_counts[column],
                null_like_count=null_like_counts[column],
                unique_count=unique_count,
                unique_ratio=round(unique_ratio, 4),
                top_values=dict(counters[column].most_common(top_n)),
                likely_unique_id=likely_unique_id,
                inferred_type="identifier"
                if likely_unique_id
                else str(type_stats["inferred_type"]),
                numeric_parse_rate=float(str(type_stats["numeric_parse_rate"])),
                datetime_parse_rate=float(str(type_stats["datetime_parse_rate"])),
                min_value=str(type_stats["min_value"]),
                max_value=str(type_stats["max_value"]),
                q1=str(type_stats["q1"]),
                median=str(type_stats["median"]),
                q3=str(type_stats["q3"]),
                currency_like=bool(type_stats["currency_like"]),
                invalid_examples=cast(tuple[str, ...], type_stats["invalid_examples"]),
            )
        )

    return profiles


def _profile_type(values: list[str], dummy_values: set[str]) -> dict[str, object]:
    meaningful = [value for value in values if value and value.lower() not in dummy_values]
    if not meaningful:
        return _type_result("empty", 0.0, 0.0)

    numeric_values: list[float] = []
    numeric_failures: list[str] = []
    currency_markers = 0
    for value in meaningful:
        numeric = _parse_number(value)
        if numeric is None:
            numeric_failures.append(value)
        else:
            numeric_values.append(numeric)
        if _looks_currency_like(value):
            currency_markers += 1

    datetime_values: list[datetime] = []
    datetime_failures: list[str] = []
    for value in meaningful:
        parsed = _parse_datetime(value)
        if parsed is None:
            datetime_failures.append(value)
        else:
            datetime_values.append(parsed)

    numeric_rate = round(len(numeric_values) / len(meaningful), 4)
    datetime_rate = round(len(datetime_values) / len(meaningful), 4)
    currency_like = bool(numeric_values) and currency_markers / len(meaningful) >= 0.5
    unique_ratio = len(set(meaningful)) / len(meaningful)

    if numeric_rate >= 0.75:
        ordered = sorted(numeric_values)
        return {
            "inferred_type": "currency" if currency_like else "numeric",
            "numeric_parse_rate": numeric_rate,
            "datetime_parse_rate": datetime_rate,
            "min_value": _format_number(ordered[0]),
            "max_value": _format_number(ordered[-1]),
            "q1": _format_number(_quantile(ordered, 0.25)),
            "median": _format_number(_quantile(ordered, 0.5)),
            "q3": _format_number(_quantile(ordered, 0.75)),
            "currency_like": currency_like,
            "invalid_examples": tuple(_sample_unique(numeric_failures)),
        }
    if datetime_rate >= 0.75:
        ordered_dates = sorted(datetime_values)
        return {
            "inferred_type": "datetime",
            "numeric_parse_rate": numeric_rate,
            "datetime_parse_rate": datetime_rate,
            "min_value": ordered_dates[0].date().isoformat(),
            "max_value": ordered_dates[-1].date().isoformat(),
            "q1": "",
            "median": "",
            "q3": "",
            "currency_like": False,
            "invalid_examples": tuple(_sample_unique(datetime_failures)),
        }
    inferred_type = "categorical" if unique_ratio <= 0.5 else "text"
    return {
        "inferred_type": inferred_type,
        "numeric_parse_rate": numeric_rate,
        "datetime_parse_rate": datetime_rate,
        "min_value": "",
        "max_value": "",
        "q1": "",
        "median": "",
        "q3": "",
        "currency_like": False,
        "invalid_examples": (),
    }


def _type_result(
    inferred_type: str,
    numeric_parse_rate: float,
    datetime_parse_rate: float,
) -> dict[str, object]:
    return {
        "inferred_type": inferred_type,
        "numeric_parse_rate": numeric_parse_rate,
        "datetime_parse_rate": datetime_parse_rate,
        "min_value": "",
        "max_value": "",
        "q1": "",
        "median": "",
        "q3": "",
        "currency_like": False,
        "invalid_examples": (),
    }


def _parse_number(value: str) -> float | None:
    candidate = value.strip()
    if not candidate:
        return None
    negative = candidate.startswith("(") and candidate.endswith(")")
    if negative:
        candidate = candidate[1:-1]
    candidate = (
        candidate.replace("$", "")
        .replace("€", "")
        .replace("£", "")
        .replace(",", "")
        .replace("%", "")
        .strip()
    )
    try:
        parsed = float(candidate)
    except ValueError:
        return None
    return -parsed if negative else parsed


def _looks_currency_like(value: str) -> bool:
    return any(marker in value for marker in ("$", "€", "£")) or "," in value


def _parse_datetime(value: str) -> datetime | None:
    candidate = value.strip()
    if not candidate:
        return None
    for date_format in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(candidate, date_format)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] + (values[upper] - values[lower]) * fraction


def _format_number(value: float) -> str:
    rounded = round(value, 4)
    if rounded.is_integer():
        return str(int(rounded))
    return str(rounded)


def _sample_unique(values: list[str], limit: int = 3) -> tuple[str, ...]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
        if len(seen) == limit:
            break
    return tuple(seen)
