from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .engine import SimulationResult


def serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return serialize(asdict(value))
    if isinstance(value, dict):
        return {str(key): serialize(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [serialize(item) for item in value]
    return value


def result_to_dict(result: SimulationResult) -> dict[str, Any]:
    return {
        "metrics": serialize(result.metrics()),
        "last_price": result.last_price,
        "fundamental_prices": result.fundamental_prices,
        "quotes": serialize(result.quotes),
        "trades": serialize(result.trades),
        "events": serialize(result.events),
    }


def write_result(result: SimulationResult, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result_to_dict(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
