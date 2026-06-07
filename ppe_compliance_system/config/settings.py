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
    # ── Person detector model ─────────────────────────────────────────────────
    # COCO-pretrained nano model — used only to detect persons.
    # Fast and accurate enough for person localisation.
    MODEL_PATH: str = field(
        default_factory=lambda: os.getenv("PPE_PERSON_MODEL", "yolov8n.pt")
    )

    # ── PPE detector model (Stage 3) ──────────────────────────────────────────
    # Our custom-trained model: helmet (0), safety_vest (1), goggles (2).
    PPE_MODEL_PATH: str = field(
        default_factory=lambda: os.getenv("PPE_MODEL_PATH", "models/best.pt")
    )

    # ── Confidence thresholds ─────────────────────────────────────────────────
    # Person detector — slightly higher to avoid false person detections.
    CONFIDENCE_THRESHOLD: float = field(
        default_factory=lambda: float(os.getenv("PPE_CONF_THRESHOLD", "0.4"))
    )
    # PPE detector — low threshold so we don't miss partially visible items.
    # vest detection benefits from a lower threshold (0.05).
    PPE_CONF_THRESHOLD: float = field(
        default_factory=lambda: float(os.getenv("PPE_PPE_CONF_THRESHOLD", "0.05"))
    )

    # ── Inference device ───────────────────────────────────────────────────────
    # "cuda" → NVIDIA GPU, "mps" → Apple Silicon, "cpu" → fallback.
    DEVICE: str = field(
        default_factory=lambda: os.getenv("PPE_DEVICE", "cpu")
    )

    # ── Display / annotation ───────────────────────────────────────────────────
    # Person box colour depends on compliance (set dynamically in display.py).
    PERSON_COMPLIANT_COLOR: tuple   = (0, 220, 0)      # green  — all PPE worn
    PERSON_NONCOMPLIANT_COLOR: tuple = (0, 0, 220)     # red    — PPE missing
    PERSON_UNKNOWN_COLOR: tuple     = (0, 165, 255)    # orange — no persons nearby

    # Per-class PPE bounding box colours (BGR)
    PPE_BOX_COLORS: dict = field(default_factory=lambda: {
        "helmet":       (0, 255, 255),    # yellow
        "safety_vest":  (255, 165, 0),    # blue-orange
        "goggles":      (255, 0, 255),    # magenta
        "gloves":       (0, 255, 128),    # green-cyan
    })

    FONT_SCALE: float  = 0.55
    BOX_THICKNESS: int = 2

    # ── PPE class map ──────────────────────────────────────────────────────────
    # Maps class_id → name for our trained model.
    PPE_CLASS_MAP: dict = field(default_factory=lambda: {
        0: "helmet",
        1: "safety_vest",
        2: "goggles",
        3: "gloves",
    })

    # ── Compliance rules ───────────────────────────────────────────────────────
    # Which PPE items are mandatory. Any person missing one of these is flagged.
    # Extend for zone-specific rules in Stage 4.
    # Only helmet and safety_vest trigger alerts — goggles are detected
    # but NOT required for compliance checks / alert firing.
    REQUIRED_PPE: list = field(
        default_factory=lambda: os.getenv(
            "PPE_REQUIRED", "helmet,safety_vest"
        ).split(",")
    )

    # Minimum fraction of a PPE bbox that must overlap with a person bbox
    # to count as "this person is wearing this item".
    PPE_ASSOCIATION_THRESH: float = 0.1

    # Required PPE per zone (Stage 4 compliance engine will consume this)
    REQUIRED_PPE_BY_ZONE: dict = field(default_factory=lambda: {
        "default":      ["helmet", "safety_vest"],
        "welding_bay":  ["helmet", "safety_vest", "goggles"],
        "chemical_lab": ["helmet", "safety_vest", "goggles"],
        "assembly_line":["helmet", "safety_vest", "gloves"],
        "full_zone":    ["helmet", "safety_vest", "goggles", "gloves"],
    })

    # ── Alert thresholds (Stage 5) ─────────────────────────────────────────────
    # N consecutive non-compliant frames before triggering an alert.
    # 20 frames @ 30 fps ≈ 0.67 s — filters transient false positives.
    ALERT_FRAME_THRESHOLD: int = field(
        default_factory=lambda: int(os.getenv("PPE_ALERT_FRAMES", "20"))
    )

    # Minimum seconds between repeated alerts for the same worker.
    ALERT_COOLDOWN_SECONDS: int = field(
        default_factory=lambda: int(os.getenv("PPE_ALERT_COOLDOWN", "60"))
    )

    # ── Paths ──────────────────────────────────────────────────────────────────
    SCREENSHOTS_DIR: str = "screenshots"
    LOG_DIR: str = "logs"
