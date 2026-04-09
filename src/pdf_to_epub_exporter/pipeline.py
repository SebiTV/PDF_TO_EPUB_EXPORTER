from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pdf_to_epub_exporter.context import PipelineContext
from pdf_to_epub_exporter.step import PipelineStep
from time import perf_counter


class Pipeline:
    def __init__(self, steps: list[PipelineStep]) -> None:
        self.steps = steps

    @staticmethod
    def _print_progress(message: str) -> None:
        print(message, flush=True)

    @staticmethod
    def _print_running(message: str) -> None:
        # Overwrite the same terminal line while a step is running.
        print(f"\r{message:<100}", end="", flush=True)

    @staticmethod
    def _end_running_line() -> None:
        print(flush=True)

    def run(self, context: PipelineContext) -> PipelineContext:
        total_steps = len(self.steps)
        for index, step in enumerate(self.steps, start=1):
            step_label = f"[{index}/{total_steps}] {step.step_id}"
            if not step.enabled:
                context.add_log(f"skip:{step.step_id}")
                self._print_progress(f"[SKIP] {step_label}")
                continue

            context.add_log(f"start:{step.step_id}")
            step_started = perf_counter()
            self._print_progress(f"[START] {step_label}")

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(step.run, context)
                running_line_active = False

                while True:
                    try:
                        future.result(timeout=1.0)
                        break
                    except TimeoutError:
                        elapsed = perf_counter() - step_started
                        self._print_running(f"[RUNNING] {step_label} elapsed={elapsed:.1f}s")
                        running_line_active = True
                    except Exception:
                        step_elapsed = perf_counter() - step_started
                        if running_line_active:
                            self._end_running_line()
                        context.add_log(f"failed:{step.step_id}")
                        context.add_log(f"duration:{step.step_id}:{step_elapsed:.3f}s")
                        self._print_progress(f"[FAIL] {step_label} elapsed={step_elapsed:.2f}s")
                        raise

            step_elapsed = perf_counter() - step_started
            if running_line_active:
                self._end_running_line()
            context.add_log(f"done:{step.step_id}")
            context.add_log(f"duration:{step.step_id}:{step_elapsed:.3f}s")
            self._print_progress(f"[DONE] {step_label} elapsed={step_elapsed:.2f}s")
        return context
