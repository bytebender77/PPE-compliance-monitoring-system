"""
add_vest_roboflow.py — Add Roboflow vest dataset into merged_v4 + oversample

The Roboflow export uses polygon/segmentation format.
This script converts polygon → bounding box, remaps class 0→1 (safety_vest),
copies into merged_v4/train, then oversamples ×4.

Run:
  python scripts/add_vest_roboflow.py
"""

import shutil
from pathlib import Path

SRC_ROOT  = Path("final_data/safety vest.v1i.yolov8")
TRAIN_IMGS = Path("data/merged_v4/train/images")
TRAIN_LBLS = Path("data/merged_v4/train/labels")
VALID_IMGS = Path("data/merged_v4/valid/images")
VALID_LBLS = Path("data/merged_v4/valid/labels")
OVERSAMPLE = 2   # add 2 extra copies per train image → 3× total

TARGET_CLASS = 1   # safety_vest in our 4-class model
IMAGE_EXTS   = {".jpg", ".jpeg", ".png", ".bmp"}


def polygon_to_bbox(coords: list) -> tuple:
    """Convert flat polygon [x1,y1,x2,y2,...] to (cx,cy,w,h) normalized."""
    xs = coords[0::2]
    ys = coords[1::2]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    w  = x2 - x1
    h  = y2 - y1
    return cx, cy, w, h


def convert_label(src_lbl: Path) -> list:
    """Read polygon label, return list of YOLO bbox lines with class=TARGET_CLASS."""
    lines = []
    with open(src_lbl) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            # parts[0] = class id (0 = safety-vest in Roboflow)
            # parts[1:] = polygon coords (flat x y x y ...)
            coords = [float(v) for v in parts[1:]]
            if len(coords) < 4:
                continue
            cx, cy, w, h = polygon_to_bbox(coords)
            # Clamp to [0,1]
            cx = max(0.0, min(1.0, cx))
            cy = max(0.0, min(1.0, cy))
            w  = max(0.01, min(1.0, w))
            h  = max(0.01, min(1.0, h))
            lines.append(f"{TARGET_CLASS} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return lines


def main():
    for d in (TRAIN_IMGS, TRAIN_LBLS, VALID_IMGS, VALID_LBLS):
        d.mkdir(parents=True, exist_ok=True)

    train_copied = 0
    valid_copied = 0
    skipped      = 0
    oversampled  = 0

    # ── Roboflow train split → merged train (with oversampling) ────────────────
    src_img_dir = SRC_ROOT / "train" / "images"
    src_lbl_dir = SRC_ROOT / "train" / "labels"
    images = [f for f in src_img_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS]
    print(f"\nProcessing train: {len(images)} images (oversample ×{OVERSAMPLE})")

    for img in images:
        lbl = src_lbl_dir / (img.stem + ".txt")
        dst_img = TRAIN_IMGS / f"vest_rf_{img.name}"
        dst_lbl = TRAIN_LBLS / f"vest_rf_{img.stem}.txt"

        if dst_img.exists():
            skipped += 1
            continue

        bbox_lines = convert_label(lbl) if lbl.exists() else []
        if not bbox_lines:
            print(f"  SKIP (no valid boxes): {img.name}")
            skipped += 1
            continue

        shutil.copy2(img, dst_img)
        with open(dst_lbl, "w") as f:
            f.write("\n".join(bbox_lines))
        train_copied += 1

        # Oversample — YOLOv8 live augmentation varies each copy during training
        for i in range(1, OVERSAMPLE + 1):
            ov_img = TRAIN_IMGS / f"vest_rf_{img.stem}_ov{i}{img.suffix}"
            ov_lbl = TRAIN_LBLS / f"vest_rf_{img.stem}_ov{i}.txt"
            if not ov_img.exists():
                shutil.copy2(img, ov_img)
                shutil.copy2(dst_lbl, ov_lbl)
                oversampled += 1

    # ── Roboflow valid split → merged valid (NO oversampling — honest metrics) ──
    src_img_dir = SRC_ROOT / "valid" / "images"
    src_lbl_dir = SRC_ROOT / "valid" / "labels"
    if src_img_dir.exists():
        images = [f for f in src_img_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS]
        print(f"Processing valid: {len(images)} images (held out — no oversampling)")
        for img in images:
            lbl = src_lbl_dir / (img.stem + ".txt")
            dst_img = VALID_IMGS / f"vest_rf_{img.name}"
            dst_lbl = VALID_LBLS / f"vest_rf_{img.stem}.txt"
            if dst_img.exists():
                skipped += 1
                continue
            bbox_lines = convert_label(lbl) if lbl.exists() else []
            if not bbox_lines:
                skipped += 1
                continue
            shutil.copy2(img, dst_img)
            with open(dst_lbl, "w") as f:
                f.write("\n".join(bbox_lines))
            valid_copied += 1

    print(f"\n{'='*55}")
    print(f"  DONE")
    print(f"{'='*55}")
    print(f"  Train originals          : {train_copied}")
    print(f"  Train oversample (×{OVERSAMPLE})    : {oversampled}")
    print(f"  Train vest added total   : {train_copied + oversampled}  ({train_copied}×{OVERSAMPLE+1})")
    print(f"  Valid vest (held out)    : {valid_copied}")
    print(f"  Skipped                  : {skipped}")
    print(f"  Total train images now   : {len(list(TRAIN_IMGS.iterdir()))}")
    print(f"  Total valid images now   : {len(list(VALID_IMGS.iterdir()))}")
    print(f"{'='*55}")
    print(f"\nNow zip and train:")
    print(f"  cd data && zip -r merged_v4.zip merged_v4/ && cd ..")


if __name__ == "__main__":
    main()
