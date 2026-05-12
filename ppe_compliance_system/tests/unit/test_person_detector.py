"""
tests/unit/test_person_detector.py
───────────────────────────────────
Unit tests for PersonDetector.

TESTING PHILOSOPHY
These tests verify the OUTPUT FORMAT and EDGE CASE HANDLING of the detector
without requiring an actual YOLO model to be downloaded. We use mocking to
replace the Ultralytics YOLO object with a fake that returns controlled results.

This means:
  - Tests run instantly (no GPU / download needed)
  - Tests are deterministic (no randomness from real inference)
  - Tests fail loud and early if someone changes the output dict format

Run with:
    pytest tests/unit/test_person_detector.py -v
"""

import sys
import types
import numpy as np
import pytest
from unittest.mock import MagicMock, patch


# ── Fake Ultralytics structure ─────────────────────────────────────────────────
# We build the minimal mock structure that PersonDetector's detect() method
# expects from the YOLO model. This lets us test parsing logic without importing
# the real ultralytics package (which isn't installed in the test environment).

def _make_fake_box(x1, y1, x2, y2, conf, cls_id):
    """Create a fake YOLO box object mimicking Ultralytics Boxes API."""
    import torch
    box = MagicMock()
    box.xyxy = [torch.tensor([x1, y1, x2, y2], dtype=torch.float32)]
    box.conf  = torch.tensor([conf])
    box.cls   = torch.tensor([cls_id])
    return box


def _make_fake_result(boxes_data, class_names=None):
    """Create a fake YOLO Results object with given boxes."""
    result = MagicMock()
    result.names = class_names or {0: "person", 1: "helmet", 2: "safety_vest"}
    result.boxes = boxes_data if boxes_data else []
    return result


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def dummy_frame():
    """640×640 black frame — the standard input size."""
    return np.zeros((640, 640, 3), dtype=np.uint8)


@pytest.fixture
def detector():
    """PersonDetector with model loading mocked out."""
    from ppe_compliance_system.inference_engine.detectors.person_detector import PersonDetector
    det = PersonDetector(model_path="fake.pt", conf_threshold=0.4)
    # Inject a mock model so _load_model() is never called
    det._model = MagicMock()
    return det


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestPersonDetectorOutputFormat:
    """The output dict must always have the correct keys and types."""

    def test_returns_list(self, detector, dummy_frame):
        """detect() must always return a list."""
        detector._model.return_value = [_make_fake_result([])]
        result = detector.detect(dummy_frame)
        assert isinstance(result, list)

    def test_empty_when_no_detections(self, detector, dummy_frame):
        """Empty list when YOLO finds nothing."""
        detector._model.return_value = [_make_fake_result(None)]
        result = detector.detect(dummy_frame)
        assert result == []

    def test_detection_dict_keys(self, detector, dummy_frame):
        """Every detection must have exactly the required keys."""
        try:
            import torch
        except ImportError:
            pytest.skip("torch not installed")

        fake_box = _make_fake_box(10, 20, 100, 200, 0.85, 0)  # person
        result_obj = _make_fake_result([fake_box])
        result_obj.boxes = [fake_box]
        detector._model.return_value = [result_obj]

        detections = detector.detect(dummy_frame)
        assert len(detections) == 1
        det = detections[0]

        required_keys = {"bbox", "confidence", "class_id", "class_name", "track_id"}
        assert required_keys.issubset(det.keys()), \
            f"Missing keys: {required_keys - det.keys()}"

    def test_bbox_is_list_of_four_ints(self, detector, dummy_frame):
        """bbox must be [x1, y1, x2, y2] as integers."""
        try:
            import torch
        except ImportError:
            pytest.skip("torch not installed")

        fake_box = _make_fake_box(10, 20, 100, 200, 0.85, 0)
        result_obj = _make_fake_result([fake_box])
        result_obj.boxes = [fake_box]
        detector._model.return_value = [result_obj]

        det = detector.detect(dummy_frame)[0]
        bbox = det["bbox"]

        assert isinstance(bbox, list) and len(bbox) == 4
        assert all(isinstance(v, int) for v in bbox), \
            "bbox coordinates must be int (pixel coords)"

    def test_track_id_is_none_in_stage_1(self, detector, dummy_frame):
        """track_id must be None until ByteTrack is added in Stage 2."""
        try:
            import torch
        except ImportError:
            pytest.skip("torch not installed")

        fake_box = _make_fake_box(10, 20, 100, 200, 0.85, 0)
        result_obj = _make_fake_result([fake_box])
        result_obj.boxes = [fake_box]
        detector._model.return_value = [result_obj]

        det = detector.detect(dummy_frame)[0]
        assert det["track_id"] is None, "Stage 1: track_id must be None"

    def test_confidence_is_rounded_float(self, detector, dummy_frame):
        """confidence should be a float rounded to 3 decimal places."""
        try:
            import torch
        except ImportError:
            pytest.skip("torch not installed")

        fake_box = _make_fake_box(10, 20, 100, 200, 0.876543, 0)
        result_obj = _make_fake_result([fake_box])
        result_obj.boxes = [fake_box]
        detector._model.return_value = [result_obj]

        det = detector.detect(dummy_frame)[0]
        # 0.876543 rounded to 3 dp = 0.877
        assert det["confidence"] == round(0.876543, 3)


