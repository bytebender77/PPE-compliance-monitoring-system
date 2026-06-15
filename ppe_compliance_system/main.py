"""
main.py — Stage 4 entry point
PPE Compliance Monitoring System

Wires together:
  1. VideoSource         — reads frames from webcam / MP4 / RTSP
  2. PersonDetector      — detects persons using COCO YOLOv8n
  3. PPEDetector         — detects helmet / safety_vest / goggles (our model)
  4. ComplianceChecker   — associates PPE with persons, flags violations
  5. AlertEngine         — tracks violation streaks, fires alerts with cooldown
  6. FrameAnnotator      — draws boxes, flash border, streak bar, alert log
  7. FPSCounter          — rolling FPS measurement

PIPELINE PER FRAME
──────────────────
  read → detect persons → detect PPE → check compliance
       → alert engine → annotate → display

ALERT BEHAVIOUR
───────────────
  - Non-compliant for 20 consecutive frames (~0.67 s @ 30 fps) → alert fires
  - Red flash border appears for 1.2 s
  - Screenshot auto-saved to screenshots/
  - Alert log panel shows last 3 alerts (bottom-right corner)
  - Violation streak progress bar on each non-compliant person box
  - Per-worker 60-second cooldown prevents alert spam

Run:
    python -m ppe_compliance_system.main                  # webcam
    python -m ppe_compliance_system.main --source video.mp4
    python -m ppe_compliance_system.main --source rtsp://...
    python -m ppe_compliance_system.main --no-display     # headless

Controls (while window is open):
    Q → quit
    S → save screenshot to screenshots/
    P → pause / unpause
    A → toggle WhatsApp alerts on / off

Model switching:
    --ppe-model models/best.pt          # default 4-class model
    --ppe-model models/best_cctv.pt     # CCTV fine-tuned (20m detection)
"""

import argparse
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

from .inference_engine.utils.video_source import VideoSource
from .inference_engine.detectors.person_detector import PersonDetector
from .inference_engine.detectors.ppe_detector import PPEDetector
from .inference_engine.detectors.ppe_smoother import PPESmoother
from .inference_engine.compliance.checker import ComplianceChecker
from .inference_engine.alerts.engine import AlertEngine
from .inference_engine.utils.display import FrameAnnotator
from .inference_engine.utils.fps_counter import FPSCounter
from .notifications.whatsapp import notifier_from_env
from .database.logger import ViolationLogger
from .config.settings import Settings

# Load .env file if present — use explicit path so it works regardless of CWD
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path, override=True)
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PPE Compliance Monitoring System — Stage 4 (Alert Engine)"
    )
    parser.add_argument(
        "--source", default="0",
        help="Video source: webcam index (0), MP4 path, or RTSP URL.",
    )
    parser.add_argument(
        "--conf", type=float, default=None,
        help="Person detection confidence threshold (overrides config).",
    )
    parser.add_argument(
        "--ppe-conf", type=float, default=None,
        help="PPE detection confidence threshold (overrides config).",
    )
    parser.add_argument(
        "--ppe-imgsz", type=int, default=1280, dest="ppe_imgsz",
        help="PPE inference resolution (default 1280 — gives the model enough "
             "pixels on the jacket for reliable live detection). Lower to 640 "
             "for max speed on weak hardware (less reliable vest detection).",
    )
    parser.add_argument(
        "--no-display", action="store_true",
        help="Run headless — no OpenCV window (useful for servers).",
    )
    parser.add_argument(
        "--device", default=None,
        help="Inference device: cpu / cuda / mps (overrides config).",
    )
    parser.add_argument(
        "--alert-frames", type=int, default=None,
        help="Consecutive non-compliant frames before alert fires (overrides config).",
    )
    parser.add_argument(
        "--alert-cooldown", type=int, default=None,
        help="Seconds between repeated alerts per worker (overrides config).",
    )
    parser.add_argument(
        "--no-alerts", action="store_true",
        help="Mute WhatsApp alerts on startup (violations still logged to DB).",
    )
    parser.add_argument(
        "--zoom", action="store_true",
        help="Crop-and-zoom mode: run PPE detector on each person crop. "
             "Improves detection at long range (e.g. 20m CCTV cameras).",
    )
    parser.add_argument(
        "--ppe-model", default=None, dest="ppe_model",
        help="Path to PPE model weights (overrides config). "
             "E.g. models/best_cctv.pt for the CCTV fine-tuned model.",
    )
    parser.add_argument(
        "--save-video", default=None, dest="save_video",
        help="Save annotated output to this path. E.g. output/vestp1_annotated.mp4",
    )
    parser.add_argument(
        "--frame-skip", type=int, default=3, dest="frame_skip",
        help="Run inference every N frames (default 3). Higher = faster but less smooth. "
             "The PPE smoother holds detections ~1.5s so higher skip stays stable.",
    )
    return parser.parse_args()


