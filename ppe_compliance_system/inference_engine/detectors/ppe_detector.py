"""
inference_engine/detectors/ppe_detector.py
──────────────────────────────────────────
Stage 3: Detect PPE items (helmet, safety_vest, goggles) using our custom
trained model (models/best.pt).

Same interface as PersonDetector — takes a BGR frame, returns a list of
detection dicts. The rest of the pipeline never needs to know whether it's
talking to the person detector or the PPE detector.

OUTPUT FORMAT (identical to PersonDetector for consistency)
────────────────────────────────────────────────────────────
    {
        "bbox":        [x1, y1, x2, y2],   # int pixel coords
        "confidence":  0.91,               # float 0–1
        "class_id":    0,                  # 0=helmet 1=safety_vest 2=goggles
        "class_name":  "helmet",           # str
        "track_id":    None,               # not used for PPE items
    }
"""

import logging
from typing import List, Dict, Any

import numpy as np

log = logging.getLogger(__name__)

# Class IDs in our trained model (must match data/data.yaml)
PPE_CLASS_NAMES = {
    0: "helmet",
    1: "safety_vest",
    2: "goggles",
}


class PPEDetector:
    """
    Wraps our custom-trained YOLOv8s model to detect PPE items in a frame.

    Runs independently from PersonDetector — the two detectors operate on
    the same frame in parallel. ComplianceChecker then associates PPE
    detections with person detections.

    Args:
        model_path:     Path to best.pt (our trained weights).
        conf_threshold: Minimum confidence to report a detection.
        device:         "cpu", "cuda", or "mps".
    """

    def __init__(
        self,
        model_path: str = "models/best.pt",
        conf_threshold: float = 0.35,
        device: str = "cpu",
        half: bool = False,
    ) -> None:
        self.model_path     = model_path
        self.conf_threshold = conf_threshold
        self.device         = device
        # FP16 only works on CUDA — silently disable on CPU/MPS
        self.half           = half and device == "cuda"
        self._model         = None   # lazy-loaded on first detect() call

        log.info(
            f"PPEDetector initialised | model={model_path} "
            f"conf={conf_threshold} device={device} half={self.half}"
        )

    def _load_model(self) -> None:
        """Lazy-load the YOLO model on first inference call."""
        try:
            from ultralytics import YOLO
            self._model = YOLO(self.model_path)
            log.info(f"PPE model loaded from: {self.model_path}")
        except ImportError:
            raise RuntimeError(
                "ultralytics is not installed. Run: pip install ultralytics"
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load PPE model '{self.model_path}': {exc}"
            )

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Run PPE inference on a single BGR frame.

        Returns all detected PPE items regardless of class — the
        ComplianceChecker decides which person each item belongs to.

        Args:
            frame: OpenCV BGR image, shape (H, W, 3).

        Returns:
            List of detection dicts. Empty list if nothing detected.
        """
        if self._model is None:
            self._load_model()

        results = self._model(
            frame,
            conf=self.conf_threshold,
            verbose=False,
            device=self.device,
            half=self.half,
        )

        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                continue

            for box in boxes:
                class_id   = int(box.cls[0])
                class_name = PPE_CLASS_NAMES.get(class_id, f"class_{class_id}")
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                confidence = float(box.conf[0])

                detections.append({
                    "bbox":       [x1, y1, x2, y2],
                    "confidence": round(confidence, 3),
                    "class_id":   class_id,
                    "class_name": class_name,
                    "track_id":   None,
                })

        log.debug(f"PPE detected: {len(detections)} item(s)")
        return detections

    def warmup(self, iterations: int = 3) -> None:
        """Warm up the model pipeline before the main loop."""
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        for _ in range(iterations):
            self.detect(dummy)
        log.info(f"PPE model warmup complete ({iterations} iterations)")
