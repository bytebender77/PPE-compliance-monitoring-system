"""
config/settings.py — Central configuration for the PPE system

WHY A SETTINGS CLASS INSTEAD OF RAW CONSTANTS?
-----------------------------------------------
A dataclass lets us:
  1. Set sensible defaults in one place
  2. Override with environment variables in production (Stage 7)
  3. Pass the entire config object around instead of a dozen separate args
  4. Validate types at startup (add __post_init__ assertions later)

All magic numbers live here — not scattered across detector.py or display.py.
Changing a threshold means editing ONE file, not hunting through the codebase.
"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # ── Model ──────────────────────────────────────────────────────────────────
    # "yolov8n.pt" is the nano variant: fastest, smallest — ideal for MVP.
    # Ultralytics auto-downloads it on first run if not present locally.
    # Stage 3 will replace this with our custom-trained best.pt.
    MODEL_PATH: str = field(
        default_factory=lambda: os.getenv("PPE_MODEL_PATH", "yolov8n.pt")
    )

    # Confidence threshold: detections below this score are discarded.
    # 0.4 is a good starting point — low enough to catch distant workers,
    # high enough to suppress background false positives.
    # Tune upward (0.5–0.6) after seeing real footage.
    CONFIDENCE_THRESHOLD: float = field(
        default_factory=lambda: float(os.getenv("PPE_CONF_THRESHOLD", "0.4"))
    )

    # ── Inference device ───────────────────────────────────────────────────────
    # "cuda" → GPU (NVIDIA). "cpu" → fallback.
    # YOLOv8 auto-detects if you pass "cuda" when no GPU is present and
    # falls back to CPU — but we make the default explicit so it's obvious
    # in logs which device is actually being used.
    DEVICE: str = field(
        default_factory=lambda: os.getenv("PPE_DEVICE", "cpu")
    )

    # ── Display / annotation ───────────────────────────────────────────────────
    # Bounding box colour for persons (BGR not RGB — OpenCV convention).
    # Green = compliant in the future UI language. We'll differentiate
    # compliant (green) vs non-compliant (red) in Stage 3.
    PERSON_BOX_COLOR: tuple = (0, 220, 0)      # bright green

    # Colour used for "untracked" detections before ByteTrack is added.
    UNTRACKED_BOX_COLOR: tuple = (0, 165, 255)  # orange

    # Font scale for annotation text. 0.55 is readable at 720p without
    # overwhelming the image.
    FONT_SCALE: float = 0.55

    # Line thickness for bounding boxes (pixels)
    BOX_THICKNESS: int = 2

    # ── Future PPE classes (Stage 2 / 3) ──────────────────────────────────────
    # These are declared here NOW so Stage 2 can simply uncomment/populate
    # them — the settings object already has the right shape.
    #
    # Maps YOLO class ID → human-readable label.
    # After fine-tuning our own model the class IDs will match these entries.
    PPE_CLASS_MAP: dict = field(default_factory=lambda: {
        0: "person",
        # 1: "helmet",       — added Stage 3
        # 2: "safety_vest",  — added Stage 3
        # 3: "goggles",      — added Stage 3
    })

    # Required PPE per zone (Stage 4 compliance engine will consume this)
    REQUIRED_PPE_BY_ZONE: dict = field(default_factory=lambda: {
        "default": ["helmet", "safety_vest"],
        # "welding_bay":  ["helmet", "safety_vest", "goggles"],
        # "chemical_lab": ["helmet", "safety_vest", "goggles"],
    })

    # ── Alert thresholds (Stage 5) ─────────────────────────────────────────────
    # N consecutive non-compliant frames before triggering an alert.
    # 20 frames @ 30 fps ≈ 0.67 s — filters transient false positives.
    ALERT_FRAME_THRESHOLD: int = int(os.getenv("PPE_ALERT_FRAMES", "20"))

    # Minimum seconds between repeated alerts for the same worker.
    ALERT_COOLDOWN_SECONDS: int = int(os.getenv("PPE_ALERT_COOLDOWN", "60"))

    # ── Paths ──────────────────────────────────────────────────────────────────
    SCREENSHOTS_DIR: str = "screenshots"
    LOG_DIR: str = "logs"
