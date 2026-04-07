import json
from pathlib import Path
from typing import Any


def load_config(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))

    if "steps" not in raw or not isinstance(raw["steps"], list):
        raise ValueError("Config must contain a list in 'steps'.")

    for index, step in enumerate(raw["steps"]):
        if "id" not in step:
            raise ValueError(f"Step entry at index {index} misses required key 'id'.")
        if "enabled" in step and not isinstance(step["enabled"], bool):
            raise ValueError(f"Step '{step['id']}' has non-boolean 'enabled'.")
        if "params" in step and not isinstance(step["params"], dict):
            raise ValueError(f"Step '{step['id']}' has non-object 'params'.")

    return raw
