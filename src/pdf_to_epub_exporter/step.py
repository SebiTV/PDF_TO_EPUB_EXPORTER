from abc import ABC, abstractmethod
from typing import Any

from pdf_to_epub_exporter.context import PipelineContext


class PipelineStep(ABC):
    step_id: str

    def __init__(self, *, enabled: bool = True, params: dict[str, Any] | None = None) -> None:
        self.enabled = enabled
        self.params = params or {}

    @abstractmethod
    def run(self, context: PipelineContext) -> None:
        raise NotImplementedError
