"""
capture_dataset.py — Complete PPE dataset capture tool

Captures ALL PPE classes + targeted negative samples:
  1 → Helmet
  2 → Safety Vest
  3 → Goggles
  4 → Gloves
  5 → Full PPE (all worn together)
  6 → BARE HANDS     (negative for gloves)
  7 → BARE FACE      (negative for goggles)
  0 → No PPE / Background (general negative)

Controls:
  1-7, 0  → switch capture mode
  SPACE   → save frame manually
  R       → toggle auto-capture
  Q       → quit

Run:
  python scripts/capture_dataset.py
  python scripts/capture_dataset.py --interval 20 --output data/ppe_capture
"""

import cv2
import argparse
import time
from pathlib import Path
from datetime import datetime


MODES = {
    "1": {
        "name":   "HELMET",
        "folder": "helmet",
        "hint":   "Wear helmet — show head from different angles",
        "color":  (0, 220, 255),   # yellow
    },
    "2": {
        "name":   "SAFETY VEST",
        "folder": "safety_vest",
        "hint":   "Wear safety vest — full torso visible",
        "color":  (0, 130, 255),   # orange
    },
    "3": {
        "name":   "GOGGLES",
        "folder": "goggles",
        "hint":   "Wear goggles — face + eye area visible",
        "color":  (255, 0, 255),   # magenta
    },
    "4": {
        "name":   "GLOVES",
        "folder": "gloves",
        "hint":   "Wear gloves — show both hands, angles, distances",
        "color":  (0, 255, 128),   # green-cyan
    },
    "5": {
        "name":   "FULL PPE",
        "folder": "full_ppe",
        "hint":   "All PPE worn — helmet + vest + goggles + gloves",
        "color":  (0, 255, 0),     # green
    },
    "6": {
        "name":   "BARE HANDS",
        "folder": "neg_bare_hands",
        "hint":   "NO gloves — bare hands only, different angles",
        "color":  (60, 180, 255),  # light blue — negative for gloves
    },
    "7": {
        "name":   "BARE FACE",
        "folder": "neg_bare_face",
        "hint":   "NO goggles — bare face/eyes, different angles",
        "color":  (180, 60, 255),  # purple — negative for goggles
    },
    "0": {
        "name":   "NO PPE / BACKGROUND",
        "folder": "no_ppe",
        "hint":   "No PPE at all — general background images",
        "color":  (80, 80, 80),    # grey
    },
}


def parse_args():
    parser = argparse.ArgumentParser(description="PPE dataset capture tool")
    parser.add_argument("--source",   default="0",               help="Camera index or video file")
    parser.add_argument("--output",   default="data/ppe_capture", help="Root output folder")
    parser.add_argument("--interval", type=int, default=20,       help="Auto-save every N frames (default 20)")
    return parser.parse_args()


