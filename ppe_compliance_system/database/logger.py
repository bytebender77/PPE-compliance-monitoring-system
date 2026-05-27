"""
database/logger.py — Stage 5: SQLite violation logger

WHAT IT STORES
──────────────
  violations table — one row per fired alert
    id, timestamp, worker_id, missing_ppe, severity,
    screenshot_path, camera, session_id, frame_number

  sessions table — one row per system run
    id, started_at, ended_at, camera, total_alerts

WHY SQLITE?
───────────
  - Zero setup — just a file on disk (logs/violations.db)
  - Built into Python stdlib — no pip install needed
  - Stage 6 FastAPI dashboard reads from the same file
  - Can be opened in DB Browser for SQLite for manual inspection
  - Easy to export to Excel / CSV for safety reports

USAGE
─────
    logger = ViolationLogger(db_path="logs/violations.db", camera="Gate-2")
    logger.open()                        # creates tables if not exist

    logger.log_violation(alert)          # call on every alert
    logger.log_violation(alert, screenshot_path="screenshots/alert_xyz.png")

    # query
    rows = logger.recent_violations(limit=20)
    stats = logger.session_stats()

    logger.close()                       # call on shutdown
"""

import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

log = logging.getLogger(__name__)

# ── Schema ────────────────────────────────────────────────────────────────────

_CREATE_VIOLATIONS = """
CREATE TABLE IF NOT EXISTS violations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    timestamp_unix  REAL    NOT NULL,
    worker_id       TEXT    NOT NULL,
    missing_ppe     TEXT    NOT NULL,
    severity        TEXT    NOT NULL,
    screenshot_path TEXT,
    camera          TEXT    NOT NULL,
    session_id      TEXT    NOT NULL,
    frame_number    INTEGER NOT NULL DEFAULT 0
);
"""

_CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id           TEXT    PRIMARY KEY,
    started_at   TEXT    NOT NULL,
    ended_at     TEXT,
    camera       TEXT    NOT NULL,
    total_alerts INTEGER NOT NULL DEFAULT 0
);
"""

_CREATE_IDX_TIMESTAMP = """
CREATE INDEX IF NOT EXISTS idx_violations_timestamp
ON violations (timestamp_unix DESC);
"""

_CREATE_IDX_SESSION = """
CREATE INDEX IF NOT EXISTS idx_violations_session
ON violations (session_id);
"""


class ViolationLogger:
    """
    Writes PPE violation alerts to a local SQLite database.

    Args
    ----
    db_path : Path to the .db file (created automatically if missing).
    camera  : Camera/location label stored with every row.
    """

    def __init__(self, db_path: str = "logs/violations.db", camera: str = "unknown") -> None:
        self._db_path   = Path(db_path)
        self._camera    = camera
        self._conn: Optional[sqlite3.Connection] = None
        self._session_id = str(uuid.uuid4())
        self._alert_count = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def open(self) -> None:
        """Open the database, create tables, and start a new session row."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,   # safe for single-threaded pipeline
            timeout=10,                # wait up to 10s when another writer holds the lock
        )
        self._conn.row_factory = sqlite3.Row   # dict-like rows
        # WAL mode: multiple processes can read while one writes — required for
        # multi-camera mode where each camera worker writes to the same DB file.
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")   # safe + fast under WAL
        cur = self._conn.cursor()
        cur.executescript(
            _CREATE_VIOLATIONS +
            _CREATE_SESSIONS   +
            _CREATE_IDX_TIMESTAMP +
            _CREATE_IDX_SESSION
        )
        self._conn.commit()

        # Insert session record
        cur.execute(
            "INSERT INTO sessions (id, started_at, camera) VALUES (?, ?, ?)",
            (self._session_id, _now_iso(), self._camera),
        )
        self._conn.commit()

        log.info(
            f"ViolationLogger ready  db={self._db_path}  "
            f"session={self._session_id[:8]}..."
        )

    def close(self) -> None:
        """Mark session as ended and close the connection."""
        if self._conn:
            try:
                self._conn.execute(
                    "UPDATE sessions SET ended_at=?, total_alerts=? WHERE id=?",
                    (_now_iso(), self._alert_count, self._session_id),
                )
                self._conn.commit()
                self._conn.close()
                log.info(
                    f"ViolationLogger closed — session {self._session_id[:8]}... "
                    f"logged {self._alert_count} alert(s)"
                )
            except Exception as exc:
                log.error(f"ViolationLogger close error: {exc}")
            finally:
                self._conn = None

    # ── Write ─────────────────────────────────────────────────────────────────

    def log_violation(
        self,
        alert,
        screenshot_path: Optional[Path] = None,
    ) -> int:
        """
        Write one violation row to the database.

        Args
        ----
        alert           : Alert object from AlertEngine
        screenshot_path : Path to the saved screenshot (stored as string)

        Returns the new row id.
        """
        if not self._conn:
            log.warning("ViolationLogger.log_violation called before open()")
            return -1

        missing_str = ",".join(alert.missing_ppe) if alert.missing_ppe else ""
        shot_str    = str(screenshot_path) if screenshot_path else None

        try:
            cur = self._conn.execute(
                """
                INSERT INTO violations
                  (timestamp, timestamp_unix, worker_id, missing_ppe,
                   severity, screenshot_path, camera, session_id, frame_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.time_str,
                    alert.timestamp,
                    str(alert.track_id),
                    missing_str,
                    alert.severity,
                    shot_str,
                    self._camera,
                    self._session_id,
                    alert.frame_number,
                ),
            )
            self._conn.commit()
            self._alert_count += 1
            row_id = cur.lastrowid
            log.info(f"Violation logged  id={row_id}  worker={alert.track_id}  missing={missing_str}")
            return row_id

        except Exception as exc:
            log.error(f"ViolationLogger write error: {exc}")
            return -1

    # ── Query ─────────────────────────────────────────────────────────────────

    def recent_violations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the N most recent violations as a list of dicts."""
        if not self._conn:
            return []
        cur = self._conn.execute(
            "SELECT * FROM violations ORDER BY timestamp_unix DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]

    def session_stats(self) -> Dict[str, Any]:
        """Stats for the current session — violations by severity."""
        if not self._conn:
            return {}
        cur = self._conn.execute(
            """
            SELECT
                COUNT(*)                                      AS total,
                SUM(severity = 'CRITICAL')                    AS critical,
                SUM(severity = 'WARNING')                     AS warnings,
                SUM(missing_ppe LIKE '%helmet%')              AS no_helmet,
                SUM(missing_ppe LIKE '%safety_vest%')         AS no_vest,
                SUM(missing_ppe LIKE '%goggles%')             AS no_goggles
            FROM violations WHERE session_id = ?
            """,
            (self._session_id,),
        )
        return dict(cur.fetchone())

    def all_time_stats(self) -> Dict[str, Any]:
        """Lifetime stats across all sessions."""
        if not self._conn:
            return {}
        cur = self._conn.execute(
            """
            SELECT
                COUNT(*)                              AS total_violations,
                COUNT(DISTINCT session_id)            AS total_sessions,
                SUM(severity = 'CRITICAL')            AS critical,
                SUM(severity = 'WARNING')             AS warnings,
                SUM(missing_ppe LIKE '%helmet%')      AS no_helmet,
                SUM(missing_ppe LIKE '%safety_vest%') AS no_vest,
                SUM(missing_ppe LIKE '%goggles%')     AS no_goggles,
                MIN(timestamp)                        AS first_violation,
                MAX(timestamp)                        AS last_violation
            FROM violations
            """
        )
        return dict(cur.fetchone())

    def export_csv(self, output_path: str = "logs/violations_export.csv") -> str:
        """Export all violations to a CSV file. Returns the path."""
        import csv
        if not self._conn:
            return ""
        rows = self._conn.execute(
            "SELECT * FROM violations ORDER BY timestamp_unix ASC"
        ).fetchall()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "timestamp", "worker_id", "missing_ppe",
                "severity", "screenshot_path", "camera", "session_id", "frame_number"
            ])
            writer.writerows(rows)
        log.info(f"Exported {len(rows)} violations → {out}")
        return str(out)


# ── Helper ────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
