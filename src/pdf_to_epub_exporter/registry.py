from collections.abc import Callable

from pdf_to_epub_exporter.step import PipelineStep

StepFactory = Callable[..., PipelineStep]


class StepRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, StepFactory] = {}

    def register(self, step_id: str, factory: StepFactory) -> None:
        if step_id in self._factories:
            raise ValueError(f"Step already registered: {step_id}")
        self._factories[step_id] = factory

    def create_steps(self, step_configs: list[dict]) -> list[PipelineStep]:
        steps: list[PipelineStep] = []
        for raw in step_configs:
            step_id = raw["id"]
            enabled = raw.get("enabled", True)
            params = raw.get("params", {})

            if step_id not in self._factories:
                raise ValueError(f"Unknown step id: {step_id}")

            step = self._factories[step_id](enabled=enabled, params=params)
            steps.append(step)
        return steps
