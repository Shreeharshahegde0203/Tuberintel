#!/usr/bin/env python3
"""Benchmark multiple tuber classifiers on a fixed provenance-aware manifest.

This script is intentionally research-oriented: it never creates a random image
split. The manifest must already contain leakage-safe train/val/test assignments.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
from collections import Counter
from pathlib import Path

import numpy as np
import timm
import torch
from PIL import Image
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
)
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms

MODELS = [
    "tf_efficientnetv2_s.in21k_ft_in1k",
    "convnext_tiny.fb_in22k_ft_in1k",
    "densenet169",
    "mobilenetv3_large_100",
    "swin_tiny_patch4_window7_224.ms_in22k_ft_in1k",
]


class ManifestDataset(Dataset):
    def __init__(self, rows: list[dict], labels: dict[str, int], transform):
        self.rows = rows
        self.labels = labels
        self.transform = transform

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        row = self.rows[index]
        with Image.open(row["path"]) as image:
            image = image.convert("RGB")
            tensor = self.transform(image)
        return tensor, self.labels[row["label"]]


def seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def make_transforms(size: int):
    normalize = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    train = transforms.Compose([
        transforms.RandomResizedCrop(size, scale=(0.72, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(0.2, 0.2, 0.15, 0.02),
        transforms.ToTensor(),
        normalize,
        transforms.RandomErasing(p=0.1),
    ])
    evaluate = transforms.Compose([transforms.Resize((size, size)), transforms.ToTensor(), normalize])
    return train, evaluate


def expected_calibration_error(probabilities: np.ndarray, labels: np.ndarray, bins: int = 15) -> float:
    confidences = probabilities.max(axis=1)
    predictions = probabilities.argmax(axis=1)
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for low, high in zip(edges[:-1], edges[1:]):
        mask = (confidences > low) & (confidences <= high)
        if not mask.any():
            continue
        accuracy = (predictions[mask] == labels[mask]).mean()
        confidence = confidences[mask].mean()
        ece += mask.mean() * abs(accuracy - confidence)
    return float(ece)


def evaluate(model, loader, device):
    model.eval()
    targets, preds, probs = [], [], []
    latency = []
    with torch.inference_mode():
        for images, labels in loader:
            images = images.to(device)
            if device.type == "cuda":
                torch.cuda.synchronize()
            start = time.perf_counter()
            logits = model(images)
            if device.type == "cuda":
                torch.cuda.synchronize()
            latency.append((time.perf_counter() - start) / images.size(0))
            probability = logits.softmax(dim=1).cpu().numpy()
            probs.append(probability)
            preds.extend(probability.argmax(axis=1).tolist())
            targets.extend(labels.tolist())
    return np.asarray(targets), np.asarray(preds), np.concatenate(probs), float(np.mean(latency) * 1000)


def train_one(model_name: str, rows: list[dict], output: Path, args) -> dict:
    labels_list = sorted({row["label"] for row in rows})
    label_to_id = {label: idx for idx, label in enumerate(labels_list)}
    train_rows = [row for row in rows if row["split"] == "train"]
    val_rows = [row for row in rows if row["split"] == "val"]
    test_rows = [row for row in rows if row["split"] == "test" and row.get("synthetic_or_augmented", "false") != "true"]
    if not train_rows or not val_rows or not test_rows:
        raise ValueError("Manifest must contain non-empty train, val and real-only test splits")

    train_tf, eval_tf = make_transforms(args.image_size)
    train_ds = ManifestDataset(train_rows, label_to_id, train_tf)
    val_ds = ManifestDataset(val_rows, label_to_id, eval_tf)
    test_ds = ManifestDataset(test_rows, label_to_id, eval_tf)

    counts = Counter(label_to_id[row["label"]] for row in train_rows)
    sample_weights = [1.0 / counts[label_to_id[row["label"]]] for row in train_rows]
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)
    common = dict(batch_size=args.batch_size, num_workers=args.workers, pin_memory=torch.cuda.is_available())
    train_loader = DataLoader(train_ds, sampler=sampler, **common)
    val_loader = DataLoader(val_ds, shuffle=False, **common)
    test_loader = DataLoader(test_ds, shuffle=False, **common)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = timm.create_model(model_name, pretrained=True, num_classes=len(labels_list)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.06)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    best_f1, best_state, stale = -1.0, None, 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
                loss = criterion(model(images), labels)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            scaler.step(optimizer)
            scaler.update()
        y_val, p_val, _, _ = evaluate(model, val_loader, device)
        score = f1_score(y_val, p_val, average="macro", zero_division=0)
        print(f"{model_name} epoch={epoch} val_macro_f1={score:.4f}")
        if score > best_f1:
            best_f1 = score
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= args.patience:
                break

    if best_state is None:
        raise RuntimeError("No checkpoint created")
    model.load_state_dict(best_state)
    model.to(device)
    y_true, y_pred, probability, latency_ms = evaluate(model, test_loader, device)
    report = classification_report(y_true, y_pred, target_names=labels_list, output_dict=True, zero_division=0)
    metrics = {
        "model": model_name,
        "labels": labels_list,
        "validation_macro_f1": best_f1,
        "test_macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "test_weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "test_balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "test_mcc": matthews_corrcoef(y_true, y_pred),
        "expected_calibration_error": expected_calibration_error(probability, y_true),
        "latency_ms_per_image": latency_ms,
        "classification_report": report,
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        "split_counts": {"train": len(train_rows), "val": len(val_rows), "test": len(test_rows)},
    }
    safe = model_name.replace("/", "_").replace(".", "_")
    torch.save({"model_name": model_name, "classes": labels_list, "state_dict": best_state, "image_size": args.image_size}, output / f"{safe}.pt")
    (output / f"{safe}.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("ml/benchmarks/classifier"))
    parser.add_argument("--models", nargs="+", default=MODELS, choices=MODELS)
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--image-size", type=int, default=320)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--seed", type=int, default=20260717)
    args = parser.parse_args()

    seed_all(args.seed)
    with args.manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    args.output.mkdir(parents=True, exist_ok=True)

    results = [train_one(name, rows, args.output, args) for name in args.models]
    results.sort(key=lambda item: item["test_macro_f1"], reverse=True)
    (args.output / "leaderboard.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\nLeaderboard")
    for result in results:
        print(f"{result['model']:<55} macro_f1={result['test_macro_f1']:.4f} ECE={result['expected_calibration_error']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
