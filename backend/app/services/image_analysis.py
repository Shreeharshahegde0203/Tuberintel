from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.core.config import get_settings
from app.services.trained_inference import TrainedModelAdapter


@dataclass
class ImageMetrics:
    potato_count: int
    image_quality: float
    size_uniformity: float
    bruise_severity: float
    crack_severity: float
    scab_severity: float
    discoloration_severity: float
    deformity_severity: float
    sprout_severity: float
    surface_defect_severity: float
    quality_score: float
    quality_grade: str
    commercial_class: str
    rejection_probability: float
    confidence: float
    explainability_mode: str
    raw_features: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PotatoImageAnalyzer:
    """Hybrid computer-vision analyser.

    The zero-weight mode is intentionally useful: it produces reproducible geometry,
    colour and texture measurements before trained weights are available. Trained
    YOLO/torch adapters can later replace or enrich the defect masks without changing
    the API contract.
    """

    def __init__(self, model_mode: str = "cv_demo") -> None:
        self.model_mode = model_mode
        settings = get_settings()
        self.trained_adapter = TrainedModelAdapter(settings.quality_model_path, settings.defect_model_path)

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
        return float(max(low, min(high, value)))

    @staticmethod
    def _largest_components(mask: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = mask.shape
        min_area = max(250, int(h * w * 0.007))
        contours = [c for c in contours if cv2.contourArea(c) >= min_area]
        contours.sort(key=cv2.contourArea, reverse=True)
        result = np.zeros_like(mask)
        for contour in contours[:60]:
            cv2.drawContours(result, [contour], -1, 255, thickness=cv2.FILLED)
        return result, contours[:60]

    def _segment_potatoes(self, image: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        lightness = lab[:, :, 0]

        # General foreground mask that works for tan potatoes on white, grey or dark mats.
        non_white = (lightness < 238) | (saturation > 28)
        non_black = value > 24
        candidate = (non_white & non_black).astype(np.uint8) * 255

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        candidate = cv2.morphologyEx(candidate, cv2.MORPH_CLOSE, kernel, iterations=2)
        candidate = cv2.morphologyEx(candidate, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8), iterations=1)
        mask, contours = self._largest_components(candidate)

        coverage = float(np.mean(mask > 0))
        if coverage < 0.02 or coverage > 0.92:
            # GrabCut fallback for unusual backgrounds.
            h, w = image.shape[:2]
            gc_mask = np.zeros((h, w), np.uint8)
            bgd = np.zeros((1, 65), np.float64)
            fgd = np.zeros((1, 65), np.float64)
            rect = (max(1, w // 30), max(1, h // 30), max(2, w - w // 15), max(2, h - h // 15))
            try:
                cv2.grabCut(image, gc_mask, rect, bgd, fgd, 4, cv2.GC_INIT_WITH_RECT)
                candidate = np.where((gc_mask == 2) | (gc_mask == 0), 0, 255).astype(np.uint8)
                candidate = cv2.morphologyEx(candidate, cv2.MORPH_CLOSE, kernel, iterations=2)
                mask, contours = self._largest_components(candidate)
            except cv2.error:
                pass

        return mask, contours

    def analyze(self, image_path: Path, annotated_path: Path) -> ImageMetrics:
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError("The uploaded file could not be decoded as an image.")

        max_side = 1280
        h, w = image.shape[:2]
        scale = min(1.0, max_side / max(h, w))
        if scale < 1.0:
            image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        mask, contours = self._segment_potatoes(image)
        mask_bool = mask > 0
        pixel_count = int(np.count_nonzero(mask_bool))
        if pixel_count < 300:
            raise ValueError("No clear potato region was detected. Use a well-lit image with the potatoes fully visible.")

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Blur/lighting quality checks.
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        exposure_mean = float(gray[mask_bool].mean())
        exposure_penalty = abs(exposure_mean - 135.0) / 135.0
        image_quality = self._clamp(38 + min(lap_var / 5.0, 45) - exposure_penalty * 25)

        areas = np.array([cv2.contourArea(c) for c in contours], dtype=np.float64)
        if len(areas) > 1 and areas.mean() > 0:
            cv_area = float(areas.std() / areas.mean())
            size_uniformity = self._clamp(100 * (1 - min(cv_area, 1.0)))
        else:
            size_uniformity = 84.0

        l_chan, a_chan, b_chan = cv2.split(lab)
        h_chan, s_chan, v_chan = cv2.split(hsv)
        valid_l = l_chan[mask_bool]
        low_l = float(np.percentile(valid_l, 22))
        very_low_l = float(np.percentile(valid_l, 9))

        eroded = cv2.erode(mask, np.ones((9, 9), np.uint8), iterations=1) > 0
        dark_mask = eroded & (l_chan < max(62, low_l - 10)) & (s_chan > 35)
        very_dark_mask = eroded & (l_chan < max(48, very_low_l - 5))
        green_mask = eroded & (h_chan >= 34) & (h_chan <= 92) & (s_chan > 42) & (v_chan > 35)

        # Texture / scab proxy: locally dark and high-frequency surface response.
        local_mean = cv2.GaussianBlur(gray, (0, 0), 7)
        local_delta = cv2.absdiff(gray, local_mean)
        lap_abs = cv2.convertScaleAbs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
        scab_mask = eroded & (local_delta > 15) & (lap_abs > 20) & (l_chan < np.percentile(valid_l, 58))

        # Crack proxy: thin high-contrast lines away from the external contour.
        edges = cv2.Canny(gray, 55, 150)
        edges = cv2.bitwise_and(edges, edges, mask=eroded.astype(np.uint8) * 255)
        edge_components = cv2.morphologyEx(edges, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        crack_ratio = float(np.count_nonzero(edge_components) / max(pixel_count, 1))

        bruise_ratio = float(np.count_nonzero(dark_mask) / pixel_count)
        scab_ratio = float(np.count_nonzero(scab_mask) / pixel_count)
        green_ratio = float(np.count_nonzero(green_mask) / pixel_count)
        severe_dark_ratio = float(np.count_nonzero(very_dark_mask) / pixel_count)

        contour_scores: list[float] = []
        solidity_scores: list[float] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            circularity = (4 * np.pi * area / (perimeter * perimeter)) if perimeter > 0 else 0
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            solidity = area / hull_area if hull_area > 0 else 1
            x, y, cw, ch = cv2.boundingRect(contour)
            aspect = min(cw, ch) / max(cw, ch) if max(cw, ch) else 1
            contour_scores.append((circularity * 0.45) + (solidity * 0.35) + (aspect * 0.20))
            solidity_scores.append(solidity)

        shape_score = float(np.mean(contour_scores)) if contour_scores else 0.75
        mean_solidity = float(np.mean(solidity_scores)) if solidity_scores else 0.90

        bruise_severity = self._clamp((bruise_ratio * 520) + (severe_dark_ratio * 120))
        scab_severity = self._clamp(scab_ratio * 610)
        crack_severity = self._clamp(max(0.0, crack_ratio - 0.006) * 1150)
        discoloration_severity = self._clamp(green_ratio * 900 + float(np.std(a_chan[mask_bool])) * 0.7)
        deformity_severity = self._clamp((1 - shape_score) * 165)
        sprout_severity = self._clamp((1 - mean_solidity) * 250)
        surface_defect_severity = self._clamp(
            0.30 * bruise_severity
            + 0.25 * scab_severity
            + 0.18 * crack_severity
            + 0.15 * discoloration_severity
            + 0.12 * sprout_severity
        )

        trained_predictions: dict[str, Any] = {}
        if self.model_mode in {"classifier", "detector", "hybrid"} and self.trained_adapter.enabled:
            try:
                trained_predictions = self.trained_adapter.predict(image_path, image)
                detected = trained_predictions.get("defect_area_percent", {})
                def blend(current: float, labels: tuple[str, ...], scale: float = 7.0) -> float:
                    trained_value = sum(float(detected.get(label, 0.0)) for label in labels) * scale
                    return self._clamp(current * 0.42 + trained_value * 0.58) if trained_value else current
                bruise_severity = blend(bruise_severity, ("bruise", "bruising", "blackspot_bruising"))
                scab_severity = blend(scab_severity, ("scab", "common_scab", "black_scurf"))
                crack_severity = blend(crack_severity, ("crack", "cracks", "growth_crack"))
                discoloration_severity = blend(discoloration_severity, ("greening", "discoloration", "pink_rot"))
                sprout_severity = blend(sprout_severity, ("sprout", "sprouting", "germination"))
                surface_defect_severity = self._clamp(
                    0.30 * bruise_severity + 0.25 * scab_severity + 0.18 * crack_severity
                    + 0.15 * discoloration_severity + 0.12 * sprout_severity
                )
            except Exception as exc:  # optional ML must never break the safety fallback
                trained_predictions = {"warning": str(exc)}

        penalty = (
            0.25 * bruise_severity
            + 0.23 * scab_severity
            + 0.17 * crack_severity
            + 0.14 * discoloration_severity
            + 0.11 * deformity_severity
            + 0.06 * sprout_severity
            + 0.04 * (100 - size_uniformity)
        )
        quality_score = self._clamp(100 - penalty)

        if quality_score >= 88 and surface_defect_severity < 12:
            grade, commercial_class = "A", "Premium fresh / export candidate"
        elif quality_score >= 74:
            grade, commercial_class = "B", "Fresh market"
        elif quality_score >= 55:
            grade, commercial_class = "C", "Processing / secondary market"
        else:
            grade, commercial_class = "D", "Clearance / feed / reject review"

        rejection_probability = self._clamp(
            5
            + (100 - quality_score) * 0.72
            + max(0, surface_defect_severity - 35) * 0.35
            + max(0, discoloration_severity - 30) * 0.18
        )
        confidence = self._clamp(55 + image_quality * 0.30 + min(len(contours), 8) * 1.3 + (5 if trained_predictions and "warning" not in trained_predictions else 0), 45, 96)

        overlay = image.copy()
        red = np.zeros_like(image); red[:, :, 2] = 255
        green = np.zeros_like(image); green[:, :, 1] = 205
        blue = np.zeros_like(image); blue[:, :, 0] = 255
        amber = np.zeros_like(image); amber[:, :, 1] = 170; amber[:, :, 2] = 255

        for defect_mask, colour_layer, alpha in [
            (dark_mask, red, 0.34),
            (scab_mask, green, 0.28),
            (green_mask, amber, 0.32),
            (edge_components > 0, blue, 0.45),
        ]:
            idx = defect_mask.astype(bool)
            overlay[idx] = cv2.addWeighted(overlay, 1 - alpha, colour_layer, alpha, 0)[idx]

        cv2.drawContours(overlay, contours, -1, (51, 121, 74), 2)
        cv2.putText(
            overlay,
            f"Grade {grade}  |  Quality {quality_score:.1f}/100",
            (24, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (245, 245, 245),
            3,
            cv2.LINE_AA,
        )
        cv2.putText(
            overlay,
            f"Grade {grade}  |  Quality {quality_score:.1f}/100",
            (24, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (28, 59, 43),
            1,
            cv2.LINE_AA,
        )
        annotated_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(annotated_path), overlay)

        return ImageMetrics(
            potato_count=max(1, len(contours)),
            image_quality=round(image_quality, 2),
            size_uniformity=round(size_uniformity, 2),
            bruise_severity=round(bruise_severity, 2),
            crack_severity=round(crack_severity, 2),
            scab_severity=round(scab_severity, 2),
            discoloration_severity=round(discoloration_severity, 2),
            deformity_severity=round(deformity_severity, 2),
            sprout_severity=round(sprout_severity, 2),
            surface_defect_severity=round(surface_defect_severity, 2),
            quality_score=round(quality_score, 2),
            quality_grade=grade,
            commercial_class=commercial_class,
            rejection_probability=round(rejection_probability, 2),
            confidence=round(confidence, 2),
            explainability_mode=("hybrid trained-model + computer-vision features" if trained_predictions and "warning" not in trained_predictions else "computer-vision feature overlays (Grad-CAM enabled when trained weights are installed)"),
            raw_features={
                "mask_coverage": round(float(np.mean(mask_bool)), 4),
                "laplacian_variance": round(lap_var, 2),
                "mean_exposure": round(exposure_mean, 2),
                "dark_ratio": round(bruise_ratio, 4),
                "scab_texture_ratio": round(scab_ratio, 4),
                "green_ratio": round(green_ratio, 4),
                "edge_ratio": round(crack_ratio, 4),
                "mean_shape_score": round(shape_score, 4),
                "mean_solidity": round(mean_solidity, 4),
                "trained_predictions": trained_predictions,
            },
        )

    @staticmethod
    def aggregate(items: list[ImageMetrics], model_mode: str) -> dict[str, Any]:
        if not items:
            raise ValueError("At least one image analysis is required.")

        def mean(field: str) -> float:
            return round(float(np.mean([getattr(item, field) for item in items])), 2)

        quality_score = mean("quality_score")
        surface = mean("surface_defect_severity")
        if quality_score >= 88 and surface < 12:
            grade, commercial = "A", "Premium fresh / export candidate"
        elif quality_score >= 74:
            grade, commercial = "B", "Fresh market"
        elif quality_score >= 55:
            grade, commercial = "C", "Processing / secondary market"
        else:
            grade, commercial = "D", "Clearance / feed / reject review"

        return {
            "quality_score": quality_score,
            "quality_grade": grade,
            "commercial_class": commercial,
            "rejection_probability": mean("rejection_probability"),
            "size_uniformity": mean("size_uniformity"),
            "bruise_severity": mean("bruise_severity"),
            "crack_severity": mean("crack_severity"),
            "scab_severity": mean("scab_severity"),
            "discoloration_severity": mean("discoloration_severity"),
            "deformity_severity": mean("deformity_severity"),
            "sprout_severity": mean("sprout_severity"),
            "surface_defect_severity": surface,
            "confidence": mean("confidence"),
            "model_mode": model_mode,
            "feature_summary": {
                "images_analyzed": len(items),
                "potatoes_detected": sum(item.potato_count for item in items),
                "average_image_quality": mean("image_quality"),
                "explainability_mode": items[0].explainability_mode,
                "per_image": [item.to_dict() for item in items],
            },
        }
