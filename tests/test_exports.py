from pathlib import Path

from er_reviewer.compare.exports import compare_export_membership_csv

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "sample_data"


def test_compare_export_membership_csv_detects_group_membership_drift() -> None:
    differences = compare_export_membership_csv(
        SAMPLE_DATA / "export_old.csv",
        SAMPLE_DATA / "export_new.csv",
        id_column="entity_id",
        member_column="record_id",
    )

    by_id = {difference.id_value: difference for difference in differences}
    assert set(by_id) == {"p002", "p004", "p006"}
    assert by_id["p002"].category == "member_count_changed"
    assert by_id["p002"].old_members == ("e003", "e004")
    assert by_id["p002"].new_members == ("e003",)
    assert by_id["p006"].category == "added"
    assert by_id["p004"].category == "added"


def test_compare_export_membership_csv_streams_delimited_exports(tmp_path: Path) -> None:
    old_path = tmp_path / "old.tsv"
    new_path = tmp_path / "new.tsv"
    old_path.write_text("id\tmember\np1\te1\np1\te2\np2\te3\n", encoding="utf-8")
    new_path.write_text("id\tmember\np1\te1\np2\te3\np3\te4\n", encoding="utf-8")

    differences = compare_export_membership_csv(
        old_path,
        new_path,
        id_column="id",
        member_column="member",
        old_delimiter="\t",
        new_delimiter="\t",
    )

    by_id = {difference.id_value: difference for difference in differences}
    assert set(by_id) == {"p1", "p3"}
    assert by_id["p1"].category == "member_count_changed"
    assert by_id["p3"].category == "added"
