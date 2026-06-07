"""
multi_main.py — Stage 7: Multi-camera orchestrator

ARCHITECTURE
────────────
  Reads cameras.yaml → spawns one worker Process per camera → each runs the
  full PPE pipeline independently.

  ┌─────────────────────────────────────────────────────────┐
  │  multi_main.py (orchestrator — parent process)          │
  │    ├── Process: Gate-1  →  VideoSource(0)               │
  │    ├── Process: Gate-2  →  VideoSource("rtsp://…")      │
  │    └── Process: Bay-3   →  VideoSource("rtsp://…")      │
  │         ↓ (all processes)                               │
  │         logs/violations.db  (SQLite WAL — shared)       │
  │         screenshots/        (shared directory)          │
  └─────────────────────────────────────────────────────────┘

  The dashboard (python -m ppe_compliance_system.api) reads from the same DB
  and shows violations from ALL cameras in one unified view.

WHY MULTIPROCESSING (not threads)?
  - Python GIL prevents true parallel CPU use in threads
  - Each camera needs its own YOLO model instance in GPU memory
  - Crash in one camera worker doesn't kill the others
  - Each process gets its own memory — no shared-state bugs

RUN
───
  python -m ppe_compliance_system.multi_main
  python -m ppe_compliance_system.multi_main --config cameras.yaml
  python -m ppe_compliance_system.multi_main --config cameras.yaml --list

Ctrl+C → graceful shutdown of all workers.
"""

import argparse
import logging
import multiprocessing
import signal
import sys
import time
from pathlib import Path
from typing import List

try:
    import yaml
except ImportError:
    raise SystemExit(
        "PyYAML not installed. Run:  pip install pyyaml"
    )

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path, override=True)
except ImportError:
    pass

from .config.settings import Settings
from .main import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_CONFIG = Path("cameras.yaml")


# ── Worker entry point ────────────────────────────────────────────────────────

def _camera_worker(camera_cfg: dict, global_cfg: dict) -> None:
    """
    Runs in its own process — complete isolation from other cameras.

    Args:
        camera_cfg:  Per-camera overrides from cameras.yaml.
        global_cfg:  Global defaults from cameras.yaml.
    """
    # Re-initialise logging in the child process
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    label  = camera_cfg.get("label",  camera_cfg.get("source", "unknown"))
    source = str(camera_cfg.get("source", "0"))

    # Per-camera overrides take priority over global defaults
    def _get(key, default=None):
        return camera_cfg.get(key, global_cfg.get(key, default))

    cfg = Settings()
    # Override Settings fields from YAML
    cfg.LOG_DIR         = _get("db_path",        "logs/violations.db").rsplit("/", 1)[0]
    cfg.SCREENSHOTS_DIR = _get("screenshots_dir", "screenshots")

    required_ppe_str = _get("required_ppe", "helmet,safety_vest")
    cfg.REQUIRED_PPE = [p.strip() for p in required_ppe_str.split(",")]

    try:
        run_pipeline(
            source_arg         = source,
            camera_label       = label,
            cfg                = cfg,
            no_display         = bool(_get("no_display", True)),
            conf_threshold     = float(_get("conf",          cfg.CONFIDENCE_THRESHOLD)),
            ppe_conf_threshold = float(_get("ppe_conf",      cfg.PPE_CONF_THRESHOLD)),
            device             = str(_get("device",          cfg.DEVICE)),
            alert_frames       = int(_get("alert_frames",    cfg.ALERT_FRAME_THRESHOLD)),
            alert_cooldown     = int(_get("alert_cooldown",  cfg.ALERT_COOLDOWN_SECONDS)),
        )
    except Exception as exc:
        log.error(f"[{label}] Worker crashed: {exc}", exc_info=True)


# ── Orchestrator ──────────────────────────────────────────────────────────────

def load_config(config_path: Path) -> dict:
    """Load and validate cameras.yaml."""
    if not config_path.exists():
        raise FileNotFoundError(
            f"Camera config not found: {config_path}\n"
            f"Create one based on the example at cameras.yaml"
        )
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    cameras = data.get("cameras", [])
    if not cameras:
        raise ValueError("cameras.yaml must have at least one entry under 'cameras:'")

    for i, cam in enumerate(cameras):
        if "source" not in cam:
            raise ValueError(f"Camera #{i+1} is missing required field 'source'")
        if "label" not in cam:
            cam["label"] = f"Camera-{i+1}"

    return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PPE Compliance — multi-camera orchestrator"
    )
    parser.add_argument(
        "--config", default=str(DEFAULT_CONFIG),
        help=f"Path to cameras.yaml (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Print configured cameras and exit",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    try:
        config = load_config(config_path)
    except (FileNotFoundError, ValueError) as e:
        log.error(str(e))
        sys.exit(1)

    global_cfg  = config.get("global", {})
    cameras_cfg = config["cameras"]

    if args.list:
        print(f"\nLoaded {len(cameras_cfg)} camera(s) from {config_path}:\n")
        for i, cam in enumerate(cameras_cfg, 1):
            print(f"  [{i}]  {cam['label']:<30}  source={cam['source']}")
        print()
        return

    log.info(f"Starting multi-camera PPE system — {len(cameras_cfg)} camera(s)")
    log.info(f"  Config : {config_path}")
    log.info(f"  DB     : {global_cfg.get('db_path', 'logs/violations.db')}")
    for cam in cameras_cfg:
        log.info(f"  Camera : [{cam['label']}] source={cam['source']}")

    # ── Spawn one process per camera ───────────────────────────────────────────
    # Use "spawn" start method for full process isolation (required on macOS)
    ctx = multiprocessing.get_context("spawn")
    processes: List[multiprocessing.Process] = []

    for cam_cfg in cameras_cfg:
        p = ctx.Process(
            target=_camera_worker,
            args=(cam_cfg, global_cfg),
            name=cam_cfg["label"],
            daemon=True,   # workers die if orchestrator dies
        )
        p.start()
        processes.append(p)
        log.info(f"Spawned worker PID={p.pid}  [{cam_cfg['label']}]")
        time.sleep(0.5)   # stagger starts so model downloads don't overlap

    log.info(f"All {len(processes)} worker(s) running.  Ctrl+C to stop all.")

    # ── Monitor workers until Ctrl+C ───────────────────────────────────────────
    def _shutdown(sig, frame):
        log.info("Shutdown signal received — stopping all workers…")
        for p in processes:
            if p.is_alive():
                p.terminate()
        for p in processes:
            p.join(timeout=5)
        log.info("All workers stopped. Exiting.")
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Re-spawn crashed workers automatically
    while True:
        time.sleep(10)
        for i, p in enumerate(processes):
            if not p.is_alive():
                cam_cfg = cameras_cfg[i]
                log.warning(
                    f"Worker [{cam_cfg['label']}] (PID={p.pid}) exited "
                    f"with code {p.exitcode}. Restarting in 5s…"
                )
                time.sleep(5)
                new_p = ctx.Process(
                    target=_camera_worker,
                    args=(cam_cfg, global_cfg),
                    name=cam_cfg["label"],
                    daemon=True,
                )
                new_p.start()
                processes[i] = new_p
                log.info(f"Restarted [{cam_cfg['label']}] PID={new_p.pid}")


if __name__ == "__main__":
    main()
