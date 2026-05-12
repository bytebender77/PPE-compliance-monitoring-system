"""
inference_engine/utils/video_source.py
───────────────────────────────────────
Abstracts the three video input types behind one interface:
  1. Webcam          →  source = "0"  (string "0", converted to int 0)
  2. Recorded MP4    →  source = "path/to/video.mp4"
  3. RTSP IP camera  →  source = "rtsp://user:pass@192.168.1.100/stream1"

WHY AN ABSTRACTION?
The rest of the pipeline (detector, annotator, main loop) should NOT care
whether video is coming from a webcam or an IP camera. If tomorrow the plant
upgrades from RTSP to ONVIF streams, we update ONLY this file.

This is the "Open/Closed Principle": the pipeline is closed for modification,
open for extension via this interface.

THREAD SAFETY NOTE (for Stage 2)
VideoSource is NOT thread-safe as written. When we add ByteTrack in Stage 2,
we will run frame capture in a dedicated background thread (a pattern called
"threaded video capture") so the inference loop is never waiting on I/O.
The class is designed so adding threading requires changes only here — not
in main.py or the detector.
"""

import logging
import cv2
import numpy as np
from typing import Optional

log = logging.getLogger(__name__)


class VideoSource:
    """
    Unified wrapper around OpenCV's VideoCapture.

    Args:
        source: String representing the video source. See module docstring.

    Example:
        src = VideoSource("0")          # webcam
        while True:
            frame = src.read()
            if frame is None:
                break
        src.release()
    """

    def __init__(self, source: str) -> None:
        self.source_str = source

        # ── Resolve source type ────────────────────────────────────────────────
        # OpenCV's VideoCapture accepts either an int (device index) or a string
        # (file path or RTSP URL). We accept everything as a string from the CLI
        # and do the conversion here — in one place.
        resolved_source = self._resolve_source(source)

        log.info(f"Opening video source: {source!r}")
        self._cap = cv2.VideoCapture(resolved_source)

        if not self._cap.isOpened():
            log.error(f"Failed to open video source: {source!r}")
        else:
            w   = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h   = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self._cap.get(cv2.CAP_PROP_FPS)
            log.info(f"Video source ready: {w}×{h} @ {fps:.1f} fps")

    # ── Source resolution ──────────────────────────────────────────────────────

    @staticmethod
    def _resolve_source(source: str):
        """
        Convert source string to the correct type for cv2.VideoCapture.

        cv2.VideoCapture(0)      → webcam index 0
        cv2.VideoCapture("0")    → ALSO works on most systems but is not
                                   guaranteed — so we explicitly cast to int.
        cv2.VideoCapture("path") → file or RTSP URL (string stays as string)
        """
        # If the string is a pure integer, treat as device index
        try:
            return int(source)                   # "0", "1", "2" → webcam
        except ValueError:
            return source                        # MP4 path or RTSP URL

    # ── Public interface ───────────────────────────────────────────────────────

    def is_open(self) -> bool:
        """Return True if the capture device was successfully opened."""
        return self._cap.isOpened()

    def read(self) -> Optional[np.ndarray]:
        """
        Read the next frame from the source.

        Returns:
            BGR NumPy array on success, None on failure (end of file,
            dropped stream, etc.).

        Why return None instead of raising?
            None is the standard OpenCV/Python idiom. The caller (main loop)
            checks for None and breaks cleanly. Exceptions would require
            try/except in the hot loop — slower and noisier.
        """
        ret, frame = self._cap.read()
        if not ret:
            return None
        return frame

    def release(self) -> None:
        """Release the capture device and free resources."""
        if self._cap:
            self._cap.release()
            log.info(f"Released video source: {self.source_str!r}")

    # ── Metadata helpers ───────────────────────────────────────────────────────

    @property
    def width(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def height(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    @property
    def native_fps(self) -> float:
        """FPS reported by the source (may be 0 for live streams)."""
        return self._cap.get(cv2.CAP_PROP_FPS)

    def __repr__(self) -> str:
        return f"VideoSource(source={self.source_str!r}, open={self.is_open()})"
