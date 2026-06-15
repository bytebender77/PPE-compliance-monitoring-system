"""
diag_pipeline_vs_raw.py — Why does the vest detect in test_vest_live but not the pipeline?

For each webcam frame, runs the model THREE ways and prints the vest result of each:
  A) RAW       : model(frame, conf=0.005)                       — like test_vest_live
  B) PIPELINE  : the actual PPEDetector class used by main.py    — exact pipeline path
  C) PIPE-LOWCONF: PPEDetector but conf forced to 0.005          — isolates threshold

If A finds vest but B/C don't → the difference is in the PPEDetector call (device/classes).
If A and C both find it but B doesn't → it's purely the confidence threshold.
Press Q to quit.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
from ultralytics import YOLO
from ppe_compliance_system.inference_engine.detectors.ppe_detector import PPEDetector

MODEL = "models/best.pt"

raw_model = YOLO(MODEL)

# Pipeline detector at its real default threshold (matches main.py path)
pipe = PPEDetector(model_path=MODEL, conf_threshold=0.05, device="mps")
# Pipeline detector but with the diagnostic's low threshold
pipe_low = PPEDetector(model_path=MODEL, conf_threshold=0.005, device="mps")

def vest_confs_raw(frame):
    res = raw_model(frame, conf=0.005, verbose=False)
    out = []
    for r in res:
        for b in r.boxes:
            if int(b.cls[0]) == 1:
                out.append(round(float(b.conf[0]), 3))
    return out

def vest_confs_pipe(det, frame):
    items = det.detect(frame)
    return [d["confidence"] for d in items if d["class_name"] == "safety_vest"]

cap = cv2.VideoCapture(0)
print("Running... wear the jacket, full torso in frame. Q to quit.\n")
n = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    n += 1
    if n % 5 != 0:           # only analyse every 5th frame to keep terminal readable
        cv2.imshow("diag", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        continue

    a = vest_confs_raw(frame)
    b = vest_confs_pipe(pipe, frame)
    c = vest_confs_pipe(pipe_low, frame)
    print(f"A raw(0.005)={a}   B pipeline(0.05)={b}   C pipeline(0.005)={c}")

    cv2.imshow("diag", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
