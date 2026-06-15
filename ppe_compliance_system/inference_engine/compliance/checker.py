"""
inference_engine/compliance/checker.py
───────────────────────────────────────
Stage 3: Associate PPE detections with persons and determine compliance.

ASSOCIATION ALGORITHM
──────────────────────
For each PPE item, we compute what fraction of its bounding box overlaps
with each person's bounding box (overlap fraction = intersection / ppe_area).
The person with the highest overlap fraction "owns" that PPE item, provided
the overlap exceeds a minimum threshold (default 0.1 = 10%).

TEMPORAL SMOOTHING
───────────────────
Live webcam detection is noisy — a vest may be detected in some frames but
missed in others due to lighting/angle. Without smoothing, the compliance
display and alert streak flicker.

Fix: keep a per-track_id memory of recently detected PPE classes. If a class
was seen within the last MEMORY_FRAMES frames, it counts as detected even if
the model missed it this frame. This prevents false violations from
transient misses.
"""

import logging
from collections import defaultdict, deque
from typing import List, Dict, Any

log = logging.getLogger(__name__)

# How many recent inference frames to remember PPE detections.
# 20 frames @ ~15 inferences/sec (frame_skip=2 on 30fps) = ~1.3 seconds.
# If vest is detected in ANY of the last 20 frames it counts as detected.
MEMORY_FRAMES = 20


class ComplianceChecker:
    """
    Associates PPE detections with persons and evaluates compliance.

    Args:
        required_ppe:       List of class names that every person must wear.
                            e.g. ["helmet", "safety_vest"]
        association_thresh: Minimum overlap fraction (PPE area inside person
                            bbox) to count as a match. Default 0.1 (10%).
    """

    def __init__(
        self,
        required_ppe: List[str] = None,
        association_thresh: float = 0.1,
    ) -> None:
        self.required_ppe       = required_ppe or ["helmet", "safety_vest"]
        self.association_thresh = association_thresh
        # Rolling window of sets — each entry is the set of PPE classes detected
        # in that inference frame. Track-ID-free: works even without a tracker.
        self._recent: deque = deque(maxlen=MEMORY_FRAMES)
        self._frame_idx = 0

        log.info(
            f"ComplianceChecker initialised | "
            f"required={self.required_ppe} thresh={self.association_thresh} "
            f"memory={MEMORY_FRAMES}frames"
        )

    def check(
        self,
        persons: List[Dict[str, Any]],
        ppe_items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Enrich each person dict with compliance information.

        Returns:
            Same persons list, each enriched with detected_ppe, missing_ppe,
            is_compliant. Original dicts are NOT mutated — returns copies.
        """
        self._frame_idx += 1

        enriched = [dict(p) for p in persons]
        for p in enriched:
            p["detected_ppe"] = set()
            p["missing_ppe"]  = []
            p["is_compliant"] = True

        # ── Associate each PPE item with a person ─────────────────────────────
        for ppe in ppe_items:
            best_person  = None
            best_overlap = 0.0

            px1, py1, px2, py2 = ppe["bbox"]
            ppe_area = max(1, (px2 - px1) * (py2 - py1))

            for person in enriched:
                bx1, by1, bx2, by2 = person["bbox"]
                ix1 = max(px1, bx1)
                iy1 = max(py1, by1)
                ix2 = min(px2, bx2)
                iy2 = min(py2, by2)

                if ix2 <= ix1 or iy2 <= iy1:
                    continue

                overlap_frac = (ix2 - ix1) * (iy2 - iy1) / ppe_area
                if overlap_frac > best_overlap:
                    best_overlap = overlap_frac
                    best_person  = person

            if best_person is not None and best_overlap >= self.association_thresh:
                best_person["detected_ppe"].add(ppe["class_name"])
                log.debug(
                    f"  {ppe['class_name']} [{ppe['confidence']:.2f}] → person "
                    f"bbox={best_person['bbox']} (overlap={best_overlap:.2f})"
                )

        # NOTE: Temporal smoothing now lives in PPESmoother (detection level), which
        # persists actual PPE *boxes* so they still associate to the correct person
        # via IoU. The old global memory here added every recently-seen class to
        # EVERY person regardless of position — double-smoothing that let a single
        # false vest mark everyone compliant. Removed; association above is per-frame
        # on the already-smoothed detections.

        # ── Compute missing PPE and compliance flag ────────────────────────────
        for p in enriched:
            missing = [
                item for item in self.required_ppe
                if item not in p["detected_ppe"]
            ]
            p["missing_ppe"]  = missing
            p["is_compliant"] = len(missing) == 0
            p["detected_ppe"] = sorted(p["detected_ppe"])

        compliant_count = sum(1 for p in enriched if p["is_compliant"])
        log.debug(f"Compliance: {compliant_count}/{len(enriched)} persons compliant")

        return enriched
