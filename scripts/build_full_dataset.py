"""
scripts/build_full_dataset.py
──────────────────────────────
Build complete dataset with INDUSTRIAL vests only — no generic/stock vest images.

nc=4: helmet(0), safety_vest(1), goggles(2), gloves(3)

Filtering logic:
  ALWAYS KEEP (confirmed industrial source):
    indvest_*         — Industrial Vest dataset (includes Tata Steel workers)
    sitev_*           — Construction site vest (user's own site footage)
    sv3_*             — User's own Tata Steel video (IMG_9343.MOV)
    ppe_construction-* — Construction worker PPE
    ppe_Video*         — Video-sourced frames (industrial CCTV)
    ppe_KakaoTalk_*    — Site worker photos (construction context)
    vest_IMG_9115*     — User's own site photos
    numeric (005xxx)   — Industrial CCTV frame extracts
    zcrop_*            — CCTV zoomed person crops
    IMG_*              — Goggles close-ups (user's own)
    glv_*              — Gloves (user's own)
    neg_*              — Negative face images
    goggles_*          — Goggles dataset

  ALWAYS REMOVE:
    ppe_*              — Entire "PPE detection" Roboflow dataset (5140 images, generic)
    vest_copy*         — Web-copied vest images

Run:
    python scripts/build_full_dataset.py
"""

import shutil
from pathlib import Path

OUT_ROOT = Path("data/full_merged")

# ── Always-keep source prefixes ───────────────────────────────────────────────
ALWAYS_KEEP = [
    "indvest_",
    "sitev_",
    "sv3_",
    "sv_",
    "ppe_construction-",
    "ppe_Video",
    "ppe_KakaoTalk_",
    "vest_IMG_9115",
    "vest_IMG_9343",   # may exist
    "zcrop_",
    "IMG_",
    "glv_",
    "neg_",
    "goggles_",
]

# ── Always-remove source prefixes ─────────────────────────────────────────────
ALWAYS_REMOVE = [
    "ppe_",        # entire "PPE detection" Roboflow dataset — generic, user-removed
    "vest_copy",   # web-copied vest images
]

def classify(img_name: str, lbl_path: Path) -> str:
    """Returns 'keep', 'remove', or 'smart_filter'."""
    name = img_name.lower()

    for prefix in ALWAYS_REMOVE:
        if name.startswith(prefix.lower()):
            return "remove"

    for prefix in ALWAYS_KEEP:
        if name.startswith(prefix.lower()):
            return "keep"

    # Numeric filenames = CCTV industrial frames
    if name[0].isdigit():
        return "keep"

    # Everything else → keep
    return "keep"


def has_helmet_and_vest(lbl_path: Path) -> bool:
    """True if label has at least one helmet(0) AND one vest(1) box."""
    if not lbl_path.exists():
        return False
    lines = lbl_path.read_text().strip().splitlines()
    has_helmet = any(l.startswith("0 ") for l in lines)
    has_vest   = any(l.startswith("1 ") for l in lines)
    return has_helmet and has_vest


# ── Clean and create output dirs ──────────────────────────────────────────────
if OUT_ROOT.exists():
    shutil.rmtree(OUT_ROOT)
    print("Removed old full_merged/")

for split in ["train", "val", "test"]:
    (OUT_ROOT / split / "images").mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / split / "labels").mkdir(parents=True, exist_ok=True)

# ── Stats ─────────────────────────────────────────────────────────────────────
stats = {"kept": 0, "removed_generic": 0, "filtered_out": 0, "smart_kept": 0}

def copy_pair(img_path: Path, lbl_path: Path, split: str) -> bool:
    if not img_path.exists():
        return False
    dst_img = OUT_ROOT / split / "images" / img_path.name
    dst_lbl = OUT_ROOT / split / "labels" / f"{lbl_path.stem}.txt"
    shutil.copy2(img_path, dst_img)
    if lbl_path.exists():
        lines = lbl_path.read_text().strip().splitlines()
        clean = [l for l in lines if l.strip() and len(l.strip().split()) == 5]
        dst_lbl.write_text("\n".join(clean))
    else:
        dst_lbl.write_text("")
    return True


