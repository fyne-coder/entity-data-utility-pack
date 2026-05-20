from pathlib import Path

import pytest

from er_reviewer.io.table import read_table_rows, resolve_table_format


def test_read_table_rows_supports_csv_and_tsv(tmp_path: Path) -> None:
    csv_path = tmp_path / "rows.csv"
    tsv_path = tmp_path / "rows.tsv"
    csv_path.write_text("id,name\n1,Ada\n", encoding="utf-8")
    tsv_path.write_text("id\tname\n2\tGrace\n", encoding="utf-8")

    assert read_table_rows(csv_path) == [{"id": "1", "name": "Ada"}]
    assert read_table_rows(tsv_path) == [{"id": "2", "name": "Grace"}]


def test_read_table_rows_supports_xlsx_when_tables_extra_is_available(tmp_path: Path) -> None:
    pandas = pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    path = tmp_path / "rows.xlsx"
    pandas.DataFrame([{"id": "1", "name": "Ada"}]).to_excel(path, index=False)

    assert read_table_rows(path) == [{"id": "1", "name": "Ada"}]


def test_read_table_rows_supports_parquet_when_tables_extra_is_available(tmp_path: Path) -> None:
    pandas = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    path = tmp_path / "rows.parquet"
    pandas.DataFrame([{"id": "1", "amount": 10.5}]).to_parquet(path, index=False)

    assert read_table_rows(path) == [{"id": "1", "amount": "10.5"}]


def test_resolve_table_format_requires_hint_for_unknown_suffix() -> None:
    with pytest.raises(ValueError, match="Could not infer input format"):
        resolve_table_format("rows.data")
