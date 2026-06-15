"""
test_vest_live.py — Live vest detection diagnostic
Shows ALL detections at very low confidence so you can see exactly what the model sees.
Press S to save a frame for analysis, Q to quit.
"""
import cv2
from ultralytics import YOLO

MODEL = "models/best.pt"
CONF  = 0.005   # extremely low — shows everything the model sees

COLORS = {
    "helmet":      (0, 255, 0),
    "safety_vest": (0, 165, 255),
    "goggles":     (255, 0, 0),
    "gloves":      (255, 0, 255),
}

model = YOLO(MODEL)
print(f"Model: {MODEL}")
print(f"Classes: {model.names}")
print(f"Conf threshold: {CONF} (showing everything)\n")

cap = cv2.VideoCapture(0)
saved = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, conf=CONF, verbose=False)

    vest_detections = []
    for r in results:
        for box in r.boxes:
            cls  = int(box.cls[0])
            conf = float(box.conf[0])
            name = model.names[cls]
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]

            color = COLORS.get(name, (255, 255, 255))
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{name} {conf:.3f}", (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

            if name == "safety_vest":
                vest_detections.append(conf)

    label = f"vest detections: {len(vest_detections)} " + \
            (f"max_conf={max(vest_detections):.3f}" if vest_detections else "(none)")
    cv2.putText(frame, label, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
    cv2.putText(frame, "S=save frame  Q=quit", (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    cv2.imshow("Vest Diagnostic (conf=0.005)", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break
    elif key == ord("s"):
        path = f"/tmp/vest_frame_{saved}.jpg"
        cv2.imwrite(path, frame)
        print(f"Saved: {path}  vest confs={vest_detections}")
        saved += 1

cap.release()
cv2.destroyAllWindows()
