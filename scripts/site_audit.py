#!/usr/bin/env python3
"""Технический аудит сайта или страницы: доступ агентов, наблюдения check_id × URL, оценка tech-v1.

Заменяет geo_audit.py и check_access.py. Только стандартная библиотека, Python 3.10+.

Примеры:
  python3 site_audit.py https://example.com/pricing                 # одна страница + доступ агентов
  python3 site_audit.py https://example.com --robots-file robots.txt --no-fetch --json
  python3 site_audit.py --site https://example.com --json            # выборка по бюджету SKILL.md
  python3 site_audit.py --site https://example.com --score --out snapshot.json

Результат идёт в stdout. Файл пишется только по --out. В HOME и cwd ничего не пишется.
Пауза между запросами не меньше 1 с, Retry-After соблюдается, после трёх 429/5xx подряд
обход останавливается и выборка помечается неполной. Цели — только публичные http(s).
"""
from __future__ import annotations

import argparse
import gzip
import html
import io
import json
import math
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import bots
import htmlinfo
import robots as robotslib
from netfetch import Fetcher, host_key

SCHEMA_VERSION = "site_audit/1"
RULES_VERSION = "tech-v1"
DEFAULT_BUDGET = 20
PER_TEMPLATE = 2
SITEMAP_MAX_DEPTH = 2
SITEMAP_MAX_REQUESTS = 10
SITEMAP_MAX_URLS = 50_000
GZIP_MAX = 50_000_000

# Реестр tech-v1: check_id → (уровень, вес, область, обязательность)
TECH_V1 = {
    "http_status": ("critical", 10, "url", "mandatory"),
    "search_crawl_access": ("critical", 10, "url", "mandatory"),
    "index_directive": ("critical", 10, "url", "mandatory"),
    "canonical_target": ("high", 5, "url", "mandatory"),
    "main_content_raw": ("high", 5, "url", "mandatory"),
    "sitemap_discovery": ("medium", 2, "site", "mandatory_site"),
    "internal_reachability": ("medium", 2, "url", "optional"),
}
CRITICAL = [c for c, v in TECH_V1.items() if v[0] == "critical"]
HIGH = [c for c, v in TECH_V1.items() if v[0] == "high"]
CDN_HEADERS = ("cf-ray", "cf-cache-status", "x-amz-cf-id", "x-served-by", "x-cache", "x-akamai-transformed",
               "x-vercel-id", "x-nf-request-id", "server")


# ---------------------------------------------------------------- аргументы

def _limit(v: str) -> int:
    n = int(v)
    if n < 1:
        raise argparse.ArgumentTypeError("--limit 0 («все URL») удалён: укажите явное N ≥ 1")
    return n


def _pair(v: str) -> tuple[str, str]:
    url, sep, rest = v.partition("::")
    return url.strip(), (rest.strip() if sep else "")


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Технический аудит: доступ агентов, наблюдения, оценка tech-v1")
    ap.add_argument("url", nargs="?", help="URL одной страницы (режим доступа и проверки страницы)")
    ap.add_argument("--site", help="корень сайта: выборка по бюджету")
    ap.add_argument("--robots-file", help="локальный robots.txt вместо загрузки")
    ap.add_argument("--no-fetch", action="store_true", help="не запрашивать страницы; robots грузится, если нет --robots-file")
    ap.add_argument("--limit", type=_limit, default=DEFAULT_BUDGET, help="бюджет URL выборки (по умолчанию 20, явное расширение)")
    ap.add_argument("--per-template", type=int, default=PER_TEMPLATE, help="URL на шаблон (по умолчанию 2)")
    ap.add_argument("--sample-file", help="файл со списком URL (по строке) — повтор той же выборки")
    ap.add_argument("--search-agent", default="Googlebot", help="поисковый агент для search_crawl_access")
    ap.add_argument("--agents", help="токены агентов через запятую для пар URL × агент (по умолчанию весь реестр)")
    ap.add_argument("--probe", choices=["none", "home", "sample"], default="home",
                    help="диагностическая UA-проба: none, только главная/страница (по умолчанию), вся выборка")
    ap.add_argument("--exclude", action="append", type=_pair, default=[], metavar="URL::причина",
                    help="подтверждённое намеренное исключение URL из целевого набора T")
    ap.add_argument("--intended-canonical", action="append", type=_pair, default=[], metavar="URL::причина",
                    help="осознанный cross-canonical: canonical_target неприменима")
    ap.add_argument("--render", action="append", type=_pair, default=[], metavar="URL::файл",
                    help="отрендеренный HTML для сверки main_content_raw")
    ap.add_argument("--max-depth", type=int, default=2, help="глубина internal_reachability")
    ap.add_argument("--score", action="store_true", help="рассчитать ориентир tech-v1")
    ap.add_argument("--delay", type=float, default=1.0, help="пауза между запросами, с (не меньше 1)")
    ap.add_argument("--json", action="store_true", help="JSON в stdout")
    ap.add_argument("--out", help="записать JSON в этот файл")
    ap.add_argument("--allow-private-targets", action="store_true", help=argparse.SUPPRESS)  # только тесты
    a = ap.parse_args(argv)
    if bool(a.url) == bool(a.site):
        ap.error("нужен ровно один вход: позиционный URL или --site")
    if a.delay < 1.0:
        ap.error("--delay не меньше 1 с")
    if a.per_template < 1:
        ap.error("--per-template ≥ 1")
    for name in ("url", "site"):
        v = getattr(a, name)
        if v and "://" not in v:
            setattr(a, name, "https://" + v)
    return a


