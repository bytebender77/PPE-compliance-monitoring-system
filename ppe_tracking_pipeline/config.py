"""
config.py — central configuration for the tracking pipeline.

Every tunable lives here so the pipeline behaviour is fully described by one
object. run.py builds a Config, optionally overrides fields from the CLI, and
threads the SAME instance through every component — so values changed live at
runtime (the N-of-M compliance window, presence ratio) propagate immediately.

This folder is self-contained: it imports nothing from ppe_compliance_system.
Copy the whole `ppe_tracking_pipeline/` directory to another machine and run.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent   # used only to locate the default PPE weights


@dataclass
class Config:
    # ── Models ───────────────────────────────────────────────────────────────
    # Person detector is run in TRACK mode (ByteTrack/BoT-SORT) → persistent IDs.
    person_model: str = "yolov8n.pt"                      # COCO; class 0 = person
    # PPE detector is run in PREDICT mode and associated to tracks by IoU.
    ppe_model: str = str(REPO / "models" / "best.pt")     # custom 4-class model
    device: str = "cpu"                                    # cpu | cuda | mps
    half: bool = False                                     # FP16 (auto on cuda)

    # ── Detection thresholds ──────────────────────────────────────────────────
    person_conf: float = 0.30
    person_imgsz: int = 640
    ppe_conf: float = 0.30
    ppe_imgsz: int = 1280            # high-res: small/!far PPE needs the pixels

    # ── Tracking ──────────────────────────────────────────────────────────────
    tracker: str = "bytetrack"       # bytetrack | botsort (botsort for occlusion)
    track_buffer: int = 30           # frames a LOST track is kept alive (~1s @30fps)
    person_class_id: int = 0         # COCO person

    # ── Per-track compliance state machine ────────────────────────────────────
    required_ppe: List[str] = field(default_factory=lambda: ["helmet", "safety_vest"])
    window_size: int = 15            # M — rolling window length (frames)
    presence_ratio: float = 0.40     # a PPE class counts as "on" if seen in ≥ this
                                     #   fraction of the window (absorbs detector flicker)
    violation_frames: int = 12       # N — consecutive raw-violation frames to FLAG
    clear_frames: int = 12           # K — consecutive raw-OK frames to CLEAR
    association_overlap: float = 0.10  # min (PPE∩person)/PPE_area to bind PPE→track
    box_hold_frames: int = 30        # render: keep drawing a track this many frames
                                     #   after its last detection (bridges misses)

    # ── Alerts ────────────────────────────────────────────────────────────────
    alert_cooldown_s: float = 60.0   # per-track_id cooldown
    screenshots_dir: str = str(ROOT / "screenshots")

    # ── PPE class map — MUST match the PPE model's training order ─────────────
    ppe_classes: Dict[int, str] = field(default_factory=lambda: {
        0: "helmet", 1: "safety_vest", 2: "goggles", 3: "gloves",
    })

    def summary(self) -> str:
        return (
            f"device={self.device} half={self.half} | "
            f"person={self.person_model}@{self.person_imgsz} "
            f"ppe={Path(self.ppe_model).name}@{self.ppe_imgsz} | "
            f"tracker={self.tracker} buffer={self.track_buffer} | "
            f"required={self.required_ppe} window(M)={self.window_size} "
            f"N={self.violation_frames} K={self.clear_frames} "
            f"presence={self.presence_ratio}"
        )
