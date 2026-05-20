from __future__ import annotations

from collections.abc import Iterable
from importlib import import_module
from typing import Any, cast

from er_reviewer.checks.cardinality import find_one_to_many_mappings
from er_reviewer.checks.clusters import summarize_clusters
from er_reviewer.checks.duplicates import find_duplicate_candidates
from er_reviewer.compare.exports import compare_export_membership
from er_reviewer.io.table import TableFormat, read_table_rows, rows_from_dataframe
from er_reviewer.profiling.columns import profile_columns


def profile(dataframe: object, *, engine: str = "python") -> object:
    _validate_engine(engine)
    rows = rows_from_dataframe(dataframe)
    fieldnames = list(cast(Any, dataframe).columns)
    return _dataframe_from_records(
        [item.to_dict() for item in profile_columns(rows, fieldnames=fieldnames)]
    )


def profile_path(
    path: str,
    *,
    format: TableFormat = "auto",
    encoding: str = "utf-8",
    delimiter: str = ",",
    sheet_name: str | int = 0,
    engine: str = "python",
) -> object:
    _validate_engine(engine)
    rows = read_table_rows(
        path,
        format=format,
        encoding=encoding,
        delimiter=delimiter,
        sheet_name=sheet_name,
    )
    return _dataframe_from_records([item.to_dict() for item in profile_columns(rows)])


def find_duplicates(
    dataframe: object,
    *,
    block: str,
    match: Iterable[str],
    id_column: str | None = None,
    threshold: float = 0.85,
    scorer: str = "auto",
    normalization: str = "basic",
    engine: str = "python",
) -> object:
    _validate_engine(engine)
    rows = rows_from_dataframe(dataframe)
    return _dataframe_from_records(
        [
            item.to_dict()
            for item in find_duplicate_candidates(
                rows,
                block_column=block,
                match_columns=match,
                id_column=id_column,
                threshold=threshold,
                scorer=scorer,
                normalization=normalization,
            )
        ]
    )


def mapping_conflicts(
    dataframe: object,
    *,
    left: str,
    right: str,
    engine: str = "python",
) -> object:
    _validate_engine(engine)
    rows = rows_from_dataframe(dataframe)
    return _dataframe_from_records(
        [
            item.to_dict()
            for item in find_one_to_many_mappings(rows, left_column=left, right_column=right)
        ]
    )


def compare_exports(
    old_dataframe: object,
    new_dataframe: object,
    *,
    id_column: str,
    member_column: str,
    include_narratives: bool = False,
    engine: str = "python",
) -> object:
    _validate_engine(engine)
    return _dataframe_from_records(
        [
            item.to_dict()
            for item in compare_export_membership(
                rows_from_dataframe(old_dataframe),
                rows_from_dataframe(new_dataframe),
                id_column=id_column,
                member_column=member_column,
                include_narratives=include_narratives,
            )
        ]
    )


def cluster_summary(
    dataframe: object,
    *,
    cluster: str,
    match_columns: Iterable[str] | None = None,
    match_prefix: str | None = None,
    engine: str = "python",
) -> object:
    _validate_engine(engine)
    return _dataframe_from_records(
        [
            item.to_dict()
            for item in summarize_clusters(
                rows_from_dataframe(dataframe),
                cluster_column=cluster,
                match_columns=match_columns,
                match_prefix=match_prefix,
            )
        ]
    )


def _validate_engine(engine: str) -> None:
    if engine != "python":
        raise ValueError(
            f"Unsupported API engine: {engine}. The current implementation supports only 'python'."
        )


def _dataframe_from_records(records: list[dict[str, object]]) -> object:
    try:
        pandas = import_module("pandas")
    except ImportError as exc:
        raise RuntimeError("pandas is required for er_reviewer.api functions.") from exc
    dataframe_class = cast(Any, pandas).DataFrame
    return dataframe_class(records)
