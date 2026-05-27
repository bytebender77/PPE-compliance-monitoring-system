"""
scripts/validate_dataset.py — Validate a YOLO-format dataset before training.

Catches the most common annotation errors that silently hurt model performance:
  - Images without a matching label file (and vice versa)
  - Label files with incorrect column count (must be 5: class x y w h)
  - Class IDs outside the valid range (0–3 for our 4-class dataset)
  - Bounding box values outside the normalised range [0, 1]
  - Zero-area bounding boxes (w=0 or h=0)
  - Completely empty label files (image has no annotations at all)

Usage
-----
# Validate the full dataset (all splits)
python scripts/validate_dataset.py

# Validate a single split
python scripts/validate_dataset.py --split train

# Validate and show every error (not just the first 10 per file)
python scripts/validate_dataset.py --verbose
"""

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path


# ── Constants ─────────────────────────────────────────────────────────────────

NUM_CLASSES = 3
CLASS_NAMES = {0: "helmet", 1: "safety_vest", 2: "goggles"}
SPLITS = ["train", "val", "test"]
VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


# ── Per-label-file validation ─────────────────────────────────────────────────

def validate_label_file(label_path: Path, verbose: bool) -> list[str]:
    """
    Validate one .txt label file. Returns a list of error strings.
    Empty list means the file is valid.
    """
    errors = []

    with open(label_path) as f:
        lines = [l.strip() for l in f if l.strip()]

    if not lines:
        # A label file with no lines means the image has no annotated objects.
        # This is valid ONLY if you deliberately included background images.
        # Flag it as a warning so the user can confirm intent.
        errors.append("WARN  Empty label file (no annotations). "
                      "OK if this is a background image — otherwise re-annotate.")
        return errors

    for line_num, line in enumerate(lines, 1):
        parts = line.split()

        # ── Column count ──────────────────────────────────────────────────────
        if len(parts) != 5:
            errors.append(
                f"ERROR Line {line_num}: expected 5 values (class x y w h), "
                f"got {len(parts)}: '{line}'"
            )
            continue  # can't parse further if column count is wrong

        cls_str, x_str, y_str, w_str, h_str = parts

        # ── Class ID ──────────────────────────────────────────────────────────
        try:
            cls_id = int(cls_str)
        except ValueError:
            errors.append(f"ERROR Line {line_num}: class ID is not an integer: '{cls_str}'")
            continue

        if cls_id < 0 or cls_id >= NUM_CLASSES:
            errors.append(
                f"ERROR Line {line_num}: class ID {cls_id} out of range "
                f"[0, {NUM_CLASSES - 1}]. Valid classes: {CLASS_NAMES}"
            )

        # ── Bounding box values ───────────────────────────────────────────────
        try:
            x, y, w, h = float(x_str), float(y_str), float(w_str), float(h_str)
        except ValueError:
            errors.append(
                f"ERROR Line {line_num}: bounding box values must be floats: "
                f"x={x_str} y={y_str} w={w_str} h={h_str}"
            )
            continue

        for name, val in [("x_center", x), ("y_center", y), ("width", w), ("height", h)]:
            if not (0.0 <= val <= 1.0):
                errors.append(
                    f"ERROR Line {line_num}: {name}={val:.4f} is outside [0, 1]. "
                    "YOLO format requires normalised coordinates."
                )

        if w == 0 or h == 0:
            errors.append(
                f"ERROR Line {line_num}: zero-area box (w={w}, h={h}). "
                "Delete or re-annotate this entry."
            )

        # ── Edge clipping ─────────────────────────────────────────────────────
        # Warn if the box extends beyond the image boundary
        if x - w / 2 < 0 or x + w / 2 > 1 or y - h / 2 < 0 or y + h / 2 > 1:
            errors.append(
                f"WARN  Line {line_num}: box ({x:.3f}, {y:.3f}, {w:.3f}, {h:.3f}) "
                "extends outside image boundary. Check annotation."
            )

        if not verbose and len(errors) >= 10:
            errors.append(f"... (truncated — use --verbose to see all errors)")
            break

    return errors


# ── Split validation ──────────────────────────────────────────────────────────

