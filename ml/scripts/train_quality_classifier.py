#!/usr/bin/env python3
"""Train a potato quality/disease classifier and export deployable artefacts.

Expected dataset layouts:

1) Pre-split:
   dataset/train/<class>/*.jpg
   dataset/val/<class>/*.jpg
   dataset/test/<class>/*.jpg

2) Unsplit:
   dataset/<class>/*.jpg
   (a deterministic stratified train/validation split is created)

The exported TorchScript model is consumed by backend/app/services/trained_inference.py.
A full checkpoint is also saved for Grad-CAM and future fine-tuning.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import timm
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from torch import nn
from torch.utils.data import DataLoader, Subset, WeightedRandomSampler
from torchvision import datasets, transforms


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def transforms_for(size: int):
    normalize = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(size, scale=(0.72, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(p=0.15),
        transforms.RandomRotation(18),
        transforms.ColorJitter(brightness=0.22, contrast=0.22, saturation=0.18, hue=0.03),
        transforms.RandomPerspective(distortion_scale=0.12, p=0.18),
        transforms.ToTensor(),
        normalize,
        transforms.RandomErasing(p=0.12, scale=(0.02, 0.10)),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        normalize,
    ])
    return train_tf, eval_tf


def make_loaders(root: Path, size: int, batch_size: int, workers: int, seed: int):
    train_tf, eval_tf = transforms_for(size)
    pre_split = (root / "train").is_dir() and (root / "val").is_dir()

    if pre_split:
        train_ds = datasets.ImageFolder(root / "train", transform=train_tf)
        val_ds = datasets.ImageFolder(root / "val", transform=eval_tf)
        test_ds = datasets.ImageFolder(root / "test", transform=eval_tf) if (root / "test").is_dir() else val_ds
        if train_ds.classes != val_ds.classes:
            raise ValueError("Train and validation class folders do not match.")
        train_targets = train_ds.targets
        classes = train_ds.classes
    else:
        raw = datasets.ImageFolder(root)
        indices = np.arange(len(raw))
        train_idx, val_idx = train_test_split(
            indices,
            test_size=0.20,
            random_state=seed,
            stratify=raw.targets,
        )
        train_base = datasets.ImageFolder(root, transform=train_tf)
        eval_base = datasets.ImageFolder(root, transform=eval_tf)
        train_ds = Subset(train_base, train_idx.tolist())
        val_ds = Subset(eval_base, val_idx.tolist())
        test_ds = val_ds
        train_targets = [raw.targets[i] for i in train_idx]
        classes = raw.classes

    counts = Counter(train_targets)
    weights_per_class = {klass: 1.0 / max(count, 1) for klass, count in counts.items()}
    sample_weights = torch.DoubleTensor([weights_per_class[target] for target in train_targets])
    sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)

    kwargs = dict(batch_size=batch_size, num_workers=workers, pin_memory=torch.cuda.is_available())
    train_loader = DataLoader(train_ds, sampler=sampler, **kwargs)
    val_loader = DataLoader(val_ds, shuffle=False, **kwargs)
    test_loader = DataLoader(test_ds, shuffle=False, **kwargs)
    return train_loader, val_loader, test_loader, classes


def run_epoch(model, loader, criterion, device, optimizer=None, scaler=None):
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    correct = 0
    count = 0
    predictions: list[int] = []
    targets: list[int] = []

    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        if training:
            optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
            logits = model(images)
            loss = criterion(logits, labels)
        if training:
            assert scaler is not None
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            scaler.step(optimizer)
            scaler.update()

        pred = logits.argmax(dim=1)
        total_loss += float(loss.item()) * labels.size(0)
        correct += int((pred == labels).sum().item())
        count += labels.size(0)
        predictions.extend(pred.detach().cpu().tolist())
        targets.extend(labels.detach().cpu().tolist())

    return {
        "loss": total_loss / max(count, 1),
        "accuracy": correct / max(count, 1),
        "predictions": predictions,
        "targets": targets,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("ml/artifacts/quality_model.ts"))
    parser.add_argument("--model", default="tf_efficientnetv2_s.in21k_ft_in1k",
                        choices=["tf_efficientnetv2_s.in21k_ft_in1k", "densenet169", "mobilenetv3_large_100"])
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--image-size", type=int, default=384)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--patience", type=int, default=7)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    seed_everything(args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    train_loader, val_loader, test_loader, classes = make_loaders(
        args.data, args.image_size, args.batch_size, args.workers, args.seed
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = timm.create_model(args.model, pretrained=True, num_classes=len(classes)).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.08)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(args.epochs, 1))
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    best_accuracy = -1.0
    stale = 0
    best_state = None
    history = []
    for epoch in range(1, args.epochs + 1):
        train_result = run_epoch(model, train_loader, criterion, device, optimizer, scaler)
        with torch.inference_mode():
            val_result = run_epoch(model, val_loader, criterion, device)
        scheduler.step()
        history.append({
            "epoch": epoch,
            "train_loss": train_result["loss"],
            "train_accuracy": train_result["accuracy"],
            "val_loss": val_result["loss"],
            "val_accuracy": val_result["accuracy"],
        })
        print(f"epoch={epoch:02d} train_acc={train_result['accuracy']:.4f} val_acc={val_result['accuracy']:.4f}")
        if val_result["accuracy"] > best_accuracy:
            best_accuracy = val_result["accuracy"]
            stale = 0
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
        else:
            stale += 1
            if stale >= args.patience:
                print("Early stopping triggered.")
                break

    if best_state is None:
        raise RuntimeError("Training produced no checkpoint.")
    model.load_state_dict(best_state)
    model.to(device)
    with torch.inference_mode():
        test_result = run_epoch(model, test_loader, criterion, device)

    report = classification_report(
        test_result["targets"], test_result["predictions"],
        target_names=classes, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(test_result["targets"], test_result["predictions"]).tolist()

    checkpoint_path = args.output.with_suffix(".checkpoint.pt")
    torch.save({
        "model_name": args.model,
        "image_size": args.image_size,
        "classes": classes,
        "state_dict": best_state,
    }, checkpoint_path)

    model.eval().cpu()
    example = torch.randn(1, 3, args.image_size, args.image_size)
    scripted = torch.jit.trace(model, example)
    scripted.save(str(args.output))
    args.output.with_suffix(".labels.json").write_text(json.dumps(classes, indent=2), encoding="utf-8")
    args.output.with_suffix(".metadata.json").write_text(json.dumps({
        "model_name": args.model,
        "image_size": args.image_size,
        "classes": classes,
        "best_validation_accuracy": best_accuracy,
        "test_accuracy": test_result["accuracy"],
        "classification_report": report,
        "confusion_matrix": matrix,
        "history": history,
    }, indent=2), encoding="utf-8")
    print(f"Saved TorchScript: {args.output}")
    print(f"Saved Grad-CAM checkpoint: {checkpoint_path}")


if __name__ == "__main__":
    main()
