"""
inference_engine/compliance/checker.py
───────────────────────────────────────
Stage 3: Associate PPE detections with persons and determine compliance.

THE CORE PROBLEM THIS SOLVES
──────────────────────────────
PersonDetector gives us person bboxes.
PPEDetector gives us helmet/vest/goggles bboxes.
But neither knows which PPE belongs to which person.

This module answers: "For each detected person, which PPE items are they
wearing, and what are they missing?"

ASSOCIATION ALGORITHM
──────────────────────
For each PPE item, we compute what fraction of its bounding box overlaps
with each person's bounding box (overlap fraction = intersection / ppe_area).
The person with the highest overlap fraction "owns" that PPE item, provided
the overlap exceeds a minimum threshold (default 0.1 = 10%).

Why overlap fraction instead of IoU?
  → A helmet bbox is small relative to the full person bbox. IoU would give
    a very low score even for a perfect match. Measuring how much of the PPE
    box falls inside the person box is more robust for this use case.

OUTPUT — enriched person dicts
──────────────────────────────
Each person dict is enriched with:
    {
        ...original fields...,
        "detected_ppe":  {"helmet", "safety_vest"},   # set of what was found
        "missing_ppe":   ["goggles"],                 # list of what's required but absent
        "is_compliant":  False,                       # True only if missing_ppe is empty
    }
"""

import logging
from typing import List, Dict, Any, Set

log = logging.getLogger(__name__)


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
        self.required_ppe        = required_ppe or ["helmet", "safety_vest"]
        self.association_thresh  = association_thresh

        log.info(
            f"ComplianceChecker initialised | "
            f"required={self.required_ppe} thresh={self.association_thresh}"
        )

    def check(
        self,
        persons: List[Dict[str, Any]],
        ppe_items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Enrich each person dict with compliance information.

        Args:
            persons:   List of person detection dicts from PersonDetector.
            ppe_items: List of PPE detection dicts from PPEDetector.

        Returns:
            Same persons list, each enriched with detected_ppe, missing_ppe,
            is_compliant. Original dicts are NOT mutated — returns copies.
        """
        # Deep-copy so we never mutate the input dicts
        enriched = [dict(p) for p in persons]

        # Initialise compliance fields on every person
        for p in enriched:
            p["detected_ppe"] = set()
            p["missing_ppe"]  = []
            p["is_compliant"] = True   # assume compliant until proven otherwise

        if not ppe_items:
            # No PPE detected → everyone is missing everything required
            for p in enriched:
                p["missing_ppe"]  = list(self.required_ppe)
                p["is_compliant"] = len(self.required_ppe) == 0
            return enriched

        # ── Associate each PPE item with a person ─────────────────────────────
        for ppe in ppe_items:
            best_person  = None
            best_overlap = 0.0

            px1, py1, px2, py2 = ppe["bbox"]
            ppe_area = max(1, (px2 - px1) * (py2 - py1))

            for person in enriched:
                bx1, by1, bx2, by2 = person["bbox"]

                # Compute intersection rectangle
                ix1 = max(px1, bx1)
                iy1 = max(py1, by1)
                ix2 = min(px2, bx2)
                iy2 = min(py2, by2)

                if ix2 <= ix1 or iy2 <= iy1:
                    continue   # no overlap

                intersection    = (ix2 - ix1) * (iy2 - iy1)
                overlap_frac    = intersection / ppe_area

                if overlap_frac > best_overlap:
                    best_overlap = overlap_frac
                    best_person  = person

            # Assign if overlap is sufficient
            if best_person is not None and best_overlap >= self.association_thresh:
                best_person["detected_ppe"].add(ppe["class_name"])
                log.debug(
                    f"  {ppe['class_name']} [{ppe['confidence']:.2f}] → person "
                    f"bbox={best_person['bbox']} (overlap={best_overlap:.2f})"
                )

        # ── Compute missing PPE and compliance flag ────────────────────────────
        for p in enriched:
            missing = [
                item for item in self.required_ppe
                if item not in p["detected_ppe"]
            ]
            p["missing_ppe"]  = missing
            p["is_compliant"] = len(missing) == 0

            # Convert set to sorted list for JSON-serialisability (Stage 5/6)
            p["detected_ppe"] = sorted(p["detected_ppe"])

        compliant_count = sum(1 for p in enriched if p["is_compliant"])
        log.debug(
            f"Compliance: {compliant_count}/{len(enriched)} persons compliant"
        )

        return enriched
