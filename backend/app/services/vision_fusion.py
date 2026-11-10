from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any


@dataclass
class VisionFusionResult:
    quality_score: float
    quality_grade: str
    commercial_class: str

    rejection_probability: float
    confidence: float

    bruise_severity: float
    crack_severity: float
    scab_severity: float
    discoloration_severity: float
    deformity_severity: float
    sprout_severity: float
    surface_defect_severity: float

    condition_risk: float
    top_condition: str | None
    top_condition_confidence: float | None

    review_required: bool
    review_reasons: list[str]

    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VisionFusionEngine:
    """Fuse deterministic CV with TuberIntel Vision v1.

    This engine intentionally keeps the scoring rules explicit.

    The numerical weights are deployment heuristics, not regulatory
    thresholds. They must later be calibrated against the untouched
    validation/test results and real buyer outcomes.
    """

    CONDITION_RISK = {
        "Healthy": 0.00,
        "Damaged": 0.35,
        "Defected": 0.50,
        "Diseased-Fungal": 0.70,
        "Sprouted": 0.85,
    }

    # Visible potato-surface percentage at which the corresponding
    # defect evidence is treated as maximum severity for the fusion
    # heuristic. These are calibration parameters, not AGMARK limits.
    DEFECT_FULL_SCALE = {
        # Calibration parameters for TuberIntel's advisory fusion only.
        # They are NOT AGMARK thresholds.
        "scab": 60.0,
        "rot": 10.0,
        "greening": 10.0,
        "mechanical_damage": 15.0,
    }

    @staticmethod
    def _clamp(
        value: float,
        low: float = 0.0,
        high: float = 100.0,
    ) -> float:
        return float(
            max(
                low,
                min(
                    high,
                    value,
                ),
            )
        )

    @classmethod
    def _area_to_severity(
        cls,
        area_percent: float,
        full_scale_percent: float,
    ) -> float:
        if full_scale_percent <= 0:
            return 0.0

        return cls._clamp(
            float(area_percent)
            / float(full_scale_percent)
            * 100.0
        )

    @classmethod
    def _blend(
        cls,
        fallback_value: float,
        learned_value: float,
        learned_weight: float,
    ) -> float:
        learned_weight = cls._clamp(
            learned_weight,
            0.0,
            1.0,
        )

        return cls._clamp(
            fallback_value
            * (1.0 - learned_weight)
            + learned_value
            * learned_weight
        )

    @staticmethod
    def _commercial_class(
        grade: str,
    ) -> str:
        mapping = {
            "A": "Premium fresh / export candidate",
            "B": "Fresh market",
            "C": "Processing / secondary market",
            "D": "Clearance / feed / reject review",
        }

        return mapping[grade]

    @classmethod
    def _grade(
        cls,
        quality_score: float,
        surface_defect_severity: float,
    ) -> tuple[str, str]:
        if (
            quality_score >= 88
            and surface_defect_severity < 12
        ):
            grade = "A"

        elif quality_score >= 74:
            grade = "B"

        elif quality_score >= 55:
            grade = "C"

        else:
            grade = "D"

        return (
            grade,
            cls._commercial_class(
                grade
            ),
        )

    @staticmethod
    def _safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:
        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return default

    @classmethod
    def fuse(
        cls,
        *,
        image_quality: float,
        size_uniformity: float,
        cv_quality_score: float,
        cv_rejection_probability: float,
        cv_confidence: float,
        bruise_severity: float,
        crack_severity: float,
        scab_severity: float,
        discoloration_severity: float,
        deformity_severity: float,
        sprout_severity: float,
        trained_predictions: dict[str, Any],
    ) -> VisionFusionResult:

        conditions = dict(
            trained_predictions.get(
                "condition_distribution",
                {},
            )
            or {}
        )

        defects = dict(
            trained_predictions.get(
                "defect_area_percent",
                {},
            )
            or {}
        )

        stages = dict(
            trained_predictions.get(
                "stages",
                {},
            )
            or {}
        )

        potatoes = list(
            trained_predictions.get(
                "potatoes",
                [],
            )
            or []
        )

        # ----------------------------------------------------
        # MODEL B ? condition evidence
        # ----------------------------------------------------

        top_condition = None
        top_condition_confidence = None

        if conditions:
            top_condition = max(
                conditions,
                key=conditions.get,
            )

            top_condition_confidence = (
                cls._safe_float(
                    conditions[
                        top_condition
                    ]
                )
            )

        condition_risk = 0.0

        for (
            label,
            probability,
        ) in conditions.items():

            risk_weight = (
                cls.CONDITION_RISK.get(
                    label,
                    0.50,
                )
            )

            condition_risk += (
                cls._safe_float(
                    probability
                )
                * risk_weight
                * 100.0
            )

        condition_risk = cls._clamp(
            condition_risk
        )

        # ----------------------------------------------------
        # MODEL C ? visible defect surface evidence
        # ----------------------------------------------------

        scab_area = cls._safe_float(
            defects.get(
                "scab",
                0.0,
            )
        )

        rot_area = cls._safe_float(
            defects.get(
                "rot",
                0.0,
            )
        )

        green_area = cls._safe_float(
            defects.get(
                "greening",
                0.0,
            )
        )

        mechanical_area = cls._safe_float(
            defects.get(
                "mechanical_damage",
                0.0,
            )
        )

        total_visible_area = cls._safe_float(
            defects.get(
                "total_visible_defect",
                0.0,
            )
        )

        scab_model = (
            cls._area_to_severity(
                scab_area,
                cls.DEFECT_FULL_SCALE[
                    "scab"
                ],
            )
        )

        rot_model = (
            cls._area_to_severity(
                rot_area,
                cls.DEFECT_FULL_SCALE[
                    "rot"
                ],
            )
        )

        green_model = (
            cls._area_to_severity(
                green_area,
                cls.DEFECT_FULL_SCALE[
                    "greening"
                ],
            )
        )

        mechanical_model = (
            cls._area_to_severity(
                mechanical_area,
                cls.DEFECT_FULL_SCALE[
                    "mechanical_damage"
                ],
            )
        )

        # Learned defect masks dominate the matching CV proxies when
        # Model C actually produced evidence.
        if "mechanical_damage" in defects:
            bruise_severity = cls._blend(
                bruise_severity,
                mechanical_model,
                0.72,
            )

        if "scab" in defects:
            scab_severity = cls._blend(
                scab_severity,
                scab_model,
                0.60,
            )

        if (
            "greening" in defects
            or "rot" in defects
        ):
            learned_colour_damage = max(
                green_model,
                rot_model * 0.85,
            )

            discoloration_severity = (
                cls._blend(
                    discoloration_severity,
                    learned_colour_damage,
                    0.78,
                )
            )

        # Model B is currently our learned sprout evidence.
        sprouted_probability = (
            cls._safe_float(
                conditions.get(
                    "Sprouted",
                    0.0,
                )
            )
        )

        if "Sprouted" in conditions:
            sprout_severity = cls._blend(
                sprout_severity,
                sprouted_probability
                * 100.0,
                0.75,
            )

        # Crack and deformity remain transparent CV features because
        # Vision v1 does not yet have dedicated learned classes for them.
        bruise_severity = cls._clamp(
            bruise_severity
        )

        crack_severity = cls._clamp(
            crack_severity
        )

        scab_severity = cls._clamp(
            scab_severity
        )

        discoloration_severity = (
            cls._clamp(
                discoloration_severity
            )
        )

        deformity_severity = (
            cls._clamp(
                deformity_severity
            )
        )

        sprout_severity = cls._clamp(
            sprout_severity
        )

        # TUBERINTEL VISION FUSION V2: semantic defect-aware scoring
        # Severity weights prioritize commercially serious visible defects.
        # Model-C scab is supporting evidence rather than an automatic grade
        # destroyer; rot and sprouting receive stronger weight. Mechanical
        # damage is also represented directly instead of being lost upstream.
        surface_defect_severity = (
            cls._clamp(
                0.12 * bruise_severity
                + 0.08 * scab_severity
                + 0.25 * rot_model
                + 0.12 * discoloration_severity
                + 0.18 * sprout_severity
                + 0.10 * crack_severity
                + 0.05 * deformity_severity
                + 0.10 * mechanical_model
            )
        )

        # ----------------------------------------------------
        # QUALITY SCORE
        # ----------------------------------------------------

        morphology_quality = cls._clamp(
            0.65 * size_uniformity
            + 0.35
            * (
                100.0
                - deformity_severity
            )
        )

        component_total = (
            morphology_quality
            * 0.20
        )

        component_weight = 0.20

        has_condition = bool(
            conditions
        )

        has_defects = bool(
            defects
        )

        if has_condition:
            component_total += (
                (
                    100.0
                    - condition_risk
                )
                * 0.35
            )

            component_weight += 0.35

        if has_defects:
            component_total += (
                (
                    100.0
                    - surface_defect_severity
                )
                * 0.45
            )

            component_weight += 0.45

        learned_score = cls._clamp(
            component_total
            / max(
                component_weight,
                0.001,
            )
        )

        if (
            has_condition
            and has_defects
        ):
            learned_weight = 0.85

        elif (
            has_condition
            or has_defects
        ):
            learned_weight = 0.65

        else:
            learned_weight = 0.0

        quality_score = cls._clamp(
            cv_quality_score
            * (
                1.0
                - learned_weight
            )
            + learned_score
            * learned_weight
        )

        # Semantic safety caps: defect TYPE matters in addition to area.
        # These are TuberIntel advisory safeguards, not AGMARK certification.
        fungal_probability_for_grade = cls._safe_float(
            conditions.get("Diseased-Fungal", 0.0)
        )

        severe_rot = (
            rot_area >= 5.0
            or rot_model >= 50.0
        )
        moderate_rot = (
            rot_area >= 2.0
            or rot_model >= 25.0
        )
        severe_sprouting = (
            sprouted_probability >= 0.60
            or sprout_severity >= 60.0
        )
        moderate_sprouting = (
            sprouted_probability >= 0.35
            or sprout_severity >= 40.0
        )

        semantic_quality_cap = 100.0
        semantic_quality_cap_reason = None

        if severe_rot and severe_sprouting:
            semantic_quality_cap = 44.0
            semantic_quality_cap_reason = (
                "Visible rot together with strong sprouting evidence requires "
                "reject/manual-review handling."
            )
        elif severe_rot:
            semantic_quality_cap = 54.0
            semantic_quality_cap_reason = (
                "Strong visible rot evidence prevents a fresh-market grade."
            )
        elif (
            fungal_probability_for_grade >= 0.70
            and moderate_rot
        ):
            semantic_quality_cap = 54.0
            semantic_quality_cap_reason = (
                "Strong fungal-condition evidence reinforced by visible rot "
                "requires reject/manual review."
            )
        elif severe_sprouting:
            # Heavy sprouting without strong rot may still be usable in a
            # secondary/processing channel, but it must not receive A/B.
            semantic_quality_cap = 69.0
            semantic_quality_cap_reason = (
                "Strong sprouting evidence caps the batch at secondary/"
                "processing quality."
            )
        elif moderate_rot and moderate_sprouting:
            semantic_quality_cap = 54.0
            semantic_quality_cap_reason = (
                "Combined rot and sprouting evidence requires reject/manual review."
            )

        if semantic_quality_cap < 100.0:
            quality_score = min(
                quality_score,
                semantic_quality_cap,
            )

        (
            quality_grade,
            commercial_class,
        ) = cls._grade(
            quality_score,
            surface_defect_severity,
        )

        # ----------------------------------------------------
        # REJECTION RISK
        # ----------------------------------------------------

        rejection_probability = (
            cls._clamp(
                5.0
                + (
                    100.0
                    - quality_score
                )
                * 0.72
                + max(
                    0.0,
                    surface_defect_severity
                    - 35.0,
                )
                * 0.35
                + max(
                    0.0,
                    discoloration_severity
                    - 30.0,
                )
                * 0.18
                + rot_model
                * 0.08
                + cls._safe_float(
                    conditions.get(
                        "Diseased-Fungal",
                        0.0,
                    )
                )
                * 12.0
            )
        )

        # Preserve a little of the deterministic baseline when only
        # partial learned evidence is installed.
        if not (
            has_condition
            and has_defects
        ):
            rejection_probability = (
                cls._clamp(
                    0.70
                    * rejection_probability
                    + 0.30
                    * cv_rejection_probability
                )
            )

        # ----------------------------------------------------
        # CONFIDENCE + MANUAL REVIEW
        # ----------------------------------------------------

        roi_confidences = [
            cls._safe_float(
                item.get(
                    "roi_confidence"
                ),
                -1.0,
            )
            for item in potatoes
            if item.get(
                "roi_confidence"
            )
            is not None
        ]

        roi_confidences = [
            value
            for value in roi_confidences
            if value >= 0.0
        ]

        average_roi_confidence = (
            mean(
                roi_confidences
            )
            if roi_confidences
            else None
        )

        confidence_signals = [
            cv_confidence,
            image_quality,
        ]

        if (
            top_condition_confidence
            is not None
        ):
            confidence_signals.append(
                top_condition_confidence
                * 100.0
            )

        if (
            average_roi_confidence
            is not None
        ):
            confidence_signals.append(
                average_roi_confidence
                * 100.0
            )

        stage_count = sum(
            1
            for value in stages.values()
            if value
        )

        if stages:
            confidence_signals.append(
                stage_count
                / 3.0
                * 100.0
            )

        confidence = cls._clamp(
            mean(
                confidence_signals
            )
            if confidence_signals
            else cv_confidence,
            35.0,
            98.0,
        )

        review_reasons: list[str] = []

        warning = trained_predictions.get(
            "warning"
        )

        if warning:
            review_reasons.append(
                str(
                    warning
                )
            )

        if image_quality < 45.0:
            review_reasons.append(
                "Capture quality is low."
            )

        if (
            stages.get(
                "roi"
            )
            and average_roi_confidence
            is not None
            and average_roi_confidence
            < 0.45
        ):
            review_reasons.append(
                "Model A ROI confidence is low."
            )

        if (
            has_condition
            and top_condition_confidence
            is not None
            and top_condition_confidence
            < 0.55
        ):
            review_reasons.append(
                "Model B condition confidence is low."
            )

        healthy_probability = (
            cls._safe_float(
                conditions.get(
                    "Healthy",
                    0.0,
                )
            )
        )

        if (
            healthy_probability >= 0.70
            and total_visible_area >= 10.0
        ):
            review_reasons.append(
                "Model B predicts Healthy while Model C "
                "shows substantial visible defect area."
            )

        fungal_probability = (
            cls._safe_float(
                conditions.get(
                    "Diseased-Fungal",
                    0.0,
                )
            )
        )

        if (
            fungal_probability >= 0.70
            and has_defects
            and total_visible_area < 0.5
        ):
            review_reasons.append(
                "Fungal classification has little supporting "
                "visible-defect evidence."
            )

        if (
            trained_predictions.get(
                "pipeline"
            )
            == "tuberintel-vision-v1"
            and stages
            and stage_count < 3
        ):
            review_reasons.append(
                "Vision v1 is running with incomplete learned stages."
            )

        review_required = bool(
            review_reasons
        )

        return VisionFusionResult(
            quality_score=round(
                quality_score,
                2,
            ),
            quality_grade=quality_grade,
            commercial_class=(
                commercial_class
            ),
            rejection_probability=round(
                rejection_probability,
                2,
            ),
            confidence=round(
                confidence,
                2,
            ),
            bruise_severity=round(
                bruise_severity,
                2,
            ),
            crack_severity=round(
                crack_severity,
                2,
            ),
            scab_severity=round(
                scab_severity,
                2,
            ),
            discoloration_severity=round(
                discoloration_severity,
                2,
            ),
            deformity_severity=round(
                deformity_severity,
                2,
            ),
            sprout_severity=round(
                sprout_severity,
                2,
            ),
            surface_defect_severity=round(
                surface_defect_severity,
                2,
            ),
            condition_risk=round(
                condition_risk,
                2,
            ),
            top_condition=top_condition,
            top_condition_confidence=(
                round(
                    top_condition_confidence,
                    6,
                )
                if top_condition_confidence
                is not None
                else None
            ),
            review_required=(
                review_required
            ),
            review_reasons=(
                review_reasons
            ),
            diagnostics={
                "pipeline": (
                    trained_predictions.get(
                        "pipeline"
                    )
                ),
                "stages": stages,
                "condition_distribution": (
                    conditions
                ),
                "defect_area_percent": (
                    defects
                ),
                "model_a_potato_count": (
                    trained_predictions.get(
                        "potato_count"
                    )
                ),
                "regions_analyzed": (
                    trained_predictions.get(
                        "regions_analyzed"
                    )
                ),
                "average_roi_confidence": (
                    round(
                        average_roi_confidence,
                        6,
                    )
                    if average_roi_confidence
                    is not None
                    else None
                ),
                "condition_risk": round(
                    condition_risk,
                    2,
                ),
                "semantic_quality_cap": (
                    semantic_quality_cap
                    if semantic_quality_cap < 100.0
                    else None
                ),
                "semantic_quality_cap_reason": semantic_quality_cap_reason,
                "rot_severity_internal": round(
                    rot_model,
                    2,
                ),
                "visible_defect_percent": round(
                    total_visible_area,
                    4,
                ),
                "cv_quality_score": round(
                    cv_quality_score,
                    2,
                ),
                "learned_quality_score": round(
                    learned_score,
                    2,
                ),
                "learned_weight": (
                    learned_weight
                ),
            },
        )
