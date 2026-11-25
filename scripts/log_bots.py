#!/usr/bin/env python3
"""Агенты и AI-рефералы в предоставленных логах (combined / common log format).

Примеры:
  python3 log_bots.py access.log access.log.1.gz --top 20 --json
  zcat access.log.*.gz | python3 log_bots.py -
  python3 log_bots.py access.log --verify-dns     # обратный + прямой DNS для агентов с известными суффиксами

«UA-совпадение» — только строка User-agent; её легко подделать. «Подтверждённая
идентичность» по умолчанию unknown. С --verify-dns проверяется reverse DNS и прямое
подтверждение для агентов, у которых в реестре bots.py заданы суффиксы.
Рефералы классифицируются по разобранному хосту Referer; запросы самих агентов
(например ChatGPT-User) переходами пользователей не считаются.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import socket
import sys
from urllib.parse import urlsplit

import bots

SCHEMA_VERSION = "log_bots/1"
LINE = re.compile(r'^(?P<ip>\S+) \S+ \S+ \[[^\]]*\] "(?P<m>[A-Z]+) (?P<path>\S+)[^"]*" (?P<st>\d{3}) (?P<size>\S+)'
                  r'(?: "(?P<ref>[^"]*)" "(?P<ua>[^"]*)")?')
ASSET = re.compile(r"\.(?:css|js|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|map)(?:\?|$)", re.I)


def verify_ip(ip: str, suffixes: list[str], resolver=None) -> tuple[str, str]:
    """confirmed | failed | unknown, с пояснением. resolver подменяется в тестах."""
    if not suffixes:
        return "unknown", "для агента в реестре нет метода проверки"
    rev = resolver.reverse if resolver else (lambda x: socket.gethostbyaddr(x)[0])
    fwd = resolver.forward if resolver else (lambda h: {i[4][0] for i in socket.getaddrinfo(h, None)})
    try:
        name = rev(ip).rstrip(".").lower()
    except OSError as e:
        return "unknown", f"reverse DNS не получен: {e}"
    if not any(name == s or name.endswith("." + s) for s in suffixes):
        return "failed", f"reverse DNS {name} вне {', '.join(suffixes)}"
    try:
        ips = fwd(name)
    except OSError as e:
        return "unknown", f"прямой DNS для {name} не получен: {e}"
    return ("confirmed", f"{ip} → {name} → {ip}") if ip in ips else ("failed", f"{name} не разрешается обратно в {ip}")


def _open(name: str):
    if name == "-":
        return sys.stdin
    if name.endswith(".gz"):
        return gzip.open(name, "rt", encoding="utf-8", errors="replace")
    return open(name, encoding="utf-8", errors="replace")


def analyze(lines, top: int = 10, verify_dns: bool = False, resolver=None) -> dict:
    total = parsed = 0
    hits = collections.Counter()
    status = collections.defaultdict(collections.Counter)
    paths = collections.defaultdict(collections.Counter)
    ident = collections.defaultdict(collections.Counter)
    ident_notes = collections.defaultdict(list)
    ip_cache: dict[tuple, tuple] = {}
    refs = collections.Counter()
    ref_paths = collections.Counter()
    for line in lines:
        total += 1
        m = LINE.search(line)
        if not m:
            continue
        parsed += 1
        ua, ref, path, ip = m.group("ua") or "", m.group("ref") or "", m.group("path"), m.group("ip")
        bot = bots.match_ua(ua)
        if bot:
            t = bot["token"]
            hits[t] += 1
            status[t][m.group("st")] += 1
            if not ASSET.search(path):
                paths[t][path] += 1
            if verify_dns:
                key = (ip, t)
                if key not in ip_cache:
                    ip_cache[key] = verify_ip(ip, bot.get("rdns", []), resolver)
                res, note = ip_cache[key]
            else:
                res, note = "unknown", "проверка не выполнялась (нужен --verify-dns)"
            ident[t][res] += 1
            if note not in ident_notes[t] and len(ident_notes[t]) < 5:
                ident_notes[t].append(note)
            continue  # запрос агента не считается переходом пользователя
        if ref and ref != "-":
            host = urlsplit(ref).hostname or ""
            dom = bots.ai_referrer(host)
            if dom:
                refs[dom] += 1
                ref_paths[path] += 1
    out_bots = []
    for t, n in hits.most_common():
        b = bots.by_token(t)
        errs = sum(c for s, c in status[t].items() if s[0] in "45")
        out_bots.append({"bot": t, "role": b["role"], "vendor": b["vendor"],
                         "ua_match_hits": n, "verified_identity": dict(ident[t]), "identity_notes": ident_notes[t],
                         "status": dict(status[t]), "error_share": round(errs / n, 3),
                         "top_paths": paths[t].most_common(top),
                         **({"note": "карточка агента требует проверки"} if b.get("needs_verification") else {})})
    findings = []
    for b in out_bots:
        if b["status"].get("403") or b["status"].get("429"):
            findings.append(f"{b['bot']}: есть ответы 403/429 при UA-совпадении — сверить правила WAF и подлинность запросов")
    return {"schema_version": SCHEMA_VERSION, "lines": total, "parsed": parsed, "bots": out_bots,
            "ai_referrals": dict(refs.most_common()), "ai_referral_pages": ref_paths.most_common(top),
            "identity_method": "reverse+forward DNS" if verify_dns else "не выполнялась",
            "findings": findings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Агенты и AI-рефералы в логах сервера")
    ap.add_argument("files", nargs="+", help="файлы логов (.gz поддерживается) или - для stdin")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verify-dns", action="store_true", help="проверить идентичность обратным и прямым DNS")
    a = ap.parse_args(argv)

    def lines():
        for name in a.files:
            fh = _open(name)
            try:
                yield from fh
            finally:
                if fh is not sys.stdin:
                    fh.close()

    res = analyze(lines(), a.top, a.verify_dns)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    print(f"Строк: {res['lines']}, разобрано: {res['parsed']}; проверка идентичности: {res['identity_method']}")
    print(f"\n{'Агент':<20}{'UA-совп.':<10}{'подтверждено':<14}{'ошибок':<8}роль")
    for b in res["bots"]:
        conf = b["verified_identity"].get("confirmed", 0)
        print(f"{b['bot']:<20}{b['ua_match_hits']:<10}{conf:<14}{b['error_share']:<8}{b['role']}")
    if res["ai_referrals"]:
        print("\nAI-рефералы (по хосту Referer):")
        for k, n in res["ai_referrals"].items():
            print(f"  {n:>6}  {k}")
    if res["findings"]:
        print("\nНаходки:")
        for f in res["findings"]:
            print(f"  - {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
