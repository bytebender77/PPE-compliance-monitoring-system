"""
merge_final_dataset.py — Merge all datasets in final_data/ into one unified dataset

Target classes (fixed):
  0 → helmet
  1 → safety_vest
  2 → goggles
  3 → gloves

Handles all class name variants across datasets:
  head, helmet, hardhat           → helmet (0)
  vest, safety-vest, safety_vest  → safety_vest (1)
  safety_goggles, goggles         → goggles (2)
  gloves                          → gloves (3)
  person                          → SKIP (not a PPE class)

Also adds negative samples (bare hands + bare face) as images with empty labels.

Output: data/merged_v4/
  train/images/ + train/labels/
  valid/images/  + valid/labels/
  test/images/   + test/labels/
  data.yaml
"""

import os
import shutil
import random
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

FINAL_DATA   = Path("final_data")
NEGATIVES    = [
    Path("data/ppe_capture/neg_bare_hands"),
    Path("data/ppe_capture/neg_bare_face"),
    Path("data/gloves_raw"),
]
OUTPUT       = Path("data/merged_v4")
VALID_RATIO  = 0.015
TEST_RATIO   = 0.015
RANDOM_SEED  = 42

# Target class map
TARGET_CLASSES = ["helmet", "safety_vest", "goggles", "gloves"]
TARGET_MAP     = {c: i for i, c in enumerate(TARGET_CLASSES)}

