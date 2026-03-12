from __future__ import annotations

from contextlib import asynccontextmanager
import ipaddress
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from activewatcher.common import config as app_config
from activewatcher.common.models import StateEvent
from activewatcher.common.time import parse_rfc3339, to_utc, utcnow

from . import db, ingest, reports, timers


def _parse_dt_param(value: str | None, *, default: datetime) -> datetime:
    if value is None:
        return default
    try:
        return to_utc(parse_rfc3339(value))
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"invalid timestamp: {value}"
        ) from e


def _frontend_dist_dir() -> Path:
    raw = os.environ.get("ACTIVEWATCHER_WEB_DIST")
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


def _normalize_origin(value: str) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw == "*":
        return raw
    parsed = urlsplit(raw)
    if parsed.scheme not in ("http", "https"):
        return None
    if not parsed.netloc:
        return None
    if parsed.path not in ("", "/"):
        return None
    if parsed.query or parsed.fragment:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _cors_allow_origins() -> list[str]:
    defaults = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:8712",
        "http://localhost:8712",
    ]
    configured = app_config.config_str_list(
        ("server", "cors_origins"),
        env_var="ACTIVEWATCHER_CORS_ORIGINS",
        default=defaults,
    )
    out: list[str] = []
    for origin in configured:
        normalized = _normalize_origin(origin)
        if normalized and normalized not in out:
            out.append(normalized)
    return out or defaults


def _trusted_hosts() -> list[str]:
    defaults = ["127.0.0.1", "localhost", "[::1]"]
    configured = app_config.config_str_list(
        ("server", "trusted_hosts"),
        env_var="ACTIVEWATCHER_TRUSTED_HOSTS",
        default=defaults,
    )
    out = [str(host).strip() for host in configured if str(host).strip()]
    return out or defaults


def _write_auth_token() -> str:
    return app_config.default_write_token()


def _extract_write_token(
    *, x_activewatcher_token: str | None, authorization: str | None
) -> str:
    header_token = str(x_activewatcher_token or "").strip()
    if header_token:
        return header_token
    raw_auth = str(authorization or "").strip()
    if raw_auth.lower().startswith("bearer "):
        return raw_auth[7:].strip()
    return ""


def _is_loopback_client_host(host: str) -> bool:
    raw = str(host or "").strip().lower()
    if not raw:
        return False
    if raw in {"localhost", "[::1]", "::1", "127.0.0.1", "testclient"}:
        return True
    try:
        return ipaddress.ip_address(raw).is_loopback
    except ValueError:
        return False