# ── Process each split ────────────────────────────────────────────────────────
for split, img_src, lbl_src in [
    ("train", Path("data/processed/images/train"), Path("data/processed/labels/train")),
    ("val",   Path("data/processed/images/val"),   Path("data/processed/labels/val")),
    ("test",  Path("data/processed/images/test"),  Path("data/processed/labels/test")),
]:
    print(f"\nProcessing {split}...")
    for img in sorted(img_src.glob("*")):
        lbl = lbl_src / f"{img.stem}.txt"
        decision = classify(img.name, lbl)

        if decision == "remove":
            stats["removed_generic"] += 1
            continue
        elif decision == "keep":
            copy_pair(img, lbl, split)
            stats["kept"] += 1
        elif decision == "smart_filter":
            if has_helmet_and_vest(lbl):
                copy_pair(img, lbl, split)
                stats["kept"] += 1
                stats["smart_kept"] += 1
            else:
                stats["filtered_out"] += 1

# ── Extra sources (goggles, gloves, CCTV, negatives) ─────────────────────────
print("\nAdding goggles_finetune extras...")
src_i = Path("data/goggles_finetune/train/images")
src_l = Path("data/goggles_finetune/train/labels")
extra_added = 0
for pattern in ["IMG_*", "glv_*", "zcrop_*", "neg_*"]:
    for img in sorted(src_i.glob(pattern)):
        lbl = src_l / f"{img.stem}.txt"
        if copy_pair(img, lbl, "train"):
            extra_added += 1

# CCTV crops for val/test
for split, subdir in [("val", "val"), ("test", "test")]:
    src_vi = Path(f"data/goggles_finetune/{subdir}/images")
    src_vl = Path(f"data/goggles_finetune/{subdir}/labels")
    if src_vi.exists():
        for img in sorted(src_vi.glob("zcrop_*")):
            copy_pair(img, src_vl / f"{img.stem}.txt", split)

print(f"  Added {extra_added} extra images (goggles/gloves/CCTV/negatives)")

# ── Write data.yaml ────────────────────────────────────────────────────────────
(OUT_ROOT / "data.yaml").write_text("""# ============================================================
#  PPE Full Dataset — Industrial vests only — nc=4
#  helmet(0)  safety_vest(1)  goggles(2)  gloves(3)
# ============================================================
#
# EDIT PATHS for Windows before training:
#   train: C:\\path\\to\\full_merged\\train\\images

train: ../train/images
val:   ../val/images
test:  ../test/images

nc: 4
names: ['helmet', 'safety_vest', 'goggles', 'gloves']
""")

# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'='*58}")
print(f"  INDUSTRIAL PPE DATASET (nc=4)")
print(f"{'='*58}")
for split in ["train", "val", "test"]:
    n = len(list((OUT_ROOT / split / "images").glob("*")))
    print(f"  {split:5s}  {n:7,} images")

print(f"\n  Filtering stats:")
print(f"    Kept (confirmed industrial) : {stats['kept']:,}")
print(f"    Smart-filtered (helmet+vest): {stats['smart_kept']:,}")
print(f"    Removed (generic/stock)     : {stats['removed_generic']:,}")
print(f"    Filtered out (vest-only)    : {stats['filtered_out']:,}")

print(f"\n  Class balance (train):")
lbl_dir = OUT_ROOT / "train" / "labels"
for cls, name in [(0,"helmet"),(1,"safety_vest"),(2,"goggles"),(3,"gloves")]:
    n = sum(
        l.startswith(f"{cls} ")
        for f in lbl_dir.glob("*.txt")
        for l in f.read_text().splitlines()
    )
    bar = "█" * (n // 2000)
    print(f"    {cls} {name:12s}: {n:6,}  {bar}")

print(f"""
{'='*58}
  Training command (Windows — RTX A5000):

    yolo detect train \\
      data=full_merged\\data.yaml \\
      model=yolov8s.pt \\
      epochs=100 imgsz=640 batch=32 device=0 \\
      name=ppe_v3_full
{'='*58}
""")
