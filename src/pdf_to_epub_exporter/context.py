from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PipelineContext:
    input_pdf: Path
    output_dir: Path
    config: dict[str, Any]
    artifacts: dict[str, Any] = field(default_factory=dict)
    texts: dict[str, str] = field(default_factory=dict)
    merged_text: str = ""
    corrected_text: str = ""
    warnings: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)

    def add_log(self, message: str) -> None:
        self.logs.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)
