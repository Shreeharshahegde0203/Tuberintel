#!/usr/bin/env python3
"""Download only licence-audited dataset sources from registry.yaml.

Mendeley sources intentionally require a manual export or a direct file URL because
API/download contracts and file versions can change. This script never scrapes pages
or silently downloads assets with unclear licences.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value)


def clone_git(url: str, destination: Path) -> None:
    if destination.exists() and (destination / ".git").exists():
        subprocess.run(["git", "-C", str(destination), "pull", "--ff-only"], check=True)
        return
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError(f"Refusing to overwrite non-empty directory: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", url, str(destination)], check=True)


def download_huggingface(repo_id: str, destination: Path) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError(
            "huggingface_hub is required. Install ml/data/requirements.txt first."
        ) from exc
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError(f"Refusing to overwrite non-empty directory: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        local_dir=destination,
        local_dir_use_symlinks=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=Path(__file__).with_name("registry.yaml"))
    parser.add_argument("--output", type=Path, default=Path("datasets/raw"))
    parser.add_argument("--source", action="append", help="Source ID to download; may be repeated")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    registry = yaml.safe_load(args.registry.read_text(encoding="utf-8"))
    sources = registry.get("sources", [])
    selected = set(args.source or [])

    if args.list:
        for item in sources:
            print(f"{item['id']:<32} {item.get('download_method', 'manual'):<20} {item.get('license', 'unknown')}")
        return 0

    args.output.mkdir(parents=True, exist_ok=True)
    manual: list[dict] = []
    for item in sources:
        if selected and item["id"] not in selected:
            continue
        if item.get("include") is False:
            continue
        method = item.get("download_method")
        target = args.output / safe_name(item["id"])
        if item.get("license") in {None, "unknown", "verify_dataset_assets"}:
            manual.append(item)
            print(f"SKIP {item['id']}: dataset asset licence needs review", file=sys.stderr)
            continue
        if method == "git":
            print(f"Downloading {item['id']} from {urlparse(item['source_url']).netloc}")
            clone_git(item["source_url"], target)
        elif method == "huggingface":
            print(f"Downloading {item['id']} from Hugging Face")
            download_huggingface(item["repo_id"], target)
        else:
            manual.append(item)

    if manual:
        print("\nManual/licence-review sources:")
        for item in manual:
            print(f"- {item['id']}: {item['source_url']} ({item.get('license', 'unknown')})")
            print(f"  Place the exported files under: {args.output / safe_name(item['id'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
