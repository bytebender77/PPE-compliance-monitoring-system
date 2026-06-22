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

# per-item PPE box colours (BGR) — distinct from the green/red person box
PPE_COLOR = {
    "helmet":      (0, 165, 255),    # orange
    "safety_vest": (0, 255, 255),    # yellow
    "goggles":     (255, 0, 255),    # magenta
    "gloves":      (255, 200, 0),    # cyan
}


class Renderer:
    def __init__(self, cfg) -> None:
        self.cfg = cfg

    def draw(self, frame, workers: List[Dict[str, Any]], hud: Optional[str] = None,
             ppe: Optional[List[Dict[str, Any]]] = None):
        out = frame.copy()
        show_ppe = bool(ppe) and getattr(self.cfg, "show_ppe_boxes", True)
        placed: List[List[int]] = []   # occupied label rects → overlap avoidance

        # 1) OUTLINES ONLY first (thin PPE boxes, then person boxes) so the
        #    worker stays fully visible — no filled label sits on top of him.
        if show_ppe:
            for d in ppe:
                x1, y1, x2, y2 = d["bbox"]
                cv2.rectangle(out, (x1, y1), (x2, y2),
                              PPE_COLOR.get(d.get("class_name", ""), GREY), 2)
        for w in workers:
            x1, y1, x2, y2 = w["bbox"]
            color = STATUS_COLOR.get(w["status"], GREY)
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2 if w["coasting"] else 3)

        # 2) LABELS on top — person status above the box, PPE tags to the side,
        #    each nudged so none overlap another.
        for w in workers:
            x1, y1, x2, y2 = w["bbox"]
            color = STATUS_COLOR.get(w["status"], GREY)
            label = f"#{w['track_id']}  {w['status']}"
            if w["status"] == "VIOLATION" and w["missing_ppe"]:
                label += "  -  " + ", ".join(
                    "NO " + PRETTY.get(m, m.upper()) for m in w["missing_ppe"]
                )
            self._tag(out, label, (x1, y1, x2, y2), color, placed, above=True)

        if show_ppe:
            for d in ppe:
                name = d.get("class_name", "")
                text = f"{PRETTY.get(name, name.upper())} {d.get('confidence', 0):.2f}"
                self._tag(out, text, d["bbox"], PPE_COLOR.get(name, GREY), placed, above=False)

        if hud:
            self._hud(out, hud)
        return out

    def _tag(self, img, text, box, color, placed, above: bool):
        """Draw a label for `box`. Person tags sit above the box; PPE tags sit
        beside it (right, or left near the edge) with a thin connector. Every tag
        is nudged downward until it clears all previously placed tags."""
        x1, y1, x2, y2 = box
        font, scale, t = cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1
        (tw, th), base = cv2.getTextSize(text, font, scale, t)
        pad = 5
        lw, lh = tw + 2 * pad, th + base + pad
        H, W = img.shape[:2]

        if above:                          # person status → above the box
            lx = max(2, min(x1, W - lw - 2))
            ly = max(0, y1 - lh - 3)
            connector = False
        else:                              # PPE item → beside the box
            lx = x2 + 8
            if lx + lw > W - 2:            # off the right edge → place on the left
                lx = x1 - lw - 8
            lx = max(2, min(lx, W - lw - 2))
            ly = y1
            connector = True

        rect = [lx, ly, lx + lw, ly + lh]
        moved, guard = True, 0
        while moved and guard < 150:
            moved = False; guard += 1
            for r in placed:
                if not (rect[2] <= r[0] or rect[0] >= r[2] or
                        rect[3] <= r[1] or rect[1] >= r[3]):
                    rect[1] = r[3] + 3; rect[3] = rect[1] + lh; moved = True
        if rect[3] > H:
            dy = rect[3] - H; rect[1] -= dy; rect[3] -= dy
        placed.append(rect)

        if connector:
            bx = x2 if rect[0] >= x2 else x1
            lxc = rect[0] if rect[0] >= x2 else rect[2]
            cv2.line(img, (bx, y1), (lxc, rect[1] + lh // 2), color, 1, cv2.LINE_AA)

        cv2.rectangle(img, (rect[0], rect[1]), (rect[2], rect[3]), color, -1)
        cv2.putText(img, text, (rect[0] + pad, rect[3] - pad - base // 2),
                    font, scale, (0, 0, 0), t, cv2.LINE_AA)

    def _hud(self, img, text):
        h, w = img.shape[:2]
        cv2.rectangle(img, (0, 0), (w, 30), DARK, -1)
        cv2.putText(img, text, (10, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)
