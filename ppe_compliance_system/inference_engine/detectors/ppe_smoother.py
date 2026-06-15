"""
inference_engine/detectors/ppe_smoother.py
───────────────────────────────────────────
Detection persistence for PPE items.

The custom PPE model detects items (esp. the safety vest) intermittently on
live video — a strong hit on one frame, then several empty frames, then a
faint hit. Drawing only the raw per-frame detections makes the box flicker and
makes compliance status oscillate.

Real PPE systems hold a detection for a short window after it was last seen:
a worker standing still in a vest still has the vest even if one frame was
blurry. This smoother does exactly that — per class, it remembers the most
recent detection box and keeps emitting it for TTL_FRAMES after the last sight.

It is intentionally simple and tracker-free (we have no per-worker IDs for PPE):
it persists detections at the frame level, which is enough to stabilise the
single-worker live demo and the compliance streak.
"""

import logging
from typing import List, Dict, Any

log = logging.getLogger(__name__)


class PPESmoother:
    """
    Holds each PPE class's most recent detection for a short window so brief
    misses don't drop it.

    Args:
        ttl_frames: How many frames to keep emitting a class after it was last
                    detected. ~45 frames ≈ 1.5 s at 30 fps.
        classes:    Which class names to smooth. Default: all PPE classes.
                    (You usually only need this for the unstable ones, but
                    smoothing all is harmless and keeps helmet/goggles steady.)
    """

    def __init__(self, ttl_frames: int = 45, classes: List[str] = None) -> None:
        self.ttl_frames = ttl_frames
        self.classes    = set(classes) if classes else None  # None = all
        # class_name -> {"det": <detection dict>, "age": int}
        self._held: Dict[str, Dict[str, Any]] = {}
        log.info(f"PPESmoother initialised | ttl={ttl_frames} classes={classes or 'all'}")

    def _should_smooth(self, cls_name: str) -> bool:
        return self.classes is None or cls_name in self.classes

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge this frame's raw detections with recently-held ones.

        For each smoothed class: if detected this frame, refresh the held box
        (age 0). Otherwise keep the held box and increment its age; drop it once
        age exceeds ttl_frames.

        Non-smoothed classes pass through unchanged. Returns a new list; the
        held detections are marked with "smoothed": True so the UI can show
        them differently if desired.
        """
        # Index this frame's detections by class (keep the highest-confidence one)
        this_frame: Dict[str, Dict[str, Any]] = {}
        passthrough: List[Dict[str, Any]] = []

        for det in detections:
            cls = det["class_name"]
            if not self._should_smooth(cls):
                passthrough.append(det)
                continue
            if cls not in this_frame or det["confidence"] > this_frame[cls]["confidence"]:
                this_frame[cls] = det

        # Refresh held state for classes seen this frame
        for cls, det in this_frame.items():
            self._held[cls] = {"det": dict(det), "age": 0}

        # Age out held classes not seen this frame; emit those still alive
        out: List[Dict[str, Any]] = list(passthrough)
        for cls in list(self._held.keys()):
            if cls in this_frame:
                out.append(dict(this_frame[cls]))           # fresh detection
                continue
            self._held[cls]["age"] += 1
            if self._held[cls]["age"] > self.ttl_frames:
                del self._held[cls]                          # expired
            else:
                held = dict(self._held[cls]["det"])
                held["smoothed"] = True                      # held-over, not seen this frame
                out.append(held)

        return out
