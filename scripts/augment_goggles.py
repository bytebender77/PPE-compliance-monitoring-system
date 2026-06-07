"""
scripts/augment_goggles.py
──────────────────────────
Converts the "safety goggles.v3i.yolov8" dataset for merging into the
main PPE training pipeline.

What this script does
─────────────────────
1. Converts segmentation polygon labels  → YOLO bounding-box labels
2. Remaps class IDs:
     original 0 (helmet)        → 0  (unchanged)
     original 1 (safety_goggles)→ 2  (matches our main model: 0=helmet, 1=safety_vest, 2=goggles)
3. Applies heavy augmentation to grow 81 train images → 400+ images
4. Writes a clean fine-tune ready dataset at:
     data/goggles_finetune/
       ├── train/images/  ├── train/labels/
       ├── val/images/    ├── val/labels/
       ├── test/images/   ├── test/labels/
       └── data.yaml

Run:
    python scripts/augment_goggles.py

Then fine-tune with:
    python scripts/train.py  --data data/goggles_finetune/data.yaml \
                              --epochs 30 --weights models/best.pt
"""

import cv2
import numpy as np
import os
import shutil
import random
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

SRC_ROOT  = Path("safety goggles.v3i.yolov8")
DST_ROOT  = Path("data/goggles_finetune")

# Class remap: {original_id: new_id}
CLASS_REMAP = {0: 0, 1: 2}

# Augmentation target per source image (train split only)
AUG_MULTIPLIER = 5          # 81 images × 5 = 405 augmented images

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

