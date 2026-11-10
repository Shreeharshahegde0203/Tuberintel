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
    """Registry for the three-stage TuberIntel Vision pipeline.

    The application remains runnable when no learned weights are installed.
    In that situation the deterministic OpenCV path remains available.

    Stage A:
        Potato ROI instance segmentation.

    Stage B:
        Per-potato condition classification.

    Stage C:
        Detailed visible-defect instance segmentation.
    """

    def __init__(
        self,
        roi_model_path: Path | None,
        condition_model_path: Path | None,
        defect_model_path: Path | None,
    ) -> None:
        self.roi_model_path = roi_model_path
        self.condition_model_path = condition_model_path
        self.defect_model_path = defect_model_path

    @staticmethod
    def _exists(path: Path | None) -> bool:
        return bool(
            path
            and path.exists()
        )

    def status(self) -> list[ModelStatus]:
        return [
            ModelStatus(
                name="Model A ? YOLO11n-Seg",
                role=(
                    "potato ROI instance segmentation, "
                    "potato-region counting and shape extraction"
                ),
                configured=self.roi_model_path is not None,
                loaded=self._exists(
                    self.roi_model_path
                ),
                path=(
                    str(self.roi_model_path)
                    if self.roi_model_path
                    else None
                ),
                note=(
                    "Produces potato masks before condition "
                    "classification and detailed defect analysis."
                ),
            ),
            ModelStatus(
                name="Model B ? YOLO11s-Cls",
                role=(
                    "five-class per-potato condition classification"
                ),
                configured=(
                    self.condition_model_path
                    is not None
                ),
                loaded=self._exists(
                    self.condition_model_path
                ),
                path=(
                    str(self.condition_model_path)
                    if self.condition_model_path
                    else None
                ),
                note=(
                    "Classes: Damaged, Defected, "
                    "Diseased-Fungal, Healthy and Sprouted."
                ),
            ),
            ModelStatus(
                name="Model C ? YOLO11s-Seg",
                role=(
                    "detailed visible-defect instance segmentation"
                ),
                configured=(
                    self.defect_model_path
                    is not None
                ),
                loaded=self._exists(
                    self.defect_model_path
                ),
                path=(
                    str(self.defect_model_path)
                    if self.defect_model_path
                    else None
                ),
                note=(
                    "Classes: Scab, Rot, Greening and "
                    "Mechanical Damage. Reports visible-surface "
                    "evidence rather than internal defects."
                ),
            ),
        ]

    def as_dict(self) -> list[dict[str, Any]]:
        return [
            status.__dict__
            for status in self.status()
        ]
