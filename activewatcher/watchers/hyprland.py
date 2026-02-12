from __future__ import annotations

import asyncio
import json
import os
import pathlib
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from activewatcher.common.http import ActiveWatcherAsyncClient
from activewatcher.common.models import END_MARKER_KEY


def socket2_path() -> str:
    his = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if his and xdg:
        return f"{xdg}/hypr/{his}/.socket2.sock"
    if xdg:
        cand = sorted(pathlib.Path(xdg, "hypr").glob("*/.socket2.sock"))
        if cand:
            return str(cand[-1])
    raise RuntimeError("Hyprland socket2 not found (need HYPRLAND_INSTANCE_SIGNATURE + XDG_RUNTIME_DIR)")


def socket1_path_from_socket2(socket2: str) -> str:
    return str(pathlib.Path(socket2).with_name(".socket.sock"))


async def _hypr_socket_json(socket1: str, command: str) -> Any:
    last_error: Exception | None = None
    for suffix in ("", "\n"):
        reader, writer = await asyncio.open_unix_connection(socket1)
        try:
            writer.write(f"j/{command}{suffix}".encode("utf-8", "strict"))
            await writer.drain()
            buf = bytearray()
            loop = asyncio.get_running_loop()
            deadline = loop.time() + 2.0
            while True:
                timeout = min(0.2, max(0.0, deadline - loop.time()))
                if timeout <= 0:
                    break
                try:
                    chunk = await asyncio.wait_for(reader.read(4096), timeout=timeout)
                except asyncio.TimeoutError:
                    break
                if not chunk:
                    break
                buf += chunk
                text = buf.decode("utf-8", "replace").strip()
                if not text:
                    continue
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    continue

            text = buf.decode("utf-8", "replace").strip()
            if not text:
                last_error = RuntimeError("empty response")
                continue
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                last_error = RuntimeError(f"invalid Hyprland IPC JSON for {command}: {text[:200]}")
                continue
        except Exception as e:
            last_error = e
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    if last_error:
        raise last_error
    return None


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _truncate_title(title: str, max_len: int) -> str:
    t = " ".join(title.split())
    if max_len <= 0:
        return ""
    if len(t) <= max_len:
        return t
    if max_len <= 3:
        return t[:max_len]
    return t[: max_len - 3] + "..."


def _ws_label(value: Any) -> str | None:
    if isinstance(value, dict):
        name = value.get("name")
        if name is not None:
            return str(name)
        ws_id = value.get("id")
        if ws_id is not None:
            return str(ws_id)
        return None
    if value is None:
        return None
    return str(value)


