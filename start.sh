#!/bin/bash

# PPE Compliance System — start pipeline + dashboard together

cd "$(dirname "$0")"

# Activate venv
source venv/bin/activate

echo ""
echo "============================================"
echo "  PPE Compliance Monitoring System"
echo "============================================"
echo ""
echo "  Dashboard → http://localhost:8000"
echo "  Press Ctrl+C to stop everything"
echo ""
echo "============================================"
echo ""

# Start dashboard in background
python -m ppe_compliance_system.api &
DASHBOARD_PID=$!

# Wait a moment for dashboard to start
sleep 2

echo ""
echo "  Dashboard running at http://localhost:8000"
echo "  Opening in browser..."
echo ""
open "http://localhost:8000"

# Start pipeline (webcam, foreground)
# --ppe-imgsz 1280  : higher resolution for reliable jacket/vest detection
# --frame-skip 3    : threaded live mode ignores this, kept for file-source fallback
# --ppe-conf 0.3    : suppress noise, tuned for v5 jacket-only model
python -m ppe_compliance_system.main \
    --source 0 \
    --device mps \
    --ppe-imgsz 1280 \
    --frame-skip 3 \
    --ppe-conf 0.3

# When pipeline exits (Q pressed), kill dashboard too
kill $DASHBOARD_PID 2>/dev/null
echo ""
echo "  System stopped."