# ---------------------------------------------------------------- выборка

def template_key(url: str) -> str:
    segs = [s for s in urlsplit(url).path.split("/") if s]
    if not segs:
        return "/"
    if len(segs) == 1:
        return "/*"
    return "/" + segs[0] + "/*" * (len(segs) - 1)


def select_sample(home: str, candidates: list[str], budget: int, per_template: int = PER_TEMPLATE) -> dict:
    """Главная + до per_template URL на шаблон, всего ≤ budget. Детерминированно:
    шаблоны по числу URL (убыв.), при равенстве — по первому появлению; раунды по одному URL."""
    home_n = htmlinfo.normalize_url(home)
    seen, order = set(), []
    for u in candidates:
        n = htmlinfo.normalize_url(u)
        if n == home_n or n in seen:
            continue
        seen.add(n)
        order.append(n)
    groups: dict[str, list[str]] = {}
    first: dict[str, int] = {}
    for i, u in enumerate(order):
        k = template_key(u)
        groups.setdefault(k, []).append(u)
        first.setdefault(k, i)
    tpl = sorted(groups, key=lambda k: (-len(groups[k]), first[k]))
    selected = [home_n]
    picked: dict[str, list[str]] = {k: [] for k in tpl}
    for rnd in range(per_template):
        for k in tpl:
            if len(selected) >= budget:
                break
            if rnd < len(groups[k]):
                selected.append(groups[k][rnd])
                picked[k].append(groups[k][rnd])
    templates = [{"template": k, "candidate_urls": len(groups[k]), "selected": picked[k]} for k in tpl]
    excluded = [{"template": k, "reason": "бюджет"} for k in tpl if not picked[k]]
    return {"budget": budget, "per_template": per_template, "selected": selected,
            "templates": templates, "excluded_templates": excluded}


# ---------------------------------------------------------------- sitemap

def _decode_body(body: bytes) -> str:
    if body[:2] == b"\x1f\x8b":
        try:
            body = gzip.GzipFile(fileobj=io.BytesIO(body)).read(GZIP_MAX)
        except (OSError, EOFError):
            return ""
    return body.decode("utf-8", "replace")