def main():
    args = parse_args()

    # Create all output folders
    root = Path(args.output)
    for m in MODES.values():
        (root / m["folder"]).mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    if not cap.isOpened():
        print(f"ERROR: Cannot open camera: {args.source}")
        return

    w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    print(f"\nCamera ready: {w}x{h} @ {fps:.0f} fps")
    print(f"Saving to: {root.resolve()}\n")
    print("  1 → Helmet       4 → Gloves")
    print("  2 → Safety Vest  5 → Full PPE")
    print("  3 → Goggles      0 → No PPE (background)")
    print("  SPACE → save  |  R → toggle auto  |  Q → quit\n")

    # State
    mode         = "1"
    auto_capture = True
    frame_count  = 0
    flash        = 0
    start_time   = time.time()
    counts       = {k: 0 for k in MODES}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        m   = MODES[mode]
        col = m["color"]

        # Auto-save
        if auto_capture and frame_count % args.interval == 0:
            _save(frame, root / m["folder"], m["folder"])
            counts[mode] += 1
            flash = 5

        # Build display
        display = frame.copy()

        # Flash border on save
        if flash > 0:
            cv2.rectangle(display, (0, 0), (w - 1, h - 1), col, 10)
            flash -= 1

        # ── Top panel ──────────────────────────────────────────────────────────
        cv2.rectangle(display, (0, 0), (w, 80), (12, 12, 12), -1)

        # Mode badge
        cv2.rectangle(display, (0, 0), (340, 80), col, -1)
        cv2.putText(display, f"[{mode}] {m['name']}",
                    (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(display, m["hint"],
                    (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)

        # Auto indicator
        auto_col = (0, 200, 0) if auto_capture else (0, 0, 200)
        auto_str = "AUTO ON" if auto_capture else "AUTO OFF"
        cv2.putText(display, auto_str,
                    (350, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, auto_col, 1)

        # FPS
        elapsed  = time.time() - start_time
        live_fps = frame_count / elapsed if elapsed > 0 else 0
        cv2.putText(display, f"FPS: {live_fps:.1f}",
                    (350, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)

        # ── Right side — counts panel ──────────────────────────────────────────
        panel_x = w - 180
        cv2.rectangle(display, (panel_x, 80), (w, 80 + len(MODES) * 30 + 10), (20, 20, 20), -1)
        cv2.putText(display, "SAVED COUNTS",
                    (panel_x + 8, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (160, 160, 160), 1)

        for i, (key, info) in enumerate(MODES.items()):
            y       = 125 + i * 28
            is_cur  = (key == mode)
            bg_col  = info["color"] if is_cur else (30, 30, 30)
            txt_col = (0, 0, 0)     if is_cur else (180, 180, 180)
            cv2.rectangle(display, (panel_x + 4, y - 16), (w - 4, y + 8), bg_col, -1)
            label = f"[{key}] {info['name'][:12]:<12} {counts[key]:>4}"
            cv2.putText(display, label,
                        (panel_x + 8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.38, txt_col, 1)

        total = sum(counts.values())
        cv2.putText(display, f"TOTAL: {total}",
                    (panel_x + 8, 125 + len(MODES) * 28 + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        # ── Bottom bar ─────────────────────────────────────────────────────────
        cv2.rectangle(display, (0, h - 30), (w, h), (12, 12, 12), -1)
        cv2.putText(display, "1:Helmet 2:Vest 3:Goggles 4:Gloves 5:FullPPE 6:BareHands 7:BareFace 0:NoPPE | SPACE:save R:auto Q:quit",
                    (8, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (120, 120, 120), 1)

        cv2.imshow("PPE Dataset Capture", display)
        key_pressed = cv2.waitKey(1) & 0xFF

        if key_pressed == ord("q"):
            break
        elif chr(key_pressed) in MODES:
            mode = chr(key_pressed)
            print(f"  Mode → {MODES[mode]['name']}")
        elif key_pressed == ord("r"):
            auto_capture = not auto_capture
            print(f"  Auto-capture → {'ON' if auto_capture else 'OFF'}")
        elif key_pressed == ord(" "):
            _save(frame, root / MODES[mode]["folder"], MODES[mode]["folder"])
            counts[mode] += 1
            flash = 5
            print(f"  Saved manually → {MODES[mode]['name']}  (total: {counts[mode]})")

    cap.release()
    cv2.destroyAllWindows()

    # Summary
    print()
    print("=" * 50)
    print("  CAPTURE COMPLETE — SUMMARY")
    print("=" * 50)
    for key, info in MODES.items():
        print(f"  {info['name']:<20} : {counts[key]:>4} frames  → {root / info['folder']}")
    print(f"  {'TOTAL':<20} : {sum(counts.values()):>4} frames")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Go to https://app.roboflow.com")
    print("  2. Upload each folder → annotate with correct class label")
    print("  3. no_ppe/ folder → upload with NO bounding boxes (background)")
    print("  4. Export as YOLOv8 format → retrain model")


def _save(frame, folder: Path, prefix: str) -> Path:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    path = folder / f"{prefix}_{ts}.jpg"
    cv2.imwrite(str(path), frame)
    return path


if __name__ == "__main__":
    main()