SPLITS = ["train", "valid", "test"]
SPLIT_MAP = {"train": "train", "valid": "val", "test": "test"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def polygon_to_bbox(coords: list[float]) -> tuple[float, float, float, float]:
    """Convert flat polygon [x1,y1,x2,y2,...] to YOLO bbox (cx, cy, w, h) — normalised."""
    xs = coords[0::2]
    ys = coords[1::2]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2
    w  = x_max - x_min
    h  = y_max - y_min
    return cx, cy, w, h


def read_label(label_path: Path) -> list[tuple]:
    """
    Read a YOLO label file (bbox or segmentation) and return
    list of (class_id, cx, cy, w, h) in normalised coords.
    """
    boxes = []
    if not label_path.exists():
        return boxes
    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            cls = int(parts[0])
            coords = list(map(float, parts[1:]))
            if len(coords) == 4:
                # Already bbox
                cx, cy, w, h = coords
            else:
                # Segmentation polygon → convert to bbox
                cx, cy, w, h = polygon_to_bbox(coords)
            # Clamp to [0, 1]
            cx = max(0.0, min(1.0, cx))
            cy = max(0.0, min(1.0, cy))
            w  = max(0.001, min(1.0, w))
            h  = max(0.001, min(1.0, h))
            # Remap class
            new_cls = CLASS_REMAP.get(cls, cls)
            boxes.append((new_cls, cx, cy, w, h))
    return boxes


def write_label(label_path: Path, boxes: list[tuple]) -> None:
    label_path.parent.mkdir(parents=True, exist_ok=True)
    with open(label_path, "w") as f:
        for cls, cx, cy, w, h in boxes:
            f.write(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")


def copy_image(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


# ── Augmentation pipeline ─────────────────────────────────────────────────────

def augment_image_and_boxes(
    img: np.ndarray,
    boxes: list[tuple],
    aug_idx: int,
) -> tuple[np.ndarray, list[tuple]]:
    """
    Apply a deterministic-random augmentation set based on aug_idx.
    Boxes stay in normalised YOLO format; spatial transforms update them.

    Returns (augmented_image, updated_boxes).
    """
    h, w = img.shape[:2]
    out   = img.copy()
    bxs   = [list(b) for b in boxes]   # mutable copy

    rng = np.random.default_rng(RANDOM_SEED + aug_idx * 31)

    # ── 1. Horizontal flip ────────────────────────────────────────────────────
    if rng.random() < 0.5:
        out = cv2.flip(out, 1)
        for b in bxs:
            b[1] = 1.0 - b[1]   # cx flips

    # ── 2. Brightness / contrast (additive + multiplicative) ─────────────────
    beta  = rng.integers(-40, 41)                # brightness shift
    alpha = rng.uniform(0.7, 1.4)               # contrast scale
    out   = cv2.convertScaleAbs(out, alpha=alpha, beta=beta)

    # ── 3. HSV colour jitter ──────────────────────────────────────────────────
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.int32)
    hsv[:, :, 0] = np.clip(hsv[:, :, 0] + rng.integers(-18, 19), 0, 179)   # hue
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] + rng.integers(-40, 41), 0, 255)   # sat
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] + rng.integers(-40, 41), 0, 255)   # val
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # ── 4. Random rotation (±15°) ────────────────────────────────────────────
    angle = rng.uniform(-15, 15)
    M     = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    out   = cv2.warpAffine(out, M, (w, h),
                           borderMode=cv2.BORDER_REFLECT_101)
    rad   = np.deg2rad(angle)
    cos_a, sin_a = np.cos(rad), np.sin(rad)
    new_bxs = []
    for b in bxs:
        cls, cx, cy, bw, bh = b
        # Convert to pixel corners, rotate, back to normalised
        px, py = cx * w, cy * h
        rpx = cos_a * (px - w/2) - sin_a * (py - h/2) + w/2
        rpy = sin_a * (px - w/2) + cos_a * (py - h/2) + h/2
        new_cx = np.clip(rpx / w, 0.01, 0.99)
        new_cy = np.clip(rpy / h, 0.01, 0.99)
        # Width/height stay approximately the same for small angles
        new_bxs.append((cls, new_cx, new_cy, bw, bh))
    bxs = new_bxs

    # ── 5. Random scale crop (zoom in 0–20%) ─────────────────────────────────
    scale = rng.uniform(0.82, 1.0)
    if scale < 0.99:
        crop_h = int(h * scale)
        crop_w = int(w * scale)
        top  = rng.integers(0, h - crop_h + 1)
        left = rng.integers(0, w - crop_w + 1)
        out  = out[top:top+crop_h, left:left+crop_w]
        out  = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
        new_bxs = []
        for b in bxs:
            cls, cx, cy, bw, bh = b
            # Remap box coords to cropped region
            new_cx = (cx * w - left) / crop_w
            new_cy = (cy * h - top)  / crop_h
            new_bw = bw * w / crop_w
            new_bh = bh * h / crop_h
            # Only keep box if center is still visible
            if 0.01 < new_cx < 0.99 and 0.01 < new_cy < 0.99:
                new_bxs.append((
                    cls,
                    np.clip(new_cx, 0.01, 0.99),
                    np.clip(new_cy, 0.01, 0.99),
                    min(new_bw, 0.99),
                    min(new_bh, 0.99),
                ))
        bxs = new_bxs

    # ── 6. Gaussian blur (occasionally) ──────────────────────────────────────
    if rng.random() < 0.3:
        k = rng.choice([3, 5])
        out = cv2.GaussianBlur(out, (k, k), 0)

    # ── 7. JPEG compression artefact (simulate CCTV) ─────────────────────────
    if rng.random() < 0.25:
        quality = int(rng.integers(55, 90))
        _, enc = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, quality])
        out = cv2.imdecode(enc, cv2.IMREAD_COLOR)

    # ── 8. Grayscale (simulate B&W CCTV feed) ────────────────────────────────
    if rng.random() < 0.15:
        gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
        out  = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    return out, [tuple(b) for b in bxs]


# ── Main conversion + augmentation ───────────────────────────────────────────

