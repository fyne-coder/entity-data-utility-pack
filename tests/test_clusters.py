from pathlib import Path

from er_reviewer.checks.clusters import summarize_clusters_in_csv

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "sample_data"


def test_summarize_clusters_is_column_configurable() -> None:
    summaries = summarize_clusters_in_csv(
        SAMPLE_DATA / "details.csv",
        cluster_column="persistentId",
    )

    by_cluster = {summary.cluster_id: summary for summary in summaries}
    assert by_cluster["p001"].size == 2
    assert by_cluster["p001"].size_bucket == "2-5"
    assert by_cluster["p003"].size == 1
    assert by_cluster["p003"].size_bucket == "1"


def test_summarize_clusters_in_csv_streams_match_scores(tmp_path: Path) -> None:
    path = tmp_path / "clusters.csv"
    path.write_text(
        "cluster_id,match_score\nc1,0.9\nc1,0.7\nc2,not-a-number\n",
        encoding="utf-8",
    )

    summaries = summarize_clusters_in_csv(
        path,
        cluster_column="cluster_id",
        match_prefix="match_",
        low_match_score=0.85,
    )

    by_cluster = {summary.cluster_id: summary for summary in summaries}
    assert by_cluster["c1"].size == 2
    assert by_cluster["c1"].average_match_score == 0.8
    assert by_cluster["c1"].outlier_reason == "low_match_score"
    assert by_cluster["c2"].average_match_score is None
