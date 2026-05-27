"""
scripts/train.py — Train a custom YOLOv8 PPE detection model.

Classes  : helmet (0) · safety_vest (1) · goggles (2)
Dataset  : data/data.yaml
Output   : runs/train/ppe_v1/weights/best.pt  (copy to models/best.pt when done)

Usage
-----
# Standard training (auto-detects GPU)
python scripts/train.py

# CPU only (slow — use only if no GPU available)
python scripts/train.py --device cpu

# Resume an interrupted training run
python scripts/train.py --resume

# Quick smoke-test (3 epochs, 10% of data) — verify setup before full run
python scripts/train.py --smoke-test
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

# Fix Unicode output on Windows (cp1252 terminal doesn't support box-drawing chars)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ── Configuration ─────────────────────────────────────────────────────────────

# Paths — relative to project root (run from /Desktop/ppedetection/)
DATA_YAML   = Path("data/data.yaml")
MODELS_DIR  = Path("models")
RUNS_DIR    = Path("runs/train")
RUN_NAME    = "ppe_v1"

# Resolve to absolute path so ultralytics doesn't prepend its own default prefix
_PROJECT_ABS = str(Path.cwd() / RUNS_DIR)

# Training hyperparameters
# These are well-tested defaults for fine-tuning YOLOv8s on a custom dataset.
# Do not change unless you understand the effect.
TRAIN_CONFIG = {
    "model":          "yolov8s.pt",   # small variant — good speed/accuracy balance
    "data":           str(DATA_YAML),
    "epochs":         100,
    "imgsz":          640,            # input resolution — standard for YOLOv8
    "batch":          16,             # reduce to 8 if GPU runs out of memory
    "lr0":            0.01,           # initial learning rate
    "lrf":            0.01,           # final lr = lr0 * lrf
    "momentum":       0.937,
    "weight_decay":   0.0005,
    "warmup_epochs":  3,              # gradual lr warmup — prevents early instability
    "patience":       20,             # early stop if val mAP doesn't improve for N epochs
    "save":           True,
    "save_period":    10,             # save checkpoint every N epochs
    "val":            True,
    "plots":          True,           # save training curves, confusion matrix
    "project":        _PROJECT_ABS,
    "name":           RUN_NAME,
    "exist_ok":       True,
}

SMOKE_TEST_CONFIG = {
    **TRAIN_CONFIG,
    "epochs":   3,
    "fraction": 0.1,                  # use 10% of dataset
    "patience":  3,
    "name":     "ppe_smoke_test",
}


# ── Pre-flight checks ─────────────────────────────────────────────────────────

def preflight(smoke_test: bool) -> None:
    """Verify everything is in place before starting training."""
    print("\nPre-flight checks")
    print("─" * 40)
    errors = []

    # data.yaml
    if DATA_YAML.exists():
        print(f"  ✓ data.yaml found       : {DATA_YAML}")
    else:
        errors.append(f"  ✗ data.yaml not found   : {DATA_YAML}")

    # Train images
    train_imgs = list(Path("data/processed/images/train").glob("*.*"))
    if train_imgs:
        print(f"  ✓ Train images          : {len(train_imgs):,}")
    else:
        errors.append("  ✗ No training images found in data/processed/images/train/")

    # Val images
    val_imgs = list(Path("data/processed/images/val").glob("*.*"))
    if val_imgs:
        print(f"  ✓ Val images            : {len(val_imgs):,}")
    else:
        errors.append("  ✗ No val images found in data/processed/images/val/")

    # ultralytics
    try:
        import ultralytics
        print(f"  ✓ ultralytics           : {ultralytics.__version__}")
    except ImportError:
        errors.append("  ✗ ultralytics not installed — run: pip install ultralytics")

    # torch + device
    try:
        import torch
        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"  ✓ GPU detected (CUDA)   : {gpu} ({vram:.1f} GB VRAM)")
            if vram < 4:
                print(f"  ⚠ Low VRAM ({vram:.1f} GB) — reduce batch to 4 in TRAIN_CONFIG")
        elif torch.backends.mps.is_available():
            print(f"  ✓ GPU detected (MPS)    : Apple Silicon — use --device mps")
        else:
            print(f"  ⚠ No GPU detected — training on CPU (will be slow)")
        print(f"  ✓ PyTorch               : {torch.__version__}")
    except ImportError:
        errors.append("  ✗ torch not installed — install from pytorch.org first")

    if errors:
        print("\nPre-flight FAILED:")
        for e in errors:
            print(e)
        sys.exit(1)

    print("\n  All checks passed.\n")


# ── Training ──────────────────────────────────────────────────────────────────

def train(device: str, resume: bool, smoke_test: bool) -> Path:
    from ultralytics import YOLO

    config = SMOKE_TEST_CONFIG if smoke_test else TRAIN_CONFIG

    if smoke_test:
        print("SMOKE TEST MODE — 3 epochs, 10% data")
        print("This is just to verify the setup works. Not a real training run.\n")

    if resume:
        # Find the last checkpoint
        last_ckpt = RUNS_DIR / RUN_NAME / "weights" / "last.pt"
        if not last_ckpt.exists():
            print(f"ERROR: No checkpoint found at {last_ckpt}")
            print("Cannot resume — start a fresh run without --resume")
            sys.exit(1)
        print(f"Resuming from: {last_ckpt}\n")
        model = YOLO(str(last_ckpt))
        results = model.train(resume=True)
    else:
        model = YOLO(config["model"])
        config_to_pass = {k: v for k, v in config.items() if k != "model"}
        if device:
            config_to_pass["device"] = device
        results = model.train(**config_to_pass)

    # Path to the best weights (use absolute path to match project setting)
    best_pt = Path(_PROJECT_ABS) / config["name"] / "weights" / "best.pt"
    return best_pt


# ── Post-training ─────────────────────────────────────────────────────────────

def post_training(best_pt: Path, smoke_test: bool) -> None:
    if smoke_test:
        print("\nSmoke test complete. Check runs/train/ppe_smoke_test/ for output.")
        print("Run without --smoke-test for full training.")
        return

    if not best_pt.exists():
        print(f"\nWARNING: best.pt not found at {best_pt}")
        print("Training may have failed or been interrupted.")
        return

    # Copy best.pt to models/
    MODELS_DIR.mkdir(exist_ok=True)
    dest = MODELS_DIR / "best.pt"
    shutil.copy2(best_pt, dest)

    print(f"\n{'═' * 50}")
    print(f"Training complete.")
    print(f"  Best weights : {best_pt}")
    print(f"  Copied to    : {dest}")
    print(f"  Results      : {best_pt.parent.parent}/")
    print(f"\nNext steps:")
    print(f"  1. Evaluate  : python scripts/eval.py")
    print(f"  2. Check     : runs/train/ppe_v1/results.png  (training curves)")
    print(f"               : runs/train/ppe_v1/confusion_matrix.png")
    print(f"  3. If mAP looks good → integrate into the inference pipeline")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train YOLOv8s PPE detector — helmet, safety_vest, goggles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--device", default="",
        help="Device: '0' (first GPU), 'cpu', '0,1' (multi-GPU). Default: auto-detect.",
    )
    parser.add_argument(
        "--epochs", type=int, default=None,
        help="Number of training epochs (overrides TRAIN_CONFIG default of 100).",
    )
    parser.add_argument(
        "--batch", type=int, default=None,
        help="Batch size (overrides TRAIN_CONFIG default of 16). Use 32 for A5000, 8 for low VRAM).",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume training from last checkpoint (runs/train/ppe_v1/weights/last.pt).",
    )
    parser.add_argument(
        "--smoke-test", action="store_true",
        help="Quick 3-epoch test on 10%% of data to verify setup. Does not produce a usable model.",
    )
    args = parser.parse_args()

    # Apply CLI overrides to TRAIN_CONFIG
    if args.epochs is not None:
        TRAIN_CONFIG["epochs"] = args.epochs
    if args.batch is not None:
        TRAIN_CONFIG["batch"] = args.batch

    print("\nPPE Detector — Training Script")
    print("═" * 50)
    print(f"Classes  : helmet · safety_vest · goggles")
    print(f"Dataset  : {DATA_YAML}")
    print(f"Model    : {TRAIN_CONFIG['model']}")
    print(f"Epochs   : {TRAIN_CONFIG['epochs']}  (early stop at patience={TRAIN_CONFIG['patience']})")
    print(f"Image sz : {TRAIN_CONFIG['imgsz']}px")
    print(f"Batch    : {TRAIN_CONFIG['batch']}")
    print(f"Output   : {RUNS_DIR / RUN_NAME}/")

    preflight(args.smoke_test)

    start = time.time()
    best_pt = train(device=args.device, resume=args.resume, smoke_test=args.smoke_test)
    elapsed = time.time() - start

    hours, rem = divmod(int(elapsed), 3600)
    mins, secs = divmod(rem, 60)
    print(f"\nTraining time: {hours}h {mins}m {secs}s")

    post_training(best_pt, args.smoke_test)


if __name__ == "__main__":
    main()
