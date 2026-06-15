"""
find_best_detection.py — Empirically find the strongest vest-detection strategy.

For each webcam frame it runs the SAME model four ways and prints the max
safety_vest confidence of each, so you can see which gives the highest, most
consistent jacket detection:

  full@640   — current pipeline default
  full@960   — higher-resolution full frame
  full@1280  — even higher resolution
  zoom@640   — crop the person, upscale to 640 (jacket fills frame ≈ training)

Watch the columns while wearing the jacket. Whichever column is consistently
highest is the strategy to configure in the pipeline. Press Q to quit.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
from ultralytics import YOLO

PPE_MODEL    = "models/best.pt"
PERSON_MODEL = "yolov8n.pt"
DEVICE       = "mps"
VEST_ID      = 1

ppe    = YOLO(PPE_MODEL)
person = YOLO(PERSON_MODEL)

def max_vest_full(frame, imgsz):
    res = ppe(frame, conf=0.01, classes=[0, 1, 2, 3], imgsz=imgsz,
              device=DEVICE, verbose=False)
    confs = [float(b.conf[0]) for r in res for b in r.boxes if int(b.cls[0]) == VEST_ID]
    return max(confs) if confs else None

def max_vest_zoom(frame):
    # detect person, crop with padding, upscale to 640, run PPE
    pres = person(frame, conf=0.4, classes=[0], device=DEVICE, verbose=False)
    boxes = [b.xyxy[0].tolist() for r in pres for b in r.boxes]
    if not boxes:
        return None
    fh, fw = frame.shape[:2]
    best = None
    for (x1, y1, x2, y2) in boxes:
        bw, bh = x2 - x1, y2 - y1
        px, py = int(bw * 0.3), int(bh * 0.3)
        cx1, cy1 = max(0, int(x1 - px)), max(0, int(y1 - py))
        cx2, cy2 = min(fw, int(x2 + px)), min(fh, int(y2 + py))
        crop = frame[cy1:cy2, cx1:cx2]
        if crop.size == 0:
            continue
        z = cv2.resize(crop, (640, 640))
        res = ppe(z, conf=0.01, classes=[0, 1, 2, 3], device=DEVICE, verbose=False)
        confs = [float(b.conf[0]) for r in res for b in r.boxes if int(b.cls[0]) == VEST_ID]
        if confs:
            m = max(confs)
            best = m if best is None else max(best, m)
    return best

cap = cv2.VideoCapture(0)
print("Wear the jacket. Columns show MAX vest confidence per strategy. Q to quit.\n")
print(f"{'full@640':>10} {'full@960':>10} {'full@1280':>10} {'zoom@640':>10}")
n = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    n += 1
    if n % 5 != 0:
        cv2.imshow("find_best", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        continue

    def fmt(v): return f"{v:.3f}" if v is not None else "  -  "
    a = max_vest_full(frame, 640)
    b = max_vest_full(frame, 960)
    c = max_vest_full(frame, 1280)
    d = max_vest_zoom(frame)
    print(f"{fmt(a):>10} {fmt(b):>10} {fmt(c):>10} {fmt(d):>10}")

    cv2.imshow("find_best", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
