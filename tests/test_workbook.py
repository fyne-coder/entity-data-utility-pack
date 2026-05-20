from pathlib import Path

import pytest

from er_reviewer.reporting import workbook
from er_reviewer.reporting.workbook import write_workbook


def test_write_workbook_writes_summary_and_section_sheets(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")

    workbook_path = write_workbook(
        tmp_path / "review.xlsx",
        {
            "Findings": [
                {"id": "p001", "issue": "missing member"},
                {"id": "p002", "severity": "warning"},
            ],
            "Empty Section": [],
        },
    )

    loaded = openpyxl.load_workbook(workbook_path)
    assert loaded.sheetnames == ["Summary", "Findings", "Empty Section"]

    summary = loaded["Summary"]
    assert [summary["A1"].value, summary["B1"].value, summary["C1"].value] == [
        "Section",
        "Worksheet",
        "Rows",
    ]
    assert [summary["A2"].value, summary["B2"].value, summary["C2"].value] == [
        "Findings",
        "Findings",
        2,
    ]
    assert [summary["A3"].value, summary["B3"].value, summary["C3"].value] == [
        "Empty Section",
        "Empty Section",
        0,
    ]

    findings = loaded["Findings"]
    assert findings.freeze_panes == "A2"
    assert findings.auto_filter.ref == "A1:C3"
    assert [findings["A1"].value, findings["B1"].value, findings["C1"].value] == [
        "id",
        "issue",
        "severity",
    ]
    assert [findings["A2"].value, findings["B2"].value, findings["C2"].value] == [
        "p001",
        "missing member",
        None,
    ]
    assert loaded["Empty Section"]["A1"].value == "No rows"


def test_write_workbook_sanitizes_and_deduplicates_sheet_names(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")

    workbook_path = write_workbook(
        tmp_path / "names.xlsx",
        {
            "A/B:C*D?E[F]": [{"value": 1}],
            "Summary": [{"value": 2}],
            "A very long section name that exceeds Excel limits": [{"value": 3}],
        },
    )

    loaded = openpyxl.load_workbook(workbook_path)
    assert loaded.sheetnames == [
        "Summary",
        "A_B_C_D_E_F_",
        "Summary 2",
        "A very long section name that e",
    ]


def test_write_workbook_can_cap_exported_rows(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")

    workbook_path = write_workbook(
        tmp_path / "capped.xlsx",
        {
            "Findings": [
                {"id": "p001"},
                {"id": "p002"},
                {"id": "p003"},
            ]
        },
        max_rows_per_sheet=2,
    )

    loaded = openpyxl.load_workbook(workbook_path)
    summary = loaded["Summary"]
    assert [summary["A1"].value, summary["B1"].value, summary["C1"].value] == [
        "Section",
        "Worksheet",
        "Rows",
    ]
    assert [summary["D1"].value, summary["E1"].value] == ["Exported Rows", "Capped"]
    assert [summary["A2"].value, summary["C2"].value, summary["D2"].value, summary["E2"].value] == [
        "Findings",
        3,
        2,
        True,
    ]

    findings = loaded["Findings"]
    assert findings.max_row == 3
    assert findings["A2"].value == "p001"
    assert findings["A3"].value == "p002"


def test_write_workbook_raises_clear_error_without_openpyxl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_import(module_name: str) -> object:
        if module_name == "openpyxl":
            raise ImportError("missing")
        raise AssertionError(module_name)

    monkeypatch.setattr(workbook, "import_module", fail_import)

    with pytest.raises(RuntimeError, match="requires the optional dependency 'openpyxl'"):
        write_workbook(tmp_path / "missing.xlsx", {"Findings": [{"id": "p001"}]})
