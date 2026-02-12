from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from activewatcher.common.models import StateEvent
from activewatcher.common.time import parse_rfc3339, to_utc, utcnow

from . import db, ingest, reports
from .ui import UI_HTML


def _parse_dt_param(value: str | None, *, default: datetime) -> datetime:
    if value is None:
        return default
    try:
        return to_utc(parse_rfc3339(value))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"invalid timestamp: {value}") from e


def create_app(db_path: str | Path) -> FastAPI:
    app = FastAPI(title="activewatcher", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        conn = db.connect(db_path)
        try:
            db.init_db(conn)
        finally:
            conn.close()

    def _get_conn():
        conn = db.connect(db_path)
        try:
            yield conn
        finally:
            conn.close()

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/")
    def root() -> RedirectResponse:
        return RedirectResponse(url="/ui", status_code=302)

    @app.get("/meta")
    def meta() -> dict[str, Any]:
        return {"name": "activewatcher", "health": "/health", "docs": "/docs", "ui": "/ui"}

    @app.get("/ui", response_class=HTMLResponse)
    def ui() -> str:
        return UI_HTML

    @app.get("/ui/stats", response_class=HTMLResponse)
    def ui_stats() -> str:
        return UI_HTML

    @app.post("/v1/state")
    def post_state(state: StateEvent, conn=Depends(_get_conn)) -> dict[str, Any]:
        try:
            result = ingest.ingest_state(conn, state)
        except ingest.NonMonotonicTimestampError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        return {"status": "ok", **result.to_json()}

    @app.get("/v1/range")
    def get_range(
        bucket: str | None = Query(None),
        source: str | None = Query(None),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        from_dt, to_dt = reports.data_range(conn, bucket=bucket, source=source)
        if from_dt is None or to_dt is None:
            return {"empty": True, "from_ts": None, "to_ts": None}
        return {
            "empty": False,
            "from_ts": reports.to_rfc3339(from_dt),
            "to_ts": reports.to_rfc3339(to_dt),
        }

    @app.get("/v1/events")
    def get_events(
        bucket: str | None = Query(None),
        source: str | None = Query(None),
        from_ts: str | None = Query(None, alias="from"),
        to_ts: str | None = Query(None, alias="to"),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        now = utcnow()
        to_dt = _parse_dt_param(to_ts, default=now)
        from_dt = _parse_dt_param(from_ts, default=(to_dt - timedelta(hours=24)))
        from_dt, to_dt, intervals = reports.load_intervals(
            conn, bucket=bucket, source=source, from_ts=from_dt, to_ts=to_dt
        )
        return {
            "from_ts": reports.to_rfc3339(from_dt),
            "to_ts": reports.to_rfc3339(to_dt),
            "events": [i.to_json() for i in intervals],
        }

    @app.get("/v1/summary")
    def get_summary(
        from_ts: str | None = Query(None, alias="from"),
        to_ts: str | None = Query(None, alias="to"),
        chunk_seconds: int = Query(300, ge=30, le=2_592_000),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        now = utcnow()
        to_dt = _parse_dt_param(to_ts, default=now)
        from_dt = _parse_dt_param(from_ts, default=(to_dt - timedelta(hours=24)))
        return reports.summary(conn, from_ts=from_dt, to_ts=to_dt, chunk_seconds=chunk_seconds)

    @app.get("/v1/apps")
    def get_apps(
        from_ts: str | None = Query(None, alias="from"),
        to_ts: str | None = Query(None, alias="to"),
        limit: int = Query(500, ge=1, le=5000),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        now = utcnow()
        to_dt = _parse_dt_param(to_ts, default=now)
        from_dt = _parse_dt_param(from_ts, default=(to_dt - timedelta(days=365)))
        return reports.list_apps(conn, from_ts=from_dt, to_ts=to_dt, limit=limit)

    @app.get("/v1/heatmap")
    def get_heatmap(
        from_ts: str | None = Query(None, alias="from"),
        to_ts: str | None = Query(None, alias="to"),
        tz: str | None = Query("UTC"),
        mode: str = Query("auto"),
        app: list[str] | None = Query(None),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        now = utcnow()
        to_dt = _parse_dt_param(to_ts, default=now)
        from_dt = _parse_dt_param(from_ts, default=(to_dt - timedelta(days=365)))
        try:
            return reports.heatmap(conn, from_ts=from_dt, to_ts=to_dt, tz=tz, mode=mode, apps=app)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    return app