def create_app(db_path: str | Path) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        conn = db.connect(db_path)
        try:
            db.init_db(conn)
        finally:
            conn.close()
        yield

    app = FastAPI(title="activewatcher", version="0.1.0", lifespan=lifespan)
    required_write_token = _write_auth_token()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_trusted_hosts())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_allow_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-ActiveWatcher-Token", "Authorization"],
    )

    def _get_conn():
        conn = db.connect(db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _require_write_access(
        request: Request,
        x_activewatcher_token: str | None = Header(
            default=None, alias="X-ActiveWatcher-Token"
        ),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> None:
        if not required_write_token:
            client_host = str(getattr(request.client, "host", "") or "")
            if client_host and not _is_loopback_client_host(client_host):
                raise HTTPException(
                    status_code=403,
                    detail="write access is limited to local clients",
                )
            return
        provided = _extract_write_token(
            x_activewatcher_token=x_activewatcher_token,
            authorization=authorization,
        )
        if not provided or not secrets.compare_digest(provided, required_write_token):
            raise HTTPException(
                status_code=401, detail="missing or invalid write token"
            )

    frontend_dist = _frontend_dist_dir()
    frontend_index = frontend_dist / "index.html"
    frontend_assets = frontend_dist / "assets"
    has_frontend_build = frontend_index.is_file()

    if frontend_assets.is_dir():
        app.mount(
            "/ui/assets", StaticFiles(directory=frontend_assets), name="ui_assets"
        )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/")
    def root() -> RedirectResponse:
        return RedirectResponse(url="/ui", status_code=302)

    @app.get("/meta")
    def meta() -> dict[str, Any]:
        return {
            "name": "activewatcher",
            "health": "/health",
            "docs": "/docs",
            "ui": "/ui",
        }

    def _ui_response():
        if has_frontend_build:
            return FileResponse(frontend_index, media_type="text/html")
        return PlainTextResponse(
            "Frontend build not found. Build frontend with `cd frontend && npm run build`.",
            status_code=503,
        )

    @app.get("/ui")
    def ui():
        return _ui_response()

    @app.get("/ui/")
    def ui_slash():
        return _ui_response()

    @app.get("/ui/stats")
    def ui_stats():
        return _ui_response()

    @app.get("/ui/timers")
    def ui_timers():
        return _ui_response()

    @app.get("/ui/settings")
    def ui_settings():
        return _ui_response()

    @app.get("/ui/favicon.svg")
    def ui_favicon():
        icon_path = frontend_dist / "favicon.svg"
        if not icon_path.is_file():
            raise HTTPException(status_code=404, detail="favicon not found")
        return FileResponse(icon_path, media_type="image/svg+xml")

    @app.get("/ui/{path:path}")
    def ui_spa(path: str):
        if path.startswith("assets/"):
            raise HTTPException(status_code=404, detail="asset not found")
        return _ui_response()

    @app.post("/v1/state")
    def post_state(
        state: StateEvent,
        _auth=Depends(_require_write_access),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
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
        limit: int = Query(5000, ge=1, le=50000),
        cursor: int = Query(0, ge=0),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        now = utcnow()
        to_dt = _parse_dt_param(to_ts, default=now)
        from_dt = _parse_dt_param(from_ts, default=(to_dt - timedelta(hours=24)))
        from_dt, to_dt, intervals, next_cursor = reports.load_intervals_limited(
            conn,
            bucket=bucket,
            source=source,
            from_ts=from_dt,
            to_ts=to_dt,
            limit=limit,
            cursor=cursor,
        )
        return {
            "from_ts": reports.to_rfc3339(from_dt),
            "to_ts": reports.to_rfc3339(to_dt),
            "events": [i.to_json() for i in intervals],
            "next_cursor": next_cursor,
        }

    @app.get("/v1/summary")
    def get_summary(
        from_ts: str | None = Query(None, alias="from"),
        to_ts: str | None = Query(None, alias="to"),
        chunk_seconds: int = Query(300, ge=30, le=2_592_000),
        include_timeline: bool = Query(False),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        now = utcnow()
        to_dt = _parse_dt_param(to_ts, default=now)
        from_dt = _parse_dt_param(from_ts, default=(to_dt - timedelta(hours=24)))
        return reports.summary(
            conn,
            from_ts=from_dt,
            to_ts=to_dt,
            chunk_seconds=chunk_seconds,
            include_timeline=include_timeline,
        )

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
            return reports.heatmap(
                conn, from_ts=from_dt, to_ts=to_dt, tz=tz, mode=mode, apps=app
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    @app.get("/v1/categories")
    def get_categories(
        from_ts: str | None = Query(None, alias="from"),
        to_ts: str | None = Query(None, alias="to"),
        mode: str = Query("auto"),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        now = utcnow()
        to_dt = _parse_dt_param(to_ts, default=now)
        from_dt = _parse_dt_param(from_ts, default=(to_dt - timedelta(hours=24)))
        try:
            return reports.categories_summary(
                conn, from_ts=from_dt, to_ts=to_dt, mode=mode
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    @app.get("/v1/timers")
    def get_timers(conn=Depends(_get_conn)) -> dict[str, Any]:
        return timers.list_timers(conn)

    @app.post("/v1/timers")
    def post_timer(
        payload: dict[str, Any],
        _auth=Depends(_require_write_access),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        try:
            timer = timers.create_timer(
                conn,
                name=payload.get("name"),
                kind=payload.get("kind"),
                duration_seconds=payload.get("duration_seconds"),
            )
            return {"status": "ok", "timer": timer}
        except timers.TimerValidationError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    @app.post("/v1/timers/{timer_id}/start")
    def post_timer_start(
        timer_id: int,
        _auth=Depends(_require_write_access),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        try:
            timer = timers.start_timer(conn, timer_id=timer_id)
            return {"status": "ok", "timer": timer}
        except timers.TimerNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.post("/v1/timers/{timer_id}/pause")
    def post_timer_pause(
        timer_id: int,
        _auth=Depends(_require_write_access),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        try:
            timer = timers.pause_timer(conn, timer_id=timer_id)
            return {"status": "ok", "timer": timer}
        except timers.TimerNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.post("/v1/timers/{timer_id}/stop")
    def post_timer_stop(
        timer_id: int,
        _auth=Depends(_require_write_access),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        try:
            timer = timers.stop_timer(conn, timer_id=timer_id)
            return {"status": "ok", "timer": timer}
        except timers.TimerNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.post("/v1/timers/{timer_id}/reactivate")
    def post_timer_reactivate(
        timer_id: int,
        _auth=Depends(_require_write_access),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        try:
            timer = timers.reactivate_timer(conn, timer_id=timer_id)
            return {"status": "ok", "timer": timer}
        except timers.TimerNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.post("/v1/timers/{timer_id}/delete")
    def post_timer_delete(
        timer_id: int,
        _auth=Depends(_require_write_access),
        conn=Depends(_get_conn),
    ) -> dict[str, Any]:
        try:
            timer = timers.delete_timer(conn, timer_id=timer_id)
            return {"status": "ok", "timer": timer}
        except timers.TimerNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.get("/v1/autotag/runs")
    def get_autotag_runs(
        limit: int = Query(50, ge=1, le=500),
    ) -> dict[str, Any]:
        return reports.list_autotag_runs(limit=limit)

    @app.get("/v1/autotag/decisions")
    def get_autotag_decisions(
        run_id: str | None = Query(None),
        decision_type: str | None = Query(None),
        state: str | None = Query(None),
        limit: int = Query(500, ge=1, le=5000),
    ) -> dict[str, Any]:
        try:
            return reports.autotag_decisions(
                run_id=run_id,
                decision_type=decision_type,
                state=state,
                limit=limit,
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    @app.get("/v1/autotag/generated")
    def get_autotag_generated(
        run_id: str | None = Query(None),
    ) -> dict[str, Any]:
        try:
            return reports.autotag_generated(run_id=run_id)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    @app.post("/v1/autotag/review-gate/approve")
    def post_autotag_review_gate_approve(
        payload: dict[str, Any], _auth=Depends(_require_write_access)
    ) -> dict[str, Any]:
        run_id = str(payload.get("run_id") or "").strip()
        approved_by = str(payload.get("approved_by") or "").strip()
        allowed_drop_ids_raw = payload.get("allowed_category_drop_ids")
        allowed_drop_ids: list[str] | None
        if isinstance(allowed_drop_ids_raw, list):
            allowed_drop_ids = [str(v) for v in allowed_drop_ids_raw]
        else:
            allowed_drop_ids = None
        try:
            return reports.approve_autotag_review_gate(
                run_id=run_id,
                approved_by=approved_by,
                allowed_category_drop_ids=allowed_drop_ids,
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    return app
