"""
inference_engine/utils/display.py
──────────────────────────────────
All OpenCV drawing / annotation logic lives here.

WHY SEPARATE FROM DETECTOR?
The detector produces data. The annotator turns data into pixels.
Keeping them separate means:
  - In Stage 6 (WebSocket streaming), we can skip drawing entirely and
    send the raw detection dicts over the network — the browser React app
    will draw its own overlays.
  - In headless server mode (--no-display), nothing in display.py is ever
    called, so OpenCV's GUI functions are never invoked (they crash on
    servers without a display).
  - Unit-testing the detector doesn't require importing OpenCV at all.

The draw() method takes the detections list from PersonDetector and the
Settings object. It never touches the model or the camera.
"""

import logging
from typing import List, Dict, Any

import cv2
import numpy as np

from ...config.settings import Settings

log = logging.getLogger(__name__)


class FrameAnnotator:
    """
    Draws bounding boxes, labels, FPS, and status overlays on a frame.

    Args:
        cfg: Settings object — provides colours, font scale, thickness.

    The annotator is intentionally stateless between frames (except for
    cached config values) so it's safe to use from multiple threads
    in the multi-camera Stage 7 expansion.
    """

    def __init__(self, cfg: Settings) -> None:
        self._cfg = cfg

        # Pre-cache font constant — cv2.FONT_HERSHEY_SIMPLEX is the most
        # readable OpenCV font at small scales in low-contrast environments.
        self._font       = cv2.FONT_HERSHEY_SIMPLEX
        self._font_scale = cfg.FONT_SCALE
        self._thickness  = cfg.BOX_THICKNESS

        # Stage 3 will add a per-class colour map here.
        # For now, "person" always gets PERSON_BOX_COLOR.
        self._color_map  = {
            "person": cfg.PERSON_BOX_COLOR,
        }
        self._default_color = cfg.UNTRACKED_BOX_COLOR

    # ── Main annotation entry point ────────────────────────────────────────────

    def draw(
        self,
        frame: np.ndarray,
        detections: List[Dict[str, Any]],
        fps: float,
    ) -> np.ndarray:
        """
        Draw all annotations on a copy of the frame.

        WHY A COPY?
        We never modify the original frame. The original may be needed later
        (e.g. saved as a raw screenshot, or passed to a second annotator for
        a different camera overlay). In-place modification is a common source
        of subtle bugs in multi-stage pipelines.

        Args:
            frame:      BGR NumPy array from VideoSource.read()
            detections: List of detection dicts from PersonDetector.detect()
            fps:        Current rolling FPS from FPSCounter.update()

        Returns:
            Annotated BGR NumPy array (same shape as input).
        """
        # .copy() ensures we don't mutate the original frame
        out = frame.copy()

        # 1. Draw bounding boxes and labels for every detection
        for det in detections:
            self._draw_detection(out, det)

        # 2. Draw HUD overlay (FPS + person count) in top-left corner
        self._draw_hud(out, detections, fps)

        # 3. Draw stage indicator (removed in Stage 3 when real PPE labels appear)
        self._draw_stage_label(out)

        return out

    # ── Per-detection drawing ──────────────────────────────────────────────────

    def _draw_detection(self, frame: np.ndarray, det: Dict[str, Any]) -> None:
        """
        Draw one bounding box + label for a single detection.

        Label format: "person [0.87]"
        In Stage 2, when track_id is populated: "person #3 [0.87]"
        In Stage 3, when compliance is known:   "person #3 ✗ helmet [0.87]"
        """
        x1, y1, x2, y2 = det["bbox"]
        class_name      = det["class_name"]
        confidence      = det["confidence"]
        track_id        = det["track_id"]   # None in Stage 1

        # Choose colour from class map (defaults to orange for unknown classes)
        color = self._color_map.get(class_name, self._default_color)

        # ── Stage 3 hook: change colour to red if non-compliant ────────────────
        # is_compliant = det.get("is_compliant", True)
        # if not is_compliant:
        #     color = (0, 0, 220)   # red — non-compliant worker

        # Draw bounding box rectangle
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, self._thickness)

        # Build label string
        # Stage 1: "person [0.87]"
        label_parts = [class_name]
        if track_id is not None:
            label_parts.append(f"#{track_id}")     # Stage 2
        label_parts.append(f"[{confidence:.2f}]")
        label = " ".join(label_parts)

        # Draw label background so text is readable on any background.
        # Get text size first, then draw a filled rectangle behind it.
        (text_w, text_h), baseline = cv2.getTextSize(
            label, self._font, self._font_scale, 1
        )

        # Label sits ABOVE the bounding box. If the box is near the top of
        # the frame, y1 might be < text_h — clamp to avoid drawing off-screen.
        label_y  = max(y1 - 8, text_h + 4)

        # Semi-transparent background rectangle for the label
        # (filled rectangle in the same colour as the box, slightly padded)
        cv2.rectangle(
            frame,
            (x1, label_y - text_h - 4),
            (x1 + text_w + 4, label_y + baseline),
            color,
            thickness=cv2.FILLED,
        )

        # White text on the coloured background
        cv2.putText(
            frame,
            label,
            (x1 + 2, label_y - 2),
            self._font,
            self._font_scale,
            (255, 255, 255),    # white
            thickness=1,
            lineType=cv2.LINE_AA,
        )

    # ── HUD overlay ───────────────────────────────────────────────────────────

    def _draw_hud(
        self,
        frame: np.ndarray,
        detections: List[Dict[str, Any]],
        fps: float,
    ) -> None:
        """
        Draw top-left HUD: FPS counter and detection count.

        A dark semi-transparent background behind the text keeps it legible
        regardless of the scene content (white walls, bright windows, etc.).
        """
        person_count = len(detections)

        # Lines of HUD text
        lines = [
            f"FPS: {fps:.1f}",
            f"Persons: {person_count}",
        ]

        # Stage 5 hook — add compliance summary line:
        # non_compliant = sum(1 for d in detections if not d.get("is_compliant", True))
        # lines.append(f"Violations: {non_compliant}")

        padding    = 8
        line_h     = 22     # pixels per line
        hud_h      = len(lines) * line_h + padding * 2
        hud_w      = 180

        # Draw a dark semi-transparent rectangle in the top-left corner.
        # We use addWeighted to simulate alpha blending — pure OpenCV has no
        # native alpha for filled rectangles.
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (hud_w, hud_h), (0, 0, 0), cv2.FILLED)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        # Draw each line of text
        for i, line in enumerate(lines):
            y = padding + (i + 1) * line_h
            cv2.putText(
                frame, line, (padding, y),
                self._font, self._font_scale,
                (200, 255, 200),    # light green — easy on the eyes
                thickness=1, lineType=cv2.LINE_AA,
            )

    # ── Stage indicator ────────────────────────────────────────────────────────

    def _draw_stage_label(self, frame: np.ndarray) -> None:
        """
        Draw a small "STAGE 1 · PERSON DETECTION" label in the bottom-right.

        This acts as a clear visual marker during demos and development.
        It will be removed (or replaced with the camera name) in Stage 3.
        """
        h, w = frame.shape[:2]
        label = "STAGE 1 - PERSON DETECTION"

        (text_w, text_h), _ = cv2.getTextSize(label, self._font, 0.45, 1)

        x = w - text_w - 10
        y = h - 10

        # Dark shadow effect for legibility
        cv2.putText(
            frame, label, (x + 1, y + 1),
            self._font, 0.45, (0, 0, 0), 2, cv2.LINE_AA
        )
        cv2.putText(
            frame, label, (x, y),
            self._font, 0.45, (180, 180, 180), 1, cv2.LINE_AA
        )
