"""
scripts/convert_seg_to_bbox.py — Convert YOLO segmentation labels to bounding boxes.

Roboflow Instance Segmentation projects export polygon coordinates even when
you choose YOLOv8 format. This script converts those polygon labels into
standard YOLO bounding box format (5 values per line).

Segmentation format (what you have):
    class  x1 y1  x2 y2  x3 y3  ...  (many polygon points)

Bounding box format (what training needs):
    class  x_center  y_center  width  height

Conversion: take the min/max of all polygon x and y points → axis-aligned bbox.

Usage
-----
# Convert a specific dataset folder (converts train/valid/test in one go)
python scripts/convert_seg_to_bbox.py \
    --input "cctv data/cctv.v2i.yolov8" \
    --output data/processed

# Dry run — preview without writing files
python scripts/convert_seg_to_bbox.py \
    --input "cctv data/cctv.v2i.yolov8" \
    --output data/processed \
    --dry-run
"""

import argparse
import os
import shutil
import glob
from pathlib import Path


# ── Conversion logic ──────────────────────────────────────────────────────────

def seg_line_to_bbox_line(line: str) -> str | None:
    """
    Convert one segmentation label line to one bounding box label line.

    Segmentation: class x1 y1 x2 y2 x3 y3 ...
    Bbox:         class x_center y_center width height

    Returns None if the line is malformed.
    """
    parts = line.strip().split()
    if len(parts) < 5:
        return None  # need at least class + 2 points (4 coords)

    cls = parts[0]

    # All values after the class ID are x,y polygon coordinates
    coords = parts[1:]

    # Must be an even number (pairs of x, y)
    if len(coords) % 2 != 0:
        # Drop the last coord if odd — Roboflow sometimes adds a trailing value
        coords = coords[:-1]

    if len(coords) < 4:
        return None

    xs = [float(coords[i]) for i in range(0, len(coords), 2)]
    ys = [float(coords[i]) for i in range(1, len(coords), 2)]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    x_center = (x_min + x_max) / 2
    y_center  = (y_min + y_max) / 2
    width     = x_max - x_min
    height    = y_max - y_min

    # Clamp to [0, 1] — polygon points occasionally exceed boundary by a tiny float error
    x_center = max(0.0, min(1.0, x_center))
    y_center  = max(0.0, min(1.0, y_center))
    width     = max(0.0, min(1.0, width))
    height    = max(0.0, min(1.0, height))

    return f"{cls} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"


def convert_label_file(src: Path, dst: Path) -> tuple[int, int]:
    """
    Convert one label file. Returns (converted_lines, skipped_lines).
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    converted = 0
    skipped = 0

    with open(src) as f_in, open(dst, "w") as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            result = seg_line_to_bbox_line(line)
            if result:
                f_out.write(result + "\n")
                converted += 1
            else:
                skipped += 1

    return converted, skipped


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convert YOLO segmentation labels to bounding box format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to the Roboflow export folder (contains train/, valid/, test/).",
    )
    parser.add_argument(
        "--output", default="data/processed",
        help="Output folder — writes to images/ and labels/ subfolders (default: data/processed).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview conversion without writing files.",
    )
    args = parser.parse_args()

    input_root = Path(args.input)
    output_root = Path(args.output)

    # Roboflow uses 'valid' but our project uses 'val' — remap
    split_map = {"train": "train", "valid": "val", "test": "test"}

    print(f"\nSegmentation → Bounding Box Converter")
    print(f"{'═' * 50}")
    print(f"Input : {input_root.resolve()}")
    print(f"Output: {output_root.resolve()}")
    if args.dry_run:
        print(f"Mode  : DRY RUN (no files written)")
    print()

    total_images = 0
    total_converted = 0
    total_skipped = 0

    for src_split, dst_split in split_map.items():
        src_img_dir = input_root / src_split / "images"
        src_lbl_dir = input_root / src_split / "labels"

        dst_img_dir = output_root / "images" / dst_split
        dst_lbl_dir = output_root / "labels" / dst_split

        if not src_img_dir.exists():
            print(f"  SKIP {src_split}/ — folder not found")
            continue

        # Collect image files
        img_files = []
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp"):
            img_files.extend(src_img_dir.glob(ext))

        lbl_files = list(src_lbl_dir.glob("*.txt")) if src_lbl_dir.exists() else []

        print(f"  [{src_split} → {dst_split}]  {len(img_files)} images, {len(lbl_files)} labels")

        if not args.dry_run:
            dst_img_dir.mkdir(parents=True, exist_ok=True)
            dst_lbl_dir.mkdir(parents=True, exist_ok=True)

        # Copy images
        for img in img_files:
            dst = dst_img_dir / img.name
            if not args.dry_run:
                shutil.copy2(img, dst)
            total_images += 1

        # Convert labels
        split_converted = 0
        split_skipped = 0
        for lbl in lbl_files:
            dst = dst_lbl_dir / lbl.name
            if args.dry_run:
                # Just count what would happen
                with open(lbl) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        result = seg_line_to_bbox_line(line)
                        if result:
                            split_converted += 1
                        else:
                            split_skipped += 1
            else:
                c, s = convert_label_file(lbl, dst)
                split_converted += c
                split_skipped += s

        print(f"         Annotations converted: {split_converted}  |  skipped: {split_skipped}")
        total_converted += split_converted
        total_skipped += split_skipped

    print(f"\n{'═' * 50}")
    print(f"Images copied        : {total_images}")
    print(f"Annotations converted: {total_converted}")
    print(f"Annotations skipped  : {total_skipped}")

    if not args.dry_run:
        print(f"\n  Output written to: {output_root.resolve()}")
        print()
        print("Next steps:")
        print("  1. python scripts/validate_dataset.py")
        print("  2. python scripts/check_class_balance.py")
    else:
        print(f"\n  Dry run complete. Remove --dry-run to write files.")


if __name__ == "__main__":
    main()
