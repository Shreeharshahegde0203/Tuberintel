from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib


@lru_cache(maxsize=4)
def load_artifact(path_value: str) -> dict[str, Any] | None:
    path = Path(path_value)
    if not path.exists() or not path.is_file():
        return None
    payload = joblib.load(path)
    if not isinstance(payload, dict) or payload.get("artifact_version") != 2:
        return None
    return payload