def run_pipeline(
    source_arg: str,
    camera_label: str,
    cfg: "Settings",
    no_display: bool = True,
    conf_threshold: float = None,
    ppe_conf_threshold: float = None,
    device: str = None,
    alert_frames: int = None,
    alert_cooldown: int = None,
    alerts_muted: bool = False,
    zoom_mode: bool = False,
    ppe_model: str = None,
    save_video: str = None,
    frame_skip: int = 3,
    ppe_imgsz: int = 1280,
) -> None:
    """
    Full PPE pipeline for ONE camera source.

    Extracted from main() so multi_main.py can call it directly in worker
    processes without going through argparse.
    """
    conf_threshold     = conf_threshold     or cfg.CONFIDENCE_THRESHOLD
    ppe_conf_threshold = ppe_conf_threshold or cfg.PPE_CONF_THRESHOLD
    device             = device             or cfg.DEVICE
    alert_frames       = alert_frames       or cfg.ALERT_FRAME_THRESHOLD
    alert_cooldown     = alert_cooldown     or cfg.ALERT_COOLDOWN_SECONDS
    ppe_model_path     = ppe_model          or cfg.PPE_MODEL_PATH
    use_half           = (device == "cuda")   # FP16 on CUDA → ~2× speed

    if zoom_mode:
        log.info(f"[{camera_label}] Zoom mode ON — crop-and-zoom PPE detection (long-range camera)")

    log.info(f"[{camera_label}] Starting PPE pipeline")
    log.info(f"  Source          : {source_arg}")
    log.info(f"  Person model    : {cfg.MODEL_PATH}  conf={conf_threshold}")
    log.info(f"  PPE model       : {ppe_model_path}  conf={ppe_conf_threshold}")
    log.info(f"  Required PPE    : {cfg.REQUIRED_PPE}")
    log.info(f"  Device          : {device}  FP16={use_half}")
    log.info(f"  Alert threshold : {alert_frames} frames")
    log.info(f"  Alert cooldown  : {alert_cooldown}s")

    # ── 1. Video source ────────────────────────────────────────────────────────
    source = VideoSource(source_arg)
    if not source.is_open():
        log.error(f"[{camera_label}] Could not open video source: {source_arg}")
        return

    # ── 1b. Optional video writer ──────────────────────────────────────────────
    video_writer = None
    if save_video:
        import cv2 as _cv2
        save_path = Path(save_video)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        # Read first frame to get dimensions, then reopen
        _test = source.read()
        if _test is not None:
            h, w = _test.shape[:2]
            fourcc = _cv2.VideoWriter_fourcc(*"mp4v")
            video_writer = _cv2.VideoWriter(str(save_path), fourcc, 25.0, (w, h))
            log.info(f"[{camera_label}] Recording output → {save_path}  ({w}x{h} @ 25fps)")
            # Re-open source since we consumed a frame
            source.release()
            source = VideoSource(source_arg)
        else:
            log.warning("Could not read first frame — video saving disabled.")

    # ── 2–3. Detectors ────────────────────────────────────────────────────────
    person_detector = PersonDetector(
        model_path=cfg.MODEL_PATH,
        conf_threshold=conf_threshold,
        device=device,
        half=use_half,
    )
    ppe_detector = PPEDetector(
        model_path=ppe_model_path,
        conf_threshold=ppe_conf_threshold,
        device=device,
        half=use_half,
        imgsz=ppe_imgsz,
    )

    # PPE detection persistence — bridges intermittent live detections so the
    # vest box and compliance status don't flicker (~1.5 s hold at 30 fps).
    ppe_smoother = PPESmoother(ttl_frames=45)

    # ── 4–5. Compliance + alert ────────────────────────────────────────────────
    compliance_checker = ComplianceChecker(
        required_ppe=cfg.REQUIRED_PPE,
        association_thresh=cfg.PPE_ASSOCIATION_THRESH,
    )
    alert_engine = AlertEngine(
        frame_threshold=alert_frames,
        cooldown_seconds=alert_cooldown,
    )

    # ── 6. WhatsApp notifier ───────────────────────────────────────────────────
    whatsapp = notifier_from_env(camera_label=camera_label)
    if whatsapp:
        whatsapp.send_test()

    # ── 7. SQLite logger ───────────────────────────────────────────────────────
    db_logger = ViolationLogger(
        db_path=str(Path(cfg.LOG_DIR) / "violations.db"),
        camera=camera_label,
    )
    db_logger.open()

    # ── 8. Display helpers ─────────────────────────────────────────────────────
    annotator   = FrameAnnotator(cfg)
    fps_counter = FPSCounter()
    screenshots = Path(cfg.SCREENSHOTS_DIR)
    screenshots.mkdir(exist_ok=True)

    log.info(f"[{camera_label}] Warming up models…")
    person_detector.warmup(iterations=2)
    ppe_detector.warmup(iterations=2)
    log.info(f"[{camera_label}] Pipeline ready.  Q=quit  S=screenshot  P=pause  A=toggle alerts")

    paused         = False
    annotated      = None
    alerts_enabled = not alerts_muted   # toggle with A key; --no-alerts starts muted
    _frame_idx     = 0

    try:
        while True:
            if not paused:
                frame = source.read()
                if frame is None:
                    log.info(f"[{camera_label}] Source exhausted. Exiting.")
                    break

                _frame_idx += 1
                # Skip inference on intermediate frames — display last annotated frame
                # to keep window responsive without running YOLO on every frame.
                if frame_skip > 1 and (_frame_idx % frame_skip != 0):
                    if not no_display and annotated is not None:
                        import cv2
                        cv2.imshow(f"PPE Monitor — {camera_label}", annotated)
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord("q"):
                            break
                    continue

                persons    = person_detector.detect(frame)
                # Crop-and-zoom mode: run PPE on each person crop
                # for long-range cameras (e.g. 20m CCTV). Enabled with --zoom.
                person_boxes = [p["bbox"] for p in persons] if zoom_mode else None
                ppe_items  = ppe_detector.detect(frame, person_boxes=person_boxes)
                ppe_items  = ppe_smoother.update(ppe_items)   # persist intermittent hits
                persons    = compliance_checker.check(persons, ppe_items)
                new_alerts = alert_engine.update(persons)

                if new_alerts and annotated is not None:
                    for a in new_alerts:
                        log.warning(f"[{camera_label}] ALERT: {a.summary}")
                        shot_path = _save_screenshot(annotated, screenshots, prefix="alert")
                        db_logger.log_violation(a, screenshot_path=shot_path)
                        if whatsapp and alerts_enabled:
                            whatsapp.send_alert(a, screenshot_path=shot_path)
                        elif whatsapp and not alerts_enabled:
                            log.info(f"[{camera_label}] WhatsApp alerts are muted — violation logged only")

                fps = fps_counter.update()
                streaks = {
                    p["track_id"]: alert_engine.streak_for(p["track_id"])
                    for p in persons if p.get("track_id") is not None
                }
                annotated = annotator.draw(
                    frame           = frame,
                    persons         = persons,
                    ppe_items       = ppe_items,
                    fps             = fps,
                    new_alerts      = new_alerts,
                    recent_alerts   = alert_engine.recent_alerts,
                    streaks         = streaks,
                    alert_threshold = alert_frames,
                    alerts_enabled  = alerts_enabled,
                )

            # Write annotated frame to output video if recording
            if video_writer is not None and annotated is not None:
                video_writer.write(annotated)

            if not no_display and annotated is not None:
                import cv2
                cv2.imshow(f"PPE Monitor — {camera_label}", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    log.info(f"[{camera_label}] Q pressed — shutting down.")
                    break
                elif key == ord("s"):
                    _save_screenshot(annotated, screenshots)
                elif key == ord("p"):
                    paused = not paused
                    log.info("Paused." if paused else "Resumed.")
                elif key == ord("a"):
                    alerts_enabled = not alerts_enabled
                    state = "ON" if alerts_enabled else "OFF (muted)"
                    log.info(f"[{camera_label}] WhatsApp alerts toggled → {state}")

    except KeyboardInterrupt:
        log.info(f"[{camera_label}] Interrupted.")

    # ── Summary ────────────────────────────────────────────────────────────────
    total = alert_engine.total_alerts()
    log.info(f"[{camera_label}] Session done — {total} alert(s) fired.")
    stats = db_logger.session_stats()
    if stats.get("total"):
        log.info(
            f"[{camera_label}] DB — total={stats['total']}  "
            f"critical={stats['critical']}  warnings={stats['warnings']}  "
            f"no_helmet={stats['no_helmet']}  no_vest={stats['no_vest']}"
        )

    db_logger.close()
    source.release()
    if video_writer is not None:
        video_writer.release()
        log.info(f"[{camera_label}] Saved annotated video → {save_video}")
    if not no_display:
        import cv2
        cv2.destroyAllWindows()
    log.info(f"[{camera_label}] Shutdown complete.")


def main() -> None:
    args         = parse_args()
    cfg          = Settings()
    camera_label = os.getenv("WHATSAPP_CAMERA_LABEL", args.source)

    run_pipeline(
        source_arg         = args.source,
        camera_label       = camera_label,
        cfg                = cfg,
        no_display         = args.no_display,
        conf_threshold     = args.conf,
        ppe_conf_threshold = args.ppe_conf,
        device             = args.device,
        alert_frames       = args.alert_frames,
        alert_cooldown     = args.alert_cooldown,
        alerts_muted       = args.no_alerts,
        zoom_mode          = args.zoom,
        ppe_model          = args.ppe_model,
        save_video         = args.save_video,
        frame_skip         = args.frame_skip,
        ppe_imgsz          = args.ppe_imgsz,
    )


def _save_screenshot(
    frame,
    screenshots_dir: Path,
    prefix: str = "frame",
) -> Path:
    """Save annotated frame as a timestamped PNG. Returns the saved path."""
    import cv2
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    path = screenshots_dir / f"{prefix}_{ts}.png"
    cv2.imwrite(str(path), frame)
    logging.getLogger(__name__).info(f"Screenshot saved → {path}")
    return path


if __name__ == "__main__":
    main()
