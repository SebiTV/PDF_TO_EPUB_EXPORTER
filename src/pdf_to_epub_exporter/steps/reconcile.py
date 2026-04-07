from pdf_to_epub_exporter.context import PipelineContext
from pdf_to_epub_exporter.step import PipelineStep


class ReconcileScansStep(PipelineStep):
    step_id = "reconcile_scans"

    def run(self, context: PipelineContext) -> None:
        text_a = context.texts.get("scan_a", "")
        text_b = context.texts.get("scan_b", "")

        if not text_a and not text_b:
            context.merged_text = ""
            context.add_warning("reconcile_scans has no input text")
            return

        lines_a = text_a.splitlines()
        lines_b = text_b.splitlines()
        max_len = max(len(lines_a), len(lines_b))
        merged_lines: list[str] = []

        for index in range(max_len):
            a = lines_a[index] if index < len(lines_a) else ""
            b = lines_b[index] if index < len(lines_b) else ""

            if len(a.strip()) >= len(b.strip()):
                chosen = a
            else:
                chosen = b
            merged_lines.append(chosen)

        context.merged_text = "\n".join(merged_lines).strip()
