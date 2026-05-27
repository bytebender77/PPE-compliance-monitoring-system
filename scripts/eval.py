"""
scripts/eval.py — Evaluate a trained PPE model on the held-out test split.

Run this ONCE after training is complete. Never use the test split for tuning.

Usage
-----
# Evaluate best.pt on test split (default)
python scripts/eval.py

# Evaluate a specific checkpoint
python scripts/eval.py --model runs/train/ppe_v1/weights/best.pt

# Evaluate on val split instead
python scripts/eval.py --split val

# Save prediction images for visual inspection
python scripts/eval.py --save-images
"""

import argparse
from pathlib import Path


CLASS_NAMES  = ["helmet", "safety_vest", "goggles"]

# Minimum acceptable mAP per class before integrating into the pipeline
MAP_TARGETS = {
    "helmet":      0.85,
    "safety_vest": 0.80,
    "goggles":     0.70,   # lower — smaller object, less training data
}


def evaluate(model_path: str, split: str, save_images: bool, conf: float) -> None:
    from ultralytics import YOLO

    model_path = Path(model_path)
    if not model_path.exists():
        print(f"ERROR: Model not found at {model_path}")
        print("Run scripts/train.py first, or pass --model <path>")
        raise SystemExit(1)

    print(f"\nPPE Model Evaluation")
    print(f"{'═' * 50}")
    print(f"Model : {model_path}")
    print(f"Split : {split}")
    print(f"Conf  : {conf}\n")

    model = YOLO(str(model_path))

    metrics = model.val(
        data="data/data.yaml",
        split=split,
        imgsz=640,
        conf=conf,
        iou=0.5,
        save=save_images,
        plots=True,
        verbose=False,
    )

    # ── Overall metrics ───────────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"  Overall results")
    print(f"{'─' * 50}")
    print(f"  mAP@0.5      : {metrics.box.map50:.3f}")
    print(f"  mAP@0.5:0.95 : {metrics.box.map:.3f}")
    print(f"  Precision    : {metrics.box.mp:.3f}")
    print(f"  Recall       : {metrics.box.mr:.3f}")

    # ── Per-class metrics ─────────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"  Per-class mAP@0.5")
    print(f"{'─' * 50}")
    print(f"  {'Class':<14} {'mAP@0.5':>8}  {'Target':>8}  {'Status'}")
    print(f"  {'─'*46}")

    failures = []
    for i, name in enumerate(CLASS_NAMES):
        try:
            class_map = metrics.box.ap50[i]
        except (IndexError, AttributeError):
            class_map = 0.0

        target = MAP_TARGETS.get(name, 0.80)
        status = "✓ PASS" if class_map >= target else "✗ FAIL"
        if class_map < target:
            failures.append((name, class_map, target))
        print(f"  {name:<14} {class_map:>8.3f}  {target:>8.3f}  {status}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    print(f"\n{'═' * 50}")
    if not failures:
        print("  All targets met. Model is ready for integration.")
        print(f"\n  Next: update inference/detector.py to load models/best.pt")
    else:
        print(f"  {len(failures)} class(es) below target:")
        for name, got, target in failures:
            gap = target - got
            print(f"    {name}: {got:.3f}  (need {target:.3f}, gap={gap:.3f})")
        print()
        print("  Options:")
        print("  1. Train more epochs     : add --epochs 150 in train.py")
        print("  2. Lower confidence threshold and retune")
        print("  3. Collect more training data for failing classes")
        print("  4. Accept lower target for goggles if data is limited")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate trained PPE model on test split.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--model", default="models/best.pt",
        help="Path to .pt weights file (default: models/best.pt).",
    )
    parser.add_argument(
        "--split", choices=["test", "val"], default="test",
        help="Which split to evaluate on (default: test).",
    )
    parser.add_argument(
        "--save-images", action="store_true",
        help="Save prediction images to runs/val/ for visual inspection.",
    )
    parser.add_argument(
        "--conf", type=float, default=0.25,
        help="Confidence threshold for evaluation (default: 0.25).",
    )
    args = parser.parse_args()
    evaluate(args.model, args.split, args.save_images, args.conf)


if __name__ == "__main__":
    main()
