from pathlib import Path

from er_reviewer.reporting.charts import write_bar_chart_svg, write_match_score_distribution_svg


def test_write_bar_chart_svg_writes_dependency_free_chart(tmp_path: Path) -> None:
    output = write_bar_chart_svg(
        tmp_path / "chart.svg", [("p001", 2), ("p002", 1)], title="Clusters"
    )

    content = output.read_text()
    assert output == tmp_path / "chart.svg"
    assert "<svg" in content
    assert "Clusters" in content
    assert "p001" in content


def test_write_match_score_distribution_svg_writes_histogram(tmp_path: Path) -> None:
    output = write_match_score_distribution_svg(
        tmp_path / "scores.svg", [0.1, 0.2, 0.8, 0.9], bins=4
    )

    content = output.read_text()
    assert output == tmp_path / "scores.svg"
    assert "Match Score Distribution" in content
    assert "n=4" in content
    assert "10%-30%" in content
