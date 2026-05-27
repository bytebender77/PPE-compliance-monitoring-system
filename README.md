# PPE Compliance Monitoring System

> Real-time AI-powered PPE detection for industrial safety — built for Tata Steel manufacturing environments.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8s-custom--trained-orange)](https://ultralytics.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-dashboard-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://docker.com)

---

## What it does

| Feature | Details |
|---|---|
| **Dual-model detection** | YOLOv8n (persons) + YOLOv8s custom (helmet, vest, goggles) |
| **Compliance checking** | Spatial association of PPE items to workers |
| **Alert engine** | Per-worker streak tracking → fires after N consecutive non-compliant frames |
| **WhatsApp alerts** | Screenshot + violation details sent via Meta Cloud API |
| **SQLite logging** | Every violation stored with timestamp, worker ID, screenshot path |
| **Live dashboard** | FastAPI + WebSocket — real-time violation feed at `localhost:8000` |
| **Multi-camera** | One process per camera, all writing to shared DB |
| **Docker** | CPU + NVIDIA GPU builds, compose stack for pipeline + API |

---

## Model Performance (test split, 860 images)

| Metric | Value |
|---|---|
| **mAP@0.5** | **0.897** |
| mAP@0.5:0.95 | 0.673 |
| Precision | 0.940 |
| Recall | 0.916 |

| Class | mAP@0.5 |
|---|---|
| Helmet | 0.844 |
| Safety Vest | 0.885 |
| Goggles | 0.963 |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Webcam, MP4, or RTSP stream
- `models/best.pt` — custom-trained YOLOv8s weights *(not in repo — train your own or request from author)*

### Install

```bash
git clone https://github.com/bytebender77/PPE-compliance-monitoring-system.git
cd PPE-compliance-monitoring-system

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# CPU
pip install -r requirements.txt

# NVIDIA GPU (install torch with CUDA first)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
```

### Configure `.env`

```bash
cp .env.example .env
# Edit .env — set your WhatsApp API token, camera label, thresholds
```

---

## Running

### Single camera

```bash
# Webcam
python -m ppe_compliance_system.main

# MP4 file
python -m ppe_compliance_system.main --source video.mp4

# RTSP IP camera
python -m ppe_compliance_system.main --source "rtsp://user:pass@192.168.1.100/stream"

# Headless (no OpenCV window — for servers)
python -m ppe_compliance_system.main --no-display

# GPU inference
python -m ppe_compliance_system.main --device cuda
```

### Live dashboard (http://localhost:8000)

```bash
# Terminal 1 — pipeline
python -m ppe_compliance_system.main --no-display

# Terminal 2 — dashboard
python -m ppe_compliance_system.api
```

### Multi-camera

```bash
# Edit cameras.yaml to add your sources, then:
python -m ppe_compliance_system.multi_main

# List configured cameras
python -m ppe_compliance_system.multi_main --list
```

### Docker

```bash
# CPU — pipeline + dashboard
docker compose up --build

# NVIDIA GPU
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

---

## Controls (live window)

| Key | Action |
|---|---|
| `Q` | Quit |
| `S` | Save screenshot |
| `P` | Pause / unpause |

---

## Project Structure

```
PPE-compliance-monitoring-system/
│
├── ppe_compliance_system/
│   ├── main.py                    Single-camera entry point
│   ├── multi_main.py              Multi-camera orchestrator
│   │
│   ├── config/
│   │   └── settings.py            All thresholds, paths, colours
│   │
│   ├── inference_engine/
│   │   ├── detectors/
│   │   │   ├── person_detector.py YOLOv8n — detects persons
│   │   │   └── ppe_detector.py    YOLOv8s custom — helmet/vest/goggles
│   │   ├── compliance/
│   │   │   └── checker.py         Associates PPE to workers (IoU-based)
│   │   ├── alerts/
│   │   │   └── engine.py          Streak tracking, cooldown, Alert dataclass
│   │   └── utils/
│   │       ├── video_source.py    Webcam / MP4 / RTSP abstraction
│   │       ├── display.py         All OpenCV annotation (boxes, HUD, flash)
│   │       └── fps_counter.py     Rolling FPS counter
│   │
│   ├── notifications/
│   │   └── whatsapp.py            Meta WhatsApp Cloud API — sends alert + screenshot
│   │
│   ├── database/
│   │   └── logger.py              SQLite logger (WAL mode, violations + sessions)
│   │
│   └── api/
│       ├── server.py              FastAPI — REST + WebSocket endpoints
│       └── static/index.html      Live dashboard (dark-theme SPA)
│
├── scripts/
│   ├── train.py                   YOLOv8 fine-tuning script
│   ├── eval.py                    Evaluation on test split (mAP, per-class)
│   ├── export_model.py            Export to ONNX / TensorRT for production
│   ├── view_violations.py         CLI viewer for violations.db
│   └── resize_dataset.py          Resize dataset images in-place (640×640)
│
├── cameras.yaml                   Multi-camera configuration
├── Dockerfile                     Production Docker image (CPU / CUDA)
├── docker-compose.yml             Pipeline + dashboard stack
├── docker-compose.gpu.yml         NVIDIA GPU override
├── .env.example                   Environment variable template
├── data/data.yaml                 YOLOv8 dataset config
└── requirements.txt               Python dependencies
```

---

## Environment Variables

Copy `.env.example` to `.env`:

```bash
# WhatsApp Cloud API (Meta for Developers)
WHATSAPP_API_TOKEN=your_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_RECIPIENTS=919XXXXXXXXX        # E.164 format, no +

# Camera label (shown in alerts and DB)
WHATSAPP_CAMERA_LABEL=Gate-1 Camera

# Detection thresholds
PPE_DEVICE=cpu                          # cpu | cuda | mps
PPE_ALERT_FRAMES=20                     # frames before alert fires
PPE_ALERT_COOLDOWN=60                   # seconds between repeated alerts
PPE_REQUIRED=helmet,safety_vest         # comma-separated
```

---

## Dashboard API

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Dashboard HTML |
| `GET` | `/api/violations` | Recent violations (JSON) |
| `GET` | `/api/stats` | All-time counts by class/severity |
| `GET` | `/api/violations/today` | Today's violations |
| `GET` | `/api/sessions` | Recent pipeline sessions |
| `GET` | `/screenshots/{file}` | Serve alert screenshot |
| `WS` | `/ws/alerts` | Live alert stream |

---

## Export for Production

```bash
# ONNX (universal — CPU, GPU, mobile)
python scripts/export_model.py --model models/best.pt --format onnx

# TensorRT FP16 (NVIDIA — ~160 FPS on RTX A5000)
python scripts/export_model.py --model models/best.pt --format engine --half
```

Set `PPE_MODEL_PATH=models/best.engine PPE_DEVICE=cuda` in `.env` to use the exported model.

---

## Roadmap

| Stage | Status | Description |
|---|---|---|
| 1 | ✅ | Person detection MVP |
| 2 | ✅ | Custom YOLOv8s PPE model (helmet, vest, goggles) |
| 3 | ✅ | Compliance checker — spatial PPE↔worker association |
| 4 | ✅ | Alert engine — streak tracking, cooldown, auto-screenshot |
| 5 | ✅ | SQLite violation logger |
| 6 | ✅ | FastAPI dashboard + WebSocket live feed |
| 7 | ✅ | Docker, multi-camera, FP16 GPU inference, ONNX/TensorRT export |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Person detection | YOLOv8n (COCO pretrained) |
| PPE detection | YOLOv8s (custom trained — helmet, vest, goggles) |
| Video I/O | OpenCV |
| Alert notifications | Meta WhatsApp Cloud API |
| Database | SQLite (WAL mode) |
| Backend API | FastAPI + Uvicorn |
| Frontend | Vanilla JS + Tailwind CSS CDN |
| Containerisation | Docker + Docker Compose |

---

## Author

**Kunal Kumar Gupta** — [@bytebender77](https://github.com/bytebender77)
