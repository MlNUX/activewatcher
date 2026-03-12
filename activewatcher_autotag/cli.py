from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from activewatcher.common.config import default_categories_path, default_db_path

from .apply import run_apply
from .cleanup import run_cleanup
from .evaluate import run_evaluate
from .runtime import (
    create_run,
    resolve_range,
    resolve_run_root,
    run_lock,
    set_lock_run_id,
)
from .scanner import run_scan
from .settings import LLM_DEFAULTS, RUNTIME_DEFAULTS
from .suggest import run_suggest

app = typer.Typer(add_completion=False)


def _print(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _run_metadata(run_root: Path) -> dict:
    path = run_root / "run-metadata.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


@app.command()
def scan(
    from_spec: Optional[str] = typer.Option(None, "--from"),
    to_spec: Optional[str] = typer.Option(None, "--to"),
    tz: str = typer.Option(RUNTIME_DEFAULTS.default_timezone, "--tz"),
    db_path: Path = typer.Option(default_db_path()),
    categories_path: Path = typer.Option(default_categories_path()),
    run_id: Optional[str] = typer.Option(None),
    force_unlock: bool = typer.Option(False, "--force-unlock"),
) -> None:
    from_dt, to_dt = resolve_range(from_spec=from_spec, to_spec=to_spec)
    with run_lock(force_unlock=force_unlock) as lockfile:
        try:
            root = create_run(run_id)
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        except FileExistsError as e:
            rid = str(run_id or "").strip()
            detail = f"run already exists: {rid}" if rid else "run already exists"
            raise typer.BadParameter(detail) from e
        set_lock_run_id(lockfile, root.name)
        metadata = run_scan(
            run_root=root,
            db_path=db_path,
            from_dt=from_dt,
            to_dt=to_dt,
            tz_name=tz,
            categories_path=categories_path,
        )
    _print(
        {
            "status": "ok",
            "run_id": root.name,
            "run_root": str(root),
            "metadata": metadata,
        }
    )


@app.command()
def suggest(
    run_id: Optional[str] = typer.Option(None),
    provider: str = typer.Option(LLM_DEFAULTS.provider),
    model: str = typer.Option(LLM_DEFAULTS.model),
    ollama_base_url: str = typer.Option("http://127.0.0.1:11434"),
    temperature: float = typer.Option(LLM_DEFAULTS.temperature),
    top_p: float = typer.Option(LLM_DEFAULTS.top_p),
    timeout_seconds: int = typer.Option(LLM_DEFAULTS.timeout_seconds),
    max_retries: int = typer.Option(LLM_DEFAULTS.max_retries),
    batch_size: int = typer.Option(LLM_DEFAULTS.batch_size),
    enable_title_regex: bool = typer.Option(RUNTIME_DEFAULTS.enable_title_regex),
    prune: bool = typer.Option(False),
    force_unlock: bool = typer.Option(False, "--force-unlock"),
) -> None:
    with run_lock(force_unlock=force_unlock) as lockfile:
        try:
            root = resolve_run_root(run_id)
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        except FileNotFoundError as e:
            raise typer.BadParameter(str(e)) from e
        set_lock_run_id(lockfile, root.name)
        metadata = _run_metadata(root)
        categories_path = Path(
            str(metadata.get("categories_path") or default_categories_path())
        )
        result = run_suggest(
            run_root=root,
            categories_path=categories_path,
            provider=provider,
            model=model,
            ollama_base_url=ollama_base_url,
            temperature=temperature,
            top_p=top_p,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            batch_size=batch_size,
            enable_title_regex=enable_title_regex,
            prune=prune,
        )
    _print({"status": "ok", **result})


@app.command()
def evaluate(
    run_id: Optional[str] = typer.Option(None),
    allow_missing_goldset: bool = typer.Option(
        False,
        "--allow-missing-goldset",
        help="Allow evaluate/apply without goldset gates.",
    ),
    force_unlock: bool = typer.Option(False, "--force-unlock"),
) -> None:
    with run_lock(force_unlock=force_unlock) as lockfile:
        try:
            root = resolve_run_root(run_id)
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        except FileNotFoundError as e:
            raise typer.BadParameter(str(e)) from e
        set_lock_run_id(lockfile, root.name)
        result = run_evaluate(
            run_root=root, allow_missing_goldset=allow_missing_goldset
        )
    _print({"status": "ok", **result})


@app.command()
def apply(
    run_id: Optional[str] = typer.Option(None),
    categories_path: Optional[Path] = typer.Option(None),
    confirm: Optional[str] = typer.Option(
        None,
        help='Explicit confirmation token. Must be exactly "APPLY".',
    ),
    force_unlock: bool = typer.Option(False, "--force-unlock"),
) -> None:
    token = str(confirm or "").strip()
    if not token:
        token = typer.prompt('Type "APPLY" to confirm writing categories.json')
    if token != "APPLY":
        raise typer.BadParameter('confirmation token must be exactly "APPLY"')

    with run_lock(force_unlock=force_unlock) as lockfile:
        try:
            root = resolve_run_root(run_id)
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        except FileNotFoundError as e:
            raise typer.BadParameter(str(e)) from e
        set_lock_run_id(lockfile, root.name)
        metadata = _run_metadata(root)
        target = categories_path or Path(
            str(metadata.get("categories_path") or default_categories_path())
        )
        try:
            result = run_apply(run_root=root, categories_path=target)
        except (FileNotFoundError, ValueError) as e:
            raise typer.BadParameter(str(e)) from e

    _print({"status": "ok", **result})


@app.command()
def cleanup(
    older_than: str = typer.Option(
        f"{RUNTIME_DEFAULTS.artifact_retention_days}d", "--older-than"
    ),
    force_unlock: bool = typer.Option(False, "--force-unlock"),
) -> None:
    with run_lock(force_unlock=force_unlock):
        result = run_cleanup(older_than=older_than)
    _print({"status": "ok", **result})


def main() -> None:
    app()


if __name__ == "__main__":
    main()
