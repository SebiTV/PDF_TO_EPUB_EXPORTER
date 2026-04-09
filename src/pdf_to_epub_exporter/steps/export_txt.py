from pathlib import Path

from pdf_to_epub_exporter.context import PipelineContext
from pdf_to_epub_exporter.step import PipelineStep


class ExportTxtStep(PipelineStep):
    step_id = "export_txt"

    def run(self, context: PipelineContext) -> None:
        text = context.corrected_text or context.merged_text
        if not text:
            context.add_warning("export_txt skipped: no text available")
            return

        output_name = self.params.get("output_file", f"{context.input_pdf.stem}.txt")
        output_path = context.output_dir / output_name

        output_path.write_text(text, encoding="utf-8")
        context.artifacts["txt_file"] = str(output_path)
