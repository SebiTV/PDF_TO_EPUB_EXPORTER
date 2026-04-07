from pathlib import Path

from pypdf import PdfReader


def load_scan_text(source_pdf: Path, scan_label: str, configured_file: str | None = None) -> str:
    if configured_file:
        custom_path = Path(configured_file)
        if custom_path.exists():
            return custom_path.read_text(encoding="utf-8")

    sidecar = source_pdf.parent / f"{source_pdf.stem}.{scan_label}.txt"
    if sidecar.exists():
        return sidecar.read_text(encoding="utf-8")

    return ""


def extract_text_fast(source_pdf: Path) -> str:
    reader = PdfReader(str(source_pdf))
    chunks: list[str] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            chunks.append(text)

    return "\n".join(chunks).strip()


def extract_text_ocr(source_pdf: Path, *, language: str = "deu+eng", dpi: int = 300) -> str:
    try:
        import pypdfium2 as pdfium
        import pytesseract
    except ImportError as exc:
        raise RuntimeError(
            "OCR dependencies missing. Install pypdfium2 and pytesseract and ensure Tesseract is installed on the system."
        ) from exc

    doc = pdfium.PdfDocument(str(source_pdf))
    chunks: list[str] = []
    scale = max(dpi, 72) / 72.0

    for index in range(len(doc)):
        page = doc[index]
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        text = pytesseract.image_to_string(image, lang=language) or ""
        if text.strip():
            chunks.append(text)

    return "\n".join(chunks).strip()
