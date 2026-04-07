from pdf_to_epub_exporter.context import PipelineContext
from pdf_to_epub_exporter.scanners import extract_text_fast, load_scan_text
from pdf_to_epub_exporter.step import PipelineStep


class ScanBStep(PipelineStep):
    step_id = "scan_b"

    def run(self, context: PipelineContext) -> None:
        text = ""

        try:
            text = extract_text_fast(context.input_pdf)
        except Exception as exc:
            context.add_warning(f"scan_b direct extraction failed: {exc}")

        if not text and self.params.get("use_sidecar_fallback", True):
            text = load_scan_text(
                source_pdf=context.input_pdf,
                scan_label="scan_b",
                configured_file=self.params.get("input_text_file"),
            )

        context.texts[self.step_id] = text
        if not text:
            context.add_warning("scan_b produced empty text")
