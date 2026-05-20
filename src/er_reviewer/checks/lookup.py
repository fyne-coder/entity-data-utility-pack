from __future__ import annotations

from pathlib import Path

from er_reviewer._csv_utils import read_dict_rows, require_columns


def lookup_entity(
    rows: list[dict[str, str]],
    *,
    id_column: str,
    id_value: str,
    cluster_column: str | None = None,
) -> list[dict[str, object]]:
    """Return a focused view of one row/entity and optional cluster siblings."""
    required = [id_column]
    if cluster_column:
        required.append(cluster_column)
    require_columns(rows[0].keys() if rows else [], required)

    match_indexes = [
        index for index, row in enumerate(rows) if (row.get(id_column) or "").strip() == id_value
    ]
    if not match_indexes:
        return []
    cluster_value = ""
    if cluster_column:
        cluster_value = (rows[match_indexes[0]].get(cluster_column) or "").strip()

    result_rows: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        relationship = ""
        if index in match_indexes:
            relationship = "match"
        elif (
            cluster_column
            and cluster_value
            and (row.get(cluster_column) or "").strip() == cluster_value
        ):
            relationship = "cluster_sibling"
        if not relationship:
            continue
        result: dict[str, object] = {column: value for column, value in row.items()}
        result["_lookup_relationship"] = relationship
        if cluster_column:
            result["_lookup_cluster"] = cluster_value
        result_rows.append(result)
    return result_rows


def lookup_entity_in_csv(
    path: str | Path,
    *,
    id_column: str,
    id_value: str,
    cluster_column: str | None = None,
    encoding: str = "utf-8",
    delimiter: str = ",",
) -> list[dict[str, object]]:
    return lookup_entity(
        read_dict_rows(path, encoding=encoding, delimiter=delimiter),
        id_column=id_column,
        id_value=id_value,
        cluster_column=cluster_column,
    )
