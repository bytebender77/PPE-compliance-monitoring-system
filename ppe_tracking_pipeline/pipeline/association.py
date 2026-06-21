"""
association.py — bind PPE detections to worker tracks.

For each PPE box we find the track whose bounding box contains the largest
fraction of the PPE box (intersection / PPE area). The PPE item is assigned to
that track if the overlap clears `association_overlap`. Returns a mapping of
track_id → set of PPE class names detected on that worker THIS frame.

Because identities come from the tracker (stable across frames), PPE evidence
accumulates reliably per worker even though raw detections flicker.
"""

from typing import Any, Dict, List, Set


def associate(
    persons: List[Dict[str, Any]],
    ppe_items: List[Dict[str, Any]],
    min_overlap: float = 0.10,
) -> Dict[int, Set[str]]:
    per_track: Dict[int, Set[str]] = {p["track_id"]: set() for p in persons}

    for ppe in ppe_items:
        px1, py1, px2, py2 = ppe["bbox"]
        ppe_area = max(1, (px2 - px1) * (py2 - py1))
        best_tid, best_frac = None, 0.0

        for p in persons:
            bx1, by1, bx2, by2 = p["bbox"]
            ix1, iy1 = max(px1, bx1), max(py1, by1)
            ix2, iy2 = min(px2, bx2), min(py2, by2)
            if ix2 <= ix1 or iy2 <= iy1:
                continue
            frac = (ix2 - ix1) * (iy2 - iy1) / ppe_area
            if frac > best_frac:
                best_frac, best_tid = frac, p["track_id"]

        if best_tid is not None and best_frac >= min_overlap:
            per_track[best_tid].add(ppe["class_name"])

    return per_track
