"""
inference_engine/detectors/person_detector.py
─────────────────────────────────────────────
Stage 1: Detect persons only.
Stage 3: This file will be renamed/extended to PPEDetector which detects
         helmet, vest, goggles, person in a single forward pass.

DESIGN PHILOSOPHY
─────────────────
This class does ONE thing: receive a raw BGR frame, run YOLOv8 inference,
return a list of detection dicts. It has NO knowledge of:
  - How frames arrive (camera / file / stream)
  - How results are displayed
  - Whether results are logged or alerted on

This strict separation means we can unit-test the detector by passing in
a dummy NumPy array and asserting the output format — no camera needed.

OUTPUT FORMAT
─────────────
Every detection is returned as a plain dict:

    {
        "bbox":        [x1, y1, x2, y2],   # int pixel coords, top-left to bottom-right
        "confidence":  0.87,               # float 0–1
        "class_id":    0,                  # int YOLO class index
        "class_name":  "person",           # str human-readable label
        "track_id":    None,               # populated by tracker in Stage 2
    }

Using plain dicts (not custom dataclasses) keeps the format JSON-serialisable
from day one — Stage 5 will need to write this to SQLite and Stage 6 will
need to send it over a WebSocket. No conversion step required.
"""

import logging
from typing import List, Dict, Any

import numpy as np

log = logging.getLogger(__name__)


