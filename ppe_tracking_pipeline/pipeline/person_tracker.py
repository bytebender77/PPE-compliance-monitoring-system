"""
person_tracker.py — YOLO in TRACK mode.

This is the core of the "boxes don't disappear" fix. Instead of detecting
persons independently each frame, we run the detector through ByteTrack /
BoT-SORT with persist=True. The tracker:

  • assigns a STABLE track_id to each worker that survives across frames, and
  • keeps a LOST track alive for `track_buffer` frames (Kalman-predicted
    internally) so a few missed detections don't drop the identity.

We generate the effective tracker .yaml from config.py at launch so --tracker
and --track-buffer are always honoured.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml
from ultralytics import YOLO

log = logging.getLogger(__name__)


class PersonTracker:
    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self.model = YOLO(cfg.person_model)
        self.tracker_cfg_path = self._write_tracker_cfg()
        log.info(
            f"PersonTracker | model={cfg.person_model} tracker={cfg.tracker} "
            f"buffer={cfg.track_buffer} device={cfg.device}"
        )

    def _write_tracker_cfg(self) -> str:
        """Materialise an ultralytics tracker yaml from config (honours buffer)."""
        base: Dict[str, Any] = {
            "tracker_type": self.cfg.tracker,
            "track_high_thresh": 0.25,
            "track_low_thresh": 0.1,
            "new_track_thresh": 0.25,
            "track_buffer": int(self.cfg.track_buffer),
            "match_thresh": 0.8,
            "fuse_score": True,
        }
        if self.cfg.tracker == "botsort":
            base.update({
                "gmc_method": "sparseOptFlow",
                "proximity_thresh": 0.5,
                "appearance_thresh": 0.8,
                "with_reid": False,
                "model": "auto",
            })
        out = Path(__file__).resolve().parent.parent / "trackers" / "_active_tracker.yaml"
        with open(out, "w") as f:
            yaml.safe_dump(base, f, sort_keys=False)
        return str(out)

    def update(self, frame) -> List[Dict[str, Any]]:
        """Run one tracking step. Returns persons with persistent track_id."""
        results = self.model.track(
            frame,
            persist=True,                      # keep tracker state across calls
            conf=self.cfg.person_conf,
            imgsz=self.cfg.person_imgsz,
            classes=[self.cfg.person_class_id],
            tracker=self.tracker_cfg_path,
            device=self.cfg.device,
            half=self.cfg.half,
            verbose=False,
        )
        persons: List[Dict[str, Any]] = []
        if not results:
            return persons
        r = results[0]
        if r.boxes is None or r.boxes.id is None:
            return persons          # no confirmed tracks this frame
        for box in r.boxes:
            if box.id is None:
                continue
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            persons.append({
                "track_id":   int(box.id[0]),
                "bbox":       [x1, y1, x2, y2],
                "confidence": round(float(box.conf[0]), 3),
            })
        return persons