class TestPersonDetectorFiltering:
    """Stage 1 must only return person detections, filter all other classes."""

    def test_filters_non_person_classes(self, detector, dummy_frame):
        """Helmet (class 1) detections must be excluded in Stage 1."""
        try:
            import torch
        except ImportError:
            pytest.skip("torch not installed")

        person_box = _make_fake_box(10, 20, 100, 200, 0.9, 0)    # person
        helmet_box = _make_fake_box(15, 25, 50, 60,   0.8, 1)    # helmet
        vest_box   = _make_fake_box(10, 80, 100, 200, 0.75, 2)   # safety_vest

        result_obj = _make_fake_result([person_box, helmet_box, vest_box])
        result_obj.boxes = [person_box, helmet_box, vest_box]
        detector._model.return_value = [result_obj]

        detections = detector.detect(dummy_frame)

        assert len(detections) == 1, "Only the person detection should be returned"
        assert detections[0]["class_name"] == "person"


class TestFPSCounter:
    """FPSCounter must return stable, non-negative values."""

    def test_fps_is_zero_on_first_call(self):
        from ppe_compliance_system.inference_engine.utils.fps_counter import FPSCounter
        counter = FPSCounter(window=30)
        fps = counter.update()
        assert fps == 0.0

    def test_fps_positive_after_multiple_updates(self):
        import time
        from ppe_compliance_system.inference_engine.utils.fps_counter import FPSCounter
        counter = FPSCounter(window=10)
        for _ in range(5):
            counter.update()
            time.sleep(0.01)   # 10ms between frames → ~100 fps
        assert counter.fps > 0

    def test_reset_clears_state(self):
        import time
        from ppe_compliance_system.inference_engine.utils.fps_counter import FPSCounter
        counter = FPSCounter(window=10)
        for _ in range(5):
            counter.update()
        counter.reset()
        assert counter.fps == 0.0


class TestVideoSourceResolution:
    """VideoSource._resolve_source must convert string integers to int."""

    def test_string_zero_becomes_int(self):
        from ppe_compliance_system.inference_engine.utils.video_source import VideoSource
        assert VideoSource._resolve_source("0") == 0

    def test_string_one_becomes_int(self):
        from ppe_compliance_system.inference_engine.utils.video_source import VideoSource
        assert VideoSource._resolve_source("1") == 1

    def test_mp4_path_stays_string(self):
        from ppe_compliance_system.inference_engine.utils.video_source import VideoSource
        assert VideoSource._resolve_source("video.mp4") == "video.mp4"

    def test_rtsp_url_stays_string(self):
        from ppe_compliance_system.inference_engine.utils.video_source import VideoSource
        result = VideoSource._resolve_source("rtsp://user:pass@192.168.1.1/stream")
        assert result == "rtsp://user:pass@192.168.1.1/stream"
