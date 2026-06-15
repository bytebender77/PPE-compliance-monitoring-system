"""
add_vest_to_dataset.py — Copy annotated vest images into merged_v4 train split

Run AFTER auto_annotate_vest.py.
Copies data/ppe_capture/safety_vest/*.jpg + *.txt
into data/merged_v4/train/images/ and data/merged_v4/train/labels/

Run:
  python scripts/add_vest_to_dataset.py
"""

import shutil
from pathlib import Path

SRC_IMGS = Path("data/ppe_capture/safety_vest")
DST_IMGS = Path("data/merged_v4/train/images")
DST_LBLS = Path("data/merged_v4/train/labels")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def main():
    DST_IMGS.mkdir(parents=True, exist_ok=True)
    DST_LBLS.mkdir(parents=True, exist_ok=True)

    images = [f for f in SRC_IMGS.iterdir() if f.suffix.lower() in IMAGE_EXTS]
    copied = 0
    skipped = 0

    for img in images:
        txt = img.with_suffix(".txt")
        if not txt.exists():
            print(f"  SKIP (no .txt): {img.name}")
            skipped += 1
            continue

        dst_img = DST_IMGS / f"vest_webcam_{img.name}"
        dst_lbl = DST_LBLS / f"vest_webcam_{img.stem}.txt"

        if dst_img.exists():
            skipped += 1
            continue

        shutil.copy2(img, dst_img)
        shutil.copy2(txt, dst_lbl)
        copied += 1

    print(f"\n{'='*50}")
    print(f"  DONE")
    print(f"{'='*50}")
    print(f"  Copied : {copied} images + labels")
    print(f"  Skipped: {skipped}")
    print(f"  Total train images now: {len(list(DST_IMGS.iterdir()))}")
    print(f"{'='*50}")
    print(f"\nNow zip and train on Windows:")
    print(f"  cd data && zip -r merged_v4.zip merged_v4/")
    print(f"  # Copy to Windows → retrain")


if __name__ == "__main__":
    main()