# All known source class name variants → target class name
CLASS_ALIASES = {
    # helmet
    "helmet":          "helmet",
    "head":            "helmet",
    "hardhat":         "helmet",
    "hard_hat":        "helmet",
    "hard-hat":        "helmet",
    # safety_vest
    "safety_vest":     "safety_vest",
    "vest":            "safety_vest",
    "safety-vest":     "safety_vest",
    "safetyvest":      "safety_vest",
    # goggles
    "goggles":         "goggles",
    "safety_goggles":  "goggles",
    "safety goggles":  "goggles",
    "goggle":          "goggles",
    # gloves
    "gloves":          "gloves",
    "glove":           "gloves",
    # skip
    "person":          None,
    "worker":          None,
    "people":          None,
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def read_yaml_names(yaml_path: Path) -> list:
    """Parse class names from data.yaml without importing yaml."""
    names = []
    in_names = False
    with open(yaml_path) as f:
        for line in f:
            line = line.rstrip()
            if line.startswith("names:"):
                rest = line[len("names:"):].strip()
                if rest.startswith("["):
                    # inline list: names: ['a', 'b']
                    rest = rest.strip("[]")
                    for n in rest.split(","):
                        names.append(n.strip().strip("'\""))
                    break
                else:
                    in_names = True
            elif in_names:
                if line.startswith("  -") or line.startswith("- "):
                    names.append(line.strip().lstrip("-").strip().strip("'\""))
                elif line and not line.startswith(" "):
                    break
    return names


def remap_label(label_path: Path, src_names: list) -> list:
    """Read a YOLO label file, remap class ids to target ids. Returns list of lines."""
    out = []
    try:
        with open(label_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 5:
                    continue
                src_id = int(parts[0])
                if src_id >= len(src_names):
                    continue
                src_name  = src_names[src_id].lower().strip()
                tgt_name  = CLASS_ALIASES.get(src_name)
                if tgt_name is None:
                    continue   # skip (person, unknown)
                tgt_id = TARGET_MAP[tgt_name]
                out.append(f"{tgt_id} {' '.join(parts[1:])}")
    except Exception:
        pass
    return out


def copy_split(src_img_dir: Path, src_lbl_dir: Path, src_names: list,
               dst_img_dir: Path, dst_lbl_dir: Path, prefix: str, stats: dict):
    """Copy images+labels from one dataset split into merged output."""
    if not src_img_dir.exists():
        return
    images = [f for f in src_img_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS]
    for img in images:
        lbl = src_lbl_dir / (img.stem + ".txt")
        remapped = remap_label(lbl, src_names) if lbl.exists() else []

        # Skip image if it has no useful annotations (all classes were skipped)
        # BUT keep if original label was empty (negative sample)
        if lbl.exists() and not remapped:
            continue   # had labels but all were person/unknown → discard

        dst_img = dst_img_dir / f"{prefix}_{img.name}"
        dst_lbl = dst_lbl_dir / f"{prefix}_{img.stem}.txt"
        shutil.copy2(img, dst_img)
        with open(dst_lbl, "w") as f:
            f.write("\n".join(remapped))

        for cls in remapped:
            cid = int(cls.split()[0])
            stats[TARGET_CLASSES[cid]] = stats.get(TARGET_CLASSES[cid], 0) + 1
        if not remapped:
            stats["negatives"] = stats.get("negatives", 0) + 1


def add_negatives(neg_folders: list, train_img: Path, train_lbl: Path, stats: dict):
    """Add negative sample images with empty label files."""
    count = 0
    for folder in neg_folders:
        if not folder.exists():
            continue
        images = [f for f in folder.iterdir() if f.suffix.lower() in IMAGE_EXTS]
        for img in images:
            dst_img = train_img / f"neg_{img.stem}{img.suffix}"
            dst_lbl = train_lbl / f"neg_{img.stem}.txt"
            shutil.copy2(img, dst_img)
            dst_lbl.touch()   # empty file = no objects = negative sample
            count += 1
    stats["negatives"] = stats.get("negatives", 0) + count
    print(f"  Added {count} negative samples (bare hands + bare face)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    random.seed(RANDOM_SEED)

    # Create output dirs
    for split in ["train", "valid", "test"]:
        (OUTPUT / split / "images").mkdir(parents=True, exist_ok=True)
        (OUTPUT / split / "labels").mkdir(parents=True, exist_ok=True)

    stats  = {}
    total  = {"train": 0, "valid": 0, "test": 0}

    print(f"\nMerging datasets from: {FINAL_DATA.resolve()}")
    print(f"Output → {OUTPUT.resolve()}\n")

    # Process each dataset folder
    for ds_dir in sorted(FINAL_DATA.iterdir()):
        if not ds_dir.is_dir() or ds_dir.name.startswith("."):
            continue

        yaml_path = ds_dir / "data.yaml"
        if not yaml_path.exists():
            continue

        src_names = read_yaml_names(yaml_path)
        if not src_names:
            print(f"  SKIP (no class names): {ds_dir.name}")
            continue

        prefix = ds_dir.name.replace(" ", "_").replace("(", "").replace(")", "")[:30]
        print(f"  Processing: {ds_dir.name}")
        print(f"    Classes: {src_names}")

        for split in ["train", "valid", "test"]:
            src_img = ds_dir / split / "images"
            src_lbl = ds_dir / split / "labels"
            dst_img = OUTPUT / split / "images"
            dst_lbl = OUTPUT / split / "labels"
            before  = sum(1 for _ in dst_img.iterdir()) if dst_img.exists() else 0
            copy_split(src_img, src_lbl, src_names, dst_img, dst_lbl, f"{prefix}_{split}", stats)
            after   = sum(1 for _ in dst_img.iterdir())
            total[split] += (after - before)

    # Add negatives to train only
    print(f"\n  Adding negative samples...")
    add_negatives(NEGATIVES, OUTPUT / "train" / "images", OUTPUT / "train" / "labels", stats)

    # Write data.yaml
    yaml_content = f"""# Merged PPE dataset — v4
# Generated by merge_final_dataset.py
# Classes: {TARGET_CLASSES}

path: {OUTPUT.resolve()}
train: train/images
val:   valid/images
test:  test/images

nc: {len(TARGET_CLASSES)}
names: {TARGET_CLASSES}
"""
    with open(OUTPUT / "data.yaml", "w") as f:
        f.write(yaml_content)

    # Final count
    train_count = len(list((OUTPUT / "train" / "images").iterdir()))
    valid_count = len(list((OUTPUT / "valid" / "images").iterdir()))
    test_count  = len(list((OUTPUT / "test"  / "images").iterdir()))

    print(f"\n{'='*55}")
    print(f"  MERGE COMPLETE")
    print(f"{'='*55}")
    print(f"  Train images : {train_count}")
    print(f"  Valid images : {valid_count}")
    print(f"  Test  images : {test_count}")
    print(f"  Total        : {train_count + valid_count + test_count}")
    print(f"\n  Annotation counts:")
    for cls in TARGET_CLASSES:
        print(f"    {cls:<15}: {stats.get(cls, 0):>6} boxes")
    print(f"    {'negatives':<15}: {stats.get('negatives', 0):>6} images")
    print(f"\n  data.yaml → {OUTPUT / 'data.yaml'}")
    print(f"{'='*55}")
    print(f"\nReady to train:")
    print(f"  yolo train model=yolov8s.pt data={OUTPUT}/data.yaml epochs=100 imgsz=640 batch=16 device=0")


if __name__ == "__main__":
    main()
