#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


def dhash(path: Path, size: int = 16) -> int:
    with Image.open(path) as image:
        gray = image.convert("L").resize((size + 1, size))
        arr = np.asarray(gray)
    diff = arr[:, 1:] > arr[:, :-1]
    value = 0
    for bit in diff.flatten():
        value = (value << 1) | int(bit)
    return value


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=Path("datasets/duplicate_report.csv"))
    parser.add_argument("--distance", type=int, default=8, help="dHash Hamming threshold")
    args = parser.parse_args()

    with args.manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    exact = defaultdict(list)
    hashes: list[tuple[dict, int]] = []
    for row in rows:
        path = Path(row["path"])
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            exact[digest].append(row)
            hashes.append((row, dhash(path)))
        except Exception as exc:
            print(f"Skip {path}: {exc}")

    report = []
    seen_pairs = set()
    for digest, group in exact.items():
        if len(group) > 1:
            base = group[0]
            for other in group[1:]:
                report.append({"type": "exact", "distance": 0, "image_a": base["path"], "image_b": other["path"], "sha256": digest})
                seen_pairs.add(tuple(sorted((base["path"], other["path"]))))

    # Bucket by leading hash bits to avoid full O(n^2) on large pools.
    buckets = defaultdict(list)
    for row, value in hashes:
        buckets[value >> 224].append((row, value))  # 16x16 dHash = 256 bits
    for bucket in buckets.values():
        for i, (row_a, hash_a) in enumerate(bucket):
            for row_b, hash_b in bucket[i + 1:]:
                pair = tuple(sorted((row_a["path"], row_b["path"])))
                if pair in seen_pairs:
                    continue
                distance = hamming(hash_a, hash_b)
                if distance <= args.distance:
                    report.append({"type": "near", "distance": distance, "image_a": row_a["path"], "image_b": row_b["path"], "sha256": ""})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["type", "distance", "image_a", "image_b", "sha256"])
        writer.writeheader()
        writer.writerows(report)
    print(f"Found {len(report)} duplicate/near-duplicate pairs -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
