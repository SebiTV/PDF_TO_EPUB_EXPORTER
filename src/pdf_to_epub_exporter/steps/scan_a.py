from pdf_to_epub_exporter.context import PipelineContext
from pdf_to_epub_exporter.scanners import extract_text_ocr, load_scan_text
from pdf_to_epub_exporter.step import PipelineStep


class ScanAStep(PipelineStep):
    step_id = "scan_a"

    def run(self, context: PipelineContext) -> None:
        text = ""

        try:
            text = extract_text_ocr(
                context.input_pdf,
                language=str(self.params.get("ocr_language", "deu+eng")),
                dpi=int(self.params.get("ocr_dpi", 300)),
            )
        except Exception as exc:
            context.add_warning(f"scan_a OCR failed: {exc}")

        if not text and self.params.get("use_sidecar_fallback", True):
            text = load_scan_text(
                source_pdf=context.input_pdf,
                scan_label="scan_a",
                configured_file=self.params.get("input_text_file"),
            )

        context.texts[self.step_id] = text
        if not text:
            context.add_warning("scan_a produced empty text")
