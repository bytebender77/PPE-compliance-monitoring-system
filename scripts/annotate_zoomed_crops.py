"""
scripts/annotate_zoomed_crops.py
──────────────────────────────────
Auto-annotate zoomed CCTV crops using best.pt (pre-finetune, 4-class model).

Why: Roboflow annotations only had 2 classes (helmet + vest, manual).
     best.pt has mAP=0.947 across all 4 classes — better quality labels.

Input : data/zoomed_crops/  (200 original 640×640 crops)
Model : models/best.pt      (helmet=0, vest=1, goggles=2, gloves=3)
Output: data/zoomed_crops_annotated/
          images/ — same 200 crops
          labels/ — YOLO bbox labels from best.pt

Run:
    python scripts/annotate_zoomed_crops.py
"""

from pathlib import Path
from ultralytics import YOLO
import shutil

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_PATH  = "models/best.pt"
CROPS_DIR   = Path("data/zoomed_crops")
OUT_DIR     = Path("data/zoomed_crops_annotated")
CONF        = 0.30   # slightly lower — crops are clear, want to catch all PPE

OUT_IMAGES  = OUT_DIR / "images"
OUT_LABELS  = OUT_DIR / "labels"
OUT_IMAGES.mkdir(parents=True, exist_ok=True)
OUT_LABELS.mkdir(parents=True, exist_ok=True)

print(f"\n── Auto-annotating zoomed crops with best.pt ──────────────────────")
print(f"   Model  : {MODEL_PATH}")
print(f"   Crops  : {CROPS_DIR}  ({len(list(CROPS_DIR.glob('*.jpg')))} images)")
print(f"   Conf   : {CONF}")
print(f"   Output : {OUT_DIR}")

model  = YOLO(MODEL_PATH)
crops  = sorted(CROPS_DIR.glob("*.jpg"))

stats  = {"annotated": 0, "empty": 0, "total_boxes": 0}
class_counts = {0: 0, 1: 0, 2: 0, 3: 0}

for crop_path in crops:
    results = model(str(crop_path), conf=CONF, verbose=False)[0]

    # Copy image
    shutil.copy2(crop_path, OUT_IMAGES / crop_path.name)

    # Write label
    lbl_path = OUT_LABELS / f"{crop_path.stem}.txt"
    lines = []

    if results.boxes is not None and len(results.boxes) > 0:
        for box in results.boxes:
            cls  = int(box.cls[0])
            xc, yc, w, h = box.xywhn[0].tolist()   # normalised xywh
            lines.append(f"{cls} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")
            class_counts[cls] = class_counts.get(cls, 0) + 1
            stats["total_boxes"] += 1
        stats["annotated"] += 1
    else:
        stats["empty"] += 1

    lbl_path.write_text("\n".join(lines))

# ── Summary ────────────────────────────────────────────────────────────────────
names = {0: "helmet", 1: "safety_vest", 2: "goggles", 3: "gloves"}
print(f"\n── Results ─────────────────────────────────────────────────────────")
print(f"   Annotated  : {stats['annotated']} / {len(crops)} crops")
print(f"   Empty      : {stats['empty']} crops (no PPE detected)")
print(f"   Total boxes: {stats['total_boxes']}")
print(f"\n   Per-class boxes:")
for cls, count in sorted(class_counts.items()):
    print(f"     {cls} {names.get(cls, cls):12s}: {count}")

print(f"\n── Done → {OUT_DIR.resolve()}")
