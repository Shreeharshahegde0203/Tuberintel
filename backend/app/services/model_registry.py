from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ModelStatus:
    name: str
    role: str
    configured: bool
    loaded: bool
    path: str | None
    note: str


class ModelRegistry:
    """Optional trained-model adapters.

    The application remains runnable without GPU frameworks. When weights are placed in
    the configured locations, this registry validates them and exposes a stable status
    contract. The training scripts in /ml generate compatible artefacts.
    """

    def __init__(self, quality_model_path: Path | None, defect_model_path: Path | None) -> None:
        self.quality_model_path = quality_model_path
        self.defect_model_path = defect_model_path

    def status(self) -> list[ModelStatus]:
        return [
            ModelStatus(
                name="EfficientNetV2-S quality classifier",
                role="multi-class tuber quality and disease classification",
                configured=self.quality_model_path is not None,
                loaded=bool(self.quality_model_path and self.quality_model_path.exists()),
                path=str(self.quality_model_path) if self.quality_model_path else None,
                note="Fine-tune on PotatoCare and local field images. DenseNet169 is included as a benchmark.",
            ),
            ModelStatus(
                name="YOLO11-Seg defect localizer",
                role="bruises, scab, cracks, greening, rot, sprouts and deformity localization",
                configured=self.defect_model_path is not None,
                loaded=bool(self.defect_model_path and self.defect_model_path.exists()),
                path=str(self.defect_model_path) if self.defect_model_path else None,
                note="Requires bounding-box or mask annotations. Classical CV remains active as a transparent fallback.",
            ),
        ]

    def as_dict(self) -> list[dict[str, Any]]:
        return [status.__dict__ for status in self.status()]
