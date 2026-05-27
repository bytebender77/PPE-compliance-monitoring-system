"""
scripts/diagnose_detection.py — Live confidence score debugger.

Shows RAW confidence scores for every detection with NO threshold filtering.
Use this to find out what confidence the model actually gives your vest.

Usage
-----
# Live webcam
python scripts/diagnose_detection.py

# On a video file
python scripts/diagnose_detection.py --source video.mp4

# Save a snapshot for inspection
python scripts/diagnose_detection.py --snapshot
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

CLASS_NAMES = {0: "helmet", 1: "safety_vest", 2: "goggles"}
COLORS = {
    "helmet":       (0, 255, 255),   # yellow
    "safety_vest":  (255, 165, 0),   # orange
    "goggles":      (255, 0, 255),   # magenta
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",   default="0",           help="Webcam index or video file path")
    parser.add_argument("--model",    default="models/best.pt", help="Path to PPE model weights")
    parser.add_argument("--snapshot", action="store_true",   help="Save one snapshot to debug_snapshot.jpg and exit")
    return parser.parse_args()


def main():
    args = parse_args()

    from ultralytics import YOLO
    print(f"Loading model: {args.model}")
    model = YOLO(args.model)
    print("Model loaded. Starting feed...\n")
    print("What to look for:")
    print("  - 'safety_vest 0.18' means it sees your vest but confidence is 0.18")
    print("  - Nothing printed = model doesn't see a vest at all")
    print("  - Press Q to quit, S to save snapshot\n")

    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"ERROR: Cannot open source: {args.source}")
        sys.exit(1)

    frame_n = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_n += 1

        # Run with conf=0.01 — show EVERYTHING the model sees
        results = model(frame, conf=0.01, verbose=False)

        display = frame.copy()
        detections_this_frame = []

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id     = int(box.cls[0])
                conf       = float(box.conf[0])
                class_name = CLASS_NAMES.get(cls_id, f"cls{cls_id}")
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                color = COLORS.get(class_name, (200, 200, 200))

                # Draw all detections — colour intensity reflects confidence
                alpha = max(0.3, conf)   # faint if low confidence
                thickness = 1 if conf < 0.20 else 2

                cv2.rectangle(display, (x1, y1), (x2, y2), color, thickness)
                label = f"{class_name} {conf:.2f}"
                cv2.putText(display, label, (x1, max(y1 - 5, 15)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

                detections_this_frame.append((class_name, conf))

        # Print every 15 frames so terminal doesn't flood
        if frame_n % 15 == 0 and detections_this_frame:
            vest_detections = [(n, c) for n, c in detections_this_frame if n == "safety_vest"]
            if vest_detections:
                for name, conf in vest_detections:
                    bar = "█" * int(conf * 20)
                    flag = " ← BELOW 0.20 threshold" if conf < 0.20 else " ← DETECTED ✓" if conf >= 0.35 else " ← try threshold=0.15"
                    print(f"  safety_vest  conf={conf:.3f}  [{bar:<20}]{flag}")
            else:
                print(f"  frame {frame_n:4d}: no safety_vest detected at all")

        # Threshold guide overlay
        h, w = display.shape[:2]
        guide = [
            "DIAGNOSTIC MODE — conf=0.01 (all detections shown)",
            "Yellow=helmet  Orange=vest  Magenta=goggles",
            "Faint box = low conf  |  Thick box = high conf",
            "Press Q to quit  S to save snapshot",
        ]
        for i, line in enumerate(guide):
            cv2.putText(display, line, (10, h - 80 + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1, cv2.LINE_AA)

        cv2.imshow("PPE Diagnostic — all detections", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key == ord("s") or args.snapshot:
            cv2.imwrite("debug_snapshot.jpg", display)
            print("Saved: debug_snapshot.jpg")
            if args.snapshot:
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
