"""
capture_gloves.py — Webcam capture for gloves dataset collection

Captures TWO types of frames:
  - GLOVES mode    → hands with gloves worn  → saved to data/gloves_raw/gloves/
  - RAW HAND mode  → bare hands no gloves    → saved to data/gloves_raw/raw_hands/

Controls:
    G     → switch to GLOVES mode
    H     → switch to RAW HAND mode
    SPACE → save current frame manually
    R     → toggle auto-capture on/off
    Q     → quit

Run:
    python scripts/capture_gloves.py
    python scripts/capture_gloves.py --interval 20
"""

import cv2
import argparse
import time
from pathlib import Path
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(description="Webcam capture for gloves dataset")
    parser.add_argument("--source",   default="0",               help="Camera index")
    parser.add_argument("--output",   default="data/gloves_raw",  help="Output root folder")
    parser.add_argument("--interval", type=int, default=20,       help="Auto-save every N frames")
    return parser.parse_args()


def main():
    args = parse_args()

    # Create both output folders
    gloves_dir   = Path(args.output) / "gloves"
    raw_hand_dir = Path(args.output) / "raw_hands"
    gloves_dir.mkdir(parents=True, exist_ok=True)
    raw_hand_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    if not cap.isOpened():
        print(f"ERROR: Cannot open camera: {args.source}")
        return

    w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    print(f"Camera ready: {w}x{h} @ {fps:.0f} fps")
    print()
    print("  G → GLOVES mode (wear gloves, show hands)")
    print("  H → RAW HAND mode (bare hands, no gloves)")
    print("  SPACE → save frame manually")
    print("  R → toggle auto-capture")
    print("  Q → quit")
    print()

    # State
    mode         = "gloves"    # "gloves" or "raw_hands"
    auto_capture = True
    frame_count  = 0
    saved_gloves = 0
    saved_raw    = 0
    start_time   = time.time()
    flash        = 0           # green flash counter on save

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        current_dir = gloves_dir if mode == "gloves" else raw_hand_dir

        # Auto-save
        saved_this_frame = False
        if auto_capture and frame_count % args.interval == 0:
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            prefix = "glove" if mode == "gloves" else "rawhand"
            path = current_dir / f"{prefix}_{ts}.jpg"
            cv2.imwrite(str(path), frame)
            if mode == "gloves":
                saved_gloves += 1
            else:
                saved_raw += 1
            saved_this_frame = True
            flash = 4

        # Build display
        display = frame.copy()

        # Flash border on save
        if flash > 0:
            border_color = (0, 255, 0) if mode == "gloves" else (0, 165, 255)
            cv2.rectangle(display, (0, 0), (w - 1, h - 1), border_color, 8)
            flash -= 1

        # Mode color
        if mode == "gloves":
            mode_color  = (0, 220, 0)
            mode_label  = "GLOVES MODE  [G]"
            mode_hint   = "Wear gloves — show both hands"
        else:
            mode_color  = (0, 165, 255)
            mode_label  = "RAW HAND MODE  [H]"
            mode_hint   = "No gloves — bare hands only"

        # Top bar
        cv2.rectangle(display, (0, 0), (w, 70), (15, 15, 15), -1)

        # Mode indicator
        cv2.rectangle(display, (0, 0), (300, 70), mode_color, -1)
        cv2.putText(display, mode_label, (8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
        cv2.putText(display, mode_hint, (8, 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

        # Stats
        elapsed  = time.time() - start_time
        live_fps = frame_count / elapsed if elapsed > 0 else 0
        auto_str = "AUTO ON" if auto_capture else "AUTO OFF"
        auto_col = (0, 200, 0) if auto_capture else (0, 0, 200)

        cv2.putText(display, f"Gloves saved : {saved_gloves}",
                    (310, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 0), 1)
        cv2.putText(display, f"Raw hand saved: {saved_raw}",
                    (310, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
        cv2.putText(display, f"FPS: {live_fps:.1f}  {auto_str}",
                    (310, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.4, auto_col, 1)

        # Bottom bar
        cv2.rectangle(display, (0, h - 35), (w, h), (15, 15, 15), -1)
        cv2.putText(display, "G: gloves mode  |  H: raw hand mode  |  SPACE: save  |  R: auto toggle  |  Q: quit",
                    (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (140, 140, 140), 1)

        cv2.imshow("Gloves Dataset Capture", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key == ord("g"):
            mode = "gloves"
            print(f"  Switched → GLOVES MODE")
        elif key == ord("h"):
            mode = "raw_hands"
            print(f"  Switched → RAW HAND MODE")
        elif key == ord("r"):
            auto_capture = not auto_capture
            print(f"  Auto-capture → {'ON' if auto_capture else 'OFF'}")
        elif key == ord(" "):
            ts     = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            prefix = "glove" if mode == "gloves" else "rawhand"
            path   = current_dir / f"{prefix}_manual_{ts}.jpg"
            cv2.imwrite(str(path), frame)
            if mode == "gloves":
                saved_gloves += 1
            else:
                saved_raw += 1
            flash = 4
            print(f"  Saved: {path.name}")

    cap.release()
    cv2.destroyAllWindows()

    print()
    print("=" * 50)
    print(f"  Gloves frames  : {saved_gloves}  → {gloves_dir.resolve()}")
    print(f"  Raw hand frames: {saved_raw}  → {raw_hand_dir.resolve()}")
    print(f"  Total saved    : {saved_gloves + saved_raw}")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Go to https://app.roboflow.com")
    print("  2. Upload gloves/ folder → annotate with 'gloves' class")
    print("  3. Upload raw_hands/ folder → annotate as BACKGROUND (no boxes)")
    print("  4. Export YOLOv8 format → retrain model")
