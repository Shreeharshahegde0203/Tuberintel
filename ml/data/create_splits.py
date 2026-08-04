#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

from sklearn.model_selection import GroupShuffleSplit


def split_grouped(rows: list[dict], seed: int, val_size: float, test_size: float) -> list[dict]:
    originals = [r for r in rows if r.get("synthetic_or_augmented", "false").lower() != "true"]
    synthetic = [r for r in rows if r.get("synthetic_or_augmented", "false").lower() == "true"]
    groups = [r["group_id"] for r in originals]
    labels = [r["label"] for r in originals]

    first = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_val_idx, test_idx = next(first.split(originals, labels, groups))
    train_val = [originals[i] for i in train_val_idx]
    test = [originals[i] for i in test_idx]

    relative_val = val_size / (1 - test_size)
    second = GroupShuffleSplit(n_splits=1, test_size=relative_val, random_state=seed + 1)
    tv_groups = [r["group_id"] for r in train_val]
    tv_labels = [r["label"] for r in train_val]
    train_idx, val_idx = next(second.split(train_val, tv_labels, tv_groups))
    train = [train_val[i] for i in train_idx]
    val = [train_val[i] for i in val_idx]

    group_split = {r["group_id"]: "train" for r in train}
    group_split.update({r["group_id"]: "val" for r in val})
    group_split.update({r["group_id"]: "test" for r in test})
    for row in originals:
        row["split"] = group_split[row["group_id"]]
    for row in synthetic:
        # Synthetic/augmented assets are never allowed in validation/test.
        row["split"] = "train"
    return originals + synthetic


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=Path("datasets/manifest_split.csv"))
    parser.add_argument("--seed", type=int, default=20260717)
    parser.add_argument("--val", type=float, default=0.15)
    parser.add_argument("--test", type=float, default=0.20)
    args = parser.parse_args()

    with args.manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("Manifest is empty")
    output_rows = split_grouped(rows, args.seed, args.val, args.test)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0].keys()))
        writer.writeheader()
        writer.writerows(output_rows)

    counts = Counter(r["split"] for r in output_rows)
    per_label = defaultdict(Counter)
    for row in output_rows:
        per_label[row["label"]][row["split"]] += 1
    print("Split totals:", dict(counts))
    for label in sorted(per_label):
        print(label, dict(per_label[label]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
