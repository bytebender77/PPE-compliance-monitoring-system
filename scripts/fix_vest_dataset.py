"""
fix_vest_dataset.py
────────────────────
Problem: generic_ppe has 2860 vest annotations of yellow/green high-vis vests.
         User's Tata Steel orange+navy jacket = 233 images, completely outnumbered.
         Model learned yellow vest, ignores the jacket.

Fix:
  1. Copy merged_v4 → merged_v5
  2. Strip class 1 (safety_vest) from ALL generic_ppe labels
  3. Add user's jacket images (vest_finalnormal) remapped class 0→1, ×15 oversample
  4. Zip for Windows retraining

Run:
  python scripts/fix_vest_dataset.py
"""

import shutil
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
SRC_DATASET   = Path("data/merged_v4")
DST_DATASET   = Path("data/merged_v5")
# Multiple jacket sources for maximum real pixel variety. Each is a Roboflow
# export (class 0 = safety_vest) of the user's orange work jacket(s).
# (path, oversample_extra_copies) — fewer copies now that we have more uniques.
JACKET_SRCS = [
    (Path("/Users/kunalkumargupta/Desktop/vest_final.v1i.yolov8"),                 2),  # 699 →~2100
    (Path("/Users/kunalkumargupta/Desktop/ppedetection/safety_vest_new_15jun.v1i.yolov8 (1)"), 3),  # 306 →~1200
    (Path("/Users/kunalkumargupta/Desktop/ppedetection/another_safety_vest.v1i.yolov8"),       2),  # 546 →~1600
]
VEST_CLASS_ID = 1    # safety_vest in our 4-class model
IMAGE_EXTS    = {".jpg", ".jpeg", ".png", ".bmp"}

def strip_vest_from_label(src_lbl: Path, dst_lbl: Path):
    """Copy label but remove any line with class 1 (safety_vest)."""
    lines = []
    if src_lbl.exists():
        with open(src_lbl) as f:
            for line in f:
                parts = line.strip().split()
                if parts and int(parts[0]) != 1:
                    lines.append(line.rstrip())
    if lines:
        with open(dst_lbl, "w") as f:
            f.write("\n".join(lines))
    elif src_lbl.exists():
        dst_lbl.touch()   # keep empty label file

