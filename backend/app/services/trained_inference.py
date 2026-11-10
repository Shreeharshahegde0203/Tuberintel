from __future__ import annotations

from pathlib import Path
import hashlib
from typing import Any

import cv2
import numpy as np


CONDITION_ALIASES = {
    "damaged": "Damaged",
    "damaged_potato": "Damaged",
    "defected": "Defected",
    "defected_potato": "Defected",
    "diseased-fungal": "Diseased-Fungal",
    "diseased_fungal": "Diseased-Fungal",
    "diseased-fungal_potato": "Diseased-Fungal",
    "diseased_fungal_potato": "Diseased-Fungal",
    "healthy": "Healthy",
    "potato": "Healthy",
    "healthy_potato": "Healthy",
    "sprouted": "Sprouted",
    "sprouted_potato": "Sprouted",
}


DEFECT_ALIASES = {
    "scab": "scab",
    "rot": "rot",
    "greening": "greening",
    "mechanical_damage": "mechanical_damage",
    "mechanical-damage": "mechanical_damage",
    "mechanicaldamage": "mechanical_damage",
}


class TrainedModelAdapter:
    """Lazy three-stage TuberIntel Vision v1 inference adapter.

    Heavy ML packages are imported only when configured weights exist.

    Ultralytics is deliberately used as the runtime abstraction so the
    selected YOLO weights can later be replaced by compatible exported
    OpenVINO artefacts without changing the API contract.
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

        self._roi_model: Any | None = None
        self._condition_model: Any | None = None
        self._defect_model: Any | None = None

        self._artifact_cache: dict[
            str,
            dict[str, Any] | None,
        ] = {}

    @staticmethod
    def _available(
        path: Path | None,
    ) -> bool:
        return bool(
            path
            and path.exists()
        )

    @property
    def enabled(self) -> bool:
        return any(
            [
                self._available(
                    self.roi_model_path
                ),
                self._available(
                    self.condition_model_path
                ),
                self._available(
                    self.defect_model_path
                ),
            ]
        )

    @property
    def stages(self) -> dict[str, bool]:
        return {
            "roi": self._available(
                self.roi_model_path
            ),
            "condition": self._available(
                self.condition_model_path
            ),
            "defects": self._available(
                self.defect_model_path
            ),
        }

    @staticmethod
    def _sha256_file(
        path: Path,
    ) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as handle:
            while True:
                chunk = handle.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                digest.update(
                    chunk
                )

        return digest.hexdigest()

    @classmethod
    def _sha256_directory(
        cls,
        path: Path,
    ) -> str:
        digest = hashlib.sha256()

        files = sorted(
            item
            for item in path.rglob("*")
            if item.is_file()
        )

        for item in files:
            relative = (
                item.relative_to(path)
                .as_posix()
                .encode("utf-8")
            )

            digest.update(
                relative
            )

            digest.update(
                b"\0"
            )

            with item.open("rb") as handle:
                while True:
                    chunk = handle.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    digest.update(
                        chunk
                    )

        return digest.hexdigest()

    def _artifact_info(
        self,
        *,
        stage: str,
        architecture: str,
        path: Path | None,
    ) -> dict[str, Any] | None:

        if (
            path is None
            or not path.exists()
        ):
            return None

        cache_key = (
            f"{stage}:{path.resolve()}"
        )

        if cache_key in self._artifact_cache:
            return self._artifact_cache[
                cache_key
            ]

        if path.is_file():
            sha256 = self._sha256_file(
                path
            )

            size_bytes = path.stat().st_size

            artifact_name = path.name

            artifact_format = (
                path.suffix.lower().lstrip(".")
                or "file"
            )

        elif path.is_dir():
            sha256 = self._sha256_directory(
                path
            )

            files = [
                item
                for item in path.rglob("*")
                if item.is_file()
            ]

            size_bytes = sum(
                item.stat().st_size
                for item in files
            )

            artifact_name = path.name

            artifact_format = (
                "openvino"
                if any(
                    item.suffix.lower()
                    == ".xml"
                    for item in files
                )
                else "directory"
            )

        else:
            return None

        info = {
            "stage": stage,
            "architecture": architecture,
            "artifact": artifact_name,
            "format": artifact_format,
            "size_bytes": int(
                size_bytes
            ),
            "sha256": sha256,
            "artifact_id": sha256[:12],
        }

        self._artifact_cache[
            cache_key
        ] = info

        return info

    @property
    def model_artifacts(
        self,
    ) -> dict[str, dict[str, Any]]:
        artifacts: dict[
            str,
            dict[str, Any]
        ] = {}

        roi = self._artifact_info(
            stage="A",
            architecture="YOLO11n-Seg",
            path=self.roi_model_path,
        )

        condition = self._artifact_info(
            stage="B",
            architecture="YOLO11s-Cls",
            path=self.condition_model_path,
        )

        defect = self._artifact_info(
            stage="C",
            architecture="YOLO11s-Seg",
            path=self.defect_model_path,
        )

        if roi:
            artifacts["model_a"] = roi

        if condition:
            artifacts["model_b"] = condition

        if defect:
            artifacts["model_c"] = defect

        return artifacts

    @staticmethod
    def _load_yolo(
        path: Path | None,
    ) -> Any | None:
        if not path or not path.exists():
            return None

        from ultralytics import YOLO

        return YOLO(
            str(path)
        )

    def _load_roi(self) -> None:
        if self._roi_model is None:
            self._roi_model = self._load_yolo(
                self.roi_model_path
            )

    def _load_condition(self) -> None:
        if self._condition_model is None:
            self._condition_model = self._load_yolo(
                self.condition_model_path
            )

    def _load_defect(self) -> None:
        if self._defect_model is None:
            self._defect_model = self._load_yolo(
                self.defect_model_path
            )

    @staticmethod
    def _slug(
        value: str,
    ) -> str:
        return (
            value.strip()
            .lower()
            .replace(" ", "_")
        )

    @classmethod
    def _condition_name(
        cls,
        value: str,
    ) -> str:
        key = cls._slug(value)

        return CONDITION_ALIASES.get(
            key,
            value.strip(),
        )

    @classmethod
    def _defect_name(
        cls,
        value: str,
    ) -> str:
        key = cls._slug(value)

        return DEFECT_ALIASES.get(
            key,
            key,
        )

    @staticmethod
    def _mask_polygon(
        mask: np.ndarray,
        *,
        offset_x: int = 0,
        offset_y: int = 0,
        max_points: int = 80,
    ) -> list[list[int]]:
        binary = (
            mask.astype(np.uint8)
            * 255
        )

        contours, _ = cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        if not contours:
            return []

        contour = max(
            contours,
            key=cv2.contourArea,
        )

        perimeter = cv2.arcLength(
            contour,
            True,
        )

        epsilon = max(
            1.0,
            perimeter * 0.003,
        )

        simplified = cv2.approxPolyDP(
            contour,
            epsilon,
            True,
        )

        points = [
            [
                int(point[0][0])
                + int(offset_x),
                int(point[0][1])
                + int(offset_y),
            ]
            for point in simplified
        ]

        if len(points) > max_points:
            step = max(
                1,
                len(points)
                // max_points,
            )

            points = points[
                ::step
            ][:max_points]

        return points

    @staticmethod
    def _mask_to_shape(
        mask: np.ndarray,
        height: int,
        width: int,
    ) -> np.ndarray:
        if (
            mask.shape[0] == height
            and mask.shape[1] == width
        ):
            return mask > 0.5

        resized = cv2.resize(
            mask.astype(
                np.float32
            ),
            (width, height),
            interpolation=cv2.INTER_NEAREST,
        )

        return resized > 0.5

    @staticmethod
    def _clip_box(
        box: np.ndarray,
        image_width: int,
        image_height: int,
        padding: float = 0.04,
    ) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = [
            float(v)
            for v in box
        ]

        bw = max(
            1.0,
            x2 - x1,
        )

        bh = max(
            1.0,
            y2 - y1,
        )

        x_pad = bw * padding
        y_pad = bh * padding

        x1 = max(
            0,
            int(x1 - x_pad),
        )

        y1 = max(
            0,
            int(y1 - y_pad),
        )

        x2 = min(
            image_width,
            int(x2 + x_pad),
        )

        y2 = min(
            image_height,
            int(y2 + y_pad),
        )

        return (
            x1,
            y1,
            x2,
            y2,
        )

    def _detect_rois(
        self,
        image_bgr: np.ndarray,
    ) -> tuple[
        list[dict[str, Any]],
        int,
    ]:
        self._load_roi()

        if self._roi_model is None:
            return [], 0

        result = self._roi_model.predict(
            source=image_bgr,
            imgsz=768,
            conf=0.25,
            verbose=False,
        )[0]

        if (
            result.boxes is None
            or len(result.boxes) == 0
        ):
            return [], 0

        height, width = image_bgr.shape[:2]

        boxes = (
            result.boxes.xyxy
            .detach()
            .cpu()
            .numpy()
        )

        confidences = (
            result.boxes.conf
            .detach()
            .cpu()
            .numpy()
        )

        raw_masks = None

        if result.masks is not None:
            raw_masks = (
                result.masks.data
                .detach()
                .cpu()
                .numpy()
            )

        candidates: list[
            dict[str, Any]
        ] = []

        for index, box in enumerate(
            boxes
        ):
            (
                x1,
                y1,
                x2,
                y2,
            ) = self._clip_box(
                box,
                width,
                height,
            )

            if (
                x2 - x1 < 16
                or y2 - y1 < 16
            ):
                continue

            crop = image_bgr[
                y1:y2,
                x1:x2,
            ].copy()

            if raw_masks is not None:
                full_mask = (
                    self._mask_to_shape(
                        raw_masks[index],
                        height,
                        width,
                    )
                )
            else:
                full_mask = np.zeros(
                    (height, width),
                    dtype=bool,
                )

                full_mask[
                    y1:y2,
                    x1:x2,
                ] = True

            crop_mask = full_mask[
                y1:y2,
                x1:x2,
            ]

            roi_polygon = self._mask_polygon(
                full_mask
            )

            candidates.append(
                {
                    "box_xyxy": [
                        x1,
                        y1,
                        x2,
                        y2,
                    ],
                    "roi_confidence": float(
                        confidences[index]
                    ),
                    "roi_area_pixels": int(
                        np.count_nonzero(
                            crop_mask
                        )
                    ),
                    "roi_polygon": roi_polygon,
                    "_crop": crop,
                    "_mask": crop_mask,
                }
            )

        total_detected = len(
            candidates
        )

        # Keep inference bounded for dense batch photographs.
        # Potato count remains the total Model-A count.
        candidates.sort(
            key=lambda item: (
                item["roi_area_pixels"],
                item["roi_confidence"],
            ),
            reverse=True,
        )

        return (
            candidates[:32],
            total_detected,
        )

    def _classify_crops(
        self,
        crops: list[np.ndarray],
    ) -> list[
        dict[str, float]
    ]:
        self._load_condition()

        if (
            self._condition_model is None
            or not crops
        ):
            return [
                {}
                for _ in crops
            ]

        results = (
            self._condition_model.predict(
                source=crops,
                imgsz=384,
                verbose=False,
            )
        )

        output: list[
            dict[str, float]
        ] = []

        for result in results:
            probabilities: dict[
                str,
                float
            ] = {}

            if result.probs is None:
                output.append(
                    probabilities
                )

                continue

            values = (
                result.probs.data
                .detach()
                .cpu()
                .numpy()
            )

            for class_id, probability in enumerate(
                values
            ):
                raw_name = str(
                    result.names[
                        class_id
                    ]
                )

                name = self._condition_name(
                    raw_name
                )

                probabilities[
                    name
                ] = float(
                    probability
                )

            output.append(
                probabilities
            )

        return output

    def _segment_defects(
        self,
        crops: list[np.ndarray],
        potato_masks: list[np.ndarray],
    ) -> list[
        dict[str, float]
    ]:
        self._load_defect()

        if (
            self._defect_model is None
            or not crops
        ):
            return [
                {}
                for _ in crops
            ]

        results = (
            self._defect_model.predict(
                source=crops,
                imgsz=768,
                conf=0.20,
                verbose=False,
            )
        )

        output: list[
            dict[str, float]
        ] = []

        for (
            result,
            crop,
            potato_mask,
        ) in zip(
            results,
            crops,
            potato_masks,
            strict=False,
        ):
            height, width = (
                crop.shape[:2]
            )

            denominator = int(
                np.count_nonzero(
                    potato_mask
                )
            )

            if denominator <= 0:
                denominator = (
                    height * width
                )

                potato_mask = np.ones(
                    (height, width),
                    dtype=bool,
                )

            class_masks: dict[
                str,
                np.ndarray
            ] = {}

            defect_regions: list[
                dict[str, Any]
            ] = []

            if (
                result.masks is not None
                and result.boxes is not None
            ):
                masks = (
                    result.masks.data
                    .detach()
                    .cpu()
                    .numpy()
                )

                class_ids = (
                    result.boxes.cls
                    .int()
                    .detach()
                    .cpu()
                    .numpy()
                )

                for (
                    raw_mask,
                    class_id,
                ) in zip(
                    masks,
                    class_ids,
                    strict=False,
                ):
                    mask = (
                        self._mask_to_shape(
                            raw_mask,
                            height,
                            width,
                        )
                    )

                    mask = (
                        mask
                        & potato_mask
                    )

                    raw_name = str(
                        result.names[
                            int(class_id)
                        ]
                    )

                    name = (
                        self._defect_name(
                            raw_name
                        )
                    )

                    polygon = self._mask_polygon(
                        mask
                    )

                    if len(polygon) >= 3:
                        defect_regions.append(
                            {
                                "label": name,
                                "polygon": polygon,
                            }
                        )

                    if name not in class_masks:
                        class_masks[
                            name
                        ] = np.zeros(
                            (
                                height,
                                width,
                            ),
                            dtype=bool,
                        )

                    class_masks[
                        name
                    ] |= mask

            percentages: dict[
                str,
                float
            ] = {}

            combined = np.zeros(
                (height, width),
                dtype=bool,
            )

            for (
                name,
                mask,
            ) in class_masks.items():
                combined |= mask

                percentages[
                    name
                ] = round(
                    float(
                        np.count_nonzero(
                            mask
                        )
                        / denominator
                        * 100.0
                    ),
                    4,
                )

            percentages[
                "total_visible_defect"
            ] = round(
                float(
                    np.count_nonzero(
                        combined
                    )
                    / denominator
                    * 100.0
                ),
                4,
            )

            percentages[
                "_regions"
            ] = defect_regions

            output.append(
                percentages
            )

        return output

    @staticmethod
    def _mean_probabilities(
        items: list[
            dict[str, float]
        ],
    ) -> dict[str, float]:
        labels = sorted(
            {
                label
                for item in items
                for label in item
            }
        )

        if (
            not labels
            or not items
        ):
            return {}

        return {
            label: round(
                float(
                    np.mean(
                        [
                            item.get(
                                label,
                                0.0,
                            )
                            for item in items
                        ]
                    )
                ),
                6,
            )
            for label in labels
        }

    @staticmethod
    def _mean_defects(
        items: list[
            dict[str, float]
        ],
    ) -> dict[str, float]:
        labels = sorted(
            {
                label
                for item in items
                for label, value in item.items()
                if not label.startswith("_")
                and isinstance(
                    value,
                    (
                        int,
                        float,
                        np.integer,
                        np.floating,
                    ),
                )
            }
        )

        if (
            not labels
            or not items
        ):
            return {}

        return {
            label: round(
                float(
                    np.mean(
                        [
                            item.get(
                                label,
                                0.0,
                            )
                            for item in items
                        ]
                    )
                ),
                4,
            )
            for label in labels
        }

    def predict(
        self,
        image_path: Path,
        image_bgr: np.ndarray,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {}

        regions: list[
            dict[str, Any]
        ] = []

        total_potatoes = 0

        if self._available(
            self.roi_model_path
        ):
            (
                regions,
                total_potatoes,
            ) = self._detect_rois(
                image_bgr
            )

            # If Model A is installed and says there is no potato,
            # do not allow B/C to hallucinate classifications.
            if total_potatoes == 0:
                return {
                    "pipeline": (
                        "tuberintel-vision-v1"
                    ),
                    "stages": self.stages,
                    "model_artifacts": self.model_artifacts,
                    "potato_count": 0,
                    "regions_analyzed": 0,
                    "quality_probabilities": {},
                    "condition_distribution": {},
                    "defect_area_percent": {},
                    "potatoes": [],
                    "review_required": True,
                    "warning": (
                        "Model A found no usable "
                        "potato ROI."
                    ),
                }

        elif (
            self._available(
                self.condition_model_path
            )
            or self._available(
                self.defect_model_path
            )
        ):
            height, width = (
                image_bgr.shape[:2]
            )

            regions = [
                {
                    "box_xyxy": [
                        0,
                        0,
                        width,
                        height,
                    ],
                    "roi_confidence": None,
                    "roi_area_pixels": (
                        height * width
                    ),
                    "_crop": (
                        image_bgr.copy()
                    ),
                    "_mask": np.ones(
                        (
                            height,
                            width,
                        ),
                        dtype=bool,
                    ),
                }
            ]

        crops = [
            region["_crop"]
            for region in regions
        ]

        masks = [
            region["_mask"]
            for region in regions
        ]

        condition_results = (
            self._classify_crops(
                crops
            )
        )

        defect_results = (
            self._segment_defects(
                crops,
                masks,
            )
        )

        potatoes: list[
            dict[str, Any]
        ] = []

        for index, region in enumerate(
            regions
        ):
            probabilities = (
                condition_results[index]
                if index
                < len(
                    condition_results
                )
                else {}
            )

            raw_defects = (
                defect_results[index]
                if index
                < len(
                    defect_results
                )
                else {}
            )

            defects = {
                key: value
                for key, value
                in raw_defects.items()
                if not str(key).startswith("_")
            }

            local_regions = (
                raw_defects.get(
                    "_regions",
                    []
                )
                if isinstance(
                    raw_defects,
                    dict,
                )
                else []
            )

            x1, y1, _, _ = (
                region["box_xyxy"]
            )

            defect_regions = []

            for defect_region in local_regions:
                polygon = (
                    defect_region.get(
                        "polygon",
                        []
                    )
                    or []
                )

                global_polygon = [
                    [
                        int(point[0])
                        + int(x1),
                        int(point[1])
                        + int(y1),
                    ]
                    for point in polygon
                    if len(point) >= 2
                ]

                if len(global_polygon) >= 3:
                    defect_regions.append(
                        {
                            "label": str(
                                defect_region.get(
                                    "label",
                                    "defect",
                                )
                            ),
                            "polygon": (
                                global_polygon
                            ),
                        }
                    )

            condition = None
            condition_confidence = None

            if probabilities:
                condition = max(
                    probabilities,
                    key=probabilities.get,
                )

                condition_confidence = (
                    probabilities[
                        condition
                    ]
                )

            potatoes.append(
                {
                    "index": index + 1,
                    "box_xyxy": (
                        region[
                            "box_xyxy"
                        ]
                    ),
                    "roi_confidence": (
                        region[
                            "roi_confidence"
                        ]
                    ),
                    "roi_area_pixels": (
                        region[
                            "roi_area_pixels"
                        ]
                    ),
                    "roi_polygon": (
                        region.get(
                            "roi_polygon",
                            [],
                        )
                    ),
                    "condition": condition,
                    "condition_confidence": (
                        round(
                            float(
                                condition_confidence
                            ),
                            6,
                        )
                        if condition_confidence
                        is not None
                        else None
                    ),
                    "condition_probabilities": (
                        probabilities
                    ),
                    "defect_area_percent": (
                        defects
                    ),
                    "defect_regions": (
                        defect_regions
                    ),
                }
            )

        condition_distribution = (
            self._mean_probabilities(
                condition_results
            )
        )

        defect_summary = (
            self._mean_defects(
                defect_results
            )
        )

        return {
            "pipeline": (
                "tuberintel-vision-v1"
            ),
            "stages": self.stages,
            "model_artifacts": self.model_artifacts,
            "potato_count": (
                total_potatoes
                if self._available(
                    self.roi_model_path
                )
                else None
            ),
            "regions_analyzed": len(
                potatoes
            ),
            # Legacy key retained so existing code does
            # not break while Vision v1 is introduced.
            "quality_probabilities": (
                condition_distribution
            ),
            # Legacy defect key retained for the same reason.
            "defect_area_percent": (
                defect_summary
            ),
            "condition_distribution": (
                condition_distribution
            ),
            "potatoes": potatoes,
            "review_required": False,
        }
