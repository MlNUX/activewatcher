from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from activewatcher.common.config import default_categories_path

_MULTI_PART_SUFFIXES = {
    "co.uk",
    "org.uk",
    "ac.uk",
    "gov.uk",
    "com.au",
    "net.au",
    "org.au",
    "co.nz",
    "co.in",
    "co.jp",
    "co.kr",
    "co.id",
    "co.il",
    "com.br",
    "com.mx",
    "com.ar",
    "com.tr",
    "com.pl",
    "com.ru",
    "com.cn",
    "com.tw",
    "com.hk",
    "com.sg",
    "com.my",
    "com.ph",
    "com.sa",
    "com.ng",
}


@dataclass(frozen=True)
class CategoryRule:
    id: str
    label: str
    color: str
    apps: tuple[str, ...]
    domains: tuple[str, ...]
    titles: tuple[str, ...]
    urls: tuple[str, ...]
    title_regex: tuple[re.Pattern[str], ...]


@dataclass(frozen=True)
class CategoryCatalog:
    rules: tuple[CategoryRule, ...]
    source: str

    def category_meta(self) -> list[dict[str, str]]:
        return [{"id": r.id, "label": r.label, "color": r.color} for r in self.rules]

    def classify_app(self, *, app: str, title: str = "") -> str:
        app_norm = str(app or "").strip().lower()
        title_norm = str(title or "").strip().lower()
        return self._classify(app=app_norm, title=title_norm, domain="", url="")

    def classify_tab(self, *, url: str, title: str = "", app: str = "") -> str:
        url_norm = str(url or "").strip().lower()
        title_norm = str(title or "").strip().lower()
        app_norm = str(app or "").strip().lower()
        host = _host_from_url(url_norm)
        base = _base_domain(host)
        domain = base or host
        return self._classify(app=app_norm, title=title_norm, domain=domain, url=url_norm)

    def _classify(self, *, app: str, title: str, domain: str, url: str) -> str:
        fallback = self.rules[-1].id if self.rules else "other"
        for rule in self.rules:
            if _matches(rule, app=app, title=title, domain=domain, url=url):
                return rule.id
        return fallback


