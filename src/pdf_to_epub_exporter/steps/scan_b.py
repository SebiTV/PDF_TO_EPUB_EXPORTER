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

        write_raw_log_file = bool(self.params.get("write_raw_log_file", True))
        if write_raw_log_file:
            context.output_dir.mkdir(parents=True, exist_ok=True)
            raw_log_file = str(self.params.get("raw_log_file", f"{context.input_pdf.stem}.scan_b.raw.txt"))
            raw_log_path = context.output_dir / raw_log_file
            raw_log_path.write_text(text, encoding="utf-8")
            context.artifacts["scan_b_raw_log_file"] = str(raw_log_path)
            context.add_log(f"scan_b raw text written: {raw_log_path} (chars={len(text)})")

        if not text:
            context.add_warning("scan_b produced empty text")