def discover_sitemaps(fetcher, origin: str, robots: robotslib.Robots, scope_host: str) -> dict:
    seeds = [(urljoin(origin + "/", s), "robots") for s in robots.sitemaps] + [(origin + "/sitemap.xml", "known_path")]
    queue, visited, entries, urls = [], set(), [], []
    for u, src in seeds:
        if htmlinfo.normalize_url(u) not in {htmlinfo.normalize_url(q[0]) for q in queue}:
            queue.append((u, 0, src))
    requests = 0
    limited = False
    while queue:
        u, depth, src = queue.pop(0)
        key = htmlinfo.normalize_url(u)
        if key in visited:
            entries.append({"url": u, "source": src, "result": "skipped_cycle_or_duplicate"})
            continue
        if requests >= SITEMAP_MAX_REQUESTS:
            limited = True
            entries.append({"url": u, "source": src, "result": "skipped_request_limit"})
            continue
        visited.add(key)
        requests += 1
        r = fetcher.fetch(u, bots.TYPICAL_CLIENT_UA)
        e = {"url": u, "source": src, "depth": depth, "status": r.status, "error": r.error}
        entries.append(e)
        if not r.ok:
            e["result"] = "error"
            continue
        text = _decode_body(r.body)
        locs = [html.unescape(x.strip()) for x in re.findall(r"<loc>\s*(.*?)\s*</loc>", text, re.S | re.I)]
        if re.search(r"<sitemapindex\b", text, re.I):
            e["result"] = "index"
            e["children"] = len(locs)
            if depth >= SITEMAP_MAX_DEPTH:
                e["note"] = f"лимит глубины {SITEMAP_MAX_DEPTH}: вложенные не загружены"
                limited = True
                continue
            for c in locs:
                queue.append((c, depth + 1, "index:" + u))
        elif re.search(r"<urlset\b", text, re.I):
            e["result"] = "urlset"
            e["urls"] = len(locs)
            for c in locs:
                if len(urls) >= SITEMAP_MAX_URLS:
                    limited = True
                    break
                if htmlinfo.is_internal(c, scope_host):
                    urls.append(c)
        else:
            e["result"] = "unknown_format"
    found = any(e.get("result") in ("index", "urlset") for e in entries)
    hard_errors = [e for e in entries if e.get("result") == "error" and (
        e["status"] is None or e["status"] == 429 or e["status"] >= 500)]
    out, seen = [], set()
    for u in urls:
        n = htmlinfo.normalize_url(u)
        if n not in seen:
            seen.add(n)
            out.append(u)
    return {"entries": entries, "urls": out, "found": found, "network_or_server_errors": len(hard_errors),
            "limited": limited}


# ---------------------------------------------------------------- наблюдения

def _obs(check_id, url, status, reason, evidence=None) -> dict:
    lvl, w, scope, mand = TECH_V1[check_id]
    return {"check_id": check_id, "scope": scope, "url": url, "status": status, "reason": reason,
            "evidence": evidence, "level": lvl}


