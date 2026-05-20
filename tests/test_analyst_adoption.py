from pathlib import Path
from typing import Any, cast

import pytest

from er_reviewer.cli import main
from er_reviewer.compare.exports import compare_export_membership
from er_reviewer.profiling.columns import profile_csv_columns
from er_reviewer.reporting.redaction import redact_rows

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "sample_data"


def test_richer_profile_detects_currency_dates_and_invalid_examples() -> None:
    profiles = {
        profile.column: profile
        for profile in profile_csv_columns(SAMPLE_DATA / "financial_extract.csv")
    }

    assert profiles["balance"].inferred_type == "currency"
    assert profiles["balance"].numeric_parse_rate == 0.75
    assert profiles["balance"].invalid_examples == ("not available",)
    assert profiles["statement_date"].inferred_type == "datetime"
    assert profiles["statement_date"].datetime_parse_rate == 1.0
    assert profiles["status"].inferred_type == "categorical"


def test_compare_export_membership_adds_reassignment_and_split_merge_narratives() -> None:
    old_rows = [
        {"group": "g1", "member": "a"},
        {"group": "g1", "member": "b"},
        {"group": "g2", "member": "c"},
    ]
    new_rows = [
        {"group": "g3", "member": "a"},
        {"group": "g4", "member": "b"},
        {"group": "g4", "member": "c"},
    ]

    rows = [
        issue.to_dict()
        for issue in compare_export_membership(
            old_rows,
            new_rows,
            id_column="group",
            member_column="member",
            include_narratives=True,
        )
    ]

    assert any(row["category"] == "member_reassigned" and row["id_value"] == "a" for row in rows)
    assert any(row["category"] == "split" and row["id_value"] == "g1" for row in rows)
    assert any(row["category"] == "merged" and row["id_value"] == "g4" for row in rows)


def test_redact_rows_masks_selected_columns() -> None:
    rows = redact_rows(
        [{"id": "1", "customer_name": "Acme Corporation"}],
        columns=["customer_name"],
    )

    assert rows == [{"id": "1", "customer_name": "[redacted]"}]


def test_cli_lookup_writes_cluster_siblings(tmp_path: Path) -> None:
    output = tmp_path / "lookup.csv"

    exit_code = main(
        [
            "lookup",
            str(SAMPLE_DATA / "details.csv"),
            "--id",
            "record_id",
            "--value",
            "e001",
            "--cluster",
            "entity_id",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    content = output.read_text()
    assert "cluster_sibling" in content
    assert "e002" in content


def test_cli_lookup_can_redact_sensitive_columns(tmp_path: Path) -> None:
    output = tmp_path / "lookup.csv"

    exit_code = main(
        [
            "lookup",
            str(SAMPLE_DATA / "details.csv"),
            "--id",
            "record_id",
            "--value",
            "e001",
            "--cluster",
            "entity_id",
            "--redact",
            "company_name,normalized_company_name",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    content = output.read_text()
    assert "[redacted]" in content
    assert "Acme Corporation" not in content


def test_cli_report_supports_toml_config_and_redaction(tmp_path: Path) -> None:
    config = tmp_path / "review.toml"
    out_dir = tmp_path / "review"
    config.write_text(
        f"""
input = "{SAMPLE_DATA / "details.csv"}"
out_dir = "{out_dir}"
title = "Configured Review"
cluster = "entity_id"
redact = ["company_name", "normalized_company_name"]

[[mappings]]
left = "entity_id"
right = "reference_id"
""",
        encoding="utf-8",
    )

    exit_code = main(["report", "--config", str(config)])

    assert exit_code == 0
    assert (out_dir / "report.html").exists()
    assert "[redacted]" in (out_dir / "profile.csv").read_text()
    assert "Acme Corporation" not in (out_dir / "profile.csv").read_text()
    assert "Acme Corporation" not in (out_dir / "report.html").read_text()


def test_cli_report_writes_optional_workbook(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    output_dir = tmp_path / "review"
    workbook = tmp_path / "review.xlsx"

    exit_code = main(
        [
            "report",
            str(SAMPLE_DATA / "details.csv"),
            "--out-dir",
            str(output_dir),
            "--mapping",
            "entity_id:reference_id",
            "--workbook-out",
            str(workbook),
            "--redact",
            "company_name,normalized_company_name",
        ]
    )

    assert exit_code == 0
    assert workbook.exists()
    loaded = openpyxl.load_workbook(workbook)
    values = [
        str(cell.value)
        for worksheet in loaded.worksheets
        for row in worksheet.iter_rows()
        for cell in row
        if cell.value is not None
    ]
    assert "Acme Corporation" not in values
    assert "[redacted]" in values


def test_api_profile_returns_dataframe_when_pandas_available() -> None:
    pandas = pytest.importorskip("pandas")
    from er_reviewer import api

    frame = pandas.DataFrame(
        [
            {"id": "1", "amount": "$10.00"},
            {"id": "2", "amount": "$20.00"},
        ]
    )

    result = api.profile(frame)

    assert list(cast(Any, result)["column"]) == ["id", "amount"]


def test_api_profile_path_rejects_future_engine_before_loading_file() -> None:
    from er_reviewer import api

    with pytest.raises(ValueError, match="Unsupported API engine"):
        api.profile_path("/does/not/exist.csv", engine="duckdb")
