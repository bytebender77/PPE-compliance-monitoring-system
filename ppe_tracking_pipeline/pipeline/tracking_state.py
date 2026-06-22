"""
tracking_state.py — per-track compliance state machine (the stability core).

Two layers of temporal smoothing turn noisy per-frame detections into a stable,
professional on-screen result:

  1. PRESENCE SMOOTHING (per PPE class)
     Each track keeps a rolling window of the last M frames. A PPE class counts
     as "worn" only if it was detected in ≥ presence_ratio of that window. This
     absorbs the detector dropping an item for a frame or two.

  2. STATUS HYSTERESIS (per worker)
     The COMPLIANT⇄VIOLATION status flips only after the raw verdict has held
     for N consecutive frames (to raise a violation) or K consecutive frames (to
     clear it). One bad frame can't raise a false alarm; one lucky frame can't
     clear a real one.

Box lifecycle: each track's last box is held (and re-drawn) for up to
box_hold_frames after its last detection, so a missed frame never makes the box
vanish — it stays put until the tracker re-acquires or the track ages out.

Thresholds (violation_frames, clear_frames, presence_ratio) are read LIVE from
the shared Config, so they can be tuned at runtime from the keyboard.
"""

import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional, Set

PENDING   = "PENDING"
COMPLIANT = "COMPLIANT"
VIOLATION = "VIOLATION"


class TrackedWorker:
    """Lifecycle + compliance state for a single track_id."""

    def __init__(self, track_id: int, cfg) -> None:
        self.track_id = track_id
        self.cfg = cfg
        self.history: deque = deque(maxlen=cfg.window_size)  # set[str] per frame

        self.status = PENDING
        self._viol_streak = 0
        self._ok_streak = 0

        self.bbox: Optional[List[int]] = None
        self.last_seen_frame = -1
        self.detected_this_frame = False
        self.detected_ppe: List[str] = []
        self.missing_ppe: List[str] = list(cfg.required_ppe)
        self.created_at = time.time()

    # ── detection / box lifecycle ────────────────────────────────────────────
    def update_detection(self, bbox: List[int], frame_idx: int) -> None:
        self.bbox = list(bbox)
        self.last_seen_frame = frame_idx
        self.detected_this_frame = True

    # ── compliance smoothing + hysteresis ────────────────────────────────────
    def update_compliance(self, detected_set: Set[str]) -> None:
        self.history.append(set(detected_set))
        n = len(self.history)

        present: Set[str] = set()
        for cls in self.cfg.required_ppe:
            seen = sum(1 for s in self.history if cls in s)
            if n > 0 and (seen / n) >= self.cfg.presence_ratio:
                present.add(cls)

        self.detected_ppe = sorted(present)
        self.missing_ppe = [c for c in self.cfg.required_ppe if c not in present]
        raw_violation = len(self.missing_ppe) > 0

        if raw_violation:
            self._viol_streak += 1
            self._ok_streak = 0
        else:
            self._ok_streak += 1
            self._viol_streak = 0

        # hysteresis transitions (PENDING resolves to whichever threshold hits first)
        if self.status != VIOLATION and self._viol_streak >= self.cfg.violation_frames:
            self.status = VIOLATION
        elif self.status != COMPLIANT and self._ok_streak >= self.cfg.clear_frames:
            self.status = COMPLIANT

    def render_box(self, now_frame: int) -> Optional[List[int]]:
        """Box to draw: held for up to box_hold_frames after the last detection."""
        if self.bbox is None:
            return None
        if (now_frame - self.last_seen_frame) > self.cfg.box_hold_frames:
            return None
        return self.bbox


class WorkerTrackManager:
    """Owns all TrackedWorkers; thread-safe (inference thread writes, UI reads)."""

    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self.workers: Dict[int, TrackedWorker] = {}
        self.frame_idx = 0
        self._lock = threading.Lock()
        self._events: List[Dict[str, Any]] = []   # violation-onset events
        self._latest_ppe: List[Dict[str, Any]] = []  # raw PPE detections (for drawing)

    def set_ppe(self, ppe: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._latest_ppe = list(ppe)

    def get_ppe(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._latest_ppe)

    def update(self, persons, per_track_ppe: Dict[int, Set[str]], frame_idx: int) -> None:
        with self._lock:
            self.frame_idx = frame_idx
            seen = set()

            for p in persons:
                tid = p["track_id"]
                seen.add(tid)
                w = self.workers.get(tid)
                if w is None:
                    w = TrackedWorker(tid, self.cfg)
                    self.workers[tid] = w
                prev = w.status
                w.update_detection(p["bbox"], frame_idx)
                w.update_compliance(per_track_ppe.get(tid, set()))
                # fire an event only on the COMPLIANT/PENDING → VIOLATION edge
                if prev != VIOLATION and w.status == VIOLATION:
                    self._events.append({
                        "track_id": tid,
                        "missing": list(w.missing_ppe),
                        "ts": time.time(),
                    })

            for tid, w in self.workers.items():
                w.detected_this_frame = tid in seen

            dead = [
                tid for tid, w in self.workers.items()
                if (frame_idx - w.last_seen_frame) > self.cfg.box_hold_frames
            ]
            for tid in dead:
                del self.workers[tid]

    def snapshot(self) -> List[Dict[str, Any]]:
        """Consistent render list for the current frame."""
        with self._lock:
            out = []
            for w in self.workers.values():
                box = w.render_box(self.frame_idx)
                if box is None:
                    continue
                out.append({
                    "track_id":     w.track_id,
                    "bbox":         box,
                    "status":       w.status,
                    "missing_ppe":  list(w.missing_ppe),
                    "detected_ppe": list(w.detected_ppe),
                    "coasting":     not w.detected_this_frame,
                })
            return out

    def drain_events(self) -> List[Dict[str, Any]]:
        with self._lock:
            ev, self._events = self._events, []
            return ev

    def stats(self) -> Dict[str, int]:
        with self._lock:
            comp = sum(1 for w in self.workers.values() if w.status == COMPLIANT)
            viol = sum(1 for w in self.workers.values() if w.status == VIOLATION)
            return {"tracked": len(self.workers), "compliant": comp, "violation": viol}
