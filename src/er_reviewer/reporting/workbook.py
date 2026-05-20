from __future__ import annotations

from collections.abc import Iterable, Mapping
from importlib import import_module
from pathlib import Path
from typing import Any, cast

INVALID_WORKSHEET_CHARS = frozenset("[]:*?/\\")
MAX_WORKSHEET_NAME_LENGTH = 31
SUMMARY_SHEET_NAME = "Summary"


def write_workbook(
    path: str | Path,
    sections: Mapping[str, Iterable[Mapping[str, object]]],
    *,
    max_rows_per_sheet: int | None = None,
) -> Path:
    """Write a multi-sheet Excel workbook from named report sections.

    The Excel dependency is intentionally optional. Install the ``reports`` extra
    or otherwise provide ``openpyxl`` before calling this function.
    """
    _validate_row_cap(max_rows_per_sheet)
    workbook_class = _load_workbook_class()
    workbook = workbook_class()

    summary_sheet = workbook.active
    summary_sheet.title = SUMMARY_SHEET_NAME
    if max_rows_per_sheet is None:
        summary_sheet.append(["Section", "Worksheet", "Rows"])
    else:
        summary_sheet.append(["Section", "Worksheet", "Rows", "Exported Rows", "Capped"])
    _polish_sheet(summary_sheet)

    used_names = {SUMMARY_SHEET_NAME}
    for section_name, records in sections.items():
        rows, total_rows = _collect_rows(records, max_rows=max_rows_per_sheet)
        worksheet_name = _unique_worksheet_name(section_name, used_names)
        used_names.add(worksheet_name)

        worksheet = workbook.create_sheet(title=worksheet_name)
        _write_section_sheet(worksheet, rows)
        if max_rows_per_sheet is None:
            summary_sheet.append([section_name, worksheet_name, total_rows])
        else:
            summary_sheet.append(
                [section_name, worksheet_name, total_rows, len(rows), len(rows) < total_rows]
            )

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    return output_path


def _load_workbook_class() -> type[Any]:
    try:
        openpyxl = cast(Any, import_module("openpyxl"))
    except ImportError as exc:
        raise RuntimeError(
            "Excel workbook output requires the optional dependency 'openpyxl'. "
            "Install er-reviewer with the 'reports' extra or install openpyxl."
        ) from exc
    return cast("type[Any]", openpyxl.Workbook)


def _write_section_sheet(worksheet: Any, rows: list[dict[str, object]]) -> None:
    if not rows:
        worksheet.append(["No rows"])
        _polish_sheet(worksheet)
        return

    headers: list[str] = []
    for row in rows:
        for column in row:
            if column not in headers:
                headers.append(column)

    worksheet.append(headers)
    for row in rows:
        worksheet.append([row.get(header, "") for header in headers])
    _polish_sheet(worksheet)


def _collect_rows(
    records: Iterable[Mapping[str, object]],
    *,
    max_rows: int | None,
) -> tuple[list[dict[str, object]], int]:
    rows: list[dict[str, object]] = []
    total_rows = 0
    for record in records:
        total_rows += 1
        if max_rows is None or len(rows) < max_rows:
            rows.append(dict(record))
    return rows, total_rows


def _polish_sheet(worksheet: Any) -> None:
    worksheet.freeze_panes = "A2"
    if worksheet.max_row > 1 and worksheet.max_column > 0:
        worksheet.auto_filter.ref = worksheet.dimensions


def _unique_worksheet_name(section_name: str, used_names: set[str]) -> str:
    base_name = _sanitize_worksheet_name(section_name)
    worksheet_name = base_name
    suffix = 2
    while worksheet_name in used_names:
        suffix_text = f" {suffix}"
        worksheet_name = f"{base_name[: MAX_WORKSHEET_NAME_LENGTH - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return worksheet_name


def _sanitize_worksheet_name(section_name: str) -> str:
    cleaned = "".join("_" if char in INVALID_WORKSHEET_CHARS else char for char in section_name)
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        cleaned = "Section"
    return cleaned[:MAX_WORKSHEET_NAME_LENGTH]


def _validate_row_cap(max_rows: int | None) -> None:
    if max_rows is not None and max_rows < 0:
        raise ValueError("max_rows_per_sheet must be greater than or equal to 0")
