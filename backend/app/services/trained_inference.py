from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np


class TrainedModelAdapter:
    """Lazy optional inference for artefacts produced by the /ml scripts.

    Heavy packages are imported only when corresponding weights exist. This keeps the
    base API lightweight while making the trained path genuinely executable.
    """

    def __init__(self, quality_model_path: Path | None, defect_model_path: Path | None) -> None:
        self.quality_model_path = quality_model_path
        self.defect_model_path = defect_model_path
        self._quality_model: Any | None = None
        self._quality_labels: list[str] = []
        self._defect_model: Any | None = None

    @property
    def enabled(self) -> bool:
        return bool(
            (self.quality_model_path and self.quality_model_path.exists())
            or (self.defect_model_path and self.defect_model_path.exists())
        )

    def _load_quality(self) -> None:
        if self._quality_model is not None or not self.quality_model_path or not self.quality_model_path.exists():
            return
        import torch

        self._quality_model = torch.jit.load(str(self.quality_model_path), map_location="cpu")
        self._quality_model.eval()
        label_path = self.quality_model_path.with_suffix(".labels.json")
        if label_path.exists():
            self._quality_labels = json.loads(label_path.read_text(encoding="utf-8"))

    def _load_detector(self) -> None:
        if self._defect_model is not None or not self.defect_model_path or not self.defect_model_path.exists():
            return
        from ultralytics import YOLO

        self._defect_model = YOLO(str(self.defect_model_path))

    def predict_quality(self, image_bgr: np.ndarray) -> dict[str, float]:
        self._load_quality()
        if self._quality_model is None:
            return {}
        import torch

        image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (384, 384), interpolation=cv2.INTER_AREA)
        tensor = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        tensor = ((tensor - mean) / std).unsqueeze(0)
        with torch.inference_mode():
            logits = self._quality_model(tensor)
            probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
        labels = self._quality_labels or [f"class_{i}" for i in range(len(probs))]
        return {label: float(prob) for label, prob in zip(labels, probs, strict=False)}

    def predict_defects(self, image_path: Path, image_area: int) -> dict[str, float]:
        self._load_detector()
        if self._defect_model is None:
            return {}
        result = self._defect_model.predict(source=str(image_path), imgsz=640, conf=0.22, verbose=False)[0]
        names = result.names
        output: dict[str, float] = {}
        if result.masks is not None:
            masks = result.masks.data.cpu().numpy()
            class_ids = result.boxes.cls.int().cpu().numpy() if result.boxes is not None else np.zeros(len(masks), dtype=int)
            for mask, class_id in zip(masks, class_ids, strict=False):
                label = str(names[int(class_id)]).lower().replace(" ", "_")
                output[label] = output.get(label, 0.0) + float(np.count_nonzero(mask) / max(image_area, 1) * 100)
        elif result.boxes is not None:
            xyxy = result.boxes.xyxy.cpu().numpy()
            class_ids = result.boxes.cls.int().cpu().numpy()
            for box, class_id in zip(xyxy, class_ids, strict=False):
                x1, y1, x2, y2 = box
                label = str(names[int(class_id)]).lower().replace(" ", "_")
                output[label] = output.get(label, 0.0) + float(max(0, x2 - x1) * max(0, y2 - y1) / max(image_area, 1) * 100)
        return output

    def predict(self, image_path: Path, image_bgr: np.ndarray) -> dict[str, Any]:
        if not self.enabled:
            return {}
        return {
            "quality_probabilities": self.predict_quality(image_bgr),
            "defect_area_percent": self.predict_defects(image_path, image_bgr.shape[0] * image_bgr.shape[1]),
        }
