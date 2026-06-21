"""
Build merged_v6 — the complete 4-class PPE training dataset.

Sources merged:
  1. data/full_merged          — nc=4 correct order, no remap needed
  2. datasets/cctv data/PPE detection.v1i.yolov8 — nc=3, remap: 0→2,1→0,2→1
  3. datasets/final_data/gloves13jun              — nc=1, remap: 0→3

Output: data/merged_v6/
  train/images/  train/labels/
  val/images/    val/labels/
  test/images/   test/labels/
  data.yaml  (relative paths, works on mac/linux/windows with the right prefix)
"""

import os, shutil, glob, hashlib, sys
from pathlib import Path

ROOT   = Path(__file__).resolve().parent.parent
OUT    = ROOT / "data" / "merged_v6"

SOURCES = [
    {
        "name": "full_merged",
        "path": ROOT / "data" / "full_merged",
        "splits": {"train": "train", "val": "val", "test": "test"},
        "remap": None,                    # already nc=4 correct
    },
    {
        "name": "ppe_detection",
        "path": ROOT / "datasets" / "cctv data" / "PPE detection.v1i.yolov8",
        "splits": {"train": "train", "val": "valid", "test": "test"},
        "remap": {0: 2, 1: 0, 2: 1},     # goggles→2, helmet→0, vest→1
    },
    {
        "name": "gloves13jun",
        "path": ROOT / "datasets" / "final_data" / "gloves13jun",
        "splits": {"train": "train", "val": "valid", "test": "test"},
        "remap": {0: 3},                  # gloves→3
    },
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def remap_label(src_txt: Path, dst_txt: Path, remap: dict):
    lines = src_txt.read_text().strip().splitlines()
    out = []
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        cls = int(parts[0])
        new_cls = remap.get(cls, cls)
        out.append(f"{new_cls} {' '.join(parts[1:])}")
    dst_txt.write_text("\n".join(out) + "\n" if out else "")

def safe_name(src_path: Path, source_name: str) -> str:
    """Prefix filename with source to avoid collisions."""
    return f"{source_name}_{src_path.name}"

def process_split(source: dict, split_key: str, out_split: Path):
    src_base  = source["path"]
    split_dir = source["splits"].get(split_key)
    if split_dir is None:
        return 0

    img_dir = src_base / split_dir / "images"
    lbl_dir = src_base / split_dir / "labels"
    if not img_dir.exists():
        print(f"  [skip] {source['name']}/{split_dir}/images not found")
        return 0

    out_img = out_split / "images"
    out_lbl = out_split / "labels"
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    copied = 0
    for img_path in sorted(img_dir.iterdir()):
        if img_path.suffix.lower() not in IMAGE_EXTS:
            continue
        dst_img = out_img / safe_name(img_path, source["name"])
        shutil.copy2(img_path, dst_img)

        lbl_path = lbl_dir / (img_path.stem + ".txt")
        dst_lbl  = out_lbl / (dst_img.stem + ".txt")
        if lbl_path.exists():
            if source["remap"]:
                remap_label(lbl_path, dst_lbl, source["remap"])
            else:
                shutil.copy2(lbl_path, dst_lbl)
        else:
            dst_lbl.write_text("")   # background image — empty label
        copied += 1
    return copied

def main():
    if OUT.exists():
        print(f"[clean] removing existing {OUT}")
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    totals = {"train": 0, "val": 0, "test": 0}

    for source in SOURCES:
        print(f"\n[source] {source['name']}  remap={source['remap']}")
        for split in ["train", "val", "test"]:
            n = process_split(source, split, OUT / split)
            totals[split] += n
            print(f"  {split}: +{n}")

    # Write data.yaml (relative paths — edit for Windows if needed)
    yaml_content = """\
# merged_v6 — 4-class PPE dataset
# helmet(0)  safety_vest(1)  goggles(2)  gloves(3)
#
# Windows: change the three paths to absolute Windows paths, e.g.
#   train: C:\\\\ppe\\\\data\\\\merged_v6\\\\train\\\\images
#   val:   C:\\\\ppe\\\\data\\\\merged_v6\\\\val\\\\images
#   test:  C:\\\\ppe\\\\data\\\\merged_v6\\\\test\\\\images

train: train/images
val:   val/images
test:  test/images

nc: 4
names: ['helmet', 'safety_vest', 'goggles', 'gloves']
"""
    (OUT / "data.yaml").write_text(yaml_content)

    print(f"\n{'='*50}")
    print(f"merged_v6 done → {OUT}")
    print(f"  train : {totals['train']:,}")
    print(f"  val   : {totals['val']:,}")
    print(f"  test  : {totals['test']:,}")
    print(f"  total : {sum(totals.values()):,}")
    print(f"\nClass remap summary:")
    print(f"  full_merged  → helmet=0,vest=1,goggles=2,gloves=3 (no remap)")
    print(f"  ppe_detect   → goggles:0→2, helmet:1→0, vest:2→1")
    print(f"  gloves13jun  → gloves:0→3")

if __name__ == "__main__":
    main()
