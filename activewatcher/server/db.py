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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_bucket_start ON events(bucket, start_ts)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_end ON events(end_ts)")
