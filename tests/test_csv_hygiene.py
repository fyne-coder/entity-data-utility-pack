from pathlib import Path

from er_reviewer.io.csv_hygiene import analyze_csv_hygiene, strip_nul_bytes

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "sample_data"


def test_analyze_csv_hygiene_flags_inconsistent_rows() -> None:
    report = analyze_csv_hygiene(SAMPLE_DATA / "bad_csv_example.csv")

    assert not report.ok
    assert report.header_columns == 3
    assert report.data_rows == 4
    assert [(issue.line_number, issue.issue_type) for issue in report.issues] == [
        (4, "column_count"),
        (5, "column_count"),
    ]


def test_strip_nul_bytes_writes_clean_copy(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    output = tmp_path / "clean.csv"
    source.write_bytes(b"id,name\x001,Alice\x00")

    removed = strip_nul_bytes(source, output)

    assert removed == 2
    assert output.read_bytes() == b"id,name1,Alice"
