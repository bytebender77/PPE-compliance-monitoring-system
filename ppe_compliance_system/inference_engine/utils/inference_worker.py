"""
inference_engine/utils/inference_worker.py
────────────────────────────────────────────
Runs the heavy detection pipeline on a background thread so the display loop
never blocks on the model.

HOW IT FITS TOGETHER
─────────────────────
    ThreadedVideoStream  →  always-latest camera frame   (thread 1)
    InferenceWorker      →  runs process_fn on that frame (thread 2)
    main display loop    →  draws latest results on the latest frame (main)

The worker repeatedly grabs the freshest frame, runs process_fn(frame) — person
+ PPE detection, smoothing, compliance, alert bookkeeping — and stores the
result. The main thread reads the most recent result with latest() and overlays
it on the current live frame. So the window refreshes at full speed (25–30 fps)
even when the model only manages ~6 fps at imgsz=1280: detection quality stays
at full resolution, and only the *display* is decoupled from inference speed.

Only this single worker thread ever touches the detector models, so there's no
concurrent model access — inference stays thread-safe.
"""

import logging
import threading
import time
from typing import Any, Callable, Optional, Tuple

log = logging.getLogger(__name__)


class InferenceWorker:
    """
    Args:
        stream:     A ThreadedVideoStream (anything with .read()→(seq, frame)
                    and a .ended property).
        process_fn: Callable that takes a BGR frame and returns whatever the
                    display loop needs (here: (persons, ppe_items, new_alerts)).
    """

    def __init__(self, stream, process_fn: Callable[[Any], Any]) -> None:
        self._stream      = stream
        self._process_fn  = process_fn
        self._lock        = threading.Lock()
        self._results: Optional[Any] = None   # latest process_fn() output
        self._results_seq = -1                 # frame seq those results came from
        self._infer_fps   = 0.0                # smoothed model FPS
        self._running     = False
        self._thread: Optional[threading.Thread] = None
        self._last_seq    = -1

    def start(self) -> "InferenceWorker":
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        ema: Optional[float] = None
        while self._running:
            seq, frame = self._stream.read()
            # Nothing new to chew on yet — back off briefly so we don't spin.
            if frame is None or seq == self._last_seq:
                if self._stream.ended:
                    break
                time.sleep(0.003)
                continue

            self._last_seq = seq
            t0 = time.time()
            results = self._process_fn(frame)
            dt = time.time() - t0

            inst = (1.0 / dt) if dt > 0 else 0.0
            ema  = inst if ema is None else (0.9 * ema + 0.1 * inst)

            with self._lock:
                self._results     = results
                self._results_seq = seq
                self._infer_fps   = ema

    def latest(self) -> Tuple[Optional[Any], int, float]:
        """Return (results, results_seq, infer_fps) — a consistent snapshot."""
        with self._lock:
            return self._results, self._results_seq, self._infer_fps

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
