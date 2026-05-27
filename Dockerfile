# ══════════════════════════════════════════════════════════════════════════════
# Dockerfile — PPE Compliance Monitoring System
#
# Build (CPU):
#   docker build -t ppe-compliance .
#
# Build (CUDA 12.1):
#   docker build --build-arg BASE=pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime \
#     -t ppe-compliance:gpu .
#
# Run pipeline (single camera):
#   docker run --rm -v $(pwd)/logs:/app/logs -v $(pwd)/screenshots:/app/screenshots \
#     --env-file .env ppe-compliance pipeline --source video.mp4 --no-display
#
# Run dashboard:
#   docker run --rm -p 8000:8000 -v $(pwd)/logs:/app/logs \
#     -v $(pwd)/screenshots:/app/screenshots ppe-compliance api
#
# Run multi-camera:
#   docker run --rm -v $(pwd)/logs:/app/logs -v $(pwd)/screenshots:/app/screenshots \
#     -v $(pwd)/cameras.yaml:/app/cameras.yaml --env-file .env \
#     ppe-compliance multi
# ══════════════════════════════════════════════════════════════════════════════

ARG BASE=python:3.11-slim
FROM ${BASE}

# ── System packages ───────────────────────────────────────────────────────────
# libgl1 + libglib2.0 are required by OpenCV (headless).
# libgomp1 is needed by some PyTorch ops.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Use headless OpenCV in Docker (no display server available)
ENV OPENCV_VIDEOIO_PRIORITY_BACKEND=0
ENV QT_QPA_PLATFORM=offscreen

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy only requirements first — Docker layer caches this until requirements change.
WORKDIR /app
COPY requirements.txt .

# Install CPU-only torch first (saves ~1GB vs CUDA build for CPU images).
# When BASE is a CUDA image, torch is already installed — pip will skip it.
RUN pip install --no-cache-dir \
        torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    || true   # already installed in GPU base image

RUN pip install --no-cache-dir -r requirements.txt

# ── Source code ───────────────────────────────────────────────────────────────
COPY ppe_compliance_system/ ./ppe_compliance_system/

# Pre-download YOLO nano weights so first run is instant
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" 2>/dev/null || true

# ── Runtime directories ───────────────────────────────────────────────────────
# These are expected to be mounted as volumes in production.
RUN mkdir -p logs screenshots models

# ── Non-root user ─────────────────────────────────────────────────────────────
RUN useradd -m -u 1000 ppe && chown -R ppe:ppe /app
USER ppe

# ── Entrypoint ────────────────────────────────────────────────────────────────
# Accepts: pipeline | api | multi
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
USER root
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
USER ppe

EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["api"]
