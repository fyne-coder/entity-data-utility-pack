from pathlib import Path

import pytest

from er_reviewer.reporting import pdf_report
from er_reviewer.reporting.pdf_report import write_pdf_report


def test_write_pdf_report_raises_clear_error_without_weasyprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_import(module_name: str) -> object:
        if module_name == "weasyprint":
            raise ImportError("missing")
        raise AssertionError(module_name)

    monkeypatch.setattr(pdf_report, "import_module", fail_import)

    with pytest.raises(RuntimeError, match="requires the optional dependency 'weasyprint'"):
        write_pdf_report(tmp_path / "report.html")


def test_write_pdf_report_uses_weasyprint_html_class(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    html_path = tmp_path / "report.html"
    html_path.write_text("<html><body>Report</body></html>", encoding="utf-8")
    pdf_path = tmp_path / "custom.pdf"
    calls: dict[str, str] = {}

    class FakeHTML:
        def __init__(self, *, filename: str) -> None:
            calls["filename"] = filename

        def write_pdf(self, output_path: str) -> None:
            calls["output_path"] = output_path
            Path(output_path).write_bytes(b"%PDF")

    class FakeWeasyPrint:
        HTML = FakeHTML

    monkeypatch.setattr(pdf_report, "import_module", lambda module_name: FakeWeasyPrint)

    output = write_pdf_report(html_path, pdf_path)

    assert output == pdf_path
    assert calls == {"filename": str(html_path), "output_path": str(pdf_path)}
    assert pdf_path.read_bytes() == b"%PDF"
