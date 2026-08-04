#!/usr/bin/env python3
"""Create SHAP summaries for a learned recommendation estimator.

The shipped application uses an exact deterministic contribution decomposition.
Use this helper after replacing the rule engine with a trained tree model and a
feature CSV whose target/identifier columns have already been removed.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import shap


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("ml/artifacts/shap-summary.png"))
    args = parser.parse_args()
    payload = joblib.load(args.model)
    model = payload.get("model", payload) if isinstance(payload, dict) else payload
    frame = pd.read_csv(args.features)
    explainer = shap.Explainer(model, frame.sample(min(300, len(frame)), random_state=42))
    values = explainer(frame.sample(min(500, len(frame)), random_state=43))
    shap.plots.beeswarm(values, show=False, max_display=15)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(args.output, dpi=180, bbox_inches="tight")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
