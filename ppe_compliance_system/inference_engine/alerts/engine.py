"""
inference_engine/alerts/engine.py — Stage 4 Alert Engine

WHAT IT DOES
────────────
  1. Watches every person dict produced by ComplianceChecker frame-by-frame.
  2. Counts consecutive non-compliant frames per track_id (violation streak).
  3. When the streak reaches ALERT_FRAME_THRESHOLD it fires an Alert.
  4. A per-worker cooldown prevents alert spam — one alert per worker per
     ALERT_COOLDOWN_SECONDS (default 60 s).
  5. Returns a list of newly-fired Alert objects each frame (usually []).

WHY STREAK-BASED, NOT INSTANT?
───────────────────────────────
  A single missed frame (person turns sideways, PPE box missed) would fire
  constant false alerts if we triggered immediately.
  20 consecutive frames ≈ 0.67 s @ 30 fps — long enough to confirm a real
  violation, short enough that a worker removing their helmet triggers fast.

THREAD SAFETY
─────────────
  Not thread-safe by design — one AlertEngine per camera pipeline.
  For multi-camera use, instantiate one AlertEngine per pipeline thread.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

log = logging.getLogger(__name__)


@dataclass
class Alert:
    """
    Represents a single fired alert.

    Attributes
    ----------
    track_id    : Worker track ID (from YOLO tracker) or -1 if untracked.
    timestamp   : Unix time the alert fired.
    missing_ppe : List of PPE item names the worker is missing.
    severity    : "WARNING" — 1 item missing | "CRITICAL" — 2+ items missing.
    frame_number: Frame index when the alert fired.
    streak      : How many consecutive frames triggered this alert.
    """
    track_id:     int
    timestamp:    float
    missing_ppe:  List[str]
    severity:     str           # "WARNING" | "CRITICAL"
    frame_number: int
    streak:       int

    @property
    def time_str(self) -> str:
        """Human-readable time string, e.g. '14:32:07'."""
        from datetime import datetime
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")

    @property
    def summary(self) -> str:
        """One-line alert summary for logs / overlays."""
        missing = ", ".join(self.missing_ppe) if self.missing_ppe else "unknown"
        return (
            f"[{self.severity}] Worker #{self.track_id} — "
            f"missing: {missing}  @ {self.time_str}"
        )


class AlertEngine:
    """
    Frame-by-frame alert tracker.

    Args
    ----
    frame_threshold   : Consecutive non-compliant frames before alert fires.
    cooldown_seconds  : Min seconds between alerts for the same worker.
    max_log_size      : How many recent alerts to keep in memory.
    """

    def __init__(
        self,
        frame_threshold:  int = 20,
        cooldown_seconds: int = 60,
        max_log_size:     int = 50,
    ) -> None:
        self._threshold    = frame_threshold
        self._cooldown     = cooldown_seconds
        self._max_log      = max_log_size

        # Per-track state
        self._streak:     Dict[int, int]   = {}   # track_id → consecutive bad frames
        self._last_alert: Dict[int, float] = {}   # track_id → last alert unix time

        # Global alert log (most recent last)
        self._alert_log: List[Alert] = []

        # Monotonic frame counter
        self._frame_n: int = 0

        log.info(
            f"AlertEngine ready — threshold={frame_threshold} frames, "
            f"cooldown={cooldown_seconds}s"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, persons: List[Dict[str, Any]]) -> List[Alert]:
        """
        Process one frame's worth of persons.

        Call this AFTER ComplianceChecker.check() so every person dict
        already has 'is_compliant', 'missing_ppe', and 'track_id'.

        Returns
        -------
        List of Alert objects that fired THIS frame (usually empty).
        """
        self._frame_n += 1
        now        = time.time()
        new_alerts: List[Alert] = []
        seen_ids   = set()

        for person in persons:
            tid = person.get("track_id")

            # ── No tracking ID — use a coarse spatial hash as surrogate ──
            # Quantise to 80px horizontal bins so small movements (jitter,
            # breathing) don't change the ID and break the streak.
            if tid is None:
                x1, y1, x2, y2 = person.get("bbox", (0, 0, 0, 0))
                cx = ((x1 + x2) // 2) // 80   # coarse horizontal bin
                cy = ((y1 + y2) // 2) // 160  # coarse vertical bin
                tid = hash((cx, cy)) % 10000

            seen_ids.add(tid)
            is_compliant = person.get("is_compliant", True)

            if not is_compliant:
                # Increment streak
                self._streak[tid] = self._streak.get(tid, 0) + 1
                streak = self._streak[tid]

                # Check threshold
                if streak >= self._threshold:
                    last_t = self._last_alert.get(tid, 0.0)
                    if (now - last_t) >= self._cooldown:
                        alert = self._fire(tid, person, streak, now)
                        new_alerts.append(alert)
                        # Reset streak so it won't fire again next frame
                        self._streak[tid] = 0
                        self._last_alert[tid] = now
            else:
                # Worker is compliant — reset streak
                self._streak[tid] = 0

        # Clean up stale track IDs (worker left the frame)
        stale = [tid for tid in self._streak if tid not in seen_ids]
        for tid in stale:
            del self._streak[tid]

        return new_alerts

    @property
    def alert_log(self) -> List[Alert]:
        """All alerts fired since start (most recent last). Read-only view."""
        return list(self._alert_log)

    @property
    def recent_alerts(self) -> List[Alert]:
        """Last 5 alerts — suitable for on-screen overlay."""
        return self._alert_log[-5:]

    def streak_for(self, track_id: int) -> int:
        """Current violation streak for a given track ID (0 if compliant)."""
        return self._streak.get(track_id, 0)

    def total_alerts(self) -> int:
        """Total alerts fired since start."""
        return len(self._alert_log)

    def reset(self) -> None:
        """Clear all state (useful between test runs)."""
        self._streak.clear()
        self._last_alert.clear()
        self._alert_log.clear()
        self._frame_n = 0

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fire(
        self,
        tid:    int,
        person: Dict[str, Any],
        streak: int,
        now:    float,
    ) -> Alert:
        """Create an Alert, log it, append to log, return it."""
        missing  = person.get("missing_ppe", [])
        severity = "CRITICAL" if len(missing) >= 2 else "WARNING"

        alert = Alert(
            track_id=tid,
            timestamp=now,
            missing_ppe=list(missing),
            severity=severity,
            frame_number=self._frame_n,
            streak=streak,
        )

        log.warning(alert.summary)

        self._alert_log.append(alert)
        # Trim log to max size
        if len(self._alert_log) > self._max_log:
            self._alert_log = self._alert_log[-self._max_log:]

        return alert