def process_split(split: str, augment: bool) -> tuple[int, int]:
    """Process one split. Returns (images_written, labels_written)."""
    src_img_dir = SRC_ROOT / split / "images"
    src_lbl_dir = SRC_ROOT / split / "labels"

    dst_name    = SPLIT_MAP[split]
    dst_img_dir = DST_ROOT / dst_name / "images"
    dst_lbl_dir = DST_ROOT / dst_name / "labels"
    dst_img_dir.mkdir(parents=True, exist_ok=True)
    dst_lbl_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(src_img_dir.glob("*.jpg")) + \
                  sorted(src_img_dir.glob("*.jpeg")) + \
                  sorted(src_img_dir.glob("*.png"))

    img_count = lbl_count = 0

    for img_path in image_paths:
        stem      = img_path.stem
        lbl_path  = src_lbl_dir / f"{stem}.txt"
        boxes     = read_label(lbl_path)

        img = cv2.imread(str(img_path))
        if img is None:
            print(f"  [WARN] Could not read {img_path}")
            continue

        # ── Copy original (converted labels) ─────────────────────────────────
        dst_img = dst_img_dir / f"{stem}.jpg"
        dst_lbl = dst_lbl_dir / f"{stem}.txt"
        cv2.imwrite(str(dst_img), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        write_label(dst_lbl, boxes)
        img_count += 1
        if boxes:
            lbl_count += 1

        # ── Augmented copies (train only) ─────────────────────────────────────
        if augment:
            for aug_i in range(AUG_MULTIPLIER):
                aug_img, aug_boxes = augment_image_and_boxes(img, boxes, aug_i)
                if not aug_boxes:
                    continue   # skip if all boxes went out of frame
                aug_stem = f"{stem}_aug{aug_i:02d}"
                cv2.imwrite(str(dst_img_dir / f"{aug_stem}.jpg"), aug_img,
                            [cv2.IMWRITE_JPEG_QUALITY, 92])
                write_label(dst_lbl_dir / f"{aug_stem}.txt", aug_boxes)
                img_count += 1
                lbl_count += 1

    return img_count, lbl_count


def write_data_yaml() -> None:
    yaml_content = f"""# Fine-tune dataset — safety goggles (clear + tinted)
# Classes match the main PPE model: 0=helmet, 1=safety_vest, 2=goggles
train: {(DST_ROOT / 'train' / 'images').resolve()}
val:   {(DST_ROOT / 'val'   / 'images').resolve()}
test:  {(DST_ROOT / 'test'  / 'images').resolve()}

nc: 3
names: ['helmet', 'safety_vest', 'goggles']
"""
    (DST_ROOT / "data.yaml").write_text(yaml_content)
    print(f"  ✓ Wrote {DST_ROOT / 'data.yaml'}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if DST_ROOT.exists():
        shutil.rmtree(DST_ROOT)
        print(f"  Cleared existing {DST_ROOT}")

    print("\n── Safety Goggles Dataset Conversion & Augmentation ──────────────────")
    print(f"   Source  : {SRC_ROOT}")
    print(f"   Output  : {DST_ROOT}")
    print(f"   Class remap: {CLASS_REMAP}  (1=safety_goggles → 2=goggles)")
    print(f"   Aug multiplier on train: ×{AUG_MULTIPLIER}\n")

    total_imgs = total_lbls = 0

    for split in SPLITS:
        src_dir = SRC_ROOT / split / "images"
        if not src_dir.exists():
            print(f"  [SKIP] {split} — no images directory")
            continue

        augment = (split == "train")
        n_imgs, n_lbls = process_split(split, augment)
        total_imgs += n_imgs
        total_lbls += n_lbls
        print(f"  {split:6s} → {SPLIT_MAP[split]:5s}  |  {n_imgs:4d} images  {n_lbls:4d} labels written")

    write_data_yaml()

    print(f"\n  ── Summary ──────────────────────────────────────────")
    print(f"  Total images : {total_imgs}")
    print(f"  Total labels : {total_lbls}")
    print(f"\n  ── Next step ─────────────────────────────────────────")
    print(f"  Fine-tune with:")
    print(f"    python scripts/train.py \\")
    print(f"      --data {DST_ROOT}/data.yaml \\")
    print(f"      --epochs 30 \\")
    print(f"      --weights models/best.pt")
    print(f"\n  Or use Ultralytics directly:")
    print(f"    yolo detect train \\")
    print(f"      data={DST_ROOT}/data.yaml \\")
    print(f"      model=models/best.pt \\")
    print(f"      epochs=30 imgsz=640 batch=16 \\")
    print(f"      name=goggles_finetune")
    print()


if __name__ == "__main__":
    main()
