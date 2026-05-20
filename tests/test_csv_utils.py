from __future__ import annotations

from pathlib import Path

import pytest

from er_reviewer._csv_utils import (
    chunked_rows,
    iter_dict_row_chunks,
    iter_dict_rows,
    open_dict_row_source,
    read_dict_rows,
)


def test_iter_dict_rows_preserves_read_dict_rows_behavior(tmp_path: Path) -> None:
    path = tmp_path / "rows.csv"
    path.write_text("id,name\n1,Ada\n2,Grace\n", encoding="utf-8")

    assert list(iter_dict_rows(path)) == read_dict_rows(path)


def test_open_dict_row_source_exposes_fieldnames_and_lazy_rows(tmp_path: Path) -> None:
    path = tmp_path / "rows.tsv"
    path.write_text("id\tname\n1\tAda\n2\tGrace\n", encoding="utf-8")

    with open_dict_row_source(path, delimiter="\t") as source:
        assert source.fieldnames == ["id", "name"]
        assert next(source.rows) == {"id": "1", "name": "Ada"}
        assert list(source.rows) == [{"id": "2", "name": "Grace"}]


def test_chunked_rows_batches_iterables_without_materializing() -> None:
    rows = ({"id": str(index)} for index in range(5))

    assert list(chunked_rows(rows, chunk_size=2)) == [
        [{"id": "0"}, {"id": "1"}],
        [{"id": "2"}, {"id": "3"}],
        [{"id": "4"}],
    ]


def test_chunked_rows_rejects_invalid_chunk_size() -> None:
    with pytest.raises(ValueError, match="chunk_size"):
        list(chunked_rows([], chunk_size=0))


def test_iter_dict_row_chunks_reads_csv_in_batches(tmp_path: Path) -> None:
    path = tmp_path / "rows.csv"
    path.write_text("id\n1\n2\n3\n", encoding="utf-8")

    assert list(iter_dict_row_chunks(path, chunk_size=2)) == [
        [{"id": "1"}, {"id": "2"}],
        [{"id": "3"}],
    ]
