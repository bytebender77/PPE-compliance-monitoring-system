"""
Export zoomed person crops from 20m CCTV footage for annotation on Roboflow.
These crops show workers clearly — ready to annotate helmet/vest/goggles/gloves.

Run:
    python scripts/export_zoomed_crops.py

Output: data/zoomed_crops/  → upload to Roboflow, annotate, export, retrain.
"""

from pathlib import Path
from ultralytics import YOLO
import cv2

FRAMES_DIR = Path("data/raw/frames")
OUT_DIR    = Path("data/zoomed_crops")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PERSON_CONF = 0.25
PADDING     = 0.35
MAX_CROPS   = 200   # enough to annotate in 1-2 hours

person_model = YOLO("yolov8n.pt")
frames = sorted(FRAMES_DIR.glob("*.jpg"))

saved = 0
print(f"Extracting up to {MAX_CROPS} person crops from {len(frames)} frames...\n")

for frame_path in frames:
    if saved >= MAX_CROPS:
        break

    frame = cv2.imread(str(frame_path))
    if frame is None:
        continue

    fh, fw = frame.shape[:2]
    results = person_model(frame, conf=PERSON_CONF, classes=[0], verbose=False)[0]

    if results.boxes is None or len(results.boxes) == 0:
        continue

    for i, box in enumerate(results.boxes):
        if saved >= MAX_CROPS:
            break

        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
        bw, bh = x2 - x1, y2 - y1
        pad_x  = int(bw * PADDING)
        pad_y  = int(bh * PADDING)
        cx1    = max(0, x1 - pad_x)
        cy1    = max(0, y1 - pad_y)
        cx2    = min(fw, x2 + pad_x)
        cy2    = min(fh, y2 + pad_y)

        crop   = frame[cy1:cy2, cx1:cx2]
        zoomed = cv2.resize(crop, (640, 640), interpolation=cv2.INTER_LINEAR)

        out_name = f"{frame_path.stem}_p{i}.jpg"
        cv2.imwrite(str(OUT_DIR / out_name), zoomed,
                    [cv2.IMWRITE_JPEG_QUALITY, 92])
        saved += 1

    if saved % 20 == 0 and saved > 0:
        print(f"  {saved} crops saved...")

print(f"\n  Done — {saved} crops → {OUT_DIR.resolve()}")
print(f"\n  Next steps:")
print(f"  1. Upload data/zoomed_crops/ to Roboflow")
print(f"  2. Annotate helmet/vest/goggles/gloves on each crop")
print(f"     (worker is clearly visible — takes ~1-2 hrs for 200 crops)")
print(f"  3. Export as YOLOv8 → merge with existing dataset → retrain")
