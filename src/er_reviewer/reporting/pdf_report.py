from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, cast


def write_pdf_report(html_path: str | Path, pdf_path: str | Path | None = None) -> Path:
    """Render an existing HTML report to PDF using optional WeasyPrint."""
    html_class = _load_html_class()
    source_path = Path(html_path)
    output_path = Path(pdf_path) if pdf_path is not None else source_path.with_suffix(".pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html_class(filename=str(source_path)).write_pdf(str(output_path))
    return output_path


def _load_html_class() -> type[Any]:
    try:
        weasyprint = cast(Any, import_module("weasyprint"))
    except ImportError as exc:
        raise RuntimeError(
            "PDF report output requires the optional dependency 'weasyprint'. "
            "Install er-reviewer with the 'reports' extra or install weasyprint."
        ) from exc
    return cast("type[Any]", weasyprint.HTML)
