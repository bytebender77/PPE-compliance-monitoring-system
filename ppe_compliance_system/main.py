"""
main.py — Stage 1 MVP entry point
PPE Compliance Monitoring System

This is the top-level runner. It wires together:
  1. A video source (webcam / MP4 / RTSP)
  2. The YOLOv8 person detector
  3. The display / annotation layer

Why is this a separate file from the detector?
  → main.py is "glue code". The detector knows nothing about windows or
    display — that separation lets us swap the display for a FastAPI
    WebSocket stream in Stage 3 without touching the detector at all.

Run:
    python main.py                    # webcam (device 0)
    python main.py --source 0         # webcam explicit
    python main.py --source video.mp4 # MP4 file
    python main.py --source rtsp://.. # RTSP stream (Stage 3+)

Controls (while window is open):
    Q  →  quit
    S  →  save screenshot to screenshots/
    P  →  pause / unpause
"""

import argparse
import sys
import logging
from pathlib import Path

# ── local imports ──────────────────────────────────────────────────────────────
from .inference_engine.utils.video_source import VideoSource
from .inference_engine.detectors.person_detector import PersonDetector
from .inference_engine.utils.display import FrameAnnotator
from .inference_engine.utils.fps_counter import FPSCounter
from .config.settings import Settings

# ── logging ────────────────────────────────────────────────────────────────────
# Configure once here at the top level; every other module does
# `logging.getLogger(__name__)` and inherits this configuration.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Keeping argument parsing in its own function makes it trivially testable
    (call parse_args(['--source', '0'])) and keeps main() clean.
    """
    parser = argparse.ArgumentParser(
        description="PPE Compliance Monitoring System — Stage 1 MVP"
    )
    parser.add_argument(
        "--source",
        default="0",                # "0" → webcam index 0
        help="Video source: webcam index (0), MP4 path, or RTSP URL",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=None,               # None → use value from settings.py
        help="Detection confidence threshold (overrides config)",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Run headless (no OpenCV window) — useful for server testing",
    )
    return parser.parse_args()


def main() -> None:
    """
    Main pipeline loop.

    The loop is intentionally simple at this stage:
        read frame → detect → annotate → display → repeat

    Later stages will insert tracking, compliance logic, and alert
    orchestration BETWEEN detect and annotate without changing this loop's
    structure — they're just additional function calls on the same frame.
    """
    args = parse_args()
    cfg  = Settings()               # load config/settings.py defaults

    # Allow CLI to override confidence threshold
    conf_threshold = args.conf if args.conf is not None else cfg.CONFIDENCE_THRESHOLD

    log.info("Starting PPE Compliance Monitoring System — Stage 1 MVP")
    log.info(f"  Source            : {args.source}")
    log.info(f"  Confidence thresh : {conf_threshold}")
    log.info(f"  Model             : {cfg.MODEL_PATH}")

    # ── 1. Video source ────────────────────────────────────────────────────────
    # VideoSource wraps OpenCV's VideoCapture. The string "0" is converted to
    # integer 0 inside VideoSource so we always pass a plain string here.
    source = VideoSource(args.source)
    if not source.is_open():
        log.error("Could not open video source. Check device index or file path.")
        sys.exit(1)

    # ── 2. Detector ────────────────────────────────────────────────────────────
    # PersonDetector loads YOLOv8 and exposes a single .detect(frame) method.
    # This is the ONLY class that knows about YOLO — the rest of the system
    # works with plain Python dicts (detection results).
    detector = PersonDetector(
        model_path=cfg.MODEL_PATH,
        conf_threshold=conf_threshold,
        device=cfg.DEVICE,
    )

    # ── 3. Annotation / display ────────────────────────────────────────────────
    annotator = FrameAnnotator(cfg)
    fps_counter = FPSCounter()

    # Ensure screenshots directory exists for the 'S' key shortcut
    Path("screenshots").mkdir(exist_ok=True)

    log.info("Pipeline ready. Press Q to quit, S to save screenshot, P to pause.")

    paused = False

    # ── Main loop ──────────────────────────────────────────────────────────────
    while True:
        if not paused:
            frame = source.read()
            if frame is None:
                # End of MP4 file or stream dropped
                log.info("Video source exhausted or dropped. Exiting.")
                break

            # ── Detect ────────────────────────────────────────────────────────
            # detections is a list of dicts:
            # [{"bbox": [x1,y1,x2,y2], "confidence": 0.87, "class_id": 0, "class_name": "person"}, ...]
            #
            # STAGE 2 will add tracking IDs to each dict here.
            # STAGE 3 will add PPE association results here.
            # The dict structure is intentionally open so future stages can
            # enrich it without breaking existing code.
            detections = detector.detect(frame)

            # ── Update FPS ────────────────────────────────────────────────────
            fps = fps_counter.update()

            # ── Annotate frame ────────────────────────────────────────────────
            # annotator draws bboxes, labels, confidence, FPS, and person count.
            # All drawing logic lives in display.py — none in detector.py.
            # Separation of concerns: detector detects, annotator draws.
            annotated = annotator.draw(frame, detections, fps)

        # ── Display ───────────────────────────────────────────────────────────
        if not args.no_display:
            import cv2
            cv2.imshow("PPE Monitor — Stage 1", annotated)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                log.info("Q pressed — shutting down.")
                break
            elif key == ord("s"):
                _save_screenshot(annotated)
            elif key == ord("p"):
                paused = not paused
                log.info("Paused." if paused else "Resumed.")

    # ── Cleanup ────────────────────────────────────────────────────────────────
    source.release()
    if not args.no_display:
        import cv2
        cv2.destroyAllWindows()
    log.info("Shutdown complete.")


def _save_screenshot(frame) -> None:
    """Save current annotated frame as a timestamped PNG.

    Why a standalone function? So Stage 5 (alert logger) can call this same
    function when a violation is triggered — no code duplication.
    """
    import cv2
    from datetime import datetime

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]   # ms precision
    path = Path("screenshots") / f"frame_{ts}.png"
    cv2.imwrite(str(path), frame)
    logging.getLogger(__name__).info(f"Screenshot saved → {path}")


if __name__ == "__main__":
    main()