def page_observations(url: str, page: dict | None, robots: robotslib.Robots, opts, render_html: str | None,
                      reach: dict | None) -> list[dict]:
    out = []
    search = opts.search_agent
    bot = bots.by_token(search) or {}
    # http_status — типичный клиент
    if page is None:
        out.append(_obs("http_status", url, "unknown", "страница не запрашивалась (--no-fetch или обход остановлен)"))
    elif page["status"] is None:
        out.append(_obs("http_status", url, "unknown", "сетевой сбой: " + (page["error"] or ""), page["redirects"]))
    elif page["error"] and page["status"] in (301, 302, 303, 307, 308):
        out.append(_obs("http_status", url, "unknown", page["error"], page["redirects"]))
    elif 200 <= page["status"] < 300:
        out.append(_obs("http_status", url, "pass", f"HTTP {page['status']} для типичного клиента",
                        {"final_url": page["final_url"], "redirects": page["redirects"]}))
    else:
        out.append(_obs("http_status", url, "fail", f"HTTP {page['status']} для типичного клиента",
                        {"final_url": page["final_url"], "redirects": page["redirects"]}))
    # search_crawl_access — политика robots целевого поискового агента
    d = robots.decide(search, page["final_url"] if page else url)
    if bot.get("needs_verification"):
        out.append(_obs("search_crawl_access", url, "unknown",
                        f"карточка {search} требует проверки: агент и трактовка robots не сверены", d.as_dict()))
    elif d.policy == "block":
        out.append(_obs("search_crawl_access", url, "fail", f"robots запрещает {search}", d.as_dict()))
    elif d.policy == "allow":
        out.append(_obs("search_crawl_access", url, "pass", f"robots разрешает {search}; фактический доступ не проверен",
                        d.as_dict()))
    else:
        out.append(_obs("search_crawl_access", url, "unknown", d.reason, d.as_dict()))
    ok = page is not None and page["status"] is not None and 200 <= page["status"] < 300 and not page["error"]
    non2xx = page is not None and page["status"] is not None and not (200 <= page["status"] < 300)
    info = page["parsed"] if ok else None

    def na_or_unknown(cid):
        if non2xx:
            out.append(_obs(cid, url, "not_applicable", "финальный ответ не 2xx: URL исключён из знаменателя"))
        else:
            out.append(_obs(cid, url, "unknown", "нет ответа страницы"))

    # index_directive
    if not ok:
        na_or_unknown("index_directive")
    elif d.policy == "block":
        out.append(_obs("index_directive", url, "not_applicable",
                        "чтение заблокировано robots: применение noindex не подтверждено", d.as_dict()))
    elif d.policy == "unknown":
        out.append(_obs("index_directive", url, "unknown", "политика robots неизвестна: читаемость представления не установлена"))
    else:
        has, ev = htmlinfo.noindex_for(search, info["robots_meta"], page["headers"].get("x-robots-tag"))
        note = "по ответу типичному клиенту (допущение: представление для бота то же)"
        out.append(_obs("index_directive", url, "fail" if has else "pass",
                        ("noindex найден " if has else "noindex нет ") + note, ev or None))
    # canonical_target
    intended = dict(opts.intended_canonical)
    if not ok:
        na_or_unknown("canonical_target")
    elif htmlinfo.normalize_url(url) in {htmlinfo.normalize_url(k) for k in intended}:
        reason = next(v for k, v in intended.items() if htmlinfo.normalize_url(k) == htmlinfo.normalize_url(url))
        out.append(_obs("canonical_target", url, "not_applicable", "осознанный cross-canonical: " + (reason or "без причины")))
    elif not info["canonical"]:
        out.append(_obs("canonical_target", url, "pass", "canonical отсутствует"))
    else:
        final_n, can_n = htmlinfo.normalize_url(page["final_url"]), htmlinfo.normalize_url(info["canonical"])
        ev = {"href": info["canonical_href"], "base_href": info["base_href"], "resolved": info["canonical"],
              "final_url": page["final_url"]}
        if can_n == final_n:
            out.append(_obs("canonical_target", url, "pass", "canonical указывает на финальный URL", ev))
        else:
            out.append(_obs("canonical_target", url, "fail", "canonical указывает на другой адрес", ev))
    # main_content_raw
    if not ok:
        na_or_unknown("main_content_raw")
    else:
        raw = info["main_text"].strip()
        ev = {"raw_chars": len(raw), "raw_excerpt": raw[:160], "main_element": info["has_main_element"]}
        if render_html is not None:
            rend = htmlinfo.parse(render_html, page["final_url"])["main_text"].strip()
            ev["render_chars"] = len(rend)
            if rend and len(raw) < 0.5 * len(rend):
                out.append(_obs("main_content_raw", url, "fail", "основной контент есть в рендере и отсутствует в raw HTML", ev))
            elif raw:
                out.append(_obs("main_content_raw", url, "pass", "основной контент есть в raw HTML", ev))
            else:
                out.append(_obs("main_content_raw", url, "unknown", "основного контента нет ни в raw, ни в рендере", ev))
        elif raw:
            out.append(_obs("main_content_raw", url, "pass", "основной контент есть в raw HTML", ev))
        else:
            out.append(_obs("main_content_raw", url, "unknown",
                            "основного контента нет в raw HTML; без рендера отсутствие не подтверждено", ev))
    # internal_reachability (опциональная)
    if reach is None:
        out.append(_obs("internal_reachability", url, "not_applicable", "проверка уровня сайта; в режиме страницы не выполняется"))
    elif not reach["complete"]:
        out.append(_obs("internal_reachability", url, "not_applicable", "фронтир неполный", {"missing": reach["missing"][:10]}))
    elif not ok:
        out.append(_obs("internal_reachability", url, "not_applicable", "финальный ответ не 2xx"))
    elif htmlinfo.normalize_url(url) in reach["reachable"]:
        out.append(_obs("internal_reachability", url, "pass", f"достижим за ≤{reach['depth']} переходов по raw-ссылкам"))
    else:
        out.append(_obs("internal_reachability", url, "fail", f"недостижим за {reach['depth']} переходов по raw-ссылкам"))
    return out


