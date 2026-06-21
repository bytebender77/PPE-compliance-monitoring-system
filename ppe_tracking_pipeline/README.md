# PPE Tracking Pipeline (standalone)

A self-contained, production-grade real-time PPE compliance pipeline built around
**multi-object tracking**. It is independent of the existing `ppe_compliance_system`
package — copy this folder to any machine, install the requirements, and run.

The goal: **stable boxes that lock onto each worker and never flicker**, with a
debounced compliance verdict, designed to run every frame on a GPU and scale to
CCTV.

## Architecture

```
                 ┌─────────────────────── per frame ───────────────────────┐
 camera/file ──► │ PersonTracker (.track, ByteTrack/BoT-SORT, persist=True) │──► stable track_ids
                 │ PPEDetector  (.predict, 4-class, imgsz=1280)             │──► PPE boxes
                 │ associate()  PPE → track  (overlap)                      │
                 │ WorkerTrackManager: per-track rolling window + hysteresis │──► stable status
                 └──────────────────────────────────────────────────────────┘
                                         │
                          Renderer (stable boxes + status)  +  AlertManager (per track_id, cooldown)
```

### Why it stays stable (the two fixes)
1. **Tracker with a lost-track buffer** — ByteTrack/BoT-SORT keep a worker's
   identity alive for `track_buffer` frames when the detector misses it, so the
   box doesn't vanish. The renderer also holds the last box for `box_hold_frames`.
2. **Per-track temporal compliance** — two layers of smoothing:
   - *presence smoothing*: a PPE class is "worn" only if seen in ≥ `presence_ratio`
     of the last `window_size` (M) frames;
   - *status hysteresis*: status flips to VIOLATION only after `violation_frames`
     (N) consecutive bad frames, and clears only after `clear_frames` (K) good ones.

## Run

```bash
pip install -r requirements.txt

# Webcam on a GPU box, every frame
python run.py --source 0 --device cuda

# A recorded clip, save annotated output
python run.py --source ../new/far.MOV --save out.mp4

# Heavy occlusion → BoT-SORT, longer buffer
python run.py --source 0 --tracker botsort --track-buffer 60

# Plug in a CCTV-trained PPE model when ready
python run.py --source rtsp://CAM --ppe-model /path/cctv_best.pt --device cuda
```

`--device` auto-detects cuda → mps → cpu if omitted. On CUDA, FP16 is enabled
automatically.

## Live tuning keys
| Key | Action |
|-----|--------|
| `q` / `Esc` | quit |
| `s` | save screenshot |
| `[` / `]` | N (violation frames) down / up |
| `-` / `=` | K (clear frames) down / up |
| `,` / `.` | presence ratio down / up |

`track_buffer` and `window_size` are set at launch (`--track-buffer`, `--window`).

## Key tunables (`config.py`)
| Field | Meaning | Default |
|-------|---------|---------|
| `tracker` | `bytetrack` (fixed cam) / `botsort` (occlusion) | bytetrack |
| `track_buffer` | frames a lost track survives | 30 |
| `required_ppe` | classes every worker must wear | helmet, safety_vest |
| `window_size` (M) | rolling window length | 15 |
| `presence_ratio` | fraction of window a PPE must appear in | 0.40 |
| `violation_frames` (N) | consecutive bad frames to flag | 12 |
| `clear_frames` (K) | consecutive good frames to clear | 12 |
| `ppe_imgsz` | PPE inference resolution | 1280 |

## Notes
- `ppe_classes` in `config.py` must match the PPE model's class order
  (`helmet, safety_vest, goggles, gloves`).
- WhatsApp / SQLite are intentionally omitted (hook points marked in
  `pipeline/alerts.py`) so this testbed has zero external dependencies.
- Person tracking uses COCO `yolov8n.pt` (class 0). The PPE model stays separate.
```
