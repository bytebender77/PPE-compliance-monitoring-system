"""
Capture ~100 face images (no goggles) as negative examples.
Press SPACE to capture, Q to quit.
Saves to data/goggles_finetune/train/images/ with empty label files.
"""

import cv2
from pathlib import Path

SAVE_DIR  = Path("data/goggles_finetune/train/images")
LABEL_DIR = Path("data/goggles_finetune/train/labels")
SAVE_DIR.mkdir(parents=True, exist_ok=True)
LABEL_DIR.mkdir(parents=True, exist_ok=True)

count    = sum(1 for f in SAVE_DIR.glob("neg_*.jpg"))
cap      = cv2.VideoCapture(0)

print(f"Already have {count} negatives. Press SPACE to capture, Q to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    display = frame.copy()
    cv2.putText(display, f"Negatives captured: {count}  |  SPACE=capture  Q=quit",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imshow("Capture Negatives", display)

    key = cv2.waitKey(1) & 0xFF
    if key == ord(' '):
        name = f"neg_{count:04d}"
        img_path = SAVE_DIR / f"{name}.jpg"
        lbl_path = LABEL_DIR / f"{name}.txt"
        cv2.imwrite(str(img_path), frame)
        lbl_path.write_text("")          # empty = background image
        count += 1
        print(f"  Saved {name}  ({count} total)")
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"\nDone. {count} negative images saved.")
print("Now retrain:")
print("  yolo detect train data=data/goggles_finetune/data.yaml model=models/best_before_goggles.pt epochs=30 imgsz=640 batch=16 freeze=10 name=goggles_v2")
