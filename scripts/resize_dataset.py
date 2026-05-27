"""
scripts/resize_dataset.py — Resize all dataset images to 640×640 in-place.

YOLOv8 trains at 640×640 anyway (--imgsz 640). Keeping 2-4 MP iPhone images
on disk just wastes space; the trainer downsamples them every epoch.
Resizing now:
  - Reduces train set from ~26 GB to ~1-2 GB
  - Makes the project zip-able
  - Labels do NOT change (YOLO uses normalised coords 0-1)

Usage
-----
    python scripts/resize_dataset.py               # all splits, 640×640
    python scripts/resize_dataset.py --size 416    # custom size
    python scripts/resize_dataset.py --dry-run     # report only, no writes
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

TARGET = 640
SPLITS = ["train", "val", "test"]
VALID_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def resize_image(path: Path, size: int, dry_run: bool) -> tuple[str, bool, str]:
    """
    Resize a single image to size×size (exact square).
    Returns (filename, changed, message).
    """
    try:
        img = Image.open(path)
        w, h = img.size
        if w == size and h == size:
            return (path.name, False, "already correct size")

        if dry_run:
            kb_before = path.stat().st_size // 1024
            return (path.name, True, f"{w}×{h} → {size}×{size}  ({kb_before}KB)")

        img_resized = img.convert("RGB").resize((size, size), Image.LANCZOS)
        img_resized.save(path, "JPEG", quality=90, optimize=True)
        kb_after = path.stat().st_size // 1024
        return (path.name, True, f"{w}×{h} → {size}×{size}  now {kb_after}KB")

    except Exception as exc:
        return (path.name, False, f"ERROR: {exc}")


def process_split(split: str, data_root: Path, size: int, dry_run: bool) -> dict:
    images_dir = data_root / "processed" / "images" / split
    if not images_dir.exists():
        return {"split": split, "total": 0, "resized": 0, "errors": 0}

    paths = [p for p in images_dir.iterdir() if p.suffix.lower() in VALID_EXTS]
    total   = len(paths)
    resized = 0
    errors  = 0

    print(f"\n[{split}]  {total} images  →  target {size}×{size}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(resize_image, p, size, dry_run): p for p in paths}
        done = 0
        for fut in as_completed(futures):
            name, changed, msg = fut.result()
            done += 1
            if changed:
                resized += 1
            if "ERROR" in msg:
                errors += 1
                print(f"  {msg}  [{name}]")
            # Progress bar every 500 images
            if done % 500 == 0 or done == total:
                pct = done / total * 100
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                label = "(dry-run)" if dry_run else ""
                print(f"  [{bar}] {done}/{total}  resized={resized} {label}", end="\r")

    print()  # newline after progress bar
    return {"split": split, "total": total, "resized": resized, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description="Resize dataset images in-place.")
    parser.add_argument("--data-root", default="data", help="Path to data/ directory")
    parser.add_argument("--size", type=int, default=TARGET, help="Target square size (default 640)")
    parser.add_argument("--split", choices=SPLITS + ["all"], default="all")
    parser.add_argument("--dry-run", action="store_true", help="Report sizes without writing")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    splits    = SPLITS if args.split == "all" else [args.split]

    print(f"{'═'*55}")
    print(f"  Dataset image resizer")
    print(f"  Target size : {args.size}×{args.size}")
    print(f"  Data root   : {data_root.resolve()}")
    print(f"  Mode        : {'DRY RUN — no files written' if args.dry_run else 'LIVE — files will be overwritten'}")
    print(f"{'═'*55}")

    if not args.dry_run:
        ans = input("\n  Overwrite images in-place? [y/N] ").strip().lower()
        if ans != "y":
            print("  Aborted.")
            sys.exit(0)

    totals = {"total": 0, "resized": 0, "errors": 0}
    for split in splits:
        r = process_split(split, data_root, args.size, args.dry_run)
        for k in totals:
            totals[k] += r[k]

    print(f"\n{'═'*55}")
    print(f"  Done.")
    print(f"  Images processed : {totals['total']}")
    print(f"  Images resized   : {totals['resized']}")
    print(f"  Errors           : {totals['errors']}")
    if args.dry_run:
        print(f"\n  Re-run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
