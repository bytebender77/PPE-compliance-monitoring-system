# PPE Compliance Monitoring System

Real-time AI-powered PPE (Personal Protective Equipment) detection for industrial safety.

**Current Stage: 1 — Person Detection MVP**

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- pip
- (Optional) NVIDIA GPU with CUDA 11.8+ for faster inference

### 2. Install dependencies

```bash
# Clone / navigate into project folder
cd ppe_compliance_system

# Create virtual environment (strongly recommended)
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate.bat     # Windows

# Install Python packages
pip install -r requirements.txt
```

> **GPU users**: Install PyTorch with CUDA FIRST, then requirements.txt:
> ```bash
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
> pip install -r requirements.txt
> ```

### 3. Run

```bash
# Webcam (default)
python main.py

# Specific webcam index
python main.py --source 1

# MP4 video file
python main.py --source path/to/video.mp4

# RTSP IP camera
python main.py --source "rtsp://user:pass@192.168.1.100/stream1"

# Override confidence threshold
python main.py --conf 0.5

# Headless (no display window — useful for testing on servers)
python main.py --no-display
```

### 4. Controls

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `S` | Save screenshot to `screenshots/` |
| `P` | Pause / unpause |

### 5. Run tests

```bash
pytest tests/unit/ -v
```

---

## Project Structure

```
ppe_compliance_system/
├── main.py                          Entry point — CLI, main loop
├── requirements.txt                 Python dependencies
├── CONTEXT.md                       Living project context (read before each stage)
├── config/
│   └── settings.py                  All configuration — thresholds, colours, paths
├── inference_engine/
│   ├── detectors/
│   │   └── person_detector.py       YOLOv8 wrapper — outputs detection dicts
│   └── utils/
│       ├── video_source.py          Webcam / MP4 / RTSP abstraction
│       ├── display.py               All OpenCV drawing logic
│       └── fps_counter.py           Rolling-average FPS counter
├── tests/unit/
│   └── test_person_detector.py      Unit tests (no camera / GPU needed)
├── models/                          Put best.pt here after Stage 3 training
└── screenshots/                     Auto-created — holds saved frames
```

---

## Configuration

Edit `config/settings.py` to change:

| Setting | Default | Description |
|---------|---------|-------------|
| `MODEL_PATH` | `yolov8n.pt` | YOLO weights file |
| `CONFIDENCE_THRESHOLD` | `0.4` | Min detection confidence |
| `DEVICE` | `cpu` | `"cpu"` or `"cuda"` |
| `PERSON_BOX_COLOR` | Green | BGR tuple |
| `ALERT_FRAME_THRESHOLD` | `20` | Frames before alert (Stage 5) |

All settings can be overridden with environment variables:
```bash
export PPE_DEVICE=cuda
export PPE_CONF_THRESHOLD=0.5
python main.py
```

---

## Roadmap

| Stage | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | Person detection MVP (this stage) |
| 2 | 🔲 Next | ByteTrack multi-object tracking |
| 3 | 🔲 | Custom YOLOv8 PPE fine-tuning (helmet, vest, goggles) |
| 4 | 🔲 | Compliance engine (PPE → worker association) |
| 5 | 🔲 | Alert orchestrator + SQLite violation logging |
| 6 | 🔲 | FastAPI backend + React dashboard |
| 7 | 🔲 | Docker + GPU optimisation + PostgreSQL |

---

## Detection Output Format

Every detection produced by `PersonDetector.detect()` is a plain dict:

```python
{
    "bbox":        [x1, y1, x2, y2],  # pixel coords
    "confidence":  0.87,               # float 0–1
    "class_id":    0,                  # YOLO class index
    "class_name":  "person",           # human-readable
    "track_id":    None,               # populated by ByteTrack in Stage 2
}
```

Future stages enrich the same dict — no format changes:
```python
# After Stage 2 (tracking):
"track_id":    3

# After Stage 3 (PPE detection):
"missing_ppe": ["helmet"],
"is_compliant": False
```

---

## Technology Stack

| Component | Tool | Notes |
|-----------|------|-------|
| Detection | YOLOv8n | Auto-downloaded on first run |
| Video I/O | OpenCV | Webcam / RTSP / MP4 |
| Tracking | ByteTrack (Stage 2) | Via roboflow/supervision |
| Backend | FastAPI (Stage 6) | REST + WebSocket |
| Database | SQLite → PostgreSQL | SQLite for dev |
| Frontend | React (Stage 6) | Live dashboard |
| Deployment | Docker (Stage 7) | Full containerisation |
# PPE-compliance-monitoring-system
