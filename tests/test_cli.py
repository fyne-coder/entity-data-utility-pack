from pathlib import Path

import pytest

import er_reviewer.checks.similarity as similarity_module
from er_reviewer.cli import main

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "sample_data"


def test_cli_profile_writes_csv(tmp_path: Path) -> None:
    output = tmp_path / "profile.csv"

    exit_code = main(["profile", str(SAMPLE_DATA / "details.csv"), "--out", str(output)])

    assert exit_code == 0
    content = output.read_text()
    assert "column,total_rows,blank_count" in content
    assert "persistentId" in content


def test_cli_profile_supports_tsv_input(tmp_path: Path) -> None:
    input_path = tmp_path / "rows.tsv"
    output = tmp_path / "profile.csv"
    input_path.write_text("id\tamount\n1\t10\n2\t20\n", encoding="utf-8")

    exit_code = main(
        [
            "profile",
            str(input_path),
            "--format",
            "tsv",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    assert "amount" in output.read_text()


def test_cli_pair_profile_writes_grouping_and_identical_outputs(tmp_path: Path) -> None:
    grouping = tmp_path / "grouping.csv"
    identical = tmp_path / "identical.csv"

    exit_code = main(
        [
            "pair-profile",
            str(SAMPLE_DATA / "products.csv"),
            "--threshold",
            "0.5",
            "--out",
            str(grouping),
            "--identical-out",
            str(identical),
        ]
    )

    assert exit_code == 0
    assert "category" in grouping.read_text()
    assert identical.read_text().startswith("left_column,right_column")


def test_cli_hygiene_returns_nonzero_when_issues_found(tmp_path: Path) -> None:
    output = tmp_path / "hygiene.csv"

    exit_code = main(["hygiene", str(SAMPLE_DATA / "bad_csv_example.csv"), "--out", str(output)])

    assert exit_code == 1
    assert "column_count" in output.read_text()


def test_cli_duplicates_writes_candidates(tmp_path: Path) -> None:
    output = tmp_path / "duplicates.csv"

    exit_code = main(
        [
            "duplicates",
            str(SAMPLE_DATA / "people_duplicates.csv"),
            "--block",
            "Date Of Birth",
            "--match",
            "Full Name",
            "--id",
            "Entity ID",
            "--threshold",
            "0.8",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 1
    assert "t001" in output.read_text()


def test_cli_duplicates_wires_block_guardrails(tmp_path: Path) -> None:
    input_path = tmp_path / "rows.csv"
    input_path.write_text(
        "id,block,name\n1,x,Alice\n2,x,Alyce\n3,x,Alicia\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "duplicates",
            str(input_path),
            "--block",
            "block",
            "--match",
            "name",
            "--id",
            "id",
            "--max-block-size",
            "2",
        ]
    )

    assert exit_code == 2


def test_cli_clusters_writes_cluster_summary(tmp_path: Path) -> None:
    output = tmp_path / "clusters.csv"
    chart = tmp_path / "clusters.svg"

    exit_code = main(
        [
            "clusters",
            str(SAMPLE_DATA / "details.csv"),
            "--cluster",
            "persistentId",
            "--chart-out",
            str(chart),
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    assert "p001" in output.read_text()
    assert "<svg" in chart.read_text()


def test_cli_report_writes_consolidated_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "review"

    exit_code = main(
        [
            "report",
            str(SAMPLE_DATA / "details.csv"),
            "--out-dir",
            str(output_dir),
            "--mapping",
            "persistentId:trusted_id",
            "--cluster",
            "persistentId",
        ]
    )

    assert exit_code == 0
    assert (output_dir / "report.html").exists()
    assert (output_dir / "profile.csv").exists()
    assert (output_dir / "hygiene.csv").exists()
    assert (output_dir / "mapping_persistentid_to_trusted_id.csv").exists()
    assert (output_dir / "clusters.csv").exists()
    assert (output_dir / "cluster_sizes.svg").exists()
    assert "One-to-Many Mapping" in (output_dir / "report.html").read_text()


def test_cli_report_caps_preview_and_workbook_outputs(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    input_path = tmp_path / "rows.csv"
    output_dir = tmp_path / "review"
    workbook = tmp_path / "review.xlsx"
    input_path.write_text(
        "id,cluster,score,name\n1,c1,0.91,Alice\n2,c1,0.82,Alyce\n3,c2,0.77,Bob\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "report",
            str(input_path),
            "--out-dir",
            str(output_dir),
            "--cluster",
            "cluster",
            "--match-prefix",
            "score",
            "--workbook-out",
            str(workbook),
            "--max-output-rows",
            "1",
        ]
    )

    assert exit_code == 0
    html = (output_dir / "report.html").read_text()
    assert "Showing first 1" in html
    assert (output_dir / "match_score_distribution.svg").exists()
    loaded = openpyxl.load_workbook(workbook)
    summary = loaded["Summary"]
    assert [summary["D1"].value, summary["E1"].value] == ["Exported Rows", "Capped"]


def test_cli_similarity_rejects_missing_tfidf_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_import_module(name: str) -> object:
        if name == "sklearn.feature_extraction.text":
            raise ImportError("simulated missing optional dependency")
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(similarity_module, "import_module", fake_import_module)

    exit_code = main(
        [
            "similarity",
            str(SAMPLE_DATA / "details.csv"),
            str(SAMPLE_DATA / "similar.csv"),
            "--cluster",
            "persistentId",
            "--compare",
            "company_name",
            "--method",
            "tfidf",
        ]
    )

    assert exit_code == 2
