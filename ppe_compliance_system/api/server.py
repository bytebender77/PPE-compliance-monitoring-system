"""
api/server.py — Stage 6: FastAPI dashboard backend

ARCHITECTURE
────────────
  Two processes run simultaneously:
    1. python -m ppe_compliance_system.main   → camera pipeline, writes to violations.db
    2. python -m ppe_compliance_system.api    → this server, reads from violations.db

  They share NO memory — only the SQLite file on disk.
  The WebSocket polls for new rows every second and pushes them to the browser.

ENDPOINTS
─────────
  GET  /                        → dashboard HTML
  GET  /api/violations          → recent N violations (JSON)
  GET  /api/stats               → all-time stats (JSON)
  GET  /api/sessions            → recent sessions (JSON)
  GET  /screenshots/{filename}  → serve screenshot image
  WS   /ws/alerts               → live alert stream (new rows only)

Run:
    python -m ppe_compliance_system.api
    → open http://localhost:8000
"""

import asyncio
import logging
import os
import sqlite3
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

log = logging.getLogger(__name__)

DB_PATH          = Path(os.getenv("PPE_DB_PATH",          "logs/violations.db"))
SCREENSHOTS_DIR  = Path(os.getenv("PPE_SCREENSHOTS_DIR",  "screenshots"))
STATIC_DIR       = Path(__file__).parent / "static"


def get_db():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def create_app() -> FastAPI:
    app = FastAPI(title="PPE Compliance Dashboard", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # In-memory alert toggle state (shared across requests within this process)
    app.state.alerts_enabled = True

    # Serve screenshots as static files
    if SCREENSHOTS_DIR.exists():
        app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")

    # ── REST endpoints ────────────────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        html = STATIC_DIR / "index.html"
        return HTMLResponse(html.read_text(encoding="utf-8"))

    @app.get("/api/violations")
    async def violations(limit: int = 50, severity: str = None):
        conn = get_db()
        if not conn:
            return {"violations": [], "error": "Database not found — start the PPE pipeline first"}
        query = "SELECT * FROM violations"
        params = []
        if severity:
            query += " WHERE severity = ?"
            params.append(severity.upper())
        query += " ORDER BY timestamp_unix DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return {"violations": [dict(r) for r in rows]}

    @app.get("/api/stats")
    async def stats():
        conn = get_db()
        if not conn:
            return {"total": 0, "critical": 0, "warnings": 0,
                    "no_helmet": 0, "no_vest": 0, "no_goggles": 0}
        row = conn.execute("""
            SELECT
                COUNT(*)                              AS total,
                SUM(severity='CRITICAL')              AS critical,
                SUM(severity='WARNING')               AS warnings,
                SUM(missing_ppe LIKE '%helmet%')      AS no_helmet,
                SUM(missing_ppe LIKE '%safety_vest%') AS no_vest,
                SUM(missing_ppe LIKE '%goggles%')     AS no_goggles
            FROM violations
        """).fetchone()
        conn.close()
        return dict(row) if row else {}

    @app.get("/api/sessions")
    async def sessions(limit: int = 10):
        conn = get_db()
        if not conn:
            return {"sessions": []}
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return {"sessions": [dict(r) for r in rows]}

    @app.get("/api/violations/today")
    async def today_violations():
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        conn = get_db()
        if not conn:
            return {"violations": []}
        rows = conn.execute(
            "SELECT * FROM violations WHERE timestamp LIKE ? ORDER BY timestamp_unix DESC",
            (f"{today}%",),
        ).fetchall()
        conn.close()
        return {"violations": [dict(r) for r in rows], "date": today}

    @app.delete("/api/clear")
    async def clear_all():
        conn = get_db()
        if not conn:
            return {"ok": False, "error": "Database not found"}
        deleted = conn.execute("SELECT COUNT(*) FROM violations").fetchone()[0]
        conn.execute("DELETE FROM violations")
        conn.execute("DELETE FROM sessions")
        conn.commit()
        conn.close()
        # Reclaim disk space in a separate connection (VACUUM can't run inside a transaction)
        try:
            import sqlite3 as _sql
            vc = _sql.connect(str(DB_PATH))
            vc.execute("VACUUM")
            vc.close()
        except Exception:
            pass
        log.warning(f"All data cleared — {deleted} violation(s) deleted")
        return {"ok": True, "deleted": deleted}

    # ── Alert toggle ─────────────────────────────────────────────────────────

    @app.get("/api/alerts/state")
    async def get_alert_state():
        return {"enabled": app.state.alerts_enabled}

    @app.post("/api/alerts/toggle")
    async def toggle_alerts():
        app.state.alerts_enabled = not app.state.alerts_enabled
        state = "ON" if app.state.alerts_enabled else "MUTED"
        log.info(f"Dashboard toggled WhatsApp alerts → {state}")
        return {"enabled": app.state.alerts_enabled, "state": state}

    # ── WebSocket — live alert stream ─────────────────────────────────────────

    @app.websocket("/ws/alerts")
    async def ws_alerts(websocket: WebSocket):
        await websocket.accept()
        log.info("WebSocket client connected")

        # Track the highest violation ID seen so far
        conn = get_db()
        if conn:
            row = conn.execute("SELECT MAX(id) as max_id FROM violations").fetchone()
            last_id = row["max_id"] or 0
            conn.close()
        else:
            last_id = 0

        try:
            while True:
                await asyncio.sleep(1)   # poll every second
                conn = get_db()
                if not conn:
                    continue
                new_rows = conn.execute(
                    "SELECT * FROM violations WHERE id > ? ORDER BY id ASC",
                    (last_id,),
                ).fetchall()
                conn.close()

                for row in new_rows:
                    last_id = row["id"]
                    await websocket.send_json(dict(row))

        except WebSocketDisconnect:
            log.info("WebSocket client disconnected")
        except Exception as exc:
            log.error(f"WebSocket error: {exc}")

    return app
