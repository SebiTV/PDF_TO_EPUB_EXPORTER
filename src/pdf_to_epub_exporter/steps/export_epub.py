from pathlib import Path

from pdf_to_epub_exporter.context import PipelineContext
from pdf_to_epub_exporter.epub import write_simple_epub
from pdf_to_epub_exporter.step import PipelineStep


class ExportEpubStep(PipelineStep):
    step_id = "export_epub"

    def run(self, context: PipelineContext) -> None:
        text = context.corrected_text or context.merged_text
        if not text:
            context.add_warning("export_epub skipped: no text available")
            return

        output_name = self.params.get("output_file", f"{context.input_pdf.stem}.epub")
        output_path = context.output_dir / output_name

        title = self.params.get("title", context.input_pdf.stem)
        author = self.params.get("author", "Unknown")

        write_simple_epub(Path(output_path), str(title), str(author), text)
        context.artifacts["epub_file"] = str(output_path)