class PersonDetector:
    """
    Wraps YOLOv8 to detect persons (and later PPE classes) in a video frame.

    Args:
        model_path:       Path to .pt weights file. "yolov8n.pt" is auto-downloaded
                          by Ultralytics on first use if not found locally.
        conf_threshold:   Minimum confidence score to report a detection (0–1).
        device:           "cpu" or "cuda". YOLOv8 will auto-fall-back to CPU
                          if CUDA is requested but not available.
    """

    # YOLO class ID for "person" in the standard COCO-pretrained model.
    # After fine-tuning on our custom PPE dataset (Stage 3), this stays 0.
    PERSON_CLASS_ID = 0

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf_threshold: float = 0.4,
        device: str = "cpu",
        half: bool = False,
        track: bool = True,
    ) -> None:
        self.model_path      = model_path
        self.conf_threshold  = conf_threshold
        self.device          = device
        # FP16 only works on CUDA — silently disable on CPU/MPS
        self.half            = half and device == "cuda"
        self._model          = None          # lazy-loaded on first detect() call

        # ── ByteTrack (Supervision) — assigns a stable track_id to each person ──
        # Without a tracker, track_id is always None, which silently disables the
        # alert-streak logic and per-worker temporal smoothing downstream. ByteTrack
        # follows each worker across frames so a transient missed detection doesn't
        # reset their compliance state or spawn a duplicate alert.
        self.track   = track
        self._tracker = None
        if self.track:
            try:
                import supervision as sv
                self._tracker = sv.ByteTrack()
                log.info("ByteTrack tracker enabled (supervision)")
            except ImportError:
                log.warning(
                    "supervision not installed — tracking disabled "
                    "(track_id will stay None). Run: pip install supervision"
                )
                self.track = False

        log.info(
            f"PersonDetector initialised | model={model_path} "
            f"conf={conf_threshold} device={device} half={self.half} track={self.track}"
        )

    # ── Model loading ──────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        """
        Lazy-load the YOLO model on first inference call.

        WHY LAZY LOADING?
        If the model were loaded in __init__, importing this module would
        immediately try to pull ~6MB weights — slow, and fails in unit tests
        that don't need actual inference. Lazy loading means the model is only
        loaded when .detect() is first called, i.e. when the pipeline actually
        starts.
        """
        try:
            from ultralytics import YOLO          # import here, not at top of file
            self._model = YOLO(self.model_path)   # loads weights from disk or downloads
            log.info(f"YOLO model loaded from: {self.model_path}")
        except ImportError:
            raise RuntimeError(
                "ultralytics is not installed. Run: pip install ultralytics"
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to load YOLO model '{self.model_path}': {exc}")

    # ── Core detection ─────────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Run inference on a single BGR frame and return person detections.

        Args:
            frame: OpenCV BGR image as a NumPy uint8 array, shape (H, W, 3).

        Returns:
            List of detection dicts. Empty list if no persons detected.

        Why filter by PERSON_CLASS_ID here?
            The COCO-pretrained model detects 80 classes. We only want persons
            in Stage 1. In Stage 3 we will detect all PPE classes in a single
            pass by removing this filter and returning all classes.
        """
        if self._model is None:
            self._load_model()

        # ── Run YOLO inference ─────────────────────────────────────────────────
        # verbose=False suppresses Ultralytics' per-frame console output.
        # conf=self.conf_threshold tells YOLO to suppress low-confidence boxes
        # before NMS — saves processing time vs filtering results afterwards.
        results = self._model(
            frame,
            conf=self.conf_threshold,
            verbose=False,
            device=self.device,
            half=self.half,
        )

        # ── Parse results ──────────────────────────────────────────────────────
        # results is a list with one element per input image.
        # results[0].boxes contains all detected bounding boxes.
        detections = []
        for result in results:
            boxes = result.boxes                   # Ultralytics Boxes object

            if boxes is None or len(boxes) == 0:
                continue                            # no detections in this frame

            for box in boxes:
                class_id = int(box.cls[0])         # YOLO class index

                # Stage 1: only report persons.
                # Stage 3: remove this guard — return all detected classes.
                if class_id != self.PERSON_CLASS_ID:
                    continue

                # box.xyxy[0] is a tensor [x1, y1, x2, y2] in pixel coords.
                # .tolist() converts it to a plain Python list of floats.
                # We cast to int because pixel coordinates are always integers.
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]

                confidence  = float(box.conf[0])   # confidence as Python float

                # Map class ID to human-readable name using YOLO's built-in
                # class name list. For COCO: 0 → "person", 67 → "cell phone", etc.
                class_name = result.names.get(class_id, f"class_{class_id}")

                detections.append({
                    "bbox":       [x1, y1, x2, y2],
                    "confidence": round(confidence, 3),  # 3 decimal places is enough
                    "class_id":   class_id,
                    "class_name": class_name,
                    "track_id":   None,        # populated by ByteTrack in Stage 2
                    # Stage 3 will add:
                    # "missing_ppe": [],       — list of missing items
                    # "is_compliant": True,    — boolean compliance flag
                })

        # ── Assign stable track IDs via ByteTrack ──────────────────────────────
        if self.track and self._tracker is not None and detections:
            detections = self._assign_track_ids(detections)

        log.debug(f"Detected {len(detections)} person(s) in frame")
        return detections

    def _assign_track_ids(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run ByteTrack over this frame's person boxes and write a stable track_id
        back onto each detection dict.

        ByteTrack matches current boxes to tracks from previous frames (by IoU +
        motion), so the same worker keeps the same id across frames. Detections
        that the tracker can't confidently associate are dropped from its output;
        we leave those with track_id=None rather than discard them.
        """
        import numpy as np
        import supervision as sv

        sv_det = sv.Detections(
            xyxy=np.array([d["bbox"] for d in detections], dtype=float),
            confidence=np.array([d["confidence"] for d in detections], dtype=float),
            class_id=np.array([d["class_id"] for d in detections], dtype=int),
        )

        tracked = self._tracker.update_with_detections(sv_det)

        # Match tracked boxes back to our dicts by bbox identity (ByteTrack returns
        # the same xyxy it was given for confirmed tracks).
        for i in range(len(tracked)):
            tx1, ty1, tx2, ty2 = (int(v) for v in tracked.xyxy[i])
            tid = tracked.tracker_id[i] if tracked.tracker_id is not None else None
            for d in detections:
                if d["bbox"] == [tx1, ty1, tx2, ty2]:
                    d["track_id"] = int(tid) if tid is not None else None
                    break

        return detections

    # ── Utility ────────────────────────────────────────────────────────────────

    def warmup(self, iterations: int = 3) -> None:
        """
        Run inference on a black frame to warm up GPU/model pipeline.

        WHY WARMUP?
        The first inference call is always slower because CUDA kernels need
        JIT compilation. Running a few dummy frames at startup ensures the
        first real frame runs at full speed. Important for consistent FPS
        measurement. Call this right after creating the detector in main.py
        if startup latency matters.
        """
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        for _ in range(iterations):
            self.detect(dummy)
        log.info(f"Model warmup complete ({iterations} iterations)")
