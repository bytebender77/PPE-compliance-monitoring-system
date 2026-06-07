"""
scripts/auto_annotate.py
─────────────────────────
Auto-annotates extracted frames using the current best.pt model.
Only saves labels with confidence >= MIN_CONF (high-confidence = trustworthy).
Skips frames where model detects nothing (saves as background/negative).

Output structure (Roboflow-ready):
  data/auto_annotated/
    ├── images/   ← frame JPEGs
    └── labels/   ← YOLO bbox .txt files (or empty for backgrounds)

Upload the images/ + labels/ folders to Roboflow for review + correction.

Run:
    python scripts/auto_annotate.py
"""

from pathlib import Path
from ultralytics import YOLO
import cv2
import shutil

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_PATH   = "models/best.pt"
FRAMES_DIR   = Path("data/raw/frames")
OUT_DIR      = Path("data/auto_annotated")
MIN_CONF     = 0.45      # only keep detections above this confidence
MAX_FRAMES   = 2000      # cap to avoid overwhelming Roboflow free tier
SAVE_BLANKS  = True      # save frames with no detections (negatives)

OUT_IMAGES   = OUT_DIR / "images"
OUT_LABELS   = OUT_DIR / "labels"
OUT_IMAGES.mkdir(parents=True, exist_ok=True)
OUT_LABELS.mkdir(parents=True, exist_ok=True)

# ── Load model ────────────────────────────────────────────────────────────────
print(f"\n── Auto-Annotation ──────────────────────────────────────────────────")
print(f"   Model  : {MODEL_PATH}")
print(f"   Frames : {FRAMES_DIR}")
print(f"   Min conf: {MIN_CONF}")
model = YOLO(MODEL_PATH)

# ── Process frames ────────────────────────────────────────────────────────────
frames = sorted(FRAMES_DIR.glob("*.jpg"))[:MAX_FRAMES]
print(f"   Processing {len(frames)} frames...\n")

saved_with_labels  = 0
saved_as_negatives = 0
skipped            = 0

for i, frame_path in enumerate(frames):
    img    = cv2.imread(str(frame_path))
    if img is None:
        continue

    h, w = img.shape[:2]
    results = model(img, conf=MIN_CONF, verbose=False)[0]
    boxes   = results.boxes

    stem     = frame_path.stem
    dst_img  = OUT_IMAGES / f"{stem}.jpg"
    dst_lbl  = OUT_LABELS / f"{stem}.txt"

    if boxes is None or len(boxes) == 0:
        if SAVE_BLANKS:
            shutil.copy2(frame_path, dst_img)
            dst_lbl.write_text("")   # empty = background
            saved_as_negatives += 1
        else:
            skipped += 1
    else:
        # Write YOLO bbox labels
        lines = []
        for box in boxes:
            cls  = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cx = ((x1 + x2) / 2) / w
            cy = ((y1 + y2) / 2) / h
            bw = (x2 - x1) / w
            bh = (y2 - y1) / h
            lines.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}  # conf={conf:.2f}")

        shutil.copy2(frame_path, dst_img)
        dst_lbl.write_text("\n".join(lines))
        saved_with_labels += 1

    if (i + 1) % 100 == 0:
        print(f"   [{i+1:4d}/{len(frames)}]  annotated={saved_with_labels}  negatives={saved_as_negatives}")

# ── Summary ───────────────────────────────────────────────────────────────────
total = saved_with_labels + saved_as_negatives
print(f"\n  ── Results ───────────────────────────────────────────────────────")
print(f"  Frames with labels  : {saved_with_labels}")
print(f"  Frames as negatives : {saved_as_negatives}")
print(f"  Total saved         : {total}")
print(f"  Output              : {OUT_DIR.resolve()}")
print(f"\n  ── Next steps ────────────────────────────────────────────────────")
print(f"  1. Upload data/auto_annotated/ to Roboflow for spot-check")
print(f"     (fix wrong labels — usually <10% need correction)")
print(f"  2. Export from Roboflow → merge with existing dataset")
print(f"  3. Retrain for 50-100 epochs on full merged dataset")
print()
