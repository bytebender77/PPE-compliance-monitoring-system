"""
scripts/fix_vest_forgetting.py
───────────────────────────────
Safety vest catastrophic forgetting fix.

Problem:  goggles_finetune has only 453 vest annotations vs 35,945 in original.
          Fine-tuning on this dataset caused the model to forget vest detection.

Fix:      Sample 1000 vest-rich images from the original dataset and merge
          them into goggles_finetune/train — restoring class balance.

Run:
    python scripts/fix_vest_forgetting.py
"""

import shutil
import random
from pathlib import Path

random.seed(42)

# ── Config ────────────────────────────────────────────────────────────────────
SRC_IMG_DIR = Path("data/processed/images/train")
SRC_LBL_DIR = Path("data/processed/labels/train")
DST_IMG_DIR = Path("data/goggles_finetune/train/images")
DST_LBL_DIR = Path("data/goggles_finetune/train/labels")
PREFIX      = "vest_"
N_SAMPLES   = 1000   # number of vest-rich images to pull

# ── Find images with vest (class 1) labels ────────────────────────────────────
print(f"\nScanning original dataset for vest-rich images...")
vest_images = []
for lbl_file in SRC_LBL_DIR.glob("*.txt"):
    content = lbl_file.read_text()
    if not content.strip():
        continue
    # Count how many vest (class 1) boxes
    vest_count = sum(1 for line in content.splitlines() if line.startswith("1 "))
    if vest_count >= 1:
        vest_images.append((lbl_file, vest_count))

print(f"  Found {len(vest_images)} images with at least 1 vest annotation")

# Sort by vest count desc, take top N for best quality
vest_images.sort(key=lambda x: x[1], reverse=True)
selected = vest_images[:N_SAMPLES]
print(f"  Selected top {len(selected)} vest-rich images (avg {sum(v for _,v in selected)/len(selected):.1f} vests/image)")

# ── Copy to goggles_finetune ───────────────────────────────────────────────────
DST_IMG_DIR.mkdir(parents=True, exist_ok=True)
DST_LBL_DIR.mkdir(parents=True, exist_ok=True)

copied = 0
skipped = 0
for lbl_file, _ in selected:
    stem = lbl_file.stem

    # Find matching image (jpg or png)
    img_file = None
    for ext in [".jpg", ".jpeg", ".png"]:
        candidate = SRC_IMG_DIR / f"{stem}{ext}"
        if candidate.exists():
            img_file = candidate
            break

    if img_file is None:
        skipped += 1
        continue

    dst_img = DST_IMG_DIR / f"{PREFIX}{img_file.name}"
    dst_lbl = DST_LBL_DIR / f"{PREFIX}{lbl_file.name}"

    if not dst_img.exists():   # don't re-copy on re-runs
        shutil.copy2(img_file, dst_img)
        shutil.copy2(lbl_file, dst_lbl)
        copied += 1

print(f"\n  Copied  : {copied} images + labels")
print(f"  Skipped : {skipped} (image file not found)")

# ── New class balance ──────────────────────────────────────────────────────────
print(f"\nNew class balance in goggles_finetune/train:")
for cls, name in [(0,"helmet"),(1,"safety_vest"),(2,"goggles")]:
    n = sum(
        1 for f in DST_LBL_DIR.glob("*.txt")
        for line in f.read_text().splitlines()
        if line.startswith(f"{cls} ")
    )
    print(f"  class {cls} ({name:12s}): {n:,} annotations")

total_imgs = len(list(DST_IMG_DIR.glob("*")))
print(f"\n  Total train images: {total_imgs:,}")
print(f"\n── Next step ────────────────────────────────────────────────────────")
print(f"   python scripts/train_finetune.py --device mps --epochs 80")
print()
