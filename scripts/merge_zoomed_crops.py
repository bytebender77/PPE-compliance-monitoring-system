"""
scripts/merge_zoomed_crops.py
─────────────────────────────
Converts zoomed_crops Roboflow export (segmentation polygon format, nc=2)
into YOLO bounding-box format and merges into the existing goggles_finetune
dataset (nc=4: helmet, safety_vest, goggles, gloves).

Class mapping:
  zoomed_crops class 0 (helmet)      → goggles_finetune class 0 (helmet)   ✓
  zoomed_crops class 1 (safety_vest) → goggles_finetune class 1 (safety_vest) ✓

Segmentation polygons: each label line is  cls x1 y1 x2 y2 ... xN yN
We convert to bbox:                         cls cx cy w h

Run from project root:
    python scripts/merge_zoomed_crops.py
"""

import shutil
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
SRC_ROOT  = Path("/Users/kunalkumargupta/Desktop/zoomed_crops.v2i.yolov8")
DST_ROOT  = Path("data/goggles_finetune")

# Source split → dest split mapping
SPLITS = [
    ("train", "images", "train", "images"),
    ("train", "labels", "train", "labels"),
    ("valid", "images", "val",   "images"),
    ("valid", "labels", "val",   "labels"),
    ("test",  "images", "test",  "images"),
    ("test",  "labels", "test",  "labels"),
]

PREFIX = "zcrop_"   # prefix to avoid filename collisions


def seg_to_bbox(line: str) -> str:
    """
    Convert one segmentation label line to a YOLO bbox label line.

    Input:  cls x1 y1 x2 y2 x3 y3 ... xN yN   (normalized, 0-1)
    Output: cls cx cy w h                        (normalized, 0-1)
    """
    parts = line.strip().split()
    if len(parts) < 5:
        return ""  # skip malformed lines

    cls = int(parts[0])
    coords = [float(v) for v in parts[1:]]

    # coords: x1 y1 x2 y2 ... xN yN
    xs = coords[0::2]
    ys = coords[1::2]

    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)

    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    w  = x2 - x1
    h  = y2 - y1

    # Clamp to [0,1]
    cx = max(0.0, min(1.0, cx))
    cy = max(0.0, min(1.0, cy))
    w  = max(0.001, min(1.0, w))
    h  = max(0.001, min(1.0, h))

    return f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def process_labels(src_lbl_dir: Path, dst_lbl_dir: Path, img_names: set) -> int:
    """Convert and copy label files. Returns number of files processed."""
    dst_lbl_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for lbl_file in sorted(src_lbl_dir.glob("*.txt")):
        # Match label to image (same stem)
        stem = lbl_file.stem
        # Only process if corresponding image was copied
        if stem not in img_names:
            continue

        lines = lbl_file.read_text().strip().splitlines()
        converted = []
        for line in lines:
            if not line.strip():
                continue
            result = seg_to_bbox(line)
            if result:
                converted.append(result)

        dst_file = dst_lbl_dir / f"{PREFIX}{lbl_file.name}"
        dst_file.write_text("\n".join(converted))
        count += 1
    return count


def copy_images(src_img_dir: Path, dst_img_dir: Path) -> set:
    """Copy images with prefix. Returns set of copied stems."""
    dst_img_dir.mkdir(parents=True, exist_ok=True)
    stems = set()
    for img in sorted(src_img_dir.glob("*.jpg")) + sorted(src_img_dir.glob("*.png")):
        dst = dst_img_dir / f"{PREFIX}{img.name}"
        shutil.copy2(img, dst)
        stems.add(img.stem)
    return stems


# ── Main ──────────────────────────────────────────────────────────────────────
print("\n── Merging zoomed_crops → goggles_finetune ─────────────────────────")
print(f"   Source : {SRC_ROOT}")
print(f"   Dest   : {DST_ROOT.resolve()}")

total_images = 0
total_labels = 0

for src_split, src_type, dst_split, dst_type in SPLITS:
    src_dir = SRC_ROOT / src_split / src_type
    dst_dir = DST_ROOT / dst_split / dst_type

    if not src_dir.exists():
        print(f"   [SKIP] {src_dir} — not found")
        continue

    if src_type == "images":
        stems = copy_images(src_dir, dst_dir)
        total_images += len(stems)
        print(f"   [{src_split}/images] → [{dst_split}/images]  {len(stems)} files")

    elif src_type == "labels":
        # Get all stems from destination images to match
        dst_img_dir = DST_ROOT / dst_split / "images"
        img_stems = {f.stem[len(PREFIX):] for f in dst_img_dir.glob(f"{PREFIX}*")} \
                    if dst_img_dir.exists() else set()
        # Actually just pass all stems from source labels
        src_stems = {f.stem for f in (SRC_ROOT / src_split / "images").glob("*.jpg")}
        src_stems |= {f.stem for f in (SRC_ROOT / src_split / "images").glob("*.png")}

        n = process_labels(src_dir, dst_dir, src_stems)
        total_labels += n
        print(f"   [{src_split}/labels] → [{dst_split}/labels]  {n} converted")

# ── Verify final counts ────────────────────────────────────────────────────────
print(f"\n── Final dataset sizes ──────────────────────────────────────────────")
for split in ["train", "val", "test"]:
    img_dir = DST_ROOT / split / "images"
    lbl_dir = DST_ROOT / split / "labels"
    n_img = len(list(img_dir.glob("*"))) if img_dir.exists() else 0
    n_lbl = len(list(lbl_dir.glob("*.txt"))) if lbl_dir.exists() else 0
    print(f"   {split:5s}  images={n_img:4d}  labels={n_lbl:4d}")

print(f"\n   Added  : {total_images} images, {total_labels} labels")
print(f"   Classes: 0=helmet  1=safety_vest  2=goggles  3=gloves")
print(f"\n── Next step ────────────────────────────────────────────────────────")
print(f"   python scripts/train_finetune.py")
print()