def _norm_list(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    for v in raw:
        s = str(v or "").strip().lower()
        if s:
            out.append(s)
    return tuple(dict.fromkeys(out))


def _compile_regex_list(raw: Any) -> tuple[re.Pattern[str], ...]:
    if not isinstance(raw, list):
        return ()
    out: list[re.Pattern[str]] = []
    for v in raw:
        s = str(v or "").strip()
        if not s:
            continue
        try:
            out.append(re.compile(s, re.IGNORECASE))
        except re.error:
            continue
    return tuple(out)


def _matches(rule: CategoryRule, *, app: str, title: str, domain: str, url: str) -> bool:
    if app and any(token in app for token in rule.apps):
        return True
    if domain and any(_domain_match(domain, token) for token in rule.domains):
        return True
    if title and any(token in title for token in rule.titles):
        return True
    if url and any(token in url for token in rule.urls):
        return True
    if title and any(rx.search(title) for rx in rule.title_regex):
        return True
    return False


def _domain_match(domain: str, token: str) -> bool:
    d = str(domain or "").strip().lower()
    t = str(token or "").strip().lower()
    if not d or not t:
        return False
    if "." in t:
        return d == t or d.endswith(f".{t}")
    return t in d


def _host_from_url(raw: str) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    parsed = urlparse(s)
    if not parsed.scheme:
        parsed = urlparse(f"http://{s}")
    host = (parsed.hostname or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _base_domain(host: str) -> str:
    h = str(host or "").strip().lower()
    if not h or "." not in h:
        return h
    parts = [p for p in h.split(".") if p]
    if len(parts) <= 2:
        return h
    tld2 = ".".join(parts[-2:])
    if tld2 in _MULTI_PART_SUFFIXES and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _default_rule_items() -> list[dict[str, Any]]:
    return [
        {
            "id": "coding",
            "label": "Coding",
            "color": "#2dd4bf",
            "apps": [
                "code",
                "cursor",
                "nvim",
                "neovim",
                "vim",
                "emacs",
                "jetbrains",
                "pycharm",
                "webstorm",
                "idea",
                "goland",
                "rustrover",
                "zed",
            ],
            "domains": [
                "github.com",
                "gitlab.com",
                "bitbucket.org",
                "stackoverflow.com",
                "stackexchange.com",
                "readthedocs.io",
            ],
            "titles": ["pull request", "merge request", "commit", "diff", "review"],
        },
        {
            "id": "communication",
            "label": "Communication",
            "color": "#38bdf8",
            "apps": [
                "slack",
                "discord",
                "telegram",
                "signal",
                "teams",
                "zoom",
                "thunderbird",
                "whatsapp",
            ],
            "domains": [
                "slack.com",
                "discord.com",
                "web.whatsapp.com",
                "teams.microsoft.com",
                "meet.google.com",
                "mail.google.com",
                "outlook.office.com",
            ],
        },
        {
            "id": "uni",
            "label": "Uni",
            "color": "#facc15",
            "domains": [
                "kit.edu",
                "campus.kit.edu",
                "ilias",
                "moodle",
                "uni-",
            ],
            "titles": [
                "vorlesung",
                "ubung",
                "klausur",
                "praktikum",
                "tutorium",
            ],
        },
        {
            "id": "research",
            "label": "Research",
            "color": "#22c55e",
            "apps": ["obsidian", "zotero", "evince", "okular"],
            "domains": [
                "wikipedia.org",
                "arxiv.org",
                "scholar.google.com",
                "docs.python.org",
                "developer.mozilla.org",
                "kubernetes.io",
                "docs.rs",
                "pypi.org",
                "npmjs.com",
            ],
        },
        {
            "id": "ops",
            "label": "Ops",
            "color": "#f59e0b",
            "apps": ["kitty", "alacritty", "wezterm", "gnome-terminal", "konsole", "docker", "k9s"],
            "domains": ["grafana", "prometheus", "kibana", "cloudflare.com", "console.aws.amazon.com"],
            "titles": ["ssh", "kubectl", "docker", "terraform", "ansible"],
        },
        {
            "id": "media",
            "label": "Media",
            "color": "#a78bfa",
            "apps": ["vlc", "spotify", "mpv", "obs", "stremio"],
            "domains": ["youtube.com", "spotify.com", "netflix.com", "twitch.tv", "soundcloud.com"],
        },
        {
            "id": "social",
            "label": "Social",
            "color": "#ec4899",
            "domains": [
                "reddit.com",
                "x.com",
                "twitter.com",
                "facebook.com",
                "instagram.com",
                "linkedin.com",
                "tiktok.com",
            ],
        },
        {
            "id": "other",
            "label": "Other",
            "color": "rgba(255,255,255,.45)",
        },
    ]


def _parse_rules(raw: Any) -> tuple[CategoryRule, ...]:
    if not isinstance(raw, list):
        raw = _default_rule_items()

    rules: list[CategoryRule] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        cat_id = str(item.get("id") or "").strip().lower()
        if not cat_id:
            continue
        label = str(item.get("label") or cat_id).strip() or cat_id
        color = str(item.get("color") or "rgba(255,255,255,.45)").strip() or "rgba(255,255,255,.45)"
        rules.append(
            CategoryRule(
                id=cat_id,
                label=label,
                color=color,
                apps=_norm_list(item.get("apps")),
                domains=_norm_list(item.get("domains")),
                titles=_norm_list(item.get("titles")),
                urls=_norm_list(item.get("urls")),
                title_regex=_compile_regex_list(item.get("title_regex")),
            )
        )

    if not rules:
        return _parse_rules(_default_rule_items())

    if all(r.id != "other" for r in rules):
        rules.append(
            CategoryRule(
                id="other",
                label="Other",
                color="rgba(255,255,255,.45)",
                apps=(),
                domains=(),
                titles=(),
                urls=(),
                title_regex=(),
            )
        )

    dedup: list[CategoryRule] = []
    seen: set[str] = set()
    for r in rules:
        if r.id in seen:
            continue
        dedup.append(r)
        seen.add(r.id)

    return tuple(dedup)


def _read_override(path: Path) -> tuple[str, list[dict[str, Any]] | None]:
    if not path.exists() or not path.is_file():
        return "default", None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "default", None
    if not isinstance(payload, dict):
        return "default", None
    raw_rules = payload.get("categories")
    if not isinstance(raw_rules, list):
        return "default", None
    return f"file:{path}", raw_rules


@lru_cache(maxsize=1)
def category_catalog() -> CategoryCatalog:
    path = default_categories_path()
    source, raw = _read_override(path)
    rules = _parse_rules(raw if raw is not None else _default_rule_items())
    return CategoryCatalog(rules=rules, source=source)