def _ws_id(value: Any) -> int | None:
    if isinstance(value, dict):
        ws_id = value.get("id")
        if isinstance(ws_id, int):
            return ws_id
        if isinstance(ws_id, str) and ws_id.isdigit():
            return int(ws_id)
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _monitor_id(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _pick_monitor(
    monitors: list[dict[str, Any]] | None,
    *,
    monitor_name: str | None,
    monitor_id: int | None,
) -> dict[str, Any] | None:
    if not monitors:
        return None
    if monitor_id is not None:
        mon = next((m for m in monitors if _monitor_id(m.get("id")) == monitor_id), None)
        if mon:
            return mon
    if monitor_name:
        mon = next((m for m in monitors if str(m.get("name") or "") == monitor_name), None)
        if mon:
            return mon
    return _pick_focused_monitor(monitors)


def _workspace_key(
    *,
    workspace: str | None,
    workspace_id: int | None,
    monitor: str | None,
    monitor_id: int | None,
) -> str:
    return f"{workspace_id}:{workspace}:{monitor_id}:{monitor}"


def _workspace_payload(
    *,
    active_ws: dict[str, Any],
    monitors: list[dict[str, Any]] | None,
    title_max_len: int,
    focused_state: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    workspace = _ws_label(active_ws)
    workspace_id = _ws_id(active_ws)

    monitor_name = str(active_ws.get("monitor") or "") or None
    monitor_id = _monitor_id(active_ws.get("monitorID")) or _monitor_id(active_ws.get("monitor"))
    mon = _pick_monitor(monitors, monitor_name=monitor_name, monitor_id=monitor_id)
    if mon:
        monitor_name = monitor_name or str(mon.get("name") or "") or None
        if monitor_id is None:
            monitor_id = _monitor_id(mon.get("id"))

    data: dict[str, Any] = {
        "workspace": workspace,
        "workspace_id": workspace_id,
        "workspace_windows": active_ws.get("windows"),
        "workspace_has_fullscreen": active_ws.get("hasfullscreen"),
        "workspace_last_window": active_ws.get("lastwindow"),
        "workspace_last_window_title": _truncate_title(
            str(active_ws.get("lastwindowtitle") or ""), title_max_len
        ),
        "monitor": monitor_name,
        "monitor_id": monitor_id,
    }

    if mon:
        data.update(
            {
                "monitor_make": mon.get("make"),
                "monitor_model": mon.get("model"),
                "monitor_serial": mon.get("serial"),
                "monitor_description": mon.get("description"),
                "monitor_x": mon.get("x"),
                "monitor_y": mon.get("y"),
                "monitor_width": mon.get("width"),
                "monitor_height": mon.get("height"),
                "monitor_scale": mon.get("scale"),
                "monitor_refresh": mon.get("refreshRate"),
                "monitor_transform": mon.get("transform"),
                "monitor_focused": bool(mon.get("focused")),
            }
        )

    if focused_state:
        data.update(
            {
                "focused_app": focused_state.get("app"),
                "focused_title": focused_state.get("title"),
                "focused_workspace": focused_state.get("workspace"),
                "focused_monitor": focused_state.get("monitor"),
                "focused_xwayland": focused_state.get("xwayland"),
                "focused_no_focus": focused_state.get("no_focus"),
            }
        )

    key = _workspace_key(
        workspace=workspace,
        workspace_id=workspace_id,
        monitor=monitor_name,
        monitor_id=monitor_id,
    )
    return data, key


async def _get_focused_state(
    *,
    socket1_path: str,
    title_max_len: int,
    monitors: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    active_window = await _hypr_socket_json(socket1_path, "activewindow")
    active_ws = await _hypr_socket_json(socket1_path, "activeworkspace")

    workspace = None
    monitor = None
    if isinstance(active_ws, dict):
        workspace = _ws_label(active_ws)
        monitor_raw = active_ws.get("monitor")
        if monitor_raw is not None:
            monitor = str(monitor_raw)

    no_focus = not isinstance(active_window, dict) or not active_window.get("class")
    if no_focus:
        return {
            "app": "__no_focus__",
            "title": "",
            "workspace": workspace,
            "monitor": monitor,
            "xwayland": False,
            "no_focus": True,
        }

    app = str(active_window.get("class") or "")
    title = _truncate_title(str(active_window.get("title") or ""), title_max_len)
    xwayland = bool(active_window.get("xwayland", False))

    # Some setups return monitor as an id; best-effort map to name.
    if monitor and monitor.isdigit():
        if monitors is None:
            try:
                monitors_raw = await _hypr_socket_json(socket1_path, "monitors")
            except Exception:
                monitors_raw = None
            if isinstance(monitors_raw, list):
                monitors = [m for m in monitors_raw if isinstance(m, dict)]
        if monitors:
            focused = next((m for m in monitors if m.get("focused")), None)
            if focused and focused.get("name"):
                monitor = str(focused.get("name"))

    return {
        "app": app,
        "title": title,
        "workspace": workspace,
        "monitor": monitor,
        "xwayland": xwayland,
        "no_focus": False,
    }


def _pick_focused_monitor(monitors: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((m for m in monitors if m.get("focused")), None) or (monitors[0] if monitors else None)


def _client_visible_on_monitor(
    client: dict[str, Any],
    *,
    monitor: dict[str, Any],
    active_ws_id: int | None,
    active_ws_label: str | None,
) -> bool:
    if bool(client.get("hidden", False)):
        return False
    if client.get("mapped") is False:
        return False

    mon_id = _monitor_id(monitor.get("id"))
    mon_name = monitor.get("name")
    c_mon = client.get("monitor")
    c_mon_id = _monitor_id(c_mon)
    if mon_id is not None and c_mon_id is not None:
        if c_mon_id != mon_id:
            return False
    elif mon_name is not None:
        if str(c_mon) != str(mon_name):
            return False

    c_ws = client.get("workspace")
    c_ws_id = _ws_id(c_ws)
    if active_ws_id is not None and c_ws_id is not None:
        return c_ws_id == active_ws_id
    return _ws_label(c_ws) == active_ws_label


def _window_payload_data(
    client: dict[str, Any],
    *,
    title_max_len: int,
    monitor_name: str | None,
) -> dict[str, Any] | None:
    address = str(client.get("address") or "")
    if not address:
        return None
    app = str(client.get("class") or "")
    if not app:
        return None
    title = _truncate_title(str(client.get("title") or ""), title_max_len)
    xwayland = bool(client.get("xwayland", False))
    workspace = _ws_label(client.get("workspace"))

    return {
        "address": address,
        "app": app,
        "title": title,
        "workspace": workspace,
        "monitor": monitor_name,
        "xwayland": xwayland,
        "no_focus": False,
    }


@dataclass
class HyprlandWatcher:
    server_url: str
    source: str
    debounce_ms: int
    title_max_len: int
    heartbeat_seconds: int
    track_focused: bool
    track_visible_windows: bool
    visible_all_monitors: bool
    track_open_apps: bool
    track_workspaces: bool

    def __post_init__(self) -> None:
        self._pending: asyncio.Task | None = None
        self._socket1_path: str | None = None
        self._last_focused_state: dict[str, Any] | None = None
        self._last_focused_sent_state: str | None = None
        self._last_focused_sent_at: float = 0.0

        self._visible_sent_state: dict[str, str] = {}
        self._last_visible_sent_at: float = 0.0

        self._open_apps_sent: set[str] = set()
        self._last_open_apps_sent_at: float = 0.0

        self._last_workspace_state: dict[str, Any] | None = None
        self._last_workspace_key: str | None = None
        self._last_workspace_sent_at: float = 0.0

    def set_socket1_path(self, socket1_path: str) -> None:
        self._socket1_path = socket1_path

    def trigger_refresh(self) -> None:
        if self._pending and not self._pending.done():
            return
        self._pending = asyncio.create_task(self._debounced_refresh())

    async def _debounced_refresh(self) -> None:
        await asyncio.sleep(max(0.0, self.debounce_ms / 1000.0))
        try:
            await self.refresh_and_send(force=False)
        except Exception as e:
            print(f"[hyprland] refresh failed: {e}")

    def _window_source(self, address: str) -> str:
        return f"{self.source}:win:{address}"

    def _app_source(self, app: str) -> str:
        return f"{self.source}:app:{app}"

    def _workspace_source(self) -> str:
        return f"{self.source}:workspace"

    def _workspace_switch_source(self) -> str:
        return f"{self.source}:workspace_switch"

    async def _post_payloads(self, payloads: list[dict[str, Any]]) -> bool:
        if not payloads:
            return True
        client = ActiveWatcherAsyncClient(self.server_url)
        try:
            for payload in payloads:
                await client.post_state(payload)
        except Exception as e:
            print(f"[hyprland] post_state failed: {e}")
            return False
        finally:
            await client.aclose()
        return True

    async def refresh_and_send(self, *, force: bool) -> None:
        if not self._socket1_path:
            return
        now = time.monotonic()
        now_dt = datetime.now(timezone.utc)
        ts = now_dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        ts_end = (now_dt + timedelta(milliseconds=1)).isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        )

        monitors: list[dict[str, Any]] | None = None
        clients: list[dict[str, Any]] | None = None

        if self.track_visible_windows or self.track_workspaces:
            try:
                monitors_raw = await _hypr_socket_json(self._socket1_path, "monitors")
                if isinstance(monitors_raw, list):
                    monitors = [m for m in monitors_raw if isinstance(m, dict)]
            except Exception as e:
                print(f"[hyprland] monitors fetch failed: {e}")
                monitors = None

        if self.track_visible_windows or self.track_open_apps:
            try:
                clients_raw = await _hypr_socket_json(self._socket1_path, "clients")
                if isinstance(clients_raw, list):
                    clients = [c for c in clients_raw if isinstance(c, dict)]
            except Exception as e:
                print(f"[hyprland] clients fetch failed: {e}")
                clients = None

        payloads: list[dict[str, Any]] = []

        next_focused_state: dict[str, Any] | None = None
        next_focused_state_json: str | None = None
        focused_should_send = False
        if self.track_focused:
            try:
                next_focused_state = await _get_focused_state(
                    socket1_path=self._socket1_path,
                    title_max_len=self.title_max_len,
                    monitors=monitors,
                )
            except Exception as e:
                print(f"[hyprland] focused state fetch failed: {e}")
                return
            next_focused_state_json = _canonical_json(next_focused_state)
            focused_should_send = force or next_focused_state_json != self._last_focused_sent_state
            if self.heartbeat_seconds > 0 and (now - self._last_focused_sent_at) >= self.heartbeat_seconds:
                focused_should_send = True
            if focused_should_send:
                payloads.append({"bucket": "window", "source": self.source, "ts": ts, "data": next_focused_state})

        workspace_state: dict[str, Any] | None = None
        workspace_key: str | None = None
        workspace_key_changed = False
        workspace_should_send = False
        workspace_payload: dict[str, Any] | None = None
        if self.track_workspaces:
            try:
                active_ws_raw = await _hypr_socket_json(self._socket1_path, "activeworkspace")
                if isinstance(active_ws_raw, dict):
                    workspace_state, workspace_key = _workspace_payload(
                        active_ws=active_ws_raw,
                        monitors=monitors,
                        title_max_len=self.title_max_len,
                        focused_state=next_focused_state,
                    )
            except Exception as e:
                print(f"[hyprland] activeworkspace fetch failed: {e}")
                workspace_state = None

            if workspace_key is not None:
                workspace_key_changed = workspace_key != self._last_workspace_key
                workspace_should_send = force or workspace_key_changed
                if self.heartbeat_seconds > 0 and (now - self._last_workspace_sent_at) >= self.heartbeat_seconds:
                    workspace_should_send = True

            if workspace_should_send and workspace_state is not None:
                if workspace_key_changed or self._last_workspace_state is None:
                    workspace_payload = dict(workspace_state)
                    if self._last_workspace_state:
                        workspace_payload.update(
                            {
                                "prev_workspace": self._last_workspace_state.get("workspace"),
                                "prev_workspace_id": self._last_workspace_state.get("workspace_id"),
                                "prev_monitor": self._last_workspace_state.get("monitor"),
                                "prev_monitor_id": self._last_workspace_state.get("monitor_id"),
                            }
                        )
                else:
                    workspace_payload = dict(self._last_workspace_state)

                payloads.append(
                    {
                        "bucket": "workspace",
                        "source": self._workspace_source(),
                        "ts": ts,
                        "data": workspace_payload,
                    }
                )

                if workspace_key_changed and self._last_workspace_state:
                    switch_payload = {
                        "from_workspace": self._last_workspace_state.get("workspace"),
                        "from_workspace_id": self._last_workspace_state.get("workspace_id"),
                        "from_monitor": self._last_workspace_state.get("monitor"),
                        "from_monitor_id": self._last_workspace_state.get("monitor_id"),
                        "to_workspace": workspace_state.get("workspace"),
                        "to_workspace_id": workspace_state.get("workspace_id"),
                        "to_monitor": workspace_state.get("monitor"),
                        "to_monitor_id": workspace_state.get("monitor_id"),
                    }
                    if next_focused_state:
                        switch_payload.update(
                            {
                                "focused_app": next_focused_state.get("app"),
                                "focused_title": next_focused_state.get("title"),
                                "focused_xwayland": next_focused_state.get("xwayland"),
                                "focused_no_focus": next_focused_state.get("no_focus"),
                            }
                        )
                    payloads.append(
                        {
                            "bucket": "workspace_switch",
                            "source": self._workspace_switch_source(),
                            "ts": ts,
                            "data": switch_payload,
                        }
                    )
                    payloads.append(
                        {
                            "bucket": "workspace_switch",
                            "source": self._workspace_switch_source(),
                            "ts": ts_end,
                            "data": {END_MARKER_KEY: True},
                        }
                    )

        visible_should_force = force
        if self.track_visible_windows and self.heartbeat_seconds > 0:
            if (now - self._last_visible_sent_at) >= self.heartbeat_seconds:
                visible_should_force = True

        next_visible_sent_state = dict(self._visible_sent_state)
        if self.track_visible_windows and monitors is not None and clients is not None:
            included_monitors: list[dict[str, Any]]
            if self.visible_all_monitors:
                included_monitors = monitors
            else:
                focused_mon = _pick_focused_monitor(monitors)
                included_monitors = [focused_mon] if focused_mon else []

            current_visible: dict[str, dict[str, Any]] = {}
            for mon in included_monitors:
                mon_name = mon.get("name")
                active_ws = mon.get("activeWorkspace")
                active_ws_id = _ws_id(active_ws)
                active_ws_label = _ws_label(active_ws)
                for c in clients:
                    if not _client_visible_on_monitor(
                        c,
                        monitor=mon,
                        active_ws_id=active_ws_id,
                        active_ws_label=active_ws_label,
                    ):
                        continue
                    data = _window_payload_data(c, title_max_len=self.title_max_len, monitor_name=mon_name)
                    if not data:
                        continue
                    current_visible[str(data["address"])] = data

            current_addrs = set(current_visible.keys())
            sent_addrs = set(self._visible_sent_state.keys())

            for addr in sorted(sent_addrs - current_addrs):
                payloads.append(
                    {
                        "bucket": "window_visible",
                        "source": self._window_source(addr),
                        "ts": ts,
                        "data": {END_MARKER_KEY: True},
                    }
                )
                next_visible_sent_state.pop(addr, None)

            for addr in sorted(current_addrs):
                data = current_visible[addr]
                data_json = _canonical_json(data)
                prev_json = self._visible_sent_state.get(addr)
                should_send = visible_should_force or prev_json != data_json
                if should_send:
                    payloads.append(
                        {
                            "bucket": "window_visible",
                            "source": self._window_source(addr),
                            "ts": ts,
                            "data": data,
                        }
                    )
                    next_visible_sent_state[addr] = data_json

        open_apps_should_force = force
        if self.track_open_apps and self.heartbeat_seconds > 0:
            if (now - self._last_open_apps_sent_at) >= self.heartbeat_seconds:
                open_apps_should_force = True

        next_open_apps_sent = set(self._open_apps_sent)
        if self.track_open_apps and clients is not None:
            current_apps: set[str] = set()
            for c in clients:
                app = str(c.get("class") or "")
                if app:
                    current_apps.add(app)

            for app in sorted(self._open_apps_sent - current_apps):
                payloads.append(
                    {
                        "bucket": "app_open",
                        "source": self._app_source(app),
                        "ts": ts,
                        "data": {END_MARKER_KEY: True},
                    }
                )
                next_open_apps_sent.discard(app)

            for app in sorted(current_apps):
                if open_apps_should_force or app not in self._open_apps_sent:
                    payloads.append(
                        {
                            "bucket": "app_open",
                            "source": self._app_source(app),
                            "ts": ts,
                            "data": {"app": app},
                        }
                    )
                    next_open_apps_sent.add(app)

        if not payloads:
            if next_focused_state is not None:
                self._last_focused_state = next_focused_state
            return

        sent_visible_payload = any(p.get("bucket") == "window_visible" for p in payloads)
        sent_apps_payload = any(p.get("bucket") == "app_open" for p in payloads)
        sent_workspace_payload = any(p.get("bucket") == "workspace" for p in payloads)

        ok = await self._post_payloads(payloads)
        if not ok:
            return

        if self.track_focused and focused_should_send:
            self._last_focused_state = next_focused_state
            self._last_focused_sent_state = next_focused_state_json
            self._last_focused_sent_at = now
        elif self.track_focused and next_focused_state is not None:
            self._last_focused_state = next_focused_state

        if self.track_visible_windows and sent_visible_payload:
            self._visible_sent_state = next_visible_sent_state
        if self.track_visible_windows and (sent_visible_payload or visible_should_force):
            self._last_visible_sent_at = now

        if self.track_open_apps and sent_apps_payload:
            self._open_apps_sent = next_open_apps_sent
        if self.track_open_apps and (sent_apps_payload or open_apps_should_force):
            self._last_open_apps_sent_at = now

        if self.track_workspaces and sent_workspace_payload:
            if workspace_key is not None:
                self._last_workspace_key = workspace_key
            if workspace_key_changed and workspace_state is not None:
                self._last_workspace_state = workspace_state
            if self._last_workspace_state is None and workspace_state is not None:
                self._last_workspace_state = workspace_state
            self._last_workspace_sent_at = now

    async def send_heartbeat_if_due(self) -> None:
        if self.heartbeat_seconds <= 0:
            return
        now = time.monotonic()
        should = False
        if self.track_focused and self._last_focused_state is not None:
            if (now - self._last_focused_sent_at) >= self.heartbeat_seconds:
                should = True
        if self.track_visible_windows:
            if (now - self._last_visible_sent_at) >= self.heartbeat_seconds:
                should = True
        if self.track_open_apps:
            if (now - self._last_open_apps_sent_at) >= self.heartbeat_seconds:
                should = True
        if self.track_workspaces and self._last_workspace_state is not None:
            if (now - self._last_workspace_sent_at) >= self.heartbeat_seconds:
                should = True
        if not should:
            return
        await self.refresh_and_send(force=True)


async def run(
    *,
    server_url: str,
    source: str,
    debounce_ms: int,
    title_max_len: int,
    heartbeat_seconds: int,
    track_focused: bool,
    track_visible_windows: bool,
    visible_all_monitors: bool,
    track_open_apps: bool,
    track_workspaces: bool,
) -> None:
    watcher = HyprlandWatcher(
        server_url=server_url,
        source=source,
        debounce_ms=debounce_ms,
        title_max_len=title_max_len,
        heartbeat_seconds=heartbeat_seconds,
        track_focused=track_focused,
        track_visible_windows=track_visible_windows,
        visible_all_monitors=visible_all_monitors,
        track_open_apps=track_open_apps,
        track_workspaces=track_workspaces,
    )

    relevant_prefixes = (
        "activewindow",
        "activewindowv2",
        "workspace",
        "focusedmon",
        "windowtitle",
        "windowtitlev2",
        "openwindow",
        "closewindow",
        "movewindow",
        "moveworkspace",
        "monitoradded",
        "monitorremoved",
    )

    while True:
        path = socket2_path()
        socket1 = socket1_path_from_socket2(path)
        watcher.set_socket1_path(socket1)
        try:
            reader, _ = await asyncio.open_unix_connection(path)
        except Exception as e:
            print(f"[hyprland] connect failed: {e}")
            await asyncio.sleep(1.0)
            continue

        print(f"[hyprland] listening on {path}")
        await watcher.refresh_and_send(force=True)

        try:
            while True:
                await watcher.send_heartbeat_if_due()
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                if not line:
                    raise RuntimeError("socket closed")
                msg = line.decode("utf-8", "replace").strip()
                if not msg:
                    continue
                event, _, _data = msg.partition(">>")
                if event.startswith(relevant_prefixes):
                    watcher.trigger_refresh()
        except Exception as e:
            print(f"[hyprland] disconnected: {e}")
            await asyncio.sleep(0.5)
