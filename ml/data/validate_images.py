#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

from PIL import Image, ImageStat

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, default=Path("image_validation.csv"))
    parser.add_argument("--min-side", type=int, default=224)
    args = parser.parse_args()

    rows = []
    for path in sorted(p for p in args.root.rglob("*") if p.suffix.lower() in EXTENSIONS):
        row = {"path": str(path), "valid": False, "error": "", "width": 0, "height": 0, "mode": "", "sha256": "", "mean": "", "stddev": ""}
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image = image.convert("RGB")
                stat = ImageStat.Stat(image.resize((64, 64)))
                row.update(
                    valid=min(image.size) >= args.min_side,
                    error="" if min(image.size) >= args.min_side else "below_min_side",
                    width=image.width,
                    height=image.height,
                    mode=image.mode,
                    sha256=sha256(path),
                    mean="|".join(f"{v:.3f}" for v in stat.mean),
                    stddev="|".join(f"{v:.3f}" for v in stat.stddev),
                )
        except Exception as exc:  # corrupted assets are reported, not fatal
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys() if rows else ["path", "valid", "error"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Validated {len(rows)} images -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
