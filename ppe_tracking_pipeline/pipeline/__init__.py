"""Production-grade PPE tracking pipeline (standalone).

Components:
    video_stream    — threaded always-latest capture for live sources
    person_tracker  — YOLO .track() wrapper → persistent track_id per worker
    ppe_detector    — YOLO PPE detection (predict mode)
    association     — bind PPE detections to tracks by overlap
    tracking_state  — per-track rolling window + hysteresis compliance state machine
    alerts          — per-track_id alert manager with cooldown + screenshots
    renderer        — draw stable tracked boxes + debounced status every frame
"""
