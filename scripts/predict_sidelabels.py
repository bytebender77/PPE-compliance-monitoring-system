"""
predict_sidelabels.py — run a YOLO PPE model on a video (or a whole folder of
videos) and draw clean boxes with the class label placed to the SIDE of each
box, with collision avoidance so labels never overlap. Saves one annotated
.mp4 per input clip.

Standalone: needs only `ultralytics` + `opencv` (no pipeline imports), so it
runs anywhere the model trained.

Usage (Windows, venv active):
  python predict_sidelabels.py ^
    --model "C:\\Users\\hp\\Desktop\\far_ppe_v2_training\\far_ppe.v2i.yolov8\\runs\\detect\\far_ppe_1280\\weights\\best.pt" ^
    --source "C:\\Users\\hp\\Desktop\\far_ppe_v2_training\\to_test" ^
    --out "C:\\Users\\hp\\Desktop\\far_ppe_v2_training\\out_labeled" ^
    --imgsz 1280 --conf 0.25
"""

import argparse
import glob
import os

import cv2
from ultralytics import YOLO

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv"}

# BGR colors per class name (distinct, readable)
COLORS = {
    "helmet":      (255, 170, 0),    # cyan-blue
    "safety_vest": (0, 200, 90),     # green
    "safety-vest": (0, 200, 90),
    "goggles":     (0, 180, 255),    # amber
    "gloves":      (200, 100, 255),  # pink
}
DEFAULT_COLOR = (200, 200, 200)


def draw_label_side(frame, box, text, color, placed, font_scale, thick):
    """Draw `text` beside `box`, nudging down to avoid overlap with `placed`."""
    x1, y1, x2, y2 = box
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), base = cv2.getTextSize(text, font, font_scale, thick)
    pad = 5
    label_w = tw + 2 * pad
    label_h = th + base + 2 * pad

    # default: to the RIGHT of the box, aligned to its top
    lx = x2 + 10
    ly = y1
    # if it runs off the right edge, place to the LEFT of the box
    if lx + label_w > frame.shape[1] - 2:
        lx = x1 - label_w - 10
        if lx < 2:
            lx = x2 + 10  # too tight either way: keep right, will clamp below
    lx = max(2, min(lx, frame.shape[1] - label_w - 2))

    rect = [lx, ly, lx + label_w, ly + label_h]

    # collision avoidance: push down until it clears every placed label
    guard = 0
    moved = True
    while moved and guard < 200:
        moved = False
        guard += 1
        for r in placed:
            overlap = not (rect[2] <= r[0] or rect[0] >= r[2] or
                           rect[3] <= r[1] or rect[1] >= r[3])
            if overlap:
                rect[1] = r[3] + 3
                rect[3] = rect[1] + label_h
                moved = True
    # clamp inside frame vertically
    if rect[3] > frame.shape[0] - 2:
        shift = rect[3] - (frame.shape[0] - 2)
        rect[1] -= shift
        rect[3] -= shift
    placed.append(rect)

    # leader line from the box corner to the label
    anchor_x = x2 if rect[0] >= x2 else x1
    cv2.line(frame, (anchor_x, y1), (rect[0] if rect[0] >= x2 else rect[2],
             rect[1] + label_h // 2), color, 1, cv2.LINE_AA)
    # filled background + dark text
    cv2.rectangle(frame, (rect[0], rect[1]), (rect[2], rect[3]), color, -1)
    cv2.putText(frame, text, (rect[0] + pad, rect[3] - pad - base // 2),
                font, font_scale, (0, 0, 0), thick, cv2.LINE_AA)


def process_video(model, path, out_path, imgsz, conf, names):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"[skip] cannot open {path}")
        return
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # scale text/line thickness to the frame size
    font_scale = max(0.5, round(w / 1600, 2))
    box_thick = max(2, w // 900)
    txt_thick = max(1, w // 1400)

    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        n += 1
        res = model.predict(frame, imgsz=imgsz, conf=conf, verbose=False)[0]
        placed = []
        if res.boxes is not None and len(res.boxes):
            # top-to-bottom so labels stack predictably
            boxes = sorted(res.boxes, key=lambda b: float(b.xyxy[0][1]))
            for b in boxes:
                x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
                cls = int(b.cls[0])
                cf = float(b.conf[0])
                name = names.get(cls, str(cls))
                color = COLORS.get(name, DEFAULT_COLOR)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, box_thick)
                draw_label_side(frame, (x1, y1, x2, y2), f"{name} {cf:.2f}",
                                color, placed, font_scale, txt_thick)
        writer.write(frame)
    cap.release()
    writer.release()
    print(f"[done] {os.path.basename(path)} -> {out_path}  ({n} frames)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--source", required=True, help="video file OR folder of videos")
    ap.add_argument("--out", default="out_labeled")
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--conf", type=float, default=0.25)
    args = ap.parse_args()

    model = YOLO(args.model)
    names = model.names  # {id: name} from the model itself — no mismatch

    os.makedirs(args.out, exist_ok=True)
    if os.path.isdir(args.source):
        vids = sorted(p for p in glob.glob(os.path.join(args.source, "*"))
                      if os.path.splitext(p)[1].lower() in VIDEO_EXTS)
    else:
        vids = [args.source]
    if not vids:
        print("No videos found.")
        return

    print(f"Model classes: {names}")
    for v in vids:
        base = os.path.splitext(os.path.basename(v))[0]
        out_path = os.path.join(args.out, base + "_labeled.mp4")
        process_video(model, v, out_path, args.imgsz, args.conf, names)
    print(f"\nAll done. Recordings in: {args.out}")


if __name__ == "__main__":
    main()
