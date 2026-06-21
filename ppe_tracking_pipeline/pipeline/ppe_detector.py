"""
ppe_detector.py — YOLO PPE detection (predict mode).

Runs the custom 4-class model on the full frame. Detections are handed to
association.py, which binds each PPE box to the worker track it overlaps. We
deliberately keep PPE detection separate from person tracking: the person
tracker provides identity/stability, the PPE model provides the safety signal.
"""

import logging
from typing import Any, Dict, List

import numpy as np
from ultralytics import YOLO

log = logging.getLogger(__name__)


class PPEDetector:
    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self.model = YOLO(cfg.ppe_model)
        self.class_ids = list(cfg.ppe_classes.keys())
        log.info(
            f"PPEDetector | model={cfg.ppe_model} conf={cfg.ppe_conf} "
            f"imgsz={cfg.ppe_imgsz} classes={list(cfg.ppe_classes.values())}"
        )

    def detect(self, frame) -> List[Dict[str, Any]]:
        results = self.model(
            frame,
            conf=self.cfg.ppe_conf,
            classes=self.class_ids,
            imgsz=self.cfg.ppe_imgsz,
            device=self.cfg.device,
            half=self.cfg.half,
            verbose=False,
        )
        dets: List[Dict[str, Any]] = []
        for r in results:
            if r.boxes is None:
                continue
            for b in r.boxes:
                cid = int(b.cls[0])
                x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
                dets.append({
                    "bbox":       [x1, y1, x2, y2],
                    "confidence": round(float(b.conf[0]), 3),
                    "class_id":   cid,
                    "class_name": self.cfg.ppe_classes.get(cid, str(cid)),
                })
        return dets

    def warmup(self, iterations: int = 1) -> None:
        dummy = np.zeros((self.cfg.ppe_imgsz, self.cfg.ppe_imgsz, 3), dtype=np.uint8)
        for _ in range(iterations):
            self.detect(dummy)
