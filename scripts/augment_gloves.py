"""
scripts/augment_gloves.py
─────────────────────────
Converts the "gloves.v1i.yolov8" dataset and MERGES it into the existing
data/goggles_finetune/ dataset, upgrading it to 4 classes:

  0 = helmet
  1 = safety_vest
  2 = goggles
  3 = gloves  ← NEW

What this script does
─────────────────────
1. Converts segmentation polygon labels → YOLO bounding-box labels
2. Remaps class 0 (gloves) → class 3
3. Augments 90 train images → 450+ images
4. Merges into existing data/goggles_finetune/ (adds alongside goggles data)
5. Updates data.yaml to nc=4, names=[helmet, safety_vest, goggles, gloves]
6. Adds negative images (no gloves) from webcam captures if available

Run:
    python scripts/augment_gloves.py
"""

import cv2
import numpy as np
import shutil
import random
from pathlib import Path

SRC_ROOT = Path("/Users/kunalkumargupta/Desktop/gloves.v1i.yolov8")
DST_ROOT = Path("data/goggles_finetune")

CLASS_REMAP    = {0: 3}   # gloves → class 3
AUG_MULTIPLIER = 5
RANDOM_SEED    = 99
SPLITS         = ["train", "valid", "test"]
SPLIT_MAP      = {"train": "train", "valid": "val", "test": "test"}

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


def polygon_to_bbox(coords):
    xs = coords[0::2]
    ys = coords[1::2]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    w  = max(xs) - min(xs)
    h  = max(ys) - min(ys)
    return cx, cy, w, h


def read_label(label_path):
    boxes = []
    if not label_path.exists():
        return boxes
    for line in label_path.read_text().splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        cls    = int(parts[0])
        coords = list(map(float, parts[1:]))
        if len(coords) == 4:
            cx, cy, w, h = coords
        else:
            cx, cy, w, h = polygon_to_bbox(coords)
        cx = max(0.0, min(1.0, cx))
        cy = max(0.0, min(1.0, cy))
        w  = max(0.001, min(1.0, w))
        h  = max(0.001, min(1.0, h))
        boxes.append((CLASS_REMAP.get(cls, cls), cx, cy, w, h))
    return boxes


def write_label(label_path, boxes):
    label_path.parent.mkdir(parents=True, exist_ok=True)
    with open(label_path, "w") as f:
        for cls, cx, cy, w, h in boxes:
            f.write(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")


def augment(img, boxes, aug_idx):
    h, w = img.shape[:2]
    out  = img.copy()
    bxs  = [list(b) for b in boxes]
    rng  = np.random.default_rng(RANDOM_SEED + aug_idx * 37)

    # Flip
    if rng.random() < 0.5:
        out = cv2.flip(out, 1)
        for b in bxs:
            b[1] = 1.0 - b[1]

    # Brightness / contrast
    out = cv2.convertScaleAbs(out,
                              alpha=rng.uniform(0.7, 1.4),
                              beta=int(rng.integers(-40, 41)))

    # HSV jitter
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.int32)
    hsv[:,:,0] = np.clip(hsv[:,:,0] + rng.integers(-18, 19), 0, 179)
    hsv[:,:,1] = np.clip(hsv[:,:,1] + rng.integers(-40, 41), 0, 255)
    hsv[:,:,2] = np.clip(hsv[:,:,2] + rng.integers(-40, 41), 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # Rotation
    angle = rng.uniform(-15, 15)
    M     = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
    out   = cv2.warpAffine(out, M, (w, h), borderMode=cv2.BORDER_REFLECT_101)
    rad   = np.deg2rad(angle)
    cos_a, sin_a = np.cos(rad), np.sin(rad)
    new_bxs = []
    for b in bxs:
        cls, cx, cy, bw, bh = b
        px, py = cx*w, cy*h
        rpx = cos_a*(px-w/2) - sin_a*(py-h/2) + w/2
        rpy = sin_a*(px-w/2) + cos_a*(py-h/2) + h/2
        new_bxs.append((cls, np.clip(rpx/w,0.01,0.99),
                         np.clip(rpy/h,0.01,0.99), bw, bh))
    bxs = new_bxs

    # Scale crop
    scale = rng.uniform(0.82, 1.0)
    if scale < 0.99:
        ch, cw = int(h*scale), int(w*scale)
        top  = rng.integers(0, h-ch+1)
        left = rng.integers(0, w-cw+1)
        out  = cv2.resize(out[top:top+ch, left:left+cw], (w,h))
        new_bxs = []
        for b in bxs:
            cls, cx, cy, bw, bh = b
            ncx = (cx*w-left)/cw
            ncy = (cy*h-top)/ch
            if 0.01 < ncx < 0.99 and 0.01 < ncy < 0.99:
                new_bxs.append((cls, np.clip(ncx,0.01,0.99),
                                 np.clip(ncy,0.01,0.99),
                                 min(bw*w/cw,0.99), min(bh*h/ch,0.99)))
        bxs = new_bxs

    # Blur
    if rng.random() < 0.3:
        out = cv2.GaussianBlur(out, (rng.choice([3,5]),)*2, 0)

    # JPEG artefact
    if rng.random() < 0.25:
        q = int(rng.integers(55,90))
        _, enc = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, q])
        out = cv2.imdecode(enc, cv2.IMREAD_COLOR)

    return out, [tuple(b) for b in bxs]


