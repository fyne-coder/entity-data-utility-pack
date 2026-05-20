from pathlib import Path

from er_reviewer.reporting.html_report import ReportSection, write_report_artifacts


def test_write_report_artifacts_writes_html_and_section_csv(tmp_path: Path) -> None:
    report_path = write_report_artifacts(
        tmp_path,
        title="Sample Review",
        sections=[
            ReportSection(
                title="Findings",
                rows=[{"id": "p001", "issue": "example"}],
                csv_filename="findings.csv",
            )
        ],
    )

    assert report_path == tmp_path / "report.html"
    assert "Sample Review" in report_path.read_text()
    assert "Findings" in report_path.read_text()
    assert (tmp_path / "findings.csv").read_text().startswith("id,issue")


def test_write_report_artifacts_can_cap_html_preview_without_capping_csv(tmp_path: Path) -> None:
    report_path = write_report_artifacts(
        tmp_path,
        title="Large Review",
        sections=[
            ReportSection(
                title="Findings",
                rows=[
                    {"id": "p001", "issue": "first"},
                    {"id": "p002", "issue": "second"},
                    {"id": "p003", "issue": "third"},
                ],
                csv_filename="findings.csv",
            )
        ],
        max_rows_per_section=2,
    )

    html = report_path.read_text()
    assert "Showing first 2 of 3 row(s)" in html
    assert "p001" in html
    assert "p002" in html
    assert "p003" not in html
    assert "p003,third" in (tmp_path / "findings.csv").read_text()
