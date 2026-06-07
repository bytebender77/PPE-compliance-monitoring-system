"""
inference_engine/utils/display.py
──────────────────────────────────
Stage 4: Alert-aware frame annotation.

WHAT CHANGED FROM STAGE 3
───────────────────────────
  - Red flashing border when an alert fires (fades over ~1 second)
  - Alert log panel in bottom-right corner (last 3 alerts)
  - Violation streak progress bar shown on non-compliant person boxes
  - Stage indicator updated to "ALERT ENGINE"

DESIGN PRINCIPLES (unchanged)
───────────────────────────────
  - Never modifies the original frame (always returns a copy)
  - Stateless between frames — safe for multi-threaded multi-camera use
  - No knowledge of models, cameras, or compliance logic
  - All magic numbers come from Settings — nothing hardcoded here
"""

import logging
import time
from typing import List, Dict, Any, Optional

import cv2
import numpy as np

from ...config.settings import Settings

log = logging.getLogger(__name__)


class FrameAnnotator:
    """
    Draws bounding boxes, labels, compliance status, HUD, and alert overlays.

    Args:
        cfg: Settings object — provides colours, font scale, thickness.
    """

    # How long the red flash border stays on screen after an alert (seconds)
    FLASH_DURATION = 1.2

    def __init__(self, cfg: Settings) -> None:
        self._cfg        = cfg
        self._font       = cv2.FONT_HERSHEY_SIMPLEX
        self._font_scale = cfg.FONT_SCALE
        self._thickness  = cfg.BOX_THICKNESS

        # PPE class → box colour (from settings)
        self._ppe_colors = cfg.PPE_BOX_COLORS

        # Timestamp of the most recent alert — drives the flash border
        self._last_alert_time: float = 0.0

    # ── Main entry point ──────────────────────────────────────────────────────

    def draw(
        self,
        frame:         np.ndarray,
        persons:       List[Dict[str, Any]],
        ppe_items:     List[Dict[str, Any]],
        fps:           float,
        new_alerts:    Optional[List] = None,
        recent_alerts: Optional[List] = None,
        streaks:       Optional[Dict[int, int]] = None,
        alert_threshold: int = 20,
        alerts_enabled: bool = True,
    ) -> np.ndarray:
        """
        Draw all annotations on a copy of the frame.

        Args:
            frame:           BGR NumPy array from VideoSource.
            persons:         Enriched person dicts from ComplianceChecker.check().
            ppe_items:       Raw PPE detection dicts from PPEDetector.
            fps:             Rolling FPS from FPSCounter.
            new_alerts:      Alert objects fired THIS frame (triggers flash).
            recent_alerts:   Last N alerts for the alert log overlay.
            streaks:         Dict of track_id → current violation streak count.
            alert_threshold: Frames needed for alert (for streak progress bar).

        Returns:
            Annotated BGR NumPy array (same shape as input).
        """
        out = frame.copy()

        # Record alert time so flash knows when to start fading
        if new_alerts:
            self._last_alert_time = time.time()

        # 1. Draw PPE item boxes (no text on box — text goes to side panel)
        for ppe in ppe_items:
            self._draw_ppe_item(out, ppe)

        # 2. Draw person boxes with compliance colouring + streak bars
        for person in persons:
            streak = 0
            if streaks and person.get("track_id") is not None:
                streak = streaks.get(person["track_id"], 0)
            self._draw_person(out, person, streak, alert_threshold)

        # 3. HUD overlay (top-left)
        total_alerts = len(recent_alerts) if recent_alerts else 0
        self._draw_hud(out, persons, fps, total_alerts, alerts_enabled)

        # 4. Detection panel (right side) — class names + confidence scores
        self._draw_detection_panel(out, persons, ppe_items)

        # 5. Alert log panel (bottom-right, above detection panel)
        if recent_alerts:
            self._draw_alert_log(out, recent_alerts)

        # 6. Flash border — red pulse when an alert fires
        self._draw_flash_border(out)

        # 7. Stage indicator
        self._draw_stage_label(out)

        return out

    # ── Person drawing ────────────────────────────────────────────────────────

    def _draw_person(
        self,
        frame:           np.ndarray,
        det:             Dict[str, Any],
        streak:          int = 0,
        alert_threshold: int = 20,
    ) -> None:
        """
        Draw a person's bounding box with compliance colour + violation streak bar.

        Label examples:
          Compliant:     "person #3 [0.91] OK"
          Non-compliant: "person #3 [0.91] MISSING: helmet, goggles"
        """
        x1, y1, x2, y2 = det["bbox"]
        confidence      = det["confidence"]
        track_id        = det.get("track_id")
        is_compliant    = det.get("is_compliant", None)
        missing_ppe     = det.get("missing_ppe", [])

        # Colour depends on compliance
        if is_compliant is None:
            color = self._cfg.PERSON_UNKNOWN_COLOR      # orange — no info yet
        elif is_compliant:
            color = self._cfg.PERSON_COMPLIANT_COLOR    # green
        else:
            color = self._cfg.PERSON_NONCOMPLIANT_COLOR  # red

        # Draw bounding box only — label goes to side panel
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, self._thickness)

        # Small compliance indicator dot in top-left corner of box
        dot_color = (0, 220, 0) if is_compliant else (0, 0, 220) if is_compliant is False else (0, 165, 255)
        cv2.circle(frame, (x1 + 7, y1 + 7), 5, dot_color, cv2.FILLED)

        # Violation streak progress bar (shown only on non-compliant persons)
        if is_compliant is False and streak > 0 and alert_threshold > 0:
            self._draw_streak_bar(frame, x1, y2, x2, streak, alert_threshold)

    # ── PPE item drawing ──────────────────────────────────────────────────────

    def _draw_ppe_item(self, frame: np.ndarray, det: Dict[str, Any]) -> None:
        """
        Draw a PPE item box only — no text on the box.
        Labels are shown in the side detection panel instead.
        """
        x1, y1, x2, y2 = det["bbox"]
        class_name      = det["class_name"]
        color = self._ppe_colors.get(class_name, (200, 200, 200))
        # Thinner box for PPE items
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
        # Small colour-coded corner dot to identify the class without text overlap
        cv2.circle(frame, (x1 + 5, y1 + 5), 4, color, cv2.FILLED)

    # ── Label helper ──────────────────────────────────────────────────────────

    def _draw_label(
        self,
        frame: np.ndarray,
        label: str,
        x: int,
        y: int,
        color: tuple,
        font_scale: float = None,
    ) -> None:
        """Draw a filled-background label above a bounding box."""
        font_scale = font_scale or self._font_scale

        (text_w, text_h), baseline = cv2.getTextSize(
            label, self._font, font_scale, 1
        )
        label_y = max(y - 8, text_h + 4)

        # Filled background rectangle
        cv2.rectangle(
            frame,
            (x, label_y - text_h - 4),
            (x + text_w + 4, label_y + baseline),
            color,
            thickness=cv2.FILLED,
        )
        # White text
        cv2.putText(
            frame, label, (x + 2, label_y - 2),
            self._font, font_scale,
            (255, 255, 255),
            thickness=1, lineType=cv2.LINE_AA,
        )

    # ── Detection panel (right side) ─────────────────────────────────────────

    def _draw_detection_panel(
        self,
        frame:     np.ndarray,
        persons:   List[Dict[str, Any]],
        ppe_items: List[Dict[str, Any]],
    ) -> None:
        """
        Right-side panel listing all detections with class + confidence.
        Keeps the frame clean — no text overlapping bounding boxes.
        """
        h, w = frame.shape[:2]
        panel_w  = 230
        padding  = 8
        line_h   = 20
        px       = w - panel_w - 4

        # Collect lines to display
        lines = []  # (text, color)

        # ── Person detections ──
        lines.append(("- PERSONS -", (180, 180, 180)))
        if persons:
            for i, p in enumerate(persons):
                tid  = p.get("track_id")
                conf = p.get("confidence", 0)
                is_c = p.get("is_compliant")
                miss = p.get("missing_ppe", [])

                label = f"Person {'#'+str(tid) if tid else str(i+1)}  [{conf:.2f}]"
                if is_c is True:
                    status_text = "  OK"
                    status_color = (60, 220, 60)
                    lines.append((label, (200, 255, 200)))
                    lines.append((status_text, status_color))
                elif is_c is False:
                    lines.append((label, (80, 80, 255)))
                    for m in miss:
                        lines.append((f"  ! {m}", (60, 60, 255)))
                else:
                    lines.append((label, (0, 165, 255)))
        else:
            lines.append(("  No persons", (120, 120, 120)))

        lines.append(("", (0, 0, 0)))  # spacer

        # ── PPE detections ──
        lines.append(("- PPE DETECTED -", (180, 180, 180)))
        if ppe_items:
            # Group by class for cleaner display
            seen = {}
            for item in ppe_items:
                cn   = item["class_name"]
                conf = item["confidence"]
                if cn not in seen or conf > seen[cn]:
                    seen[cn] = conf
            for cn, conf in seen.items():
                color = self._ppe_colors.get(cn, (200, 200, 200))
                lines.append((f"  {cn}  [{conf:.2f}]", color))
        else:
            lines.append(("  None", (120, 120, 120)))

        # Panel height based on content
        panel_h = len(lines) * line_h + padding * 2 + 16
        py = max(4, (h - panel_h) // 4)   # upper-right area

        # Semi-transparent dark background
        overlay = frame.copy()
        cv2.rectangle(overlay, (px - 4, py), (w - 4, py + panel_h), (15, 15, 15), cv2.FILLED)
        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

        # Header
        cv2.putText(frame, "DETECTIONS", (px + padding, py + padding + 12),
                    self._font, 0.45, (100, 200, 255), 1, cv2.LINE_AA)

        # Draw each line
        for i, (text, color) in enumerate(lines):
            if not text:
                continue
            y = py + padding + 28 + i * line_h
            cv2.putText(frame, text, (px + padding, y),
                        self._font, 0.40, color, 1, cv2.LINE_AA)

    # ── Streak bar ────────────────────────────────────────────────────────────

    def _draw_streak_bar(
        self,
        frame:     np.ndarray,
        x1: int, y_bottom: int, x2: int,
        streak:    int,
        threshold: int,
    ) -> None:
        """
        Thin progress bar along the bottom edge of a non-compliant person box.
        Fills from left to right as streak approaches the alert threshold.
        Colour transitions yellow → orange → red.
        """
        bar_h    = 5
        ratio    = min(streak / threshold, 1.0)
        bar_w    = int((x2 - x1) * ratio)

        # Background (dark)
        cv2.rectangle(frame, (x1, y_bottom), (x2, y_bottom + bar_h), (40, 40, 40), cv2.FILLED)

        if bar_w > 0:
            # Colour: yellow at 0%, orange at 50%, red at 100%
            if ratio < 0.5:
                r = int(255 * ratio * 2)
                color = (0, 255 - r, 255)       # yellow → orange (BGR)
            else:
                g = int(255 * (1 - ratio) * 2)
                color = (0, g, 255)              # orange → red (BGR)

            cv2.rectangle(frame, (x1, y_bottom), (x1 + bar_w, y_bottom + bar_h), color, cv2.FILLED)

    # ── Flash border ──────────────────────────────────────────────────────────

    def _draw_flash_border(self, frame: np.ndarray) -> None:
        """
        Draw a pulsing red border around the whole frame when an alert has
        recently fired. Intensity fades linearly over FLASH_DURATION seconds.
        """
        elapsed = time.time() - self._last_alert_time
        if elapsed >= self.FLASH_DURATION:
            return

        alpha     = 1.0 - (elapsed / self.FLASH_DURATION)   # 1.0 → 0.0
        intensity = int(alpha * 255)
        h, w      = frame.shape[:2]
        thickness = max(4, int(alpha * 18))
        color     = (0, 0, intensity)                        # BGR red

        cv2.rectangle(frame, (0, 0), (w - 1, h - 1), color, thickness)

        # "ALERT" text centred at top
        if alpha > 0.3:
            label     = "! VIOLATION ALERT !"
            font_size = 0.9
            (tw, th), _ = cv2.getTextSize(label, self._font, font_size, 2)
            tx = (w - tw) // 2
            ty = th + 12
            cv2.putText(frame, label, (tx + 2, ty + 2), self._font, font_size,
                        (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, label, (tx, ty), self._font, font_size,
                        (0, 0, intensity), 2, cv2.LINE_AA)

    # ── Alert log panel ───────────────────────────────────────────────────────

    def _draw_alert_log(self, frame: np.ndarray, recent_alerts: list) -> None:
        """
        Compact alert history panel in the bottom-right corner.
        Shows the last 3 alerts with time, worker ID, and missing PPE.
        """
        if not recent_alerts:
            return

        h, w    = frame.shape[:2]
        alerts  = recent_alerts[-3:]          # show at most 3
        line_h  = 18
        padding = 8
        panel_h = len(alerts) * line_h + padding * 2 + 16
        panel_w = 310

        # Bottom-left (avoids the detection panel on the right)
        px = 8
        py = h - panel_h - 8

        # Semi-transparent dark background
        overlay = frame.copy()
        cv2.rectangle(overlay, (px, py), (px + panel_w, h - 8), (20, 20, 20), cv2.FILLED)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        # Header
        cv2.putText(frame, "ALERT LOG", (px + padding, py + padding + 12),
                    self._font, 0.42, (80, 80, 255), 1, cv2.LINE_AA)

        # Alert entries (newest at bottom)
        for i, alert in enumerate(alerts):
            y       = py + padding + 26 + i * line_h
            missing = ", ".join(alert.missing_ppe) if alert.missing_ppe else "?"
            color   = (60, 60, 255) if alert.severity == "CRITICAL" else (60, 140, 255)
            line    = f"{alert.time_str}  W#{alert.track_id}  -{missing}"
            cv2.putText(frame, line, (px + padding, y),
                        self._font, 0.38, color, 1, cv2.LINE_AA)

    # ── HUD overlay ───────────────────────────────────────────────────────────

    def _draw_hud(
        self,
        frame:          np.ndarray,
        persons:        List[Dict[str, Any]],
        fps:            float,
        total_alerts:   int  = 0,
        alerts_enabled: bool = True,
    ) -> None:
        """Top-left HUD: FPS, person count, compliance summary, alert status."""
        total      = len(persons)
        compliant  = sum(1 for p in persons if p.get("is_compliant") is True)
        violations = sum(1 for p in persons if p.get("is_compliant") is False)

        alert_status = "ON" if alerts_enabled else "MUTED"
        lines = [
            f"FPS: {fps:.1f}",
            f"Persons: {total}",
            f"Compliant: {compliant}",
            f"Alerts: {alert_status}",
        ]
        if violations:
            lines.append(f"Violations: {violations}")
        if total_alerts:
            lines.append(f"Fired: {total_alerts}")

        padding = 8
        line_h  = 22
        hud_h   = len(lines) * line_h + padding * 2
        hud_w   = 210

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (hud_w, hud_h), (0, 0, 0), cv2.FILLED)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        for i, line in enumerate(lines):
            if "Violations" in line:
                text_color = (80, 80, 255)
            elif "Fired" in line:
                text_color = (60, 60, 255)
            elif "Alerts:" in line:
                # Green when ON, amber when MUTED
                text_color = (60, 220, 60) if alerts_enabled else (0, 165, 255)
            else:
                text_color = (200, 255, 200)
            y = padding + (i + 1) * line_h
            cv2.putText(frame, line, (padding, y),
                        self._font, self._font_scale,
                        text_color, thickness=1, lineType=cv2.LINE_AA)

    # ── Stage indicator ────────────────────────────────────────────────────────

    def _draw_stage_label(self, frame: np.ndarray) -> None:
        """Small stage label in the bottom-right corner."""
        h, w    = frame.shape[:2]
        label   = "STAGE 4 - ALERT ENGINE"

        (text_w, text_h), _ = cv2.getTextSize(label, self._font, 0.45, 1)
        x = w - text_w - 10
        y = h - 10

        cv2.putText(
            frame, label, (x + 1, y + 1),
            self._font, 0.45, (0, 0, 0), 2, cv2.LINE_AA
        )
        cv2.putText(
            frame, label, (x, y),
            self._font, 0.45, (180, 180, 180), 1, cv2.LINE_AA
        )
