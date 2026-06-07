"""
scripts/train_finetune.py
──────────────────────────
Fine-tune the existing best.pt on the augmented goggles_finetune dataset,
which now includes 496 CCTV zoomed-crop images for 20m detection.

Strategy:
  - Start from models/best.pt  (our 4-class PPE model, mAP=0.947)
  - Freeze backbone (layers 0-9) → only train detection head
  - 80 epochs, small lr → prevent catastrophic forgetting
  - Data: data/goggles_finetune/data.yaml  (1583 train, 27 val)
  - Save best weights as: models/best_cctv.pt

Run:
    python scripts/train_finetune.py
    python scripts/train_finetune.py --device mps    # Apple Silicon
    python scripts/train_finetune.py --epochs 100
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Config ────────────────────────────────────────────────────────────────────
BASE_MODEL   = Path("models/best.pt")
DATA_YAML    = Path("data/goggles_finetune/data.yaml")
MODELS_DIR   = Path("models")
RUNS_DIR     = Path("runs/finetune")
RUN_NAME     = "ppe_cctv_v1"
OUTPUT_NAME  = "best_cctv.pt"

_PROJECT_ABS = str(Path.cwd() / RUNS_DIR)

TRAIN_CONFIG = {
    "data":          str(DATA_YAML),
    "epochs":        80,
    "imgsz":         640,
    "batch":         8,           # small — MPS / CPU friendly
    "lr0":           0.001,       # lower lr for fine-tuning
    "lrf":           0.01,
    "momentum":      0.937,
    "weight_decay":  0.0005,
    "warmup_epochs": 2,
    "patience":      20,
    "freeze":        10,          # freeze backbone (layers 0-9)
    "augment":       True,
    "hsv_h":         0.015,
    "hsv_s":         0.7,
    "hsv_v":         0.4,
    "flipud":        0.0,
    "fliplr":        0.5,
    "mosaic":        0.5,
    "save":          True,
    "save_period":   10,
    "val":           True,
    "plots":         True,
    "project":       _PROJECT_ABS,
    "name":          RUN_NAME,
    "exist_ok":      True,
}


def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune PPE model on CCTV data")
    parser.add_argument("--device", default="", help="cpu / mps / cuda")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch",  type=int, default=None)
    parser.add_argument("--no-freeze", action="store_true",
                        help="Train all layers (slower, may forget old classes)")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.epochs: TRAIN_CONFIG["epochs"] = args.epochs
    if args.batch:  TRAIN_CONFIG["batch"]  = args.batch
    if args.no_freeze: TRAIN_CONFIG["freeze"] = 0

    device = args.device or "mps"  # default to Apple Silicon

    print("\nPPE Fine-Tuning — CCTV Zoomed Crops")
    print("═" * 50)
    print(f"  Base model : {BASE_MODEL}")
    print(f"  Dataset    : {DATA_YAML}")
    print(f"  Epochs     : {TRAIN_CONFIG['epochs']}")
    print(f"  Batch      : {TRAIN_CONFIG['batch']}")
    print(f"  Freeze     : {TRAIN_CONFIG['freeze']} backbone layers")
    print(f"  Device     : {device}")
    print(f"  Output     : models/{OUTPUT_NAME}")

    # Pre-flight
    errors = []
    if not BASE_MODEL.exists():
        errors.append(f"  ✗ Base model not found: {BASE_MODEL}")
    else:
        print(f"\n  ✓ Base model: {BASE_MODEL}  ({BASE_MODEL.stat().st_size/1e6:.1f} MB)")
    if not DATA_YAML.exists():
        errors.append(f"  ✗ data.yaml not found: {DATA_YAML}")
    else:
        train_dir = DATA_YAML.parent / "train" / "images"
        val_dir   = DATA_YAML.parent / "val"   / "images"
        n_train = len(list(train_dir.glob("*"))) if train_dir.exists() else 0
        n_val   = len(list(val_dir.glob("*")))   if val_dir.exists() else 0
        print(f"  ✓ Dataset: {n_train} train / {n_val} val images")

    try:
        import torch
        if torch.backends.mps.is_available():
            print(f"  ✓ MPS (Apple Silicon) available")
        elif torch.cuda.is_available():
            print(f"  ✓ CUDA GPU: {torch.cuda.get_device_name(0)}")
        else:
            print(f"  ⚠ CPU only — training will be slow")
    except ImportError:
        pass

    if errors:
        for e in errors: print(e)
        sys.exit(1)

    print(f"\n  Starting fine-tuning in 3s... (Ctrl+C to cancel)")
    time.sleep(3)

    # ── Train ──────────────────────────────────────────────────────────────────
    from ultralytics import YOLO
    model = YOLO(str(BASE_MODEL))

    cfg = {**TRAIN_CONFIG}
    if device:
        cfg["device"] = device

    t0 = time.time()
    model.train(**cfg)
    elapsed = int(time.time() - t0)
    h, r = divmod(elapsed, 3600)
    m, s = divmod(r, 60)
    print(f"\n  Training time: {h}h {m}m {s}s")

    # ── Copy best.pt ───────────────────────────────────────────────────────────
    best_pt = Path(_PROJECT_ABS) / RUN_NAME / "weights" / "best.pt"
    if best_pt.exists():
        dest = MODELS_DIR / OUTPUT_NAME
        shutil.copy2(best_pt, dest)
        print(f"\n{'═'*50}")
        print(f"  Fine-tuning complete!")
        print(f"  Best weights : {best_pt}")
        print(f"  Saved as     : {dest}")
        print(f"\n  Test it:")
        print(f"    python -m ppe_compliance_system.main \\")
        print(f"      --source data/raw/videos/one_man_far.mp4 \\")
        print(f"      --zoom --device mps \\")
        print(f"      --ppe-model models/{OUTPUT_NAME}")
    else:
        print(f"\n  WARNING: best.pt not found at {best_pt}")
        print(f"  Check runs/finetune/{RUN_NAME}/weights/ manually")


if __name__ == "__main__":
    main()
