from __future__ import annotations

from collections.abc import Iterable
from importlib import import_module
from pathlib import Path
from typing import Any, Literal, cast

from er_reviewer._csv_utils import read_dict_rows

TableFormat = Literal["auto", "csv", "tsv", "xlsx", "parquet"]


def read_table_rows(
    path: str | Path,
    *,
    format: TableFormat = "auto",
    encoding: str = "utf-8",
    delimiter: str = ",",
    sheet_name: str | int = 0,
) -> list[dict[str, str]]:
    """Read a supported tabular file into normalized string dictionaries.

    CSV/TSV input stays dependency-free. Excel and Parquet are optional analyst
    conveniences and use pandas lazily so the core CLI can still install small.
    """
    table_path = Path(path)
    resolved_format = resolve_table_format(table_path, format=format)
    if resolved_format == "csv":
        return read_dict_rows(table_path, encoding=encoding, delimiter=delimiter)
    if resolved_format == "tsv":
        return read_dict_rows(table_path, encoding=encoding, delimiter="\t")
    if resolved_format == "xlsx":
        pandas = _load_pandas("Excel input")
        frame = cast(Any, pandas).read_excel(table_path, sheet_name=sheet_name)
        return rows_from_dataframe(frame)
    if resolved_format == "parquet":
        pandas = _load_pandas("Parquet input")
        frame = cast(Any, pandas).read_parquet(table_path)
        return rows_from_dataframe(frame)
    raise ValueError(f"Unsupported table format: {resolved_format}")


def rows_from_dataframe(dataframe: object) -> list[dict[str, str]]:
    """Normalize a pandas-like DataFrame to string rows for core analyzers."""
    if not hasattr(dataframe, "to_dict"):
        raise TypeError("Expected a pandas DataFrame-like object with to_dict().")
    records = cast(Any, dataframe).to_dict(orient="records")
    return [normalize_record(record) for record in cast(Iterable[dict[object, object]], records)]


def normalize_record(record: dict[object, object]) -> dict[str, str]:
    pandas = _try_load_pandas()
    normalized: dict[str, str] = {}
    for column, value in record.items():
        if value is None:
            normalized[str(column)] = ""
            continue
        if pandas is not None and bool(cast(Any, pandas).isna(value)):
            normalized[str(column)] = ""
            continue
        normalized[str(column)] = str(value)
    return normalized


def resolve_table_format(path: str | Path, *, format: TableFormat = "auto") -> str:
    if format != "auto":
        return format
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".tsv", ".tab"}:
        return "tsv"
    if suffix in {".xlsx", ".xls"}:
        return "xlsx"
    if suffix in {".parquet", ".pq"}:
        return "parquet"
    raise ValueError(
        "Could not infer input format. Use --format csv|tsv|xlsx|parquet for this file."
    )


def _load_pandas(feature: str) -> object:
    pandas = _try_load_pandas()
    if pandas is None:
        raise RuntimeError(
            f"{feature} requires pandas plus the relevant file-format dependency. "
            "Install er-reviewer with the 'tables' extra."
        )
    return pandas


def _try_load_pandas() -> object | None:
    try:
        return import_module("pandas")
    except ImportError:
        return None