def main():
    print("="*60)
    print("  VEST DATASET FIX")
    print("="*60)

    # ── 1. Clean copy of merged_v4 → merged_v5 ────────────────────────────────
    if DST_DATASET.exists():
        print(f"\nRemoving old {DST_DATASET} ...")
        shutil.rmtree(DST_DATASET)

    print(f"\nCopying {SRC_DATASET} → {DST_DATASET} ...")
    shutil.copytree(SRC_DATASET, DST_DATASET)

    # ── 2. Strip class 1 (safety_vest) from EVERY existing label ───────────────
    # Jacket labels are added fresh in step 3 with the jacket_ prefix, so we can
    # safely remove ALL pre-existing vest annotations here (yellow high-vis from
    # generic_ppe AND any helmet/CCTV sub-datasets that also labelled vests).
    print("\nStripping ALL existing safety_vest (class 1) labels ...")
    lbl_dir  = DST_DATASET / "train" / "labels"
    stripped = 0

    for lbl in lbl_dir.iterdir():
        if lbl.suffix != ".txt":
            continue
        original_lines = lbl.read_text().splitlines()
        vest_lines = [l for l in original_lines
                      if l.strip().split() and int(l.strip().split()[0]) == 1]
        if vest_lines:
            non_vest = [l for l in original_lines
                        if l.strip().split() and int(l.strip().split()[0]) != 1]
            stripped += len(vest_lines)
            lbl.write_text("\n".join(non_vest))

    print(f"  Removed {stripped} pre-existing vest annotation lines")

    # Also strip vest from VALID labels — so mAP measures the jacket, not yellow vests
    v_stripped = 0
    for lbl in (DST_DATASET / "valid" / "labels").iterdir():
        if lbl.suffix != ".txt":
            continue
        original_lines = lbl.read_text().splitlines()
        vest_lines = [l for l in original_lines
                      if l.strip().split() and int(l.strip().split()[0]) == 1]
        if vest_lines:
            non_vest = [l for l in original_lines
                        if l.strip().split() and int(l.strip().split()[0]) != 1]
            v_stripped += len(vest_lines)
            lbl.write_text("\n".join(non_vest))
    print(f"  Removed {v_stripped} vest annotations from valid set")

    # ── 3. Add jacket images from ALL sources, each with its own oversample ────
    dst_img_dir = DST_DATASET / "train" / "images"
    dst_lbl_dir = DST_DATASET / "train" / "labels"
    dst_v_img   = DST_DATASET / "valid" / "images"
    dst_v_lbl   = DST_DATASET / "valid" / "labels"

    def remap_label(lbl: Path) -> str:
        """Read a class-0 vest label, remap to class 1, return text ('' if none)."""
        lines = []
        if lbl.exists():
            for line in lbl.read_text().splitlines():
                parts = line.strip().split()
                if len(parts) >= 5:
                    lines.append(f"1 {' '.join(parts[1:])}")
        return "\n".join(lines)

    jacket_added = 0
    oversampled  = 0
    v_added      = 0

    for src, oversample in JACKET_SRCS:
        tag = src.name.split(".")[0].replace(" ", "")[:20]   # unique prefix per source
        print(f"\nAdding jacket source '{tag}' (×{oversample} oversample) ...")

        # --- train split ---
        src_img_dir = src / "train" / "images"
        src_lbl_dir = src / "train" / "labels"
        images = [f for f in src_img_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS]

        for img in images:
            label_text = remap_label(src_lbl_dir / (img.stem + ".txt"))
            if not label_text:
                continue

            dst_img = dst_img_dir / f"jacket_{tag}_{img.name}"
            dst_lbl = dst_lbl_dir / f"jacket_{tag}_{img.stem}.txt"
            if not dst_img.exists():
                shutil.copy2(img, dst_img)
                dst_lbl.write_text(label_text)
                jacket_added += 1

            for i in range(1, oversample + 1):
                ov_img = dst_img_dir / f"jacket_{tag}_{img.stem}_ov{i}{img.suffix}"
                ov_lbl = dst_lbl_dir / f"jacket_{tag}_{img.stem}_ov{i}.txt"
                if not ov_img.exists():
                    shutil.copy2(img, ov_img)
                    ov_lbl.write_text(label_text)
                    oversampled += 1

        # --- valid split (no oversample — honest metrics) ---
        src_v_img = src / "valid" / "images"
        if src_v_img.exists():
            for img in src_v_img.iterdir():
                if img.suffix.lower() not in IMAGE_EXTS:
                    continue
                label_text = remap_label(src / "valid" / "labels" / (img.stem + ".txt"))
                if not label_text:
                    continue
                dst_i = dst_v_img / f"jacket_{tag}_{img.name}"
                dst_l = dst_v_lbl / f"jacket_{tag}_{img.stem}.txt"
                if not dst_i.exists():
                    shutil.copy2(img, dst_i)
                    dst_l.write_text(label_text)
                    v_added += 1

    # ── 5. Update data.yaml ───────────────────────────────────────────────────
    yaml_path = DST_DATASET / "data.yaml"
    yaml_path.write_text(
        "path: .\n"
        "train: train/images\n"
        "val:   valid/images\n"
        "test:  test/images\n"
        "nc: 4\n"
        "names: ['helmet', 'safety_vest', 'goggles', 'gloves']\n"
    )

    # ── 6. Print summary ──────────────────────────────────────────────────────
    total_train = len(list((DST_DATASET / "train" / "images").iterdir()))
    total_valid = len(list((DST_DATASET / "valid" / "images").iterdir()))

    # Count class distribution
    class_counts = {0:0, 1:0, 2:0, 3:0}
    for lbl in (DST_DATASET / "train" / "labels").iterdir():
        if lbl.suffix == ".txt":
            for line in lbl.read_text().splitlines():
                parts = line.strip().split()
                if parts:
                    c = int(parts[0])
                    if c in class_counts:
                        class_counts[c] += 1

    print(f"\n{'='*60}")
    print(f"  DONE — merged_v5 ready")
    print(f"{'='*60}")
    print(f"  Generic vest annotations removed : {stripped}")
    print(f"  Jacket originals added           : {jacket_added}")
    print(f"  Jacket oversample copies         : {oversampled}")
    print(f"  Jacket valid added               : {v_added}")
    print(f"  Total train images               : {total_train}")
    print(f"  Total valid images               : {total_valid}")
    print(f"\n  Class distribution (train annotations):")
    names = ['helmet','safety_vest','goggles','gloves']
    for c, n in enumerate(names):
        print(f"    {n:15s}: {class_counts[c]}")
    print(f"\n  Now zip:")
    print(f"    cd data && zip -r merged_v5.zip merged_v5/ && cd ..")
    print(f"  Then copy merged_v5.zip to Windows and train:")
    print(f"    yolo train model=yolov8s.pt data=C:\\...\\merged_v5\\data.yaml epochs=80 imgsz=640 batch=16 device=0")


if __name__ == "__main__":
    main()