def validate_split(split: str, data_root: Path, verbose: bool) -> dict:
    """
    Validate one split (train / val / test).

    Returns a summary dict:
      {
        "images": int,
        "labels": int,
        "errors": int,
        "warnings": int,
        "orphan_images": [str],   # images with no label file
        "orphan_labels": [str],   # label files with no image
        "file_errors": {filename: [error_strings]},
      }
    """
    images_dir = data_root / "processed" / "images" / split
    labels_dir = data_root / "processed" / "labels" / split

    summary = {
        "images": 0,
        "labels": 0,
        "errors": 0,
        "warnings": 0,
        "orphan_images": [],
        "orphan_labels": [],
        "file_errors": defaultdict(list),
    }

    if not images_dir.exists():
        print(f"  SKIP: {images_dir} does not exist.")
        return summary
    if not labels_dir.exists():
        print(f"  SKIP: {labels_dir} does not exist.")
        return summary

    # Collect image stems and label stems
    image_files = {
        p.stem: p
        for p in images_dir.iterdir()
        if p.suffix.lower() in VALID_IMAGE_EXTS
    }
    label_files = {
        p.stem: p
        for p in labels_dir.iterdir()
        if p.suffix == ".txt"
    }

    summary["images"] = len(image_files)
    summary["labels"] = len(label_files)

    # Orphan images (no matching label)
    for stem in sorted(image_files):
        if stem not in label_files:
            summary["orphan_images"].append(image_files[stem].name)

    # Orphan labels (no matching image)
    for stem in sorted(label_files):
        if stem not in image_files:
            summary["orphan_labels"].append(label_files[stem].name)

    # Validate each label file that has a matching image
    for stem in sorted(label_files):
        if stem not in image_files:
            continue  # already flagged as orphan above
        errors = validate_label_file(label_files[stem], verbose)
        for e in errors:
            summary["file_errors"][label_files[stem].name].append(e)
            if e.startswith("ERROR"):
                summary["errors"] += 1
            elif e.startswith("WARN"):
                summary["warnings"] += 1

    return summary


# ── Reporting ─────────────────────────────────────────────────────────────────

def print_split_report(split: str, summary: dict) -> None:
    print(f"\n  {'─' * 46}")
    print(f"  Split: {split.upper()}")
    print(f"  {'─' * 46}")
    print(f"  Images : {summary['images']}")
    print(f"  Labels : {summary['labels']}")
    print(f"  Errors : {summary['errors']}")
    print(f"  Warnings: {summary['warnings']}")

    if summary["orphan_images"]:
        print(f"\n  Images without a label file ({len(summary['orphan_images'])}):")
        for name in summary["orphan_images"][:10]:
            print(f"    {name}")
        if len(summary["orphan_images"]) > 10:
            print(f"    ... and {len(summary['orphan_images']) - 10} more")

    if summary["orphan_labels"]:
        print(f"\n  Label files without an image ({len(summary['orphan_labels'])}):")
        for name in summary["orphan_labels"][:10]:
            print(f"    {name}")
        if len(summary["orphan_labels"]) > 10:
            print(f"    ... and {len(summary['orphan_labels']) - 10} more")

    if summary["file_errors"]:
        print(f"\n  Files with issues ({len(summary['file_errors'])}):")
        for filename, errs in list(summary["file_errors"].items())[:20]:
            print(f"\n    {filename}")
            for e in errs:
                print(f"      {e}")
        if len(summary["file_errors"]) > 20:
            print(f"\n    ... and {len(summary['file_errors']) - 20} more files with issues")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a YOLO-format PPE dataset before training.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--data-root", default="data",
        help="Path to the data/ directory (default: data).",
    )
    parser.add_argument(
        "--split", choices=SPLITS + ["all"], default="all",
        help="Which split to validate (default: all).",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show all errors per file, not just the first 10.",
    )
    args = parser.parse_args()

    data_root = Path(args.data_root)
    splits = SPLITS if args.split == "all" else [args.split]

    print(f"\nPPE Dataset Validator")
    print(f"{'═' * 50}")
    print(f"Data root : {data_root.resolve()}")
    print(f"Classes   : {CLASS_NAMES}")
    print(f"Splits    : {splits}")

    total_errors = 0
    total_warnings = 0

    for split in splits:
        summary = validate_split(split, data_root, args.verbose)
        print_split_report(split, summary)
        total_errors += summary["errors"]
        total_warnings += summary["warnings"]

    print(f"\n{'═' * 50}")
    print(f"Total errors  : {total_errors}")
    print(f"Total warnings: {total_warnings}")

    if total_errors == 0 and total_warnings == 0:
        print("\n  All checks passed. Dataset looks clean.")
        print("  Run scripts/check_class_balance.py next.")
    elif total_errors == 0:
        print(f"\n  No errors. {total_warnings} warning(s) to review.")
        print("  Warnings do not block training but should be inspected.")
    else:
        print(f"\n  {total_errors} error(s) found. Fix before training.")
        sys.exit(1)


if __name__ == "__main__":
    main()
