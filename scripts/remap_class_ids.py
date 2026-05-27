"""
scripts/remap_class_ids.py — Remap class IDs in YOLO label files.

The cctv.v2i dataset uses:  0=helmet, 1=safety_vest
Our project needs:          0=person, 1=helmet, 2=safety_vest, 3=goggles

This script rewrites every label file in data/processed/ with the correct IDs.

Usage
-----
python scripts/remap_class_ids.py
python scripts/remap_class_ids.py --dry-run   # preview without writing
"""

import argparse
import glob
import os
from pathlib import Path

# Source class IDs (what the dataset currently has)
# → Target class IDs (what our project needs)
REMAP = {
    "0": "1",   # helmet      (was 0) → helmet      (now 1)
    "1": "2",   # safety_vest (was 1) → safety_vest (now 2)
}

SOURCE_NAMES = {0: "helmet", 1: "safety_vest"}
TARGET_NAMES = {0: "person", 1: "helmet", 2: "safety_vest", 3: "goggles"}


def remap_file(path: Path, dry_run: bool) -> tuple[int, int]:
    """Remap class IDs in one label file. Returns (remapped, skipped)."""
    with open(path) as f:
        lines = f.readlines()

    new_lines = []
    remapped = 0
    skipped = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            new_lines.append(line)
            continue
        parts = stripped.split()
        old_cls = parts[0]
        if old_cls in REMAP:
            parts[0] = REMAP[old_cls]
            new_lines.append(" ".join(parts) + "\n")
            remapped += 1
        else:
            new_lines.append(line)
            skipped += 1

    if not dry_run:
        with open(path, "w") as f:
            f.writelines(new_lines)

    return remapped, skipped


def main():
    parser = argparse.ArgumentParser(description="Remap class IDs in YOLO label files.")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.data_root)

    print(f"\nClass ID Remapper")
    print(f"{'═' * 50}")
    print(f"Data root: {root.resolve()}")
    print(f"Remap    : {REMAP}")
    if args.dry_run:
        print(f"Mode     : DRY RUN")
    print()

    total_remapped = 0
    total_skipped = 0

    for split in ["train", "val", "test"]:
        lbl_dir = root / "labels" / split
        files = list(lbl_dir.glob("*.txt"))
        split_remapped = 0
        split_skipped = 0

        for f in files:
            r, s = remap_file(f, args.dry_run)
            split_remapped += r
            split_skipped += s

        print(f"  {split:6s}: {len(files)} files | {split_remapped} IDs remapped | {split_skipped} unchanged")
        total_remapped += split_remapped
        total_skipped += split_skipped

    print(f"\n{'═' * 50}")
    print(f"Total remapped : {total_remapped}")
    print(f"Total unchanged: {total_skipped}")
    if not args.dry_run:
        print(f"\nDone. Run scripts/check_class_balance.py to verify.")


if __name__ == "__main__":
    main()
