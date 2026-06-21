"""
alerts.py — per-track_id alert manager.

Alerts are keyed on track_id (not a per-frame heuristic), so each worker fires
at most one alert per cooldown window. The manager receives violation-onset
events from the state machine, applies a per-track cooldown, saves a screenshot
of the annotated frame, and logs the alert.

Hook points for WhatsApp / SQLite are marked — kept out of this standalone
testbed on purpose so it has zero external dependencies.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2

log = logging.getLogger(__name__)


class AlertManager:
    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self.dir = Path(cfg.screenshots_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._last_fire: Dict[int, float] = {}
        self.total = 0

    def handle(self, events: List[Dict[str, Any]], annotated_frame=None) -> List[Dict[str, Any]]:
        fired: List[Dict[str, Any]] = []
        now = time.time()

        for ev in events:
            tid = ev["track_id"]
            if now - self._last_fire.get(tid, 0.0) < self.cfg.alert_cooldown_s:
                continue   # still cooling down for this worker
            self._last_fire[tid] = now
            self.total += 1

            shot: Optional[str] = None
            if annotated_frame is not None:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                shot = str(self.dir / f"violation_t{tid}_{ts}.jpg")
                cv2.imwrite(shot, annotated_frame)

            missing = ", ".join(ev["missing"]) or "PPE"
            log.warning(f"🚨 ALERT  worker #{tid}  missing: {missing}  shot={shot}")
            fired.append({**ev, "screenshot": shot})

            # ── Hook: send WhatsApp / write to SQLite here in production ───────
            # whatsapp.send(...); db.log_violation(...)

        return fired
