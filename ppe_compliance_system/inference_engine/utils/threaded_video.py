"""
inference_engine/utils/threaded_video.py
─────────────────────────────────────────
Background-thread frame grabber for LIVE sources (webcam / RTSP).

WHY
───
On an M1 Pro, running the PPE detector at imgsz=1280 takes ~150–200 ms/frame.
If capture + inference + display all share one thread, the camera's internal
buffer fills up and the displayed video drifts further and further behind
reality (the "lag" the operator sees).

This class moves capture into its own thread that continuously grabs frames and
keeps ONLY THE LATEST one. The main loop always works on "now" — stale frames
are discarded instead of queueing up — so the live feed never accumulates lag,
no matter how slow inference is. Paired with InferenceWorker, display FPS is
fully decoupled from model FPS.

Recorded files want every frame preserved (no dropping) so the saved output
isn't choppy — main.py keeps the simple synchronous VideoSource for files and
uses this class only for live sources.
"""

import logging
import threading
from typing import Optional, Tuple

import cv2
import numpy as np

log = logging.getLogger(__name__)


class ThreadedVideoStream:
    """
    Always-latest-frame capture running on a daemon thread.

    Usage:
        stream = ThreadedVideoStream("0").start()
        while True:
            seq, frame = stream.read()       # seq lets you tell frames apart
            if frame is None and stream.ended:
                break
        stream.release()
    """

    def __init__(self, source: str) -> None:
        self.source_str = source
        self._cap = cv2.VideoCapture(self._resolve(source))
        # Keep the driver buffer tiny so read() returns a fresh frame, not an
        # old queued one. Not all backends honour this — ignore if unsupported.
        try:
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        self._lock    = threading.Lock()
        self._frame: Optional[np.ndarray] = None
        self._seq     = 0          # increments on every grabbed frame
        self._running = False
        self._ended   = False
        self._thread: Optional[threading.Thread] = None

        if self._cap.isOpened():
            w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            log.info(f"ThreadedVideoStream ready: {w}×{h}  source={source!r}")
        else:
            log.error(f"ThreadedVideoStream failed to open source: {source!r}")

    @staticmethod
    def _resolve(source: str):
        """'0' → webcam index 0; everything else stays a string (path / RTSP)."""
        try:
            return int(source)
        except (ValueError, TypeError):
            return source

    def is_open(self) -> bool:
        return self._cap.isOpened()

    def start(self) -> "ThreadedVideoStream":
        self._running = True
        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()
        return self

    def _update(self) -> None:
        """Capture loop — runs on the background thread."""
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                self._ended = True
                break
            with self._lock:
                self._frame = frame
                self._seq  += 1

    def read(self) -> Tuple[int, Optional[np.ndarray]]:
        """Return (seq, latest_frame). frame is None until the first grab."""
        with self._lock:
            return self._seq, self._frame

    @property
    def ended(self) -> bool:
        """True once the source stops yielding frames (file end / stream drop)."""
        return self._ended

    def release(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._cap:
            self._cap.release()
        log.info(f"ThreadedVideoStream released: {self.source_str!r}")

    def __repr__(self) -> str:
        return f"ThreadedVideoStream(source={self.source_str!r}, open={self.is_open()})"
