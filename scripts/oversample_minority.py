"""
oversample_minority.py — Balance minority classes by duplicating their images

PROBLEM (in data/merged_v4/train):
  helmet      6978 images   (majority)
  safety_vest 3948 images
  goggles     1161 images   (minority)
  gloves       600 images   (severe minority)

FIX:
  Duplicate images containing minority classes so they appear more often per
  epoch. YOLOv8's live augmentation makes each duplicate look different, so this
  adds real variety — NOT frozen copies.

Oversample factors (extra copies added per image):
  gloves  → +3 copies  (600  → ~2400 effective)
  goggles → +1 copy    (1161 → ~2300 effective)
  If an image has BOTH, the larger factor wins.

Duplicates are written into the SAME train/ folder with an _ovN suffix.
Run ONCE. Re-running detects existing _ov copies and skips them.

Run:
  python scripts/oversample_minority.py
  python scripts/oversample_minority.py --gloves 3 --goggles 1
"""

import argparse
import shutil
from pathlib import Path

TRAIN_IMG = Path("data/merged_v4/train/images")
TRAIN_LBL = Path("data/merged_v4/train/labels")

# class ids in merged_v4
GOGGLES = 2
GLOVES  = 3

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--gloves",  type=int, default=3, help="Extra copies per gloves image")
    p.add_argument("--goggles", type=int, default=1, help="Extra copies per goggles image")
    return p.parse_args()


def classes_in(label_path: Path) -> set:
    out = set()
    if not label_path.exists():
        return out
    with open(label_path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.add(int(line.split()[0]))
    return out


def main():
    args = parse_args()

    images = [f for f in TRAIN_IMG.iterdir()
              if f.suffix.lower() in IMAGE_EXTS and "_ov" not in f.stem]

    added = {"gloves": 0, "goggles": 0}
    for img in images:
        lbl = TRAIN_LBL / (img.stem + ".txt")
        cls = classes_in(lbl)

        # Decide oversample factor for this image
        factor = 0
        tag    = None
        if GLOVES in cls:
            factor = max(factor, args.gloves)
            tag = "gloves"
        if GOGGLES in cls:
            if args.goggles > factor:
                factor = args.goggles
                tag = "goggles"
            elif tag is None:
                tag = "goggles"

        if factor <= 0:
            continue

        for i in range(1, factor + 1):
            dst_img = TRAIN_IMG / f"{img.stem}_ov{i}{img.suffix}"
            dst_lbl = TRAIN_LBL / f"{img.stem}_ov{i}.txt"
            if dst_img.exists():
                continue
            shutil.copy2(img, dst_img)
            if lbl.exists():
                shutil.copy2(lbl, dst_lbl)
            else:
                dst_lbl.touch()
            added[tag] += 1

    # Recount after
    total = len([f for f in TRAIN_IMG.iterdir() if f.suffix.lower() in IMAGE_EXTS])

    print(f"\n{'='*50}")
    print(f"  OVERSAMPLING COMPLETE")
    print(f"{'='*50}")
    print(f"  Copies added (gloves images) : {added['gloves']}")
    print(f"  Copies added (goggles images): {added['goggles']}")
    print(f"  Total train images now       : {total}")
    print(f"{'='*50}")
    print(f"\n  NOTE: valid/ and test/ are untouched — metrics stay honest.\n")


if __name__ == "__main__":
    main()
