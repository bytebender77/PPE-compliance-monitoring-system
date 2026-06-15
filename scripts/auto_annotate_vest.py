"""
auto_annotate_vest.py — Auto-annotate captured vest images using existing model

Runs the PPE model at very low confidence on data/ppe_capture/safety_vest/
and saves YOLO .txt annotation files next to each image.

For frames where model misses the vest, we auto-draw a full-body box
(since we KNOW the image contains a vest — the user captured it in vest mode).

Run:
  python scripts/auto_annotate_vest.py
  python scripts/auto_annotate_vest.py --conf 0.01 --fallback
"""

import argparse
import shutil
from pathlib import Path
import cv2

VEST_FOLDER  = Path("data/ppe_capture/safety_vest")
VEST_CLASS_ID = 1   # safety_vest = class 1 in our model
IMAGE_EXTS   = {".jpg", ".jpeg", ".png", ".bmp"}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--conf",     type=float, default=0.01,
                   help="Model confidence threshold (default 0.01 — very low)")
    p.add_argument("--fallback", action="store_true", default=True,
                   help="If model misses vest, write a full-torso box (default True)")
    p.add_argument("--model",    default="models/best.pt",
                   help="PPE model path")
    return p.parse_args()


def xyxy_to_yolo(x1, y1, x2, y2, W, H):
    cx = ((x1 + x2) / 2) / W
    cy = ((y1 + y2) / 2) / H
    w  = (x2 - x1) / W
    h  = (y2 - y1) / H
    return cx, cy, w, h


def main():
    args = parse_args()

    from ultralytics import YOLO
    model = YOLO(args.model)
    print(f"\nModel loaded: {args.model}")
    print(f"Classes: {model.names}")
    print(f"Confidence threshold: {args.conf}")
    print(f"Fallback full-body box: {args.fallback}\n")

    images = sorted([f for f in VEST_FOLDER.iterdir()
                     if f.suffix.lower() in IMAGE_EXTS])
    if not images:
        print(f"No images found in {VEST_FOLDER}")
        return

    print(f"Found {len(images)} images in {VEST_FOLDER}\n")

    model_detected = 0
    fallback_used  = 0
    already_done   = 0

    for img_path in images:
        txt_path = img_path.with_suffix(".txt")

        if txt_path.exists():
            already_done += 1
            continue

        frame = cv2.imread(str(img_path))
        if frame is None:
            print(f"  SKIP (could not read): {img_path.name}")
            continue

        H, W = frame.shape[:2]

        results = model(frame, conf=args.conf, verbose=False)
        lines   = []

        for r in results:
            for box in r.boxes:
                cls  = int(box.cls[0])
                conf = float(box.conf[0])
                if cls != VEST_CLASS_ID:
                    continue
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                cx, cy, w, h = xyxy_to_yolo(x1, y1, x2, y2, W, H)
                lines.append(f"{VEST_CLASS_ID} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                print(f"  ✓ {img_path.name}  vest conf={conf:.3f}  box=[{x1},{y1},{x2},{y2}]")

        if not lines and args.fallback:
            # Model missed vest — write a centre-torso box (top 20%→80% height, full width)
            # Vest is typically chest-to-waist = middle 60% of frame height
            cx, cy = 0.5, 0.5
            w,  h  = 0.85, 0.60
            lines.append(f"{VEST_CLASS_ID} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            fallback_used += 1
            print(f"  ~ {img_path.name}  fallback box (model missed vest)")
        elif lines:
            model_detected += 1

        with open(txt_path, "w") as f:
            f.write("\n".join(lines))

    print(f"\n{'='*55}")
    print(f"  AUTO-ANNOTATION COMPLETE")
    print(f"{'='*55}")
    print(f"  Model detected vest : {model_detected} images")
    print(f"  Fallback box used   : {fallback_used} images")
    print(f"  Already annotated   : {already_done} images")
    print(f"  Total annotated     : {model_detected + fallback_used + already_done}")
    print(f"{'='*55}")
    print(f"\nNext — copy into merged dataset and retrain:")
    print(f"  python scripts/add_vest_to_dataset.py")


if __name__ == "__main__":
    main()
