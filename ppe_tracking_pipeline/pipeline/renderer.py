"""
renderer.py — draw stable tracked boxes + debounced status every frame.

Colour code:
    green  = COMPLIANT
    red    = VIOLATION  (+ "NO HELMET, NO VEST" labels)
    amber  = PENDING    (not enough frames yet to decide)

A held (coasting) box — drawn from memory because the detector missed this
frame — is rendered with a thinner, dashed-feel outline so you can see the
tracker bridging a gap. Status text comes from the per-track state machine, so
it does not flicker.
"""

from typing import Any, Dict, List, Optional

import cv2

GREEN = (96, 201, 124)
RED   = (60, 60, 235)
AMBER = (40, 180, 240)
GREY  = (150, 150, 150)
DARK  = (28, 24, 20)
WHITE = (245, 245, 245)

STATUS_COLOR = {"COMPLIANT": GREEN, "VIOLATION": RED, "PENDING": AMBER}
PRETTY = {"helmet": "HELMET", "safety_vest": "VEST", "goggles": "GOGGLES", "gloves": "GLOVES"}


class Renderer:
    def __init__(self, cfg) -> None:
        self.cfg = cfg

    def draw(self, frame, workers: List[Dict[str, Any]], hud: Optional[str] = None):
        out = frame.copy()
        for w in workers:
            x1, y1, x2, y2 = w["bbox"]
            color = STATUS_COLOR.get(w["status"], GREY)
            thick = 2 if w["coasting"] else 3
            cv2.rectangle(out, (x1, y1), (x2, y2), color, thick)

            label = f"#{w['track_id']}  {w['status']}"
            if w["status"] == "VIOLATION" and w["missing_ppe"]:
                label += "  -  " + ", ".join(
                    "NO " + PRETTY.get(m, m.upper()) for m in w["missing_ppe"]
                )
            self._label(out, label, x1, y1, color)

        if hud:
            self._hud(out, hud)
        return out

    def _label(self, img, text, x, y, color):
        font, scale, t = cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        (tw, th), _ = cv2.getTextSize(text, font, scale, t)
        y_top = max(0, y - th - 9)
        cv2.rectangle(img, (x, y_top), (x + tw + 10, y), color, -1)
        cv2.putText(img, text, (x + 5, y - 5), font, scale, (0, 0, 0), t, cv2.LINE_AA)

    def _hud(self, img, text):
        h, w = img.shape[:2]
        cv2.rectangle(img, (0, 0), (w, 30), DARK, -1)
        cv2.putText(img, text, (10, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)
