#!/usr/bin/env python3
"""Train a YOLO11 segmentation model for potato surface defects.

Use polygon masks in Ultralytics segmentation format. Recommended classes:
bruise, common_scab, black_scurf, crack, greening, sprout, rot, cut.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("ml/configs/potato_defects.yaml"))
    parser.add_argument("--model", default="yolo11s-seg.pt")
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--project", type=Path, default=Path("ml/runs/defect-segmentation"))
    parser.add_argument("--name", default="yolo11s-potato-defects")
    parser.add_argument("--device", default=None, help="Examples: 0, cpu, 0,1")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    model = YOLO(args.model)
    result = model.train(
        data=str(args.data),
        epochs=args.epochs,
        imgsz=args.image_size,
        batch=args.batch_size,
        project=str(args.project),
        name=args.name,
        device=args.device,
        workers=args.workers,
        patience=25,
        optimizer="AdamW",
        lr0=5e-4,
        weight_decay=5e-4,
        hsv_h=0.012,
        hsv_s=0.35,
        hsv_v=0.28,
        degrees=12,
        translate=0.08,
        scale=0.25,
        fliplr=0.5,
        flipud=0.12,
        mosaic=0.65,
        mixup=0.08,
        close_mosaic=12,
        plots=True,
        seed=42,
    )
    best = Path(result.save_dir) / "weights" / "best.pt"
    print(f"Best weights: {best}")
    if best.exists():
        YOLO(str(best)).export(format="onnx", imgsz=args.image_size, simplify=True, dynamic=True)


if __name__ == "__main__":
    main()
