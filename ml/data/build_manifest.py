#!/usr/bin/env python3
"""Build a provenance-aware manifest from label-directory datasets.

Expected layout: <root>/<source>/<class>/<image>.jpg. A CSV label map may be
added later; this conservative default avoids guessing labels from filenames.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

from PIL import Image

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, default=Path("datasets/manifest.csv"))
    parser.add_argument("--licence", default="unknown")
    args = parser.parse_args()

    rows = []
    for path in sorted(p for p in args.root.rglob("*") if p.suffix.lower() in EXTENSIONS):
        rel = path.relative_to(args.root)
        if len(rel.parts) < 3:
            print(f"Skipping unlabeled path (needs source/class/image): {rel}")
            continue
        source, label = rel.parts[0], rel.parts[-2]
        try:
            with Image.open(path) as image:
                width, height = image.size
        except Exception:
            continue
        stem = path.stem.lower()
        synthetic = any(token in stem for token in ("aug", "synthetic", "gan", "generated"))
        parent_id = stem.split("_aug")[0].split("-aug")[0]
        rows.append({
            "image_id": file_hash(path)[:20],
            "path": str(path.resolve()),
            "source": source,
            "label": label,
            "group_id": f"{source}:{parent_id}",
            "parent_id": parent_id,
            "synthetic_or_augmented": str(synthetic).lower(),
            "width": width,
            "height": height,
            "licence": args.licence,
            "split": "",
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["image_id", "path", "source", "label", "group_id", "parent_id", "synthetic_or_augmented", "width", "height", "licence", "split"]
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Manifest contains {len(rows)} images -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
