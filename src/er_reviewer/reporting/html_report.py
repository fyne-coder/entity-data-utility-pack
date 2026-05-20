from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from er_reviewer._csv_utils import write_dict_rows


@dataclass(frozen=True)
class ReportSection:
    title: str
    rows: list[dict[str, object]]
    csv_filename: str | None = None
    summary: str | None = None


def write_report_artifacts(
    output_dir: str | Path,
    *,
    title: str,
    sections: list[ReportSection],
    max_rows_per_section: int | None = None,
) -> Path:
    """Write section CSVs plus one consolidated dependency-free HTML report."""
    _validate_row_cap(max_rows_per_section)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    rendered_sections: list[str] = []
    for section in sections:
        csv_name = section.csv_filename
        if csv_name:
            write_dict_rows(output_path / csv_name, section.rows)
        rendered_sections.append(_render_section(section, max_rows=max_rows_per_section))

    html = _render_document(title, rendered_sections)
    report_path = output_path / "report.html"
    report_path.write_text(html, encoding="utf-8")
    return report_path


def _render_document(title: str, sections: list[str]) -> str:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; color: #1f2933; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .meta {{ color: #667085; margin-bottom: 2rem; }}
    section {{ margin: 2rem 0; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
    th, td {{ border: 1px solid #d0d5dd; padding: 0.45rem 0.55rem; text-align: left; vertical-align: top; }}
    th {{ background: #f2f4f7; }}
    .empty {{ color: #667085; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <div class="meta">Generated {escape(generated_at)}</div>
  {"".join(sections)}
</body>
</html>
"""


def _render_section(section: ReportSection, *, max_rows: int | None = None) -> str:
    summary = section.summary
    if summary is None:
        summary = f"{len(section.rows)} row(s)"
    display_rows = _cap_rows(section.rows, max_rows)
    cap_hint = ""
    if max_rows is not None and len(display_rows) < len(section.rows):
        cap_hint = (
            f'<p class="cap">Showing first {len(display_rows)} of '
            f"{len(section.rows)} row(s) in this HTML preview.</p>"
        )
    body = _render_table(display_rows)
    csv_hint = (
        f"<p>CSV: <code>{escape(section.csv_filename)}</code></p>" if section.csv_filename else ""
    )
    return (
        f"<section><h2>{escape(section.title)}</h2>"
        f"<p>{escape(summary)}</p>"
        f"{cap_hint}"
        f"{csv_hint}"
        f"{body}</section>"
    )


def _render_table(rows: list[dict[str, object]]) -> str:
    if not rows:
        return '<p class="empty">No rows.</p>'
    columns: list[str] = []
    for row in rows:
        for column in row:
            if column not in columns:
                columns.append(column)
    header = "".join(f"<th>{escape(column)}</th>" for column in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{escape(str(row.get(column, '')))}</td>" for column in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _cap_rows(rows: list[dict[str, object]], max_rows: int | None) -> list[dict[str, object]]:
    if max_rows is None:
        return rows
    return rows[:max_rows]


def _validate_row_cap(max_rows: int | None) -> None:
    if max_rows is not None and max_rows < 0:
        raise ValueError("max_rows_per_section must be greater than or equal to 0")
