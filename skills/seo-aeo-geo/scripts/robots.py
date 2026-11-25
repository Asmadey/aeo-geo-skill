"""Единый разбор robots.txt для утилит навыка.

Правила разбора:
- подряд идущие строки User-agent образуют одну группу;
- повторные секции одного агента сливаются;
- группа `*` применяется только при отсутствии именованной группы агента;
- шаблоны пути поддерживают `*` и `$`;
- побеждает самое длинное совпадение, при равенстве длины — Allow;
- пустой Disallow ничего не запрещает.

Статус получения robots.txt переводится в политику:
ok/local → по правилам; 404 и прочие 4xx → allow; 401/403 → unknown
(трактовка зависит от политики целевого бота); 429, 5xx, сеть → unknown.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

RULE_KEYS = {"allow", "disallow", "crawl-delay", "clean-param", "host", "request-rate", "visit-time"}


@dataclass
class Rule:
    allow: bool
    pattern: str
    line: int
    regex: re.Pattern = field(repr=False)


@dataclass
class Decision:
    policy: str  # allow | block | unknown
    reason: str
    group: str | None = None
    rule: str | None = None

    def as_dict(self) -> dict:
        return {"policy": self.policy, "reason": self.reason, "group": self.group, "rule": self.rule}


def _compile(pattern: str) -> re.Pattern:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    rx = "".join(".*" if c == "*" else re.escape(c) for c in body)
    return re.compile(rx + ("$" if anchored else ""), re.S)


def classify_fetch(status: int | None, error: str | None = None) -> str:
    """HTTP-статус robots.txt → ok | 404 | 4xx | 403 | 429 | 5xx | network."""
    if status is None:
        return "network"
    if 200 <= status < 300:
        return "ok"
    if status in (401, 403):
        return "403"
    if status == 429:
        return "429"
    if status == 404:
        return "404"
    if 400 <= status < 500:
        return "4xx"
    if status >= 500:
        return "5xx"
    return "network"  # 1xx/3xx без разрешения — данных нет


class Robots:
    def __init__(self, text: str = "", fetch_status: str = "local", http_status: int | None = None,
                 error: str | None = None, source: str | None = None):
        self.fetch_status = fetch_status
        self.http_status = http_status
        self.error = error
        self.source = source
        self.groups: dict[str, list[Rule]] = {}
        self.sitemaps: list[str] = []
        if fetch_status in ("ok", "local"):
            self._parse(text or "")

    # --- разбор ---
    def _parse(self, text: str) -> None:
        agents: list[str] = []
        in_rules = False
        for n, raw in enumerate(text.splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key, val = key.strip().lower(), val.strip()
            if key == "user-agent":
                if in_rules:
                    agents, in_rules = [], False
                name = val.split("/", 1)[0].strip().lower() if val != "*" else "*"
                if name:
                    agents.append(name)
                    self.groups.setdefault(name, [])
            elif key == "sitemap":
                if val:
                    self.sitemaps.append(val)
            elif key in RULE_KEYS:
                if not agents:
                    continue
                in_rules = True
                if key not in ("allow", "disallow") or not val:
                    continue
                for a in agents:
                    self.groups[a].append(Rule(key == "allow", val, n, _compile(val)))

    # --- решение ---
    def group_for(self, agent: str) -> str | None:
        a = agent.lower()
        if a in self.groups:
            return a
        if "*" in self.groups:
            return "*"
        return None

    def decide(self, agent: str, url: str) -> Decision:
        fs = self.fetch_status
        if fs in ("404", "4xx"):
            return Decision("allow", f"robots.txt HTTP {self.http_status}: файла нет, ограничений нет")
        if fs == "403":
            return Decision("unknown", f"robots.txt HTTP {self.http_status}: трактовка зависит от политики целевого бота")
        if fs == "429":
            return Decision("unknown", "robots.txt HTTP 429: политика не получена")
        if fs == "5xx":
            return Decision("unknown", f"robots.txt HTTP {self.http_status}: ошибка сервера, политика не получена")
        if fs == "network":
            return Decision("unknown", f"сетевая ошибка при получении robots.txt: {self.error or 'нет ответа'}")
        group = self.group_for(agent)
        if group is None:
            return Decision("allow", "нет группы для агента и нет группы *")
        parts = urlsplit(url)
        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query
        best: Rule | None = None
        for r in self.groups[group]:
            if r.regex.match(path):
                if best is None or len(r.pattern) > len(best.pattern) or (
                        len(r.pattern) == len(best.pattern) and r.allow and not best.allow):
                    best = r
        if best is None:
            return Decision("allow", f"в группе {group} нет правила для пути", group)
        verb = "Allow" if best.allow else "Disallow"
        return Decision("allow" if best.allow else "block",
                        f"самое длинное совпадение в группе {group}", group,
                        f"строка {best.line}: {verb}: {best.pattern}")


def from_response(status: int | None, body: bytes | str | None, error: str | None = None,
                  source: str | None = None) -> Robots:
    fs = classify_fetch(status, error)
    text = body.decode("utf-8", "replace") if isinstance(body, bytes) else (body or "")
    return Robots(text if fs == "ok" else "", fs, status, error, source)
