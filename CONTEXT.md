# CONTEXT.md — PPE Compliance Monitoring System
# Paste this file (or relevant sections) into future Claude prompts
# so the AI knows exactly what exists and what still needs building.

## Project identity
Real-time AI-powered PPE compliance monitoring for industrial safety.
Detection classes: person · helmet · safety vest/jacket · goggles
Tech stack: Python · YOLOv8 · OpenCV · ByteTrack · FastAPI · React · SQLite → PostgreSQL · Docker

---

## ✅ STAGE 1 — COMPLETE: Minimal Working MVP (Person Detection)

### What was built
| File | Purpose |
|---|---|
| `main.py` | Entry point. CLI args, main loop, keyboard controls |
| `config/settings.py` | Centralised config dataclass (all magic numbers live here) |
| `inference_engine/detectors/person_detector.py` | YOLOv8 wrapper — detect() returns list of dicts |
| `inference_engine/utils/video_source.py` | OpenCV VideoCapture abstraction (webcam / MP4 / RTSP) |
| `inference_engine/utils/display.py` | All OpenCV drawing logic — bboxes, HUD, labels |
| `inference_engine/utils/fps_counter.py` | Rolling-window FPS counter |
| `tests/unit/test_person_detector.py` | Unit tests for detector output format + FPS + VideoSource |
| `requirements.txt` | Pinned deps (Stage 2–7 deps commented but listed) |

### Key design decisions made in Stage 1
1. **Detection output is a plain dict** `{bbox, confidence, class_id, class_name, track_id}` — JSON-serialisable, open for extension by future stages.
2. **Strict separation**: detector detects, annotator draws, video_source captures — none know about each other.
3. **Config centralised** in `Settings` dataclass — all thresholds in one place, overridable via env vars.
4. **Lazy model loading** — YOLO weights not loaded until first `.detect()` call.
5. `track_id` field exists in every detection dict but is `None` until Stage 2 adds ByteTrack.
6. `is_compliant` and `missing_ppe` keys are commented but documented for Stage 3.

### How to run
```bash
python main.py              # webcam index 0
python main.py --source 0   # explicit
python main.py --source video.mp4
python main.py --no-display  # headless
```
Controls: Q=quit, S=screenshot, P=pause

---

## 🔲 STAGE 2 — TODO: ByteTrack Multi-Object Tracking

### What to add
- `pip install supervision` (roboflow supervision includes ByteTrack)
- New file: `inference_engine/trackers/bytetrack_wrapper.py`
  - Class `ByteTrackWrapper` with `.update(detections, frame) → detections_with_ids`
  - Populates `track_id` in each detection dict (currently always None)
- Update `main.py` to call tracker between detector and annotator
- Update `FrameAnnotator._draw_detection` to show track ID in label: "person #3 [0.87]"

### Expected output change
Before (Stage 1): `{"bbox": [...], "track_id": None, ...}`
After  (Stage 2): `{"bbox": [...], "track_id": 3, ...}`

---

## 🔲 STAGE 3 — TODO: Custom YOLOv8 PPE Fine-tuning + Multi-class Detection

### What to add
- Dataset annotation: helmet, safety_vest, goggles, person (4 classes)
- Training script: `scripts/train.py` using `ultralytics train`
- Evaluation script: `scripts/evaluate.py`
- Update `PersonDetector.PERSON_CLASS_ID` → detect all 4 classes
- Update `Settings.PPE_CLASS_MAP` with all class IDs
- Update `FrameAnnotator._color_map` with per-class colours
- Replace `yolov8n.pt` with `models/best.pt`

---

## 🔲 STAGE 4 — TODO: Compliance Engine

### What to add
- New file: `inference_engine/compliance/compliance_engine.py`
  - `ComplianceEngine.check(detections, zone="default") → detections_with_compliance`
  - Populates `missing_ppe` and `is_compliant` fields in each detection dict
  - Uses `Settings.REQUIRED_PPE_BY_ZONE`
- Update `FrameAnnotator` to colour non-compliant workers RED

### Logic
For each tracked person, check if their bounding box overlaps with detected PPE bounding boxes. If required PPE not overlapping → mark as missing.

---

## 🔲 STAGE 5 — TODO: Alert Orchestrator + SQLite Logging

### What to add
- `inference_engine/alerts/alert_orchestrator.py` — N-frame counter per track_id
- `backend/database/models.py` — SQLAlchemy Violation model
- `backend/database/session.py` — SQLite session factory
- Screenshot capture on violation trigger (reuse `_save_screenshot` from main.py)
- Email / webhook notification (SMTP + httpx)

---

## 🔲 STAGE 6 — TODO: FastAPI Backend + React Dashboard

### What to add
- `backend/main.py` — FastAPI app
- `backend/routers/violations.py` — GET /violations, GET /stats
- `backend/routers/stream.py` — WebSocket MJPEG stream
- React SPA: live feed · violation table · compliance % chart · heatmap

---

## 🔲 STAGE 7 — TODO: Docker + GPU Optimisation

### What to add
- `Dockerfile` (inference engine), `Dockerfile.backend`, `docker-compose.yml`
- ONNX / TensorRT export for <50ms/frame inference
- Multi-camera concurrent inference (batch mode)
- PostgreSQL migration via Alembic
- Pytest CI pipeline

---

## Architecture reference (quick)
```
Tier 1 Edge      → Tier 2 Inference Engine  → Tier 3 Backend → Tier 4 React
webcam/RTSP/MP4    detect→track→comply→alert   FastAPI+SQLite    Dashboard
```

## File structure
```
ppe_compliance_system/
├── main.py
├── requirements.txt
├── CONTEXT.md                   ← you are here
├── config/
│   ├── __init__.py
│   └── settings.py
├── inference_engine/
│   ├── __init__.py
│   ├── detectors/
│   │   ├── __init__.py
│   │   └── person_detector.py   ← Stage 1 ✅
│   ├── trackers/                ← Stage 2 (empty)
│   ├── compliance/              ← Stage 4 (empty)
│   └── utils/
│       ├── __init__.py
│       ├── display.py           ← Stage 1 ✅
│       ├── fps_counter.py       ← Stage 1 ✅
│       └── video_source.py      ← Stage 1 ✅
├── backend/                     ← Stage 5–6 (empty)
├── tests/
│   ├── __init__.py
│   └── unit/
│       ├── __init__.py
│       └── test_person_detector.py  ← Stage 1 ✅
├── models/                      ← put best.pt here after Stage 3 training
├── screenshots/                 ← auto-created at runtime
└── logs/                        ← auto-created at runtime
```
