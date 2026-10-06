#!/usr/bin/env python3
"""Download the ONNX MiniLM-L6-v2 embedding model from Hugging Face.

Weights (model.onnx, ~90MB) are gitignored; tokenizer/config are committed.
Run from anywhere:  backend/.venv/bin/python scripts/fetch_embeddings_model.py [--force]
"""

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

HF_BASE = "https://huggingface.co/qdrant/all-MiniLM-L6-v2-onnx/resolve/main"
MODEL_DIR = (
    Path(__file__).resolve().parents[1] / "backend" / "models" / "all-MiniLM-L6-v2"
)
REQUIRED = ["tokenizer.json", "config.json", "vocab.txt", "model.onnx"]
OPTIONAL = ["model.onnx_data"]


def download(name: str, dest: Path, *, force: bool) -> bool:
    if dest.exists() and not force:
        print(f"  = {name} already present")
        return True
    url = f"{HF_BASE}/{name}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        print(f"  -> {url}")
        urllib.request.urlretrieve(url, dest)
        print(f"  ok {name} ({dest.stat().st_size // 1024} KB)")
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and name in OPTIONAL:
            print(f"  - {name} not in repo, skipping")
            return True
        print(f"  ! failed: {name}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="re-download even if present"
    )
    args = parser.parse_args()

    print(f"Model dir: {MODEL_DIR}")
    ok = all(
        download(
            name,
            MODEL_DIR / "onnx" / name if name.startswith("model.") else MODEL_DIR / name,
            force=args.force,
        )
        for name in REQUIRED
    )
    for name in OPTIONAL:
        download(name, MODEL_DIR / "onnx" / name, force=args.force)
    if not ok:
        print("Download failed.", file=sys.stderr)
        return 1
    print("Done. Weights ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
