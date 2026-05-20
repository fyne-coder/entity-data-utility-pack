from __future__ import annotations

from collections.abc import Iterable
from html import escape
from pathlib import Path
from statistics import mean


def write_bar_chart_svg(
    path: str | Path,
    items: Iterable[tuple[str, int]],
    *,
    title: str = "Bar Chart",
    width: int = 900,
    row_height: int = 28,
) -> Path:
    """Write a dependency-free horizontal SVG bar chart for numeric summaries."""
    values = [(str(label), int(value)) for label, value in items]
    chart_path = Path(path)
    chart_path.parent.mkdir(parents=True, exist_ok=True)

    margin_left = 170
    margin_right = 40
    margin_top = 48
    height = max(120, margin_top + row_height * len(values) + 30)
    max_value = max((value for _, value in values), default=1)
    bar_max_width = width - margin_left - margin_right

    rows: list[str] = []
    for index, (label, value) in enumerate(values):
        y = margin_top + index * row_height
        bar_width = 0 if max_value == 0 else int((value / max_value) * bar_max_width)
        rows.append(
            f'<text x="12" y="{y + 16}" font-size="13">{escape(label)}</text>'
            f'<rect x="{margin_left}" y="{y}" width="{bar_width}" height="18" fill="#4f46e5" />'
            f'<text x="{margin_left + bar_width + 6}" y="{y + 14}" font-size="12">{value}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img">
  <title>{escape(title)}</title>
  <rect width="100%" height="100%" fill="white" />
  <text x="12" y="28" font-size="18" font-family="Arial, sans-serif" font-weight="700">{escape(title)}</text>
  <g font-family="Arial, sans-serif">
    {"".join(rows)}
  </g>
</svg>
"""
    chart_path.write_text(svg, encoding="utf-8")
    return chart_path


def write_match_score_distribution_svg(
    path: str | Path,
    scores: Iterable[float],
    *,
    title: str = "Match Score Distribution",
    bins: int = 10,
    width: int = 900,
    row_height: int = 28,
) -> Path:
    """Write a dependency-free histogram SVG for match-score distributions."""
    if bins <= 0:
        raise ValueError("bins must be greater than 0")

    values = [float(score) for score in scores]
    if not values:
        return write_bar_chart_svg(path, [], title=title, width=width, row_height=row_height)

    min_score = min(values)
    max_score = max(values)
    if min_score == max_score:
        labels = [
            _format_score_range(min_score, max_score, values_are_unit=_scores_are_unit(values))
        ]
        return write_bar_chart_svg(path, [(labels[0], len(values))], title=title, width=width)

    values_are_unit = _scores_are_unit(values)
    bin_width = (max_score - min_score) / bins
    counts = [0] * bins
    for value in values:
        index = int((value - min_score) / bin_width)
        if index == bins:
            index -= 1
        counts[index] += 1

    items: list[tuple[str, int]] = []
    for index, count in enumerate(counts):
        start = min_score + index * bin_width
        end = max_score if index == bins - 1 else start + bin_width
        label = _format_score_range(start, end, values_are_unit=values_are_unit)
        items.append((label, count))

    return write_bar_chart_svg(
        path, items, title=f"{title} (n={len(values)}, avg={mean(values):.2f})"
    )


def _scores_are_unit(values: list[float]) -> bool:
    return all(0 <= value <= 1 for value in values)


def _format_score_range(start: float, end: float, *, values_are_unit: bool) -> str:
    if values_are_unit:
        return f"{start:.0%}-{end:.0%}"
    return f"{start:.2f}-{end:.2f}"
