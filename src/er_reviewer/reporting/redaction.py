from __future__ import annotations

import hashlib
from collections.abc import Iterable

from er_reviewer.reporting.html_report import ReportSection


def redact_rows(
    rows: Iterable[dict[str, object]],
    *,
    columns: Iterable[str],
    mode: str = "mask",
) -> list[dict[str, object]]:
    """Return rows with selected columns masked or hashed before report rendering."""
    redacted_columns = set(columns)
    if not redacted_columns:
        return [dict(row) for row in rows]
    if mode not in {"mask", "hash"}:
        raise ValueError(f"Unknown redaction mode: {mode}")
    return [_redact_row(row, columns=redacted_columns, mode=mode) for row in rows]


def redact_sections(
    sections: Iterable[ReportSection],
    *,
    columns: Iterable[str],
    mode: str = "mask",
) -> list[ReportSection]:
    """Return report sections with selected columns redacted in every output writer."""
    return [
        ReportSection(
            title=section.title,
            rows=redact_rows(section.rows, columns=columns, mode=mode),
            csv_filename=section.csv_filename,
            summary=section.summary,
        )
        for section in sections
    ]


def _redact_value(value: object, *, mode: str) -> str:
    text = str(value)
    if text == "":
        return ""
    if mode == "hash":
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return "[redacted]"


def _redact_row(
    row: dict[str, object],
    *,
    columns: set[str],
    mode: str,
) -> dict[str, object]:
    redacted = {
        column: _redact_value(value, mode=mode) if column in columns else value
        for column, value in row.items()
    }
    profiled_column = row.get("column")
    if isinstance(profiled_column, str) and profiled_column in columns:
        for derived_field in ("top_values", "invalid_examples", "min_value", "max_value"):
            if derived_field in redacted and redacted[derived_field] != "":
                redacted[derived_field] = "[redacted]"
    return redacted
