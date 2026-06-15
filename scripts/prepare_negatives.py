"""
prepare_negatives.py — Auto-create empty YOLO annotation files for negative samples

In YOLO format:
  Positive image → image.jpg + image.txt (with box coordinates)
  Negative image → image.jpg + image.txt (EMPTY file = no objects)

This script takes your neg_bare_hands/ and neg_bare_face/ folders
and creates an empty .txt for every image — ready to merge into your dataset.

Run:
  python scripts/prepare_negatives.py
"""

from pathlib import Path

NEGATIVE_FOLDERS = [
    "data/ppe_capture/neg_bare_hands",
    "data/ppe_capture/neg_bare_face",
    "data/ppe_capture/no_ppe",
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def prepare(folder: str):
    path = Path(folder)
    if not path.exists():
        print(f"  SKIP (folder not found): {folder}")
        return

    images = [f for f in path.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS]
    if not images:
        print(f"  SKIP (no images found): {folder}")
        return

    created = 0
    skipped = 0
    for img in images:
        txt = img.with_suffix(".txt")
        if txt.exists():
            skipped += 1
            continue
        txt.touch()   # create empty .txt file
        created += 1

    print(f"  {path.name:<20} — {created} empty .txt created  ({skipped} already existed)  [{len(images)} images total]")


def main():
    print()
    print("Creating empty YOLO annotation files for negative samples...")
    print()
    for folder in NEGATIVE_FOLDERS:
        prepare(folder)
    print()
    print("Done. Your negative folders now have empty .txt files.")
    print()
    print("Next — merge into your dataset:")
    print("  Copy images + .txt files from neg folders into your dataset's train/images/ and train/labels/")


if __name__ == "__main__":
    main()
