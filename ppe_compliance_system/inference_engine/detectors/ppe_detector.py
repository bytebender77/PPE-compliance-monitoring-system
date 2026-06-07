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
# New model (ppe_v3_full) is nc=4 — all 4 classes active.
PPE_CLASS_NAMES = {
    0: "helmet",
    1: "safety_vest",
    2: "goggles",
    3: "gloves",
}

# Class IDs passed to YOLO classes= filter.
_ACTIVE_CLASS_IDS = list(PPE_CLASS_NAMES.keys())  # [0, 1, 2, 3]


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

    def detect(
        self,
        frame: np.ndarray,
        person_boxes: List[List[int]] = None,
        zoom_padding: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Run PPE inference on a single BGR frame.

        When person_boxes is provided (crop-and-zoom mode), each person
        region is cropped, upscaled to 640×640, and run through the model
        independently. This dramatically improves detection at long range
        (e.g. 20m CCTV) where PPE items are only ~15–25px in the full frame.

        Args:
            frame:        OpenCV BGR image, shape (H, W, 3).
            person_boxes: Optional list of [x1,y1,x2,y2] person boxes.
                          When supplied, detection runs per-person crop.
            zoom_padding: Fractional padding around each person crop (0.3 = 30%).

        Returns:
            List of detection dicts with coords in original frame space.
        """
        if self._model is None:
            self._load_model()

        if person_boxes:
            return self._detect_zoomed(frame, person_boxes, zoom_padding)
        return self._detect_full(frame)

    def _detect_full(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Standard full-frame detection."""
        results = self._model(
            frame,
            conf=self.conf_threshold,
            classes=_ACTIVE_CLASS_IDS,
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
                detections.append({
                    "bbox":       [x1, y1, x2, y2],
                    "confidence": round(float(box.conf[0]), 3),
                    "class_id":   class_id,
                    "class_name": class_name,
                    "track_id":   None,
                })
        log.debug(f"PPE detected (full): {len(detections)} item(s)")
        return detections

    def _detect_zoomed(
        self,
        frame: np.ndarray,
        person_boxes: List[List[int]],
        padding: float,
    ) -> List[Dict[str, Any]]:
        """
        Crop-and-zoom detection: run PPE detector on each person crop.
        Maps results back to original frame coordinates.
        """
        import cv2
        fh, fw = frame.shape[:2]
        detections = []

        for pb in person_boxes:
            px1, py1, px2, py2 = pb
            bw = px2 - px1
            bh = py2 - py1

            # Add padding around person box
            pad_x = int(bw * padding)
            pad_y = int(bh * padding)
            cx1 = max(0, px1 - pad_x)
            cy1 = max(0, py1 - pad_y)
            cx2 = min(fw, px2 + pad_x)
            cy2 = min(fh, py2 + pad_y)

            crop = frame[cy1:cy2, cx1:cx2]
            if crop.size == 0:
                continue

            # Resize crop to 640×640 for model input
            crop_h, crop_w = crop.shape[:2]
            zoomed = cv2.resize(crop, (640, 640), interpolation=cv2.INTER_LINEAR)

            results = self._model(
                zoomed,
                conf=self.conf_threshold,
                classes=_ACTIVE_CLASS_IDS,
                verbose=False,
                device=self.device,
                half=self.half,
            )

            for result in results:
                boxes = result.boxes
                if boxes is None or len(boxes) == 0:
                    continue
                for box in boxes:
                    # Map back from 640×640 zoomed space → crop space → full frame
                    zx1, zy1, zx2, zy2 = box.xyxy[0].tolist()
                    ox1 = int(cx1 + (zx1 / 640) * crop_w)
                    oy1 = int(cy1 + (zy1 / 640) * crop_h)
                    ox2 = int(cx1 + (zx2 / 640) * crop_w)
                    oy2 = int(cy1 + (zy2 / 640) * crop_h)
                    class_id   = int(box.cls[0])
                    class_name = PPE_CLASS_NAMES.get(class_id, f"class_{class_id}")
                    detections.append({
                        "bbox":       [ox1, oy1, ox2, oy2],
                        "confidence": round(float(box.conf[0]), 3),
                        "class_id":   class_id,
                        "class_name": class_name,
                        "track_id":   None,
                    })

        log.debug(f"PPE detected (zoomed): {len(detections)} item(s)")
        return detections

    def warmup(self, iterations: int = 3) -> None:
        """Warm up the model pipeline before the main loop."""
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        for _ in range(iterations):
            self.detect(dummy)
        log.info(f"PPE model warmup complete ({iterations} iterations)")
