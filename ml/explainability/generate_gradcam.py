#!/usr/bin/env python3
"""Generate a Grad-CAM heatmap from a checkpoint created by train_quality_classifier.py."""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import timm
import torch
from PIL import Image
from torchvision import transforms


def find_last_conv(model: torch.nn.Module) -> torch.nn.Module:
    layers = [module for module in model.modules() if isinstance(module, torch.nn.Conv2d)]
    if not layers:
        raise ValueError("No convolution layer found in the model.")
    return layers[-1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("gradcam.jpg"))
    parser.add_argument("--class-index", type=int, default=None)
    args = parser.parse_args()

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    model = timm.create_model(checkpoint["model_name"], pretrained=False, num_classes=len(checkpoint["classes"]))
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    target_layer = find_last_conv(model)
    activations = []
    gradients = []
    target_layer.register_forward_hook(lambda _m, _i, output: activations.append(output))
    target_layer.register_full_backward_hook(lambda _m, _gi, go: gradients.append(go[0]))

    size = int(checkpoint.get("image_size", 384))
    rgb = Image.open(args.image).convert("RGB")
    tensor = transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])(rgb).unsqueeze(0)
    logits = model(tensor)
    class_index = args.class_index if args.class_index is not None else int(logits.argmax(1).item())
    model.zero_grad(set_to_none=True)
    logits[0, class_index].backward()
    weights = gradients[-1].mean(dim=(2, 3), keepdim=True)
    cam = torch.relu((weights * activations[-1]).sum(dim=1))[0]
    cam = cam.detach().numpy()
    cam = (cam - cam.min()) / max(cam.max() - cam.min(), 1e-8)

    original = cv2.imread(str(args.image))
    cam = cv2.resize(cam, (original.shape[1], original.shape[0]))
    heatmap = cv2.applyColorMap(np.uint8(cam * 255), cv2.COLORMAP_TURBO)
    result = cv2.addWeighted(original, 0.58, heatmap, 0.42, 0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output), result)
    label = checkpoint["classes"][class_index]
    print(f"Predicted/explained class: {label}; saved {args.output}")


if __name__ == "__main__":
    main()
