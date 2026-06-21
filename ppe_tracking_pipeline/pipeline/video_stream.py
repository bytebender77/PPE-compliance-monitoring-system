"""
video_stream.py — frame sources.

ThreadedCamera: a background capture thread that always holds the LATEST frame
and drops stale ones. Used for LIVE sources (webcam / RTSP) so the consumer
never accumulates lag behind the camera. For recorded FILES, run.py reads
frames synchronously in order so the tracker sees an unbroken temporal sequence
and the output video keeps every frame.
"""

import logging
import threading
from typing import Optional, Tuple

import cv2
import numpy as np

log = logging.getLogger(__name__)


def resolve_source(source: str):
    """'0' → webcam index 0; otherwise a file path or RTSP/HTTP URL."""
    try:
        return int(source)
    except (ValueError, TypeError):
        return source


def is_live_source(source: str) -> bool:
    s = str(source)
    return s.isdigit() or s.lower().startswith(("rtsp://", "http://", "https://"))


class ThreadedCamera:
    """Always-latest-frame capture on a daemon thread (for live sources)."""

    def __init__(self, source: str) -> None:
        self.source_str = source
        self._cap = cv2.VideoCapture(resolve_source(source))
        try:
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        self._lock = threading.Lock()
        self._frame: Optional[np.ndarray] = None
        self._seq = 0
        self._running = False
        self._ended = False
        self._thread: Optional[threading.Thread] = None

        if self._cap.isOpened():
            w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            log.info(f"ThreadedCamera ready: {w}x{h}  source={source!r}")
        else:
            log.error(f"ThreadedCamera failed to open: {source!r}")

    def is_open(self) -> bool:
        return self._cap.isOpened()

    def start(self) -> "ThreadedCamera":
        self._running = True
        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()
        return self

    def _update(self) -> None:
        while self._running:
            ok, frame = self._cap.read()
            if not ok:
                self._ended = True
                break
            with self._lock:
                self._frame = frame
                self._seq += 1

    def read(self) -> Tuple[int, Optional[np.ndarray]]:
        """Return (seq, latest_frame). seq increments per grabbed frame."""
        with self._lock:
            return self._seq, self._frame

    @property
    def ended(self) -> bool:
        return self._ended

    def release(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._cap:
            self._cap.release()
        log.info(f"ThreadedCamera released: {self.source_str!r}")
