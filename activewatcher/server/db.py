from __future__ import annotations

import sqlite3
from pathlib import Path

from activewatcher.common.config import ensure_parent_dir


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    ensure_parent_dir(path)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY,
          bucket TEXT NOT NULL,
          source TEXT NOT NULL,
          start_ts TEXT NOT NULL,
          end_ts TEXT,
          last_seen_ts TEXT NOT NULL,
          data_json TEXT NOT NULL
        )
        """.strip()
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_events_open_unique
          ON events(bucket, source)
          WHERE end_ts IS NULL
        """.strip()
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_bucket_source_start ON events(bucket, source, start_ts)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_bucket_start ON events(bucket, start_ts)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_end ON events(end_ts)")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS timers (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          kind TEXT NOT NULL,
          duration_seconds INTEGER NOT NULL DEFAULT 0,
          elapsed_seconds REAL NOT NULL DEFAULT 0,
          running_since_ts TEXT,
          state TEXT NOT NULL DEFAULT 'idle',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          CHECK (kind IN ('timer', 'counter')),
          CHECK (state IN ('idle', 'running', 'paused', 'finished')),
          CHECK (duration_seconds >= 0),
          CHECK (elapsed_seconds >= 0)
        )
        """.strip()
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timers_state ON timers(state)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_timers_updated_at ON timers(updated_at)"
    )