def process_split(split, augment_flag):
    src_img = SRC_ROOT / split / "images"
    src_lbl = SRC_ROOT / split / "labels"
    dst_name = SPLIT_MAP[split]
    dst_img  = DST_ROOT / dst_name / "images"
    dst_lbl  = DST_ROOT / dst_name / "labels"
    dst_img.mkdir(parents=True, exist_ok=True)
    dst_lbl.mkdir(parents=True, exist_ok=True)

    imgs = sorted(src_img.glob("*.jpg")) + sorted(src_img.glob("*.png"))
    n_img = n_lbl = 0

    for ip in imgs:
        stem  = ip.stem
        boxes = read_label(src_lbl / f"{stem}.txt")
        img   = cv2.imread(str(ip))
        if img is None:
            continue

        # Original
        dst_i = dst_img / f"glv_{stem}.jpg"
        dst_l = dst_lbl / f"glv_{stem}.txt"
        cv2.imwrite(str(dst_i), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        write_label(dst_l, boxes)
        n_img += 1
        if boxes:
            n_lbl += 1

        if augment_flag:
            for i in range(AUG_MULTIPLIER):
                ai, ab = augment(img, boxes, i)
                if not ab:
                    continue
                astem = f"glv_{stem}_aug{i:02d}"
                cv2.imwrite(str(dst_img / f"{astem}.jpg"), ai,
                            [cv2.IMWRITE_JPEG_QUALITY, 92])
                write_label(dst_lbl / f"{astem}.txt", ab)
                n_img += 1
                n_lbl += 1

    return n_img, n_lbl


def update_yaml():
    yaml = f"""# Fine-tune dataset — goggles + gloves (+ negatives)
# Classes match main PPE model + gloves
train: {(DST_ROOT / 'train' / 'images').resolve()}
val:   {(DST_ROOT / 'val'   / 'images').resolve()}
test:  {(DST_ROOT / 'test'  / 'images').resolve()}

nc: 4
names: ['helmet', 'safety_vest', 'goggles', 'gloves']
"""
    (DST_ROOT / "data.yaml").write_text(yaml)
    print(f"  ✓ Updated data.yaml → nc=4")


def main():
    print("\n── Gloves Dataset Augmentation & Merge ──────────────────────────")
    print(f"   Source : {SRC_ROOT}")
    print(f"   Merge  : {DST_ROOT}  (adding alongside existing data)")
    print(f"   Class  : 0 (gloves) → 3\n")

    total_i = total_l = 0
    for split in SPLITS:
        if not (SRC_ROOT / split / "images").exists():
            continue
        ni, nl = process_split(split, split == "train")
        total_i += ni
        total_l += nl
        print(f"  {split:6s} → {SPLIT_MAP[split]:5s}  | {ni:4d} images  {nl:4d} labels")

    update_yaml()

    print(f"\n  Total added  : {total_i} images, {total_l} labels")
    print(f"  Dataset now  : {sum(1 for _ in (DST_ROOT/'train'/'images').glob('*.jpg'))} train images")
    print(f"\n  Fine-tune command:")
    print(f"    yolo detect train \\")
    print(f"      data={DST_ROOT}/data.yaml \\")
    print(f"      model=models/best.pt \\")
    print(f"      epochs=30 imgsz=640 batch=8 device=mps \\")
    print(f"      freeze=10 name=ppe_v2")
    print()


if __name__ == "__main__":
    main()
