"""Общий анализатор raw HTML для site_audit.py и page_audit.py.

Возвращает наблюдения без оценок: title, lang, meta, canonical (разрешённый от
финального URL с учётом <base>), заголовки, ссылки, изображения, JSON-LD,
основной контент и первый блок после H1 в основном контенте.
Основной контент: текст внутри <main>/<article>, если они есть, иначе текст
<body> без <nav>/<header>/<footer>/<aside>. JavaScript не исполняется.
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

SKIP = {"script", "style", "noscript", "template", "svg", "iframe", "object"}
CHROME = {"nav", "header", "footer", "aside"}
MAIN = {"main", "article"}
HEAD = {"h1", "h2", "h3", "h4", "h5", "h6"}
BLOCK = {"p", "li", "td", "th", "div", "section", "br", "tr", "blockquote", "dd", "dt", "pre",
         "figcaption", "ul", "ol", "table", "form"} | HEAD | MAIN | CHROME


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.lang = None
        self.meta: dict[str, str] = {}
        self.canonical_href = None
        self.base_href = None
        self.links: list[str] = []
        self.images: list[dict] = []
        self.tables = 0
        self.jsonld: list[str] = []
        self.blocks: list[dict] = []
        self.has_main = False
        self._skip = 0
        self._chrome = 0
        self._main = 0
        self._in_title = False
        self._in_ld = False
        self._ld: list[str] = []
        self._buf: list[str] = []
        self._kind = "p"

    def _flush(self) -> None:
        t = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        self._buf = []
        if t:
            self.blocks.append({"kind": self._kind, "text": t, "chrome": self._chrome > 0, "main": self._main > 0})

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v if v is not None else "") for k, v in attrs}
        if tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._in_ld, self._ld = True, []
        if tag in SKIP:
            self._skip += 1
            return
        if self._skip:
            return
        if tag == "html":
            self.lang = a.get("lang") or None
        elif tag == "title":
            self._in_title = True
        elif tag == "base" and a.get("href") and self.base_href is None:
            self.base_href = a["href"]
        elif tag == "meta":
            k = (a.get("name") or a.get("property") or "").lower()
            if k:
                self.meta[k] = a.get("content", "")
        elif tag == "link" and "canonical" in a.get("rel", "").lower().split() and self.canonical_href is None:
            self.canonical_href = a.get("href", "")
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "img":
            self.images.append({"src": a.get("src", ""), "alt": a["alt"] if "alt" in a else None,
                                "role": a.get("role", ""), "aria_hidden": a.get("aria-hidden", "")})
        elif tag == "table":
            self.tables += 1
        if tag in BLOCK:
            self._flush()
            self._kind = tag if tag in HEAD else "p"
        if tag in CHROME:
            self._chrome += 1
        if tag in MAIN:
            self._main += 1
            self.has_main = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld:
            self._in_ld = False
            self.jsonld.append("".join(self._ld))
        if tag in SKIP:
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag == "title":
            self._in_title = False
        if tag in BLOCK:
            self._flush()
            self._kind = "p"
        if tag in CHROME:
            self._chrome = max(0, self._chrome - 1)
        if tag in MAIN:
            self._main = max(0, self._main - 1)

    def handle_data(self, data):
        if self._in_ld:
            self._ld.append(data)
        elif self._skip:
            return
        elif self._in_title:
            self.title += data
        else:
            self._buf.append(data)

    def close(self):
        super().close()
        self._flush()


def normalize_url(url: str) -> str:
    """Без склейки схем и хостов: нижний регистр схемы/хоста, без порта по умолчанию и фрагмента."""
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    port = p.port
    if port and not ((p.scheme == "http" and port == 80) or (p.scheme == "https" and port == 443)):
        host = f"{host}:{port}"
    return urlunsplit((p.scheme.lower(), host, p.path or "/", p.query, ""))


def jsonld_types(blocks: list[str]) -> tuple[list[str], int]:
    types: list[str] = []
    errors = 0

    def walk(o):
        if isinstance(o, dict):
            t = o.get("@type")
            if isinstance(t, str):
                types.append(t)
            elif isinstance(t, list):
                types.extend(x for x in t if isinstance(x, str))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for raw in blocks:
        try:
            walk(json.loads(raw))
        except ValueError:
            errors += 1
    return sorted(set(types)), errors


def parse(html: str, final_url: str | None = None) -> dict:
    p = _Parser()
    try:
        p.feed(html or "")
        p.close()
    except Exception:  # noqa: BLE001 — битый HTML: берём то, что разобрано
        pass
    base = final_url or ""
    if p.base_href is not None and final_url:
        base = urljoin(final_url, p.base_href)
    canonical = None
    if p.canonical_href is not None:
        canonical = urljoin(base, p.canonical_href.strip()) if base else p.canonical_href.strip()
    links = []
    for href in p.links:
        h = href.strip()
        if not h or h.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        links.append(urljoin(base, h).split("#", 1)[0] if base else h)
    blocks = p.blocks
    region = [b for b in blocks if b["main"]] if p.has_main else [b for b in blocks if not b["chrome"]]
    main_text = " ".join(b["text"] for b in region if not b["chrome"])
    h1 = [b["text"] for b in blocks if b["kind"] == "h1"]
    lede = None
    seen = False
    for b in region:
        if b["chrome"]:
            continue
        if b["kind"] == "h1" and not seen:
            seen = True
            continue
        if seen and b["kind"] == "p":
            lede = b["text"]
            break
        if seen and b["kind"] in HEAD:
            break
    types, ld_errors = jsonld_types(p.jsonld)
    robots_meta = {k: v for k, v in p.meta.items() if k == "robots" or k.endswith("bot") or k in (
        "googlebot-news", "yandex")}
    return {
        "title": p.title.strip(),
        "lang": p.lang,
        "meta": p.meta,
        "robots_meta": robots_meta,
        "base_href": p.base_href,
        "canonical_href": p.canonical_href,
        "canonical": canonical,
        "h1": h1,
        "headings": [(b["kind"], b["text"]) for b in blocks if b["kind"] in HEAD],
        "links": links,
        "images": p.images,
        "tables": p.tables,
        "jsonld_blocks": len(p.jsonld),
        "jsonld_types": types,
        "jsonld_errors": ld_errors,
        "has_main_element": p.has_main,
        "main_text": main_text,
        "lede_after_h1": lede,
    }


DIRECTIVES = {"noindex", "nofollow", "none", "noarchive", "nosnippet", "max-snippet", "max-image-preview",
              "max-video-preview", "unavailable_after", "notranslate", "noimageindex", "indexifembedded", "all",
              "index", "follow"}


def _has_noindex(content: str) -> bool:
    tokens = [t.strip() for t in content.lower().split(",")]
    return "noindex" in tokens or "none" in tokens


def noindex_for(agent: str, robots_meta: dict, x_robots: str | None) -> tuple[bool, list[str]]:
    """noindex для агента: meta robots, meta <agent>, X-Robots-Tag общий или с префиксом агента."""
    a = agent.lower()
    evidence = []
    for name in ("robots", a):
        if name in robots_meta and _has_noindex(robots_meta[name]):
            evidence.append(f'<meta name="{name}" content="{robots_meta[name]}">')
    for part in (x_robots or "").split("\n"):
        val = part.strip()
        if not val:
            continue
        who, sep, rest = val.partition(":")
        if sep and who.strip().lower() not in DIRECTIVES:
            if who.strip().lower() != a:
                continue
            val = rest
        if _has_noindex(val):
            evidence.append(f"X-Robots-Tag: {part.strip()}")
    return bool(evidence), evidence


def is_internal(url: str, host: str) -> bool:
    h = (urlsplit(url).hostname or "").lower()
    return h == host.lower() or h.removeprefix("www.") == host.lower().removeprefix("www.")
