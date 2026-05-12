"""
inference_engine/utils/fps_counter.py
──────────────────────────────────────
Rolling-window FPS counter.

WHY A ROLLING WINDOW INSTEAD OF INSTANTANEOUS FPS?
Instantaneous FPS (1 / frame_delta) is too noisy — a single slow frame
(GC pause, model warmup) spikes the number wildly. A rolling window of N
frames gives a stable, human-readable value.

Default window = 30 frames → FPS updates roughly once per second at 30 fps.
A smaller window (10) is more responsive; larger (60) is smoother.

This utility has zero dependencies on YOLO, OpenCV, or the rest of the system.
It can be unit-tested with just Python stdlib.
"""

import time
from collections import deque
import logging

log = logging.getLogger(__name__)


class FPSCounter:
    """
    Compute a rolling-average frames-per-second metric.

    Usage:
        counter = FPSCounter(window=30)
        while True:
            frame = source.read()
            fps = counter.update()   # call once per frame
            # fps is the rolling average
    """

    def __init__(self, window: int = 30) -> None:
        """
        Args:
            window: Number of recent frame timestamps to average over.
                    Larger = smoother but slower to react to speed changes.
        """
        self._window     = window
        # deque with maxlen automatically discards oldest timestamps
        # when the buffer is full — no manual management needed.
        self._timestamps: deque = deque(maxlen=window)
        self._fps        = 0.0

    def update(self) -> float:
        """
        Record the current timestamp and return the updated FPS estimate.

        Call once per processed frame — not per displayed frame.
        If frames are skipped (e.g. paused), don't call update() during the
        skip so the rolling average reflects actual processing throughput.

        Returns:
            Current rolling-average FPS as a float. Returns 0.0 until
            at least 2 frames have been recorded.
        """
        now = time.perf_counter()   # higher resolution than time.time()
        self._timestamps.append(now)

        if len(self._timestamps) < 2:
            return 0.0

        # Elapsed time between oldest and newest timestamp in the window
        elapsed = self._timestamps[-1] - self._timestamps[0]

        if elapsed <= 0:
            return 0.0

        # (window_size - 1) frame intervals across elapsed seconds
        self._fps = (len(self._timestamps) - 1) / elapsed
        return self._fps

    @property
    def fps(self) -> float:
        """Most recent FPS value (read without updating)."""
        return self._fps

    def reset(self) -> None:
        """Clear all timestamps (e.g. after un-pausing to avoid stale data)."""
        self._timestamps.clear()
        self._fps = 0.0
