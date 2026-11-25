#!/usr/bin/env python3
"""Страница в raw HTML: наблюдения и эвристики content/technical без баллов.

Примеры:
  python3 page_audit.py https://example.com/guide
  python3 page_audit.py --file page.html --brand "Acme" --json
  python3 page_audit.py https://example.com/guide --ua "<UA бота>"   # диагностика под конкретный UA

По умолчанию запрос идёт с UA типичного клиента. Ответ на подставленный UA бота —
диагностический запрос, а не доказательство визита бота. Эвристики — находки без
баллов: их влияние на поверхности спорно (см. references/content.md и evidence.md).
"""
from __future__ import annotations

import argparse
import json
import re
import sys

import bots
import htmlinfo
from netfetch import Fetcher

SCHEMA_VERSION = "page_audit/1"
FILLER_START = re.compile(
    r"^(?:в этой (?:статье|главе)|в этом (?:разделе|материале)|давайте|сегодня мы|прежде чем|"
    r"in this (?:article|section|guide|post)|let's|before we|in today's)", re.I)
QUESTION = re.compile(r"\?\s*$")


def analyze(html: str, url: str | None = None, brand: str | None = None, x_robots: str | None = None) -> dict:
    info = htmlinfo.parse(html, url)
    imgs = info["images"]
    missing_alt = [i["src"] for i in imgs if i["alt"] is None]
    empty_alt = [i["src"] for i in imgs if i["alt"] is not None and not i["alt"].strip()]
    with_alt = [i for i in imgs if i["alt"] and i["alt"].strip()]
    obs = {
        "title": info["title"], "title_chars": len(info["title"]), "lang": info["lang"],
        "h1": info["h1"], "headings": [{"level": k, "text": t} for k, t in info["headings"]],
        "meta_description": info["meta"].get("description"), "robots_meta": info["robots_meta"],
        "x_robots_tag": x_robots, "canonical_href": info["canonical_href"], "canonical": info["canonical"],
        "base_href": info["base_href"], "main_element": info["has_main_element"],
        "main_content_chars": len(info["main_text"]), "lede_after_h1": (info["lede_after_h1"] or "")[:300] or None,
        "images": {"total": len(imgs), "with_alt_text": len(with_alt), "decorative_empty_alt": len(empty_alt),
                   "missing_alt_attribute": len(missing_alt), "missing_alt_src": missing_alt[:20]},
        "tables": info["tables"], "jsonld_blocks": info["jsonld_blocks"], "jsonld_types": info["jsonld_types"],
        "jsonld_errors": info["jsonld_errors"], "links": len(info["links"]),
    }
    H = []

    def h(hid, status, reason, evidence=None):
        H.append({"id": hid, "status": status, "reason": reason, "evidence": evidence})

    if not info["title"]:
        h("title", "warn", "нет <title>")
    else:
        h("title", "info", "title есть; самодостаточность проверить вручную", info["title"])
    if len(info["h1"]) == 1:
        h("h1", "pass", "один H1", info["h1"])
    else:
        h("h1", "warn", f"H1 на странице: {len(info['h1'])}", info["h1"])
    lede = info["lede_after_h1"]
    if not info["h1"]:
        h("answer_after_h1", "not_applicable", "нет H1")
    elif not lede:
        h("answer_after_h1", "warn", "после H1 в основном контенте raw HTML нет текстового блока")
    elif FILLER_START.match(lede):
        h("answer_after_h1", "warn", "первый блок после H1 начинается со вступления, а не с ответа", lede[:200])
    else:
        h("answer_after_h1", "info", "первый блок после H1 в основном контенте; соответствие интенту проверить вручную",
          lede[:200])
    if missing_alt:
        h("img_alt", "warn", f"без атрибута alt: {len(missing_alt)} из {len(imgs)}; alt=\"\" у декоративных допустим",
          missing_alt[:10])
    elif imgs:
        h("img_alt", "pass", f"alt есть у всех {len(imgs)}; пустой alt (декоративные): {len(empty_alt)}")
    if info["jsonld_errors"]:
        h("jsonld", "warn", f"{info['jsonld_errors']} блок(ов) JSON-LD не разбираются как JSON")
    elif info["jsonld_types"]:
        h("jsonld", "info", "типы JSON-LD; соответствие видимым фактам проверить по content.md", info["jsonld_types"])
    else:
        h("jsonld", "info", "JSON-LD в raw HTML нет")
    q = [t for k, t in info["headings"] if k in ("h2", "h3") and QUESTION.search(t)]
    h("question_headings", "info", f"заголовков H2/H3 с вопросом: {len(q)}", q[:10])
    if brand:
        hay = " ".join([info["title"], lede or "", " ".join(info["h1"])]).lower()
        if brand.lower() in hay:
            h("brand_named", "pass", f"«{brand}» назван в title/H1/первом блоке")
        else:
            h("brand_named", "warn", f"«{brand}» не назван в title, H1 и первом блоке после H1")
    if not info["main_text"].strip():
        h("main_content_raw", "warn", "основного контента нет в raw HTML; без рендера JS-зависимость не подтверждена")
    return {"observations": obs, "heuristics": H}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Страница в raw HTML: наблюдения и эвристики без баллов")
    ap.add_argument("url", nargs="?")
    ap.add_argument("--file", help="локальный HTML вместо загрузки")
    ap.add_argument("--brand")
    ap.add_argument("--ua", default=bots.TYPICAL_CLIENT_UA, help="User-Agent запроса (по умолчанию типичный клиент)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--allow-private-targets", action="store_true", help=argparse.SUPPRESS)  # только тесты
    a = ap.parse_args(argv)
    source = {"url": a.url, "file": a.file, "ua": a.ua,
              "ua_kind": "typical_client" if a.ua == bots.TYPICAL_CLIENT_UA else "custom_diagnostic"}
    x_robots = None
    if a.file:
        with open(a.file, encoding="utf-8", errors="replace") as fh:
            html = fh.read()
    elif a.url:
        url = a.url if "://" in a.url else "https://" + a.url
        r = Fetcher(delay=1.0, allow_private=a.allow_private_targets).fetch(url, a.ua)
        source.update(url=url, http_status=r.status, final_url=r.final_url, redirects=r.redirects, error=r.error)
        if r.status is None or not r.ok:
            print(json.dumps({"schema_version": SCHEMA_VERSION, "source": source,
                              "error": r.error or f"HTTP {r.status}"}, ensure_ascii=False, indent=1))
            return 1
        html, x_robots = r.text(), r.headers.get("x-robots-tag")
        a.url = r.final_url
    else:
        ap.error("нужен url или --file")
    res = {"schema_version": SCHEMA_VERSION, "source": source} | analyze(html, a.url, a.brand, x_robots)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    o = res["observations"]
    print(f"Источник: {a.url or a.file} | UA: {source['ua_kind']}")
    print(f"Title ({o['title_chars']} симв.): {o['title'] or '—'}")
    print(f"H1: {' | '.join(o['h1']) or '—'}")
    print(f"Первый блок после H1: {o['lede_after_h1'] or '—'}")
    print(f"canonical: {o['canonical'] or '—'} | JSON-LD: {', '.join(o['jsonld_types']) or 'нет'}")
    im = o["images"]
    print(f"Изображения: {im['total']}, без alt: {im['missing_alt_attribute']}, декоративные alt=\"\": {im['decorative_empty_alt']}")
    print("\nЭвристики (без баллов):")
    for x in res["heuristics"]:
        print(f"  [{x['status']}] {x['id']}: {x['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
