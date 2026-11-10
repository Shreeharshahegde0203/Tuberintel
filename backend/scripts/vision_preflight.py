from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings


EXPECTED_CONDITION_CLASSES = {
    "Damaged",
    "Defected",
    "Diseased-Fungal",
    "Healthy",
    "Sprouted",
}

EXPECTED_DEFECT_CLASSES = {
    "Scab",
    "Rot",
    "Greening",
    "Mechanical Damage",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def normalize_names(
    names: Any,
) -> set[str]:
    if isinstance(names, dict):
        values = names.values()

    elif isinstance(names, (list, tuple)):
        values = names

    else:
        return set()

    return {
        str(value).strip()
        for value in values
    }


def inspect_model(
    *,
    label: str,
    path: Path | None,
    expected_task: str,
    expected_classes: set[str] | None = None,
) -> dict[str, Any]:

    result: dict[str, Any] = {
        "label": label,
        "configured": path is not None,
        "exists": False,
        "path": str(path) if path else None,
        "task": None,
        "classes": [],
        "sha256": None,
        "artifact_id": None,
        "valid": False,
        "errors": [],
    }

    if path is None:
        result["errors"].append(
            "Model path is not configured."
        )
        return result

    if not path.exists():
        result["errors"].append(
            "Configured model path does not exist."
        )
        return result

    result["exists"] = True

    try:
        from ultralytics import YOLO

        model = YOLO(str(path))

        task = getattr(
            model,
            "task",
            None,
        )

        result["task"] = task

        names = normalize_names(
            getattr(
                model,
                "names",
                {},
            )
        )

        result["classes"] = sorted(names)

        if task != expected_task:
            result["errors"].append(
                f"Expected task '{expected_task}', "
                f"found '{task}'."
            )

        if expected_classes is not None:
            if names != expected_classes:
                missing = sorted(
                    expected_classes - names
                )

                unexpected = sorted(
                    names - expected_classes
                )

                if missing:
                    result["errors"].append(
                        "Missing classes: "
                        + ", ".join(missing)
                    )

                if unexpected:
                    result["errors"].append(
                        "Unexpected classes: "
                        + ", ".join(unexpected)
                    )

        if path.is_file():
            fingerprint = sha256_file(path)

            result["sha256"] = fingerprint
            result["artifact_id"] = fingerprint[:12]

    except Exception as exc:
        result["errors"].append(
            f"Could not inspect model: {exc}"
        )

    result["valid"] = (
        result["exists"]
        and len(result["errors"]) == 0
    )

    return result


def main() -> None:
    settings = get_settings()

    condition_path = (
        settings.condition_model_path
        or settings.quality_model_path
    )

    reports = [
        inspect_model(
            label="Model A",
            path=settings.roi_model_path,
            expected_task="segment",
        ),
        inspect_model(
            label="Model B",
            path=condition_path,
            expected_task="classify",
            expected_classes=EXPECTED_CONDITION_CLASSES,
        ),
        inspect_model(
            label="Model C",
            path=settings.defect_model_path,
            expected_task="segment",
            expected_classes=EXPECTED_DEFECT_CLASSES,
        ),
    ]

    print()
    print("=" * 72)
    print("TUBERINTEL VISION V1 PREFLIGHT")
    print("=" * 72)

    print()
    print(
        "Runtime mode:",
        settings.model_mode,
    )

    for report in reports:
        print()
        print("-" * 72)
        print(report["label"])
        print("-" * 72)

        print(
            "configured:",
            report["configured"],
        )

        print(
            "exists:",
            report["exists"],
        )

        print(
            "path:",
            report["path"],
        )

        if report["task"]:
            print(
                "task:",
                report["task"],
            )

        if report["classes"]:
            print(
                "classes:",
                report["classes"],
            )

        if report["artifact_id"]:
            print(
                "artifact id:",
                report["artifact_id"],
            )

        print(
            "valid:",
            report["valid"],
        )

        for error in report["errors"]:
            print(
                "  ERROR:",
                error,
            )

    ready = all(
        report["valid"]
        for report in reports
    )

    print()
    print("=" * 72)

    if ready:
        print(
            "VISION V1 PREFLIGHT: READY"
        )
    else:
        print(
            "VISION V1 PREFLIGHT: NOT READY"
        )
        print(
            "This is expected while final validated "
            "A/B/C artifacts are not installed."
        )

    print("=" * 72)

    manifest = {
        "runtime_mode": settings.model_mode,
        "ready": ready,
        "models": reports,
    }

    output = Path(
        "vision_preflight_report.json"
    )

    output.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "Report:",
        output.resolve(),
    )


if __name__ == "__main__":
    main()
