"""
run.py — entry point for the standalone PPE tracking pipeline.

    detect (every frame) → TRACK (ByteTrack/BoT-SORT) → associate PPE → per-track
    hysteresis state machine → render stable boxes + debounced status → alerts

LIVE sources (webcam / RTSP) use a threaded capture + a dedicated inference
thread so the display stays smooth and low-latency. FILE sources are processed
synchronously, every frame in order, so tracking is continuous and the saved
output keeps every frame.

Examples
────────
  # Webcam on a GPU box, every frame, ByteTrack
  python run.py --source 0 --device cuda

  # Far CCTV-style clip, BoT-SORT for occlusion, save annotated output
  python run.py --source ../new/far.MOV --tracker botsort --save out.mp4

  # Feed a CCTV-trained PPE model later
  python run.py --source rtsp://... --ppe-model /path/cctv_best.pt --device cuda

Live tuning keys (while the window is focused)
  q quit   s screenshot
  [ / ]  N  (violation frames ↓/↑)      - / =  K (clear frames ↓/↑)
  , / .  presence ratio ↓/↑
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# make `pipeline` importable whether run as `python run.py` or `-m`
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2

from config import Config
from pipeline.video_stream import ThreadedCamera, is_live_source, resolve_source
from pipeline.person_tracker import PersonTracker
from pipeline.ppe_detector import PPEDetector
from pipeline.association import associate
from pipeline.tracking_state import WorkerTrackManager
from pipeline.alerts import AlertManager
from pipeline.renderer import Renderer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("run")


def auto_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Standalone PPE tracking pipeline (ByteTrack/BoT-SORT)")
    p.add_argument("--source", default="0", help="webcam index, file path, or RTSP/HTTP URL")
    p.add_argument("--device", default=None, help="cpu | cuda | mps (default: auto)")
    p.add_argument("--ppe-model", default=None, help="path to PPE weights (default: ../models/best.pt)")
    p.add_argument("--person-model", default=None, help="person/tracker weights (default: yolov8n.pt)")
    p.add_argument("--tracker", default=None, choices=["bytetrack", "botsort"])
    p.add_argument("--track-buffer", type=int, default=None, help="frames a lost track is kept alive")
    p.add_argument("--ppe-imgsz", type=int, default=None)
    p.add_argument("--ppe-conf", type=float, default=None)
    p.add_argument("--person-conf", type=float, default=None)
    p.add_argument("--required", default=None, help="comma-separated required PPE, e.g. helmet,safety_vest")
    p.add_argument("--window", type=int, default=None, help="M — rolling window length")
    p.add_argument("--violation-frames", type=int, default=None, help="N — frames to flag a violation")
    p.add_argument("--clear-frames", type=int, default=None, help="K — frames to clear a violation")
    p.add_argument("--presence-ratio", type=float, default=None)
    p.add_argument("--no-display", action="store_true", help="headless (no window)")
    p.add_argument("--save", default=None, help="write annotated output to this path")
    p.add_argument("--max-frames", type=int, default=None, help="stop after N processed frames (testing)")
    return p.parse_args()


def build_config(args) -> Config:
    cfg = Config()
    cfg.device = args.device or auto_device()
    cfg.half = (cfg.device == "cuda")
    if args.ppe_model:     cfg.ppe_model = args.ppe_model
    if args.person_model:  cfg.person_model = args.person_model
    if args.tracker:       cfg.tracker = args.tracker
    if args.track_buffer is not None:    cfg.track_buffer = args.track_buffer
    if args.ppe_imgsz is not None:       cfg.ppe_imgsz = args.ppe_imgsz
    if args.ppe_conf is not None:        cfg.ppe_conf = args.ppe_conf
    if args.person_conf is not None:     cfg.person_conf = args.person_conf
    if args.required:      cfg.required_ppe = [s.strip() for s in args.required.split(",") if s.strip()]
    if args.window is not None:          cfg.window_size = args.window
    if args.violation_frames is not None: cfg.violation_frames = args.violation_frames
    if args.clear_frames is not None:    cfg.clear_frames = args.clear_frames
    if args.presence_ratio is not None:  cfg.presence_ratio = args.presence_ratio
    return cfg


def make_hud(cfg, stats, fps) -> str:
    return (
        f"{cfg.tracker} buf={cfg.track_buffer} | "
        f"tracked={stats['tracked']} ok={stats['compliant']} VIOL={stats['violation']} | "
        f"N={cfg.violation_frames} K={cfg.clear_frames} M={cfg.window_size} "
        f"pres={cfg.presence_ratio:.2f} | {fps:.1f} fps"
    )


def handle_key(key, cfg, annotated, alerts) -> bool:
    """Return False to quit. Live-tune thresholds on the shared cfg."""
    if key in (ord("q"), 27):
        return False
    elif key == ord("s") and annotated is not None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = str(Path(cfg.screenshots_dir) / f"snap_{ts}.jpg")
        cv2.imwrite(path, annotated)
        log.info(f"screenshot → {path}")
    elif key == ord("["):
        cfg.violation_frames = max(1, cfg.violation_frames - 1); log.info(f"N={cfg.violation_frames}")
    elif key == ord("]"):
        cfg.violation_frames += 1; log.info(f"N={cfg.violation_frames}")
    elif key == ord("-"):
        cfg.clear_frames = max(1, cfg.clear_frames - 1); log.info(f"K={cfg.clear_frames}")
    elif key == ord("="):
        cfg.clear_frames += 1; log.info(f"K={cfg.clear_frames}")
    elif key == ord(","):
        cfg.presence_ratio = max(0.05, round(cfg.presence_ratio - 0.05, 2)); log.info(f"presence={cfg.presence_ratio}")
    elif key == ord("."):
        cfg.presence_ratio = min(1.0, round(cfg.presence_ratio + 0.05, 2)); log.info(f"presence={cfg.presence_ratio}")
    return True


def main() -> None:
    args = parse_args()
    cfg = build_config(args)
    log.info(f"Config | {cfg.summary()}")

    tracker = PersonTracker(cfg)
    ppe_det = PPEDetector(cfg)
    manager = WorkerTrackManager(cfg)
    alerts  = AlertManager(cfg)
    renderer = Renderer(cfg)

    log.info("Warming up PPE model…")
    ppe_det.warmup(1)

    def process_frame(frame, idx):
        persons = tracker.update(frame)
        ppe = ppe_det.detect(frame)
        per_track = associate(persons, ppe, cfg.association_overlap)
        manager.update(persons, per_track, idx)

    writer = None
    if args.save:
        Path(args.save).parent.mkdir(parents=True, exist_ok=True)

    # ── frame-rate meter (EMA) ────────────────────────────────────────────────
    _last = [time.time()]
    _fps = [0.0]
    def tick():
        now = time.time(); dt = now - _last[0]; _last[0] = now
        inst = 1.0 / dt if dt > 0 else 0.0
        _fps[0] = inst if _fps[0] == 0 else 0.9 * _fps[0] + 0.1 * inst
        return _fps[0]

    live = is_live_source(args.source)
    processed = 0

    try:
        if live:
            processed = _run_live(args, cfg, tracker, ppe_det, manager, alerts,
                                  renderer, process_frame, tick, make_hud)
        else:
            processed = _run_file(args, cfg, manager, alerts, renderer,
                                  process_frame, tick, make_hud)
    except KeyboardInterrupt:
        log.info("Interrupted.")

    log.info(f"Done. processed={processed} frames | alerts fired={alerts.total} | {manager.stats()}")
    if not args.no_display:
        cv2.destroyAllWindows()


def _open_writer(path, frame):
    h, w = frame.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(path, fourcc, 25.0, (w, h))


def _run_file(args, cfg, manager, alerts, renderer, process_frame, tick, make_hud) -> int:
    cap = cv2.VideoCapture(resolve_source(args.source))
    if not cap.isOpened():
        log.error(f"Could not open source: {args.source}")
        return 0
    writer = None
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx += 1
        process_frame(frame, idx)
        workers = manager.snapshot()
        events = manager.drain_events()
        fps = tick()
        annotated = renderer.draw(frame, workers, make_hud(cfg, manager.stats(), fps))
        alerts.handle(events, annotated)

        if args.save:
            if writer is None:
                writer = _open_writer(args.save, annotated)
            writer.write(annotated)
        if not args.no_display:
            cv2.imshow("PPE Tracking", annotated)
            if not handle_key(cv2.waitKey(1) & 0xFF, cfg, annotated, alerts):
                break
        if args.max_frames and idx >= args.max_frames:
            break

    cap.release()
    if writer is not None:
        writer.release()
        log.info(f"saved → {args.save}")
    return idx


def _run_live(args, cfg, tracker, ppe_det, manager, alerts, renderer,
              process_frame, tick, make_hud) -> int:
    import threading
    cam = ThreadedCamera(args.source)
    if not cam.is_open():
        log.error(f"Could not open live source: {args.source}")
        return 0
    cam.start()

    state = {"running": True, "processed": 0}

    def infer_loop():
        last_seq = -1
        while state["running"]:
            seq, frame = cam.read()
            if frame is None:
                if cam.ended:
                    break
                time.sleep(0.003); continue
            if seq == last_seq:
                time.sleep(0.002); continue
            last_seq = seq
            process_frame(frame, seq)
            state["processed"] += 1

    worker = threading.Thread(target=infer_loop, daemon=True)
    worker.start()
    log.info("Live threaded pipeline running (capture + inference threads).")

    writer = None
    try:
        while True:
            seq, frame = cam.read()
            if frame is None:
                if cam.ended:
                    break
                time.sleep(0.005); continue
            workers = manager.snapshot()
            events = manager.drain_events()
            fps = tick()
            annotated = renderer.draw(frame, workers, make_hud(cfg, manager.stats(), fps))
            alerts.handle(events, annotated)

            if args.save:
                if writer is None:
                    writer = _open_writer(args.save, annotated)
                writer.write(annotated)
            if not args.no_display:
                cv2.imshow("PPE Tracking", annotated)
                if not handle_key(cv2.waitKey(1) & 0xFF, cfg, annotated, alerts):
                    break
            if args.max_frames and state["processed"] >= args.max_frames:
                break
    finally:
        state["running"] = False
        worker.join(timeout=2.0)
        cam.release()
        if writer is not None:
            writer.release()
            log.info(f"saved → {args.save}")
    return state["processed"]


if __name__ == "__main__":
    main()