def reachability(home: str, pages: dict, depth: int, host: str) -> dict:
    """BFS по raw-ссылкам загруженных страниц. Фронтир полный, если все URL глубины < depth загружены."""
    home_n = htmlinfo.normalize_url(home)
    reachable = {home_n}
    frontier = [home_n]
    missing = []
    for _ in range(depth):
        nxt = []
        for u in frontier:
            p = pages.get(u)
            if p is None:
                missing.append(u)
                continue
            if p["parsed"] is None:
                continue
            for link in p["parsed"]["links"]:
                if not htmlinfo.is_internal(link, host):
                    continue
                n = htmlinfo.normalize_url(link)
                if n not in reachable:
                    reachable.add(n)
                    nxt.append(n)
        frontier = nxt
    return {"complete": not missing, "missing": missing, "reachable": reachable, "depth": depth}


# ---------------------------------------------------------------- оценка tech-v1

def _round(x: float) -> int:
    return int(math.floor(x + 0.5))


def compute_score(observations: list[dict], target: list[str], home: str | None, site_mode: bool,
                  checked: int | None = None, valid: bool = True, invalid_reason: str | None = None) -> dict:
    T = [htmlinfo.normalize_url(u) for u in target]
    home_n = htmlinfo.normalize_url(home) if home else None
    idx = {}
    for o in observations:
        key = (o["check_id"], htmlinfo.normalize_url(o["url"]) if o["scope"] == "url" and o["url"] else None)
        idx[key] = o["status"]
    res = {"rules_version": RULES_VERSION, "weights": {c: v[1] for c, v in TECH_V1.items()},
           "levels": {c: v[0] for c, v in TECH_V1.items()}, "target_size": len(T),
           "checked": checked if checked is not None else len(T), "value": None,
           "date": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if not T:
        res.update(status="not_applicable", reason="целевой набор T пуст")
        return res
    if not valid:
        res.update(status="invalid", reason=invalid_reason or "прогон недействителен")
        return res
    mandatory = [c for c, v in TECH_V1.items() if v[3] == "mandatory" or (v[3] == "mandatory_site" and site_mode)]
    missing = []
    for c in mandatory:
        if TECH_V1[c][2] == "site":
            if idx.get((c, None)) in (None, "unknown"):
                missing.append({"check_id": c, "url": None})
        else:
            for u in T:
                if idx.get((c, u)) in (None, "unknown"):
                    missing.append({"check_id": c, "url": u})
    res["coverage"] = {"complete": not missing, "missing": missing}
    if missing:
        res.update(status="incomplete_coverage", reason="обязательная проверка без результата хотя бы на одном URL из T")
        return res
    included_optional = []
    for c, v in TECH_V1.items():
        if v[3] != "optional":
            continue
        sts = [idx.get((c, u)) for u in T]
        if all(s in ("pass", "fail", "not_applicable") for s in sts) and any(s in ("pass", "fail") for s in sts):
            included_optional.append(c)
    penalties, total = [], 0.0
    for c in mandatory + included_optional:
        if TECH_V1[c][2] == "site":
            st = idx.get((c, None))
            if st == "not_applicable":
                continue
            share, aff, den = (1.0 if st == "fail" else 0.0), int(st == "fail"), 1
        else:
            app = [u for u in T if idx.get((c, u)) in ("pass", "fail")]
            aff_l = [u for u in app if idx.get((c, u)) == "fail"]
            if not app:
                continue
            aff, den = len(aff_l), len(app)
            share = aff / den
        pen = share * TECH_V1[c][1]
        total += pen
        penalties.append({"check_id": c, "affected": aff, "denominator": den, "weight": TECH_V1[c][1],
                          "penalty": round(pen, 4)})
    base = max(0.0, 100.0 - total)
    # потолки
    by_reason = {c: [u for u in T if idx.get((c, u)) == "fail"] for c in CRITICAL}
    B = sorted({u for us in by_reason.values() for u in us})
    overlap = [u for u in B if sum(u in us for us in by_reason.values()) > 1]
    ceilings = []
    if set(B) == set(T):
        ceilings.append((0, "B = T: critical-fail на каждом целевом URL"))
    if home_n in B or len(B) / len(T) >= 0.5:
        ceilings.append((50, "главная в B" if home_n in B else f"доля B/T = {len(B)}/{len(T)} ≥ 0,5"))
    for c in HIGH:
        if all(idx.get((c, u)) == "fail" for u in T):
            ceilings.append((70, f"{c}: fail на каждом URL T"))
    ceiling = min(ceilings, key=lambda x: x[0]) if ceilings else None
    value = _round(base)
    if ceiling:
        value = min(value, ceiling[0])
    res.update(status="ok", value=value, raw=round(base, 4), penalties=penalties, included_optional=included_optional,
               ceiling={"value": ceiling[0], "reason": ceiling[1]} if ceiling else None,
               blockers={"B_size": len(B), "T_size": len(T), "B": B,
                         "by_reason": {c: us for c, us in by_reason.items() if us}, "overlap": overlap})
    return res


# ---------------------------------------------------------------- прогон

def _page_record(resp) -> dict:
    parsed = None
    if resp.ok and not resp.error:
        parsed = htmlinfo.parse(resp.text(), resp.final_url)
    cdn = {k: resp.headers[k] for k in CDN_HEADERS if k in resp.headers}
    return {"url": resp.url, "final_url": resp.final_url, "status": resp.status, "error": resp.error,
            "redirects": resp.redirects, "headers": resp.headers, "cdn_hints": cdn, "parsed": parsed}


def _read(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def run(opts, fetcher=None) -> dict:
    fetcher = fetcher or Fetcher(delay=opts.delay, allow_private=opts.allow_private_targets)
    site_mode = bool(opts.site)
    start = opts.site if site_mode else opts.url
    sp = urlsplit(start)
    origin = f"{sp.scheme}://{sp.netloc}"
    host = sp.hostname or ""
    home = origin + "/"
    report = {"schema_version": SCHEMA_VERSION, "rules_version": RULES_VERSION,
              "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "mode": "site" if site_mode else "page", "input": start, "search_agent": opts.search_agent,
              "fetch": not opts.no_fetch, "notes": []}
    # robots
    if opts.robots_file:
        rb = robotslib.Robots(_read(opts.robots_file), "local", None, None, opts.robots_file)
    else:
        r = fetcher.fetch(origin + "/robots.txt", bots.TYPICAL_CLIENT_UA, scope_host=host)
        rb = robotslib.from_response(r.status, r.body, r.error, origin + "/robots.txt")
    report["robots"] = {"source": rb.source, "fetch_status": rb.fetch_status, "http_status": rb.http_status,
                        "error": rb.error, "groups": sorted(rb.groups), "sitemaps": rb.sitemaps}
    # sitemap и выборка
    smap = None
    if site_mode and not opts.no_fetch:
        smap = discover_sitemaps(fetcher, origin, rb, host)
        report["sitemaps"] = {k: v for k, v in smap.items() if k != "urls"} | {"url_count": len(smap["urls"])}
    pages: dict[str, dict] = {}

    def get(u):
        n = htmlinfo.normalize_url(u)
        if n not in pages and not opts.no_fetch and not fetcher.stopped:
            pages[n] = _page_record(fetcher.fetch(u, bots.TYPICAL_CLIENT_UA, scope_host=host))
        return pages.get(n)

    if not site_mode:
        sample = {"budget": 1, "selected": [htmlinfo.normalize_url(start)], "templates": [], "excluded_templates": []}
    elif opts.sample_file:
        lines = [l.strip() for l in _read(opts.sample_file).splitlines() if l.strip() and not l.startswith("#")]
        sample = {"budget": len(lines), "selected": [htmlinfo.normalize_url(u) for u in lines], "templates": [],
                  "excluded_templates": [], "source": opts.sample_file}
    else:
        cands = smap["urls"] if smap else []
        source = "sitemap"
        if not cands and not opts.no_fetch:
            hp = get(home)
            cands = [l for l in (hp["parsed"]["links"] if hp and hp["parsed"] else []) if htmlinfo.is_internal(l, host)]
            source = "навигация главной"
        sample = select_sample(home, cands, opts.limit, opts.per_template)
        sample["candidates_source"] = source
    for u in sample["selected"]:
        get(u)
    fetched = [u for u in sample["selected"] if u in pages]
    sample["checked"] = len(fetched)
    sample["complete"] = opts.no_fetch is False and len(fetched) == len(sample["selected"]) and not fetcher.stopped
    sample["stop_reason"] = fetcher.stopped
    report["sample"] = sample
    # целевой набор T
    excl = {htmlinfo.normalize_url(u): r or "намеренно исключён владельцем" for u, r in opts.exclude}
    T = [u for u in sample["selected"] if u not in excl]
    report["target_set"] = {"T": T, "excluded": [{"url": u, "reason": r} for u, r in excl.items()
                                                  if u in sample["selected"]]}
    # доступ: пары URL × агент
    agents = [bots.by_token(t.strip()) for t in opts.agents.split(",")] if opts.agents else list(bots.BOTS)
    agents = [a for a in agents if a]
    probe_urls = [] if opts.no_fetch or opts.probe == "none" else (
        sample["selected"][:1] if opts.probe == "home" else sample["selected"])
    access, diag = [], []
    for u in sample["selected"]:
        page = pages.get(u)
        target_url = page["final_url"] if page else u
        for a in agents:
            d = rb.decide(a["token"], target_url)
            row = {"url": u, "agent": a["token"], "role": a["role"], "vendor": a["vendor"],
                   "robots_policy": d.policy, "robots_evidence": d.as_dict(), "probe_http_status": None,
                   "probe_error": None, "verified_access": "unknown",
                   "verified_evidence": "нет проверенных логов сервера/WAF: фактический доступ бота не подтверждён"}
            if a.get("needs_verification"):
                row["note"] = "карточка агента требует проверки"
            if u in probe_urls and a["ua"] and not fetcher.stopped:
                pr = fetcher.fetch(target_url, a["ua"], scope_host=host)
                row["probe_http_status"], row["probe_error"] = pr.status, pr.error
                cs = page["status"] if page else None
                if cs is not None and 200 <= cs < 300 and not (pr.status is not None and 200 <= pr.status < 300):
                    diag.append({"type": "ua_probe_mismatch", "url": u, "agent": a["token"], "client_status": cs,
                                 "probe_status": pr.status, "penalty": None,
                                 "note": "требует проверки по логам: подстановка UA не доказывает, как сервер "
                                         "обходится с настоящим ботом"})
            access.append(row)
    report["access"] = access
    # наблюдения
    renders = {htmlinfo.normalize_url(u): _read(p) for u, p in opts.render if p}
    reach = None
    if site_mode and not opts.no_fetch:
        reach = reachability(home, pages, opts.max_depth, host)
    obs = []
    for u in sample["selected"]:
        obs += page_observations(u, pages.get(u), rb, opts, renders.get(u), reach)
    if site_mode:
        if smap is None:
            obs.append({"check_id": "sitemap_discovery", "scope": "site", "url": None, "status": "unknown",
                        "reason": "sitemap не запрашивался (--no-fetch)", "evidence": None, "level": "medium"})
        elif smap["found"]:
            obs.append({"check_id": "sitemap_discovery", "scope": "site", "url": None, "status": "pass",
                        "reason": "sitemap найден", "evidence": [e["url"] for e in smap["entries"]
                                                                 if e.get("result") in ("index", "urlset")],
                        "level": "medium"})
        elif smap["network_or_server_errors"]:
            obs.append({"check_id": "sitemap_discovery", "scope": "site", "url": None, "status": "unknown",
                        "reason": "sitemap не получен из-за сети/429/5xx: отсутствие не подтверждено",
                        "evidence": smap["entries"], "level": "medium"})
        else:
            obs.append({"check_id": "sitemap_discovery", "scope": "site", "url": None, "status": "fail",
                        "reason": "ни один sitemap не найден в robots и /sitemap.xml при успешных запросах",
                        "evidence": smap["entries"], "level": "medium"})
    else:
        obs.append({"check_id": "sitemap_discovery", "scope": "site", "url": None, "status": "not_applicable",
                    "reason": "аудит одной страницы", "evidence": None, "level": "medium"})
    report["observations"] = obs
    report["diagnostics"] = diag
    report["pages"] = [{"url": u, "final_url": p["final_url"], "status": p["status"], "error": p["error"],
                        "redirects": p["redirects"], "cdn_hints": p["cdn_hints"],
                        "title": p["parsed"]["title"] if p["parsed"] else None,
                        "canonical": p["parsed"]["canonical"] if p["parsed"] else None,
                        "x_robots_tag": p["headers"].get("x-robots-tag"),
                        "main_content_chars": len(p["parsed"]["main_text"]) if p["parsed"] else None}
                       for u, p in pages.items()]
    # действительность прогона
    valid, why = True, None
    if not opts.no_fetch and T:
        if not any(pages.get(u) and pages[u]["status"] and 200 <= pages[u]["status"] < 300 for u in T):
            valid, why = False, "типичному клиенту недоступно содержимое всех URL выборки"
    report["run"] = {"valid": valid if not opts.no_fetch else None, "invalid_reason": why,
                     "requests": len(fetcher.requests)}
    if opts.score:
        if opts.no_fetch:
            report["score"] = {"rules_version": RULES_VERSION, "value": None, "status": "incomplete_coverage",
                               "reason": "--no-fetch: страницы не проверены"}
        else:
            report["score"] = compute_score(obs, T, home if site_mode else None, site_mode,
                                            checked=len(sample["selected"]), valid=valid, invalid_reason=why)
    return report


# ---------------------------------------------------------------- вывод

def render_text(rep: dict) -> str:
    L = [f"# Технический аудит {rep['input']} ({rep['mode']}, {rep['rules_version']}, {rep['generated_at']})"]
    sc = rep.get("score")
    if sc:
        if sc.get("value") is None:
            L.append(f"Оценка: нет ({sc.get('status')}: {sc.get('reason')})")
        else:
            b = sc["blockers"]
            L.append(f"Блокировщики: {b['B_size']} из {b['T_size']} целевых URL; по причинам: "
                     + (", ".join(f"{c} {len(u)}" for c, u in b["by_reason"].items()) or "нет")
                     + (f"; пересечения {len(b['overlap'])}" if b["overlap"] else ""))
            cap = f", потолок {sc['ceiling']['value']} ({sc['ceiling']['reason']})" if sc["ceiling"] else ""
            L.append(f"Оценка tech-v1: {sc['value']}/100 (до потолка {sc['raw']}){cap}; проверено {sc['checked']}, T = {sc['target_size']}")
    r = rep["robots"]
    L.append(f"robots.txt: {r['fetch_status']} (HTTP {r['http_status']}); sitemap в robots: {', '.join(r['sitemaps']) or 'нет'}")
    s = rep["sample"]
    L.append(f"Выборка: {len(s['selected'])} URL, проверено {s.get('checked', 0)}, полная: {s.get('complete')}"
             + (f", стоп: {s['stop_reason']}" if s.get("stop_reason") else ""))
    for t in s.get("excluded_templates", []):
        L.append(f"  исключён шаблон {t['template']}: {t['reason']}")
    for e in rep["target_set"]["excluded"]:
        L.append(f"  вне T: {e['url']} — {e['reason']}")
    L.append("\n## Наблюдения (fail/unknown)")
    for o in rep["observations"]:
        if o["status"] in ("fail", "unknown"):
            L.append(f"- [{o['status']}] {o['check_id']} {o['url'] or '(сайт)'}: {o['reason']}")
    if rep["diagnostics"]:
        L.append("\n## Диагностика без баллов")
        for d in rep["diagnostics"]:
            L.append(f"- {d['agent']} {d['url']}: клиент {d['client_status']}, проба {d['probe_status']} — {d['note']}")
    L.append("\n## Доступ агентов (robots / проба / подтверждённый доступ)")
    for a in rep["access"]:
        L.append(f"- {a['url']} {a['agent']} ({a['role']}): {a['robots_policy']} / "
                 f"{a['probe_http_status'] if a['probe_http_status'] is not None else '-'} / {a['verified_access']}")
    return "\n".join(L)


def main(argv=None) -> int:
    opts = parse_args(argv)
    rep = run(opts)
    data = json.dumps(rep, ensure_ascii=False, indent=1)
    if opts.out:
        with open(opts.out, "w", encoding="utf-8") as fh:
            fh.write(data)
    print(data if opts.json else render_text(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
