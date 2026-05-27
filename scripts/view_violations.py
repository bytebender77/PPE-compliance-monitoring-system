"""
scripts/view_violations.py — View and export the violations database

Usage
-----
    # Show last 20 violations
    python scripts/view_violations.py

    # Show last 50
    python scripts/view_violations.py --limit 50

    # Show all-time stats summary
    python scripts/view_violations.py --stats

    # Export to CSV
    python scripts/view_violations.py --export

    # Show violations from today only
    python scripts/view_violations.py --today
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("logs/violations.db")


def main():
    parser = argparse.ArgumentParser(description="View PPE violation log")
    parser.add_argument("--db",     default=str(DB_PATH), help="Path to violations.db")
    parser.add_argument("--limit",  type=int, default=20,  help="Number of rows to show")
    parser.add_argument("--stats",  action="store_true",   help="Show summary statistics")
    parser.add_argument("--export", action="store_true",   help="Export to CSV")
    parser.add_argument("--today",  action="store_true",   help="Show today's violations only")
    args = parser.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"Database not found: {db}")
        print("Run the system first to generate violations.")
        sys.exit(1)

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row

    # ── Stats summary ──────────────────────────────────────────────────────────
    if args.stats:
        row = conn.execute("""
            SELECT
                COUNT(*)                              AS total,
                COUNT(DISTINCT session_id)            AS sessions,
                SUM(severity='CRITICAL')              AS critical,
                SUM(severity='WARNING')               AS warnings,
                SUM(missing_ppe LIKE '%helmet%')      AS no_helmet,
                SUM(missing_ppe LIKE '%safety_vest%') AS no_vest,
                SUM(missing_ppe LIKE '%goggles%')     AS no_goggles,
                MIN(timestamp)                        AS first,
                MAX(timestamp)                        AS last
            FROM violations
        """).fetchone()

        print(f"\n{'═'*45}")
        print(f"  PPE Violation Statistics — All Time")
        print(f"{'═'*45}")
        print(f"  Total violations  : {row['total']}")
        print(f"  Sessions logged   : {row['sessions']}")
        print(f"  Critical (2+ PPE) : {row['critical']}")
        print(f"  Warnings (1 PPE)  : {row['warnings']}")
        print(f"  No helmet         : {row['no_helmet']}")
        print(f"  No safety vest    : {row['no_vest']}")
        print(f"  No goggles        : {row['no_goggles']}")
        print(f"  First violation   : {row['first']}")
        print(f"  Last violation    : {row['last']}")
        print(f"{'═'*45}\n")
        return

    # ── Export CSV ────────────────────────────────────────────────────────────
    if args.export:
        import csv
        out = Path("logs/violations_export.csv")
        rows = conn.execute(
            "SELECT * FROM violations ORDER BY timestamp_unix ASC"
        ).fetchall()
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id","timestamp","worker_id","missing_ppe",
                        "severity","screenshot_path","camera","session_id","frame_number"])
            w.writerows(rows)
        print(f"Exported {len(rows)} rows → {out}")
        return

    # ── Recent violations table ───────────────────────────────────────────────
    if args.today:
        today = datetime.now().strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT * FROM violations WHERE timestamp LIKE ? ORDER BY timestamp_unix DESC LIMIT ?",
            (f"{today}%", args.limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM violations ORDER BY timestamp_unix DESC LIMIT ?",
            (args.limit,),
        ).fetchall()

    if not rows:
        print("No violations found.")
        return

    print(f"\n{'═'*80}")
    print(f"  {'ID':<5} {'Time':<20} {'Worker':<8} {'Missing PPE':<22} {'Severity':<10} {'Camera'}")
    print(f"{'─'*80}")
    for r in rows:
        print(
            f"  {r['id']:<5} {r['timestamp']:<20} "
            f"#{r['worker_id']:<7} {r['missing_ppe']:<22} "
            f"{r['severity']:<10} {r['camera']}"
        )
    print(f"{'═'*80}")
    print(f"  Showing {len(rows)} violation(s).  Use --stats for summary, --export for CSV.\n")


if __name__ == "__main__":
    main()
