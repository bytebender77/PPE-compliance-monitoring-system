"""
scripts/check_class_balance.py — Check per-class instance counts across splits.

Run this after annotation and before training to confirm you have enough
examples of each class. Prints a table and exits with code 1 if any class
in the training split falls below the minimum threshold.

Usage
-----
# Check all splits with default thresholds
python scripts/check_class_balance.py

# Check only the training split
python scripts/check_class_balance.py --split train

# Override minimum thresholds (e.g. if goggles are rare at your site)
python scripts/check_class_balance.py --min-person 800 --min-helmet 500 \
                                       --min-vest 500 --min-goggles 300
"""

import argparse
import os
import sys
from collections import Counter
from pathlib import Path


# ── Constants ─────────────────────────────────────────────────────────────────

CLASS_NAMES = {0: "helmet", 1: "safety_vest", 2: "goggles"}

DEFAULT_MIN_COUNTS = {
    0: 600,   # helmet
    1: 600,   # safety_vest
    2: 400,   # goggles — smaller object, lower target
}

SPLITS = ["train", "val", "test"]


# ── Core counting ─────────────────────────────────────────────────────────────

def count_instances_in_split(labels_dir: Path) -> Counter:
    """
    Count the number of annotated instances per class in a labels directory.
    Returns a Counter {class_id: instance_count}.
    """
    counts = Counter()
    if not labels_dir.exists():
        return counts

    for label_file in labels_dir.glob("*.txt"):
        with open(label_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 1:
                    try:
                        cls_id = int(parts[0])
                        counts[cls_id] += 1
                    except ValueError:
                        continue  # malformed line — validate_dataset.py catches this

    return counts


def count_images_in_split(images_dir: Path) -> int:
    if not images_dir.exists():
        return 0
    return sum(
        1 for f in images_dir.iterdir()
        if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
    )


# ── Reporting ─────────────────────────────────────────────────────────────────

def _bar(value: int, max_value: int, width: int = 30) -> str:
    if max_value == 0:
        return " " * width
    filled = round(width * value / max_value)
    return "█" * filled + "░" * (width - filled)


def print_split_table(split: str, counts: Counter, image_count: int, min_counts: dict) -> list[str]:
    """
    Print a formatted table for one split.
    Returns a list of failure messages (empty = all OK).
    """
    print(f"\n  {'─' * 60}")
    print(f"  Split: {split.upper()}  ({image_count} images)")
    print(f"  {'─' * 60}")
    print(f"  {'Class':<14} {'ID':>3}  {'Count':>6}  {'Min':>6}  {'Status':<8}  Bar")
    print(f"  {'─' * 60}")

    max_count = max(counts.values(), default=1)
    failures = []

    for cls_id in sorted(CLASS_NAMES):
        name = CLASS_NAMES[cls_id]
        count = counts.get(cls_id, 0)
        minimum = min_counts.get(cls_id, 0)
        bar = _bar(count, max_count)

        # Only enforce minimums against training split
        if split == "train" and count < minimum:
            status = "FAIL ✗"
            failures.append(
                f"{name} (ID {cls_id}): {count} instances, need {minimum}"
            )
        elif count == 0:
            status = "EMPTY !"
        elif split == "train" and count < minimum * 1.1:
            status = "LOW ~"
        else:
            status = "OK ✓"

        print(f"  {name:<14} {cls_id:>3}  {count:>6}  {minimum:>6}  {status:<8}  {bar}")

    return failures


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check per-class instance counts for the PPE dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--data-root", default="data",
        help="Path to the data/ directory (default: data).",
    )
    parser.add_argument(
        "--split", choices=SPLITS + ["all"], default="all",
        help="Which split to check (default: all).",
    )
    parser.add_argument(
        "--min-helmet", type=int, default=DEFAULT_MIN_COUNTS[0],
        help=f"Min helmet instances in train (default: {DEFAULT_MIN_COUNTS[0]}).",
    )
    parser.add_argument(
        "--min-vest", type=int, default=DEFAULT_MIN_COUNTS[1],
        help=f"Min safety_vest instances in train (default: {DEFAULT_MIN_COUNTS[1]}).",
    )
    parser.add_argument(
        "--min-goggles", type=int, default=DEFAULT_MIN_COUNTS[2],
        help=f"Min goggles instances in train (default: {DEFAULT_MIN_COUNTS[2]}).",
    )
    args = parser.parse_args()

    min_counts = {
        0: args.min_helmet,
        1: args.min_vest,
        2: args.min_goggles,
    }

    data_root = Path(args.data_root)
    splits = SPLITS if args.split == "all" else [args.split]

    print(f"\nPPE Dataset Class Balance Check")
    print(f"{'═' * 62}")
    print(f"Data root : {data_root.resolve()}")
    print(f"Classes   : {list(CLASS_NAMES.values())}")
    print(f"Min counts (train): helmet={min_counts[0]}, vest={min_counts[1]}, goggles={min_counts[2]}")

    all_failures = []

    for split in splits:
        labels_dir = data_root / "processed" / "labels" / split
        images_dir = data_root / "processed" / "images" / split
        counts = count_instances_in_split(labels_dir)
        image_count = count_images_in_split(images_dir)
        failures = print_split_table(split, counts, image_count, min_counts)
        if split == "train":
            all_failures.extend(failures)

    # Grand summary
    print(f"\n{'═' * 62}")

    if not all_failures:
        print("  All training class counts meet minimum thresholds.")
        print("  Ready to run scripts/validate_dataset.py for label format checks.")
    else:
        print(f"  Training split does not meet minimum counts ({len(all_failures)} class(es)):")
        for msg in all_failures:
            print(f"    - {msg}")
        print()
        print("  Options:")
        print("  1. Annotate more images for the failing classes.")
        print("  2. Use --min-goggles / --min-vest etc. to lower thresholds if")
        print("     the class is genuinely rare at your site.")
        print("  3. Supplement with open-dataset images (Roboflow Universe).")
        sys.exit(1)


if __name__ == "__main__":
    main()
