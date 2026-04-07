from pdf_to_epub_exporter.context import PipelineContext
from pdf_to_epub_exporter.step import PipelineStep


class Pipeline:
    def __init__(self, steps: list[PipelineStep]) -> None:
        self.steps = steps

    def run(self, context: PipelineContext) -> PipelineContext:
        for step in self.steps:
            if not step.enabled:
                context.add_log(f"skip:{step.step_id}")
                continue

            context.add_log(f"start:{step.step_id}")
            step.run(context)
            context.add_log(f"done:{step.step_id}")
        return context
