#!/usr/bin/env python3
"""Журнал наблюдений AI-видимости (владелец контракта — references/visibility.md).

Формат: JSONL. Первая строка — meta, далее строка на бренд и ход попытки.
Флаги citation, mention, recommend_for, recommend_against независимы: true/false/unknown.
Основания рекомендации: список направление / условие / выдержка / позиция (целое ≥ 1 или пусто).

Примеры:
  python3 visibility_tracker.py init --path journal.jsonl --brand Acme
  python3 visibility_tracker.py add --path journal.jsonl --brand Acme --surface chatgpt --mode search \\
      --scenario-id crm --scenario-version 1 --turn 1 --prompt-id p1 --prompt-version 1 --prompt-text "..." \\
      --completed true --citation true --mention false --recommend-for false --recommend-against false
  python3 visibility_tracker.py report --path journal.jsonl --period-a 2026-10-01:2026-10-31 --period-b 2026-11-01:2026-11-30
  python3 visibility_tracker.py import --path journal.jsonl --source old.csv          # карантин, provenance=unverified

Исходные файлы импорта не изменяются. Повторный импорт не создаёт дублей
(ключ — абсолютный путь файла и идентификатор строки).
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone

SCHEMA_VERSION = "visibility-journal/1"
FLAGS = ("citation", "mention", "recommend_for", "recommend_against")
TRI = {"true": "true", "y": "true", "yes": "true", "1": "true", "да": "true", "д": "true",
       "false": "false", "n": "false", "no": "false", "0": "false", "нет": "false", "н": "false",
       "unknown": "unknown", "": "unknown", "?": "unknown"}
SEGMENT = ("brand", "surface", "mode", "language", "geo", "cohort", "stage")
KEY = ("scenario_id", "scenario_version", "turn", "branch", "prompt_id", "prompt_version", "classification_version")
FIELDS = ("record_id", "run_id", "session_id", "brand", "scenario_id", "scenario_version", "turn", "branch",
          "prompt_id", "prompt_version", "prompt_text", "cohort", "stage", "language", "geo", "surface", "mode",
          "time", "completed", "history_ref", "answer_ref", "shortlisted", "attitude", "classification_version",
          *FLAGS, "bases", "provenance", "source_ref", "legacy")


def tri(v) -> str:
    s = str(v if v is not None else "").strip().lower()
    if s not in TRI:
        raise ValueError(f"значение {v!r}: ожидается true/false/unknown")
    return TRI[s]


def parse_basis(s: str) -> dict:
    parts = s.split("|")
    if len(parts) != 4:
        raise ValueError("основание: 'for|условие|выдержка|позиция' или 'against|…' (позиция — целое ≥ 1 или пусто)")
    d, cond, exc, pos = (p.strip() for p in parts)
    if d not in ("for", "against"):
        raise ValueError("направление основания: for или against")
    if pos:
        if not pos.isdigit() or int(pos) < 1:
            raise ValueError(f"позиция {pos!r}: целое ≥ 1 или пусто")
        pos_v = int(pos)
    else:
        pos_v = None
    return {"direction": d, "condition": cond, "excerpt": exc, "position": pos_v}


# ------------------------------------------------------------------ файл журнала

def load(path: str) -> tuple[dict, list[dict]]:
    if not os.path.exists(path):
        sys.exit(f"{path} не найден. Сначала: visibility_tracker.py init --path {path} --brand …")
    meta, rows = {}, []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("record_type") == "meta":
                meta = rec
            else:
                rows.append(rec)
    return meta, rows


def append(path: str, recs: list[dict]) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def new_record(**kw) -> dict:
    r = {f: None for f in FIELDS}
    r.update(record_type="observation", record_id=uuid.uuid4().hex, bases=[], legacy=None, source_ref=None)
    for f in FLAGS:
        r[f] = "unknown"
    r["shortlisted"] = "unknown"
    r["completed"] = "unknown"
    r.update(kw)
    return r


# ------------------------------------------------------------------ команды

def cmd_init(a) -> int:
    if os.path.exists(a.path):
        sys.exit(f"{a.path} уже существует")
    append(a.path, [{"record_type": "meta", "schema_version": SCHEMA_VERSION, "brand": a.brand,
                     "created": datetime.now(timezone.utc).isoformat(timespec="seconds")}])
    print(f"Создан журнал {a.path}")
    return 0


def cmd_add(a) -> int:
    load(a.path)
    try:
        flags = {f: tri(getattr(a, f)) for f in FLAGS}
        bases = [parse_basis(b) for b in a.basis]
        completed = tri(a.completed)
        shortlisted = tri(a.shortlisted)
    except ValueError as e:
        sys.exit(str(e))
    for f, d in (("recommend_for", "for"), ("recommend_against", "against")):
        if flags[f] == "true" and not any(b["direction"] == d for b in bases):
            sys.exit(f"{f}=true требует основание --basis '{d}|условие|выдержка|позиция'")
        if flags[f] == "false" and any(b["direction"] == d for b in bases):
            sys.exit(f"{f}=false противоречит основанию направления {d}")
    rec = new_record(
        run_id=a.run_id, session_id=a.session_id, brand=a.brand, scenario_id=a.scenario_id,
        scenario_version=a.scenario_version, turn=a.turn, branch=a.branch, prompt_id=a.prompt_id,
        prompt_version=a.prompt_version, prompt_text=a.prompt_text, cohort=a.cohort, stage=a.stage,
        language=a.language, geo=a.geo, surface=a.surface, mode=a.mode,
        time=a.time or datetime.now(timezone.utc).isoformat(timespec="seconds"), completed=completed,
        history_ref=a.history_ref, answer_ref=a.answer_ref, shortlisted=shortlisted, attitude=a.attitude,
        classification_version=a.classification_version, bases=bases, provenance=a.provenance, **flags)
    append(a.path, [rec])
    print(f"Записано: {rec['record_id']}")
    return 0


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_legacy(src: str, fmt: str) -> tuple[str, list[tuple[str, dict]]]:
    if fmt == "auto":
        fmt = "csv" if src.lower().endswith(".csv") else "citation-json"
    if fmt == "csv":
        with open(src, encoding="utf-8", newline="") as fh:
            return fmt, [(f"csv:{i}", dict(r)) for i, r in enumerate(csv.DictReader(fh), 1)]
    with open(src, encoding="utf-8") as fh:
        data = json.load(fh)
    items = data.get("citations", []) if isinstance(data, dict) else data
    return fmt, [(f"json:{i}:{(e or {}).get('id', '')}", e) for i, e in enumerate(items, 1)]


def import_rows(path: str, src: str, fmt: str = "auto") -> dict:
    _, rows = load(path)
    abs_src = os.path.abspath(src)
    digest = _sha256(abs_src)
    fmt, items = read_legacy(abs_src, fmt)
    have = {(r["source_ref"]["file"], r["source_ref"]["row_id"]) for r in rows if r.get("source_ref")}
    new, dup = [], 0
    legacy_dist = collections.Counter()
    for row_id, e in items:
        if (abs_src, row_id) in have:
            dup += 1
            continue
        if fmt == "csv":
            base = dict(brand=e.get("brand"), surface=(e.get("engine") or None), stage=e.get("stage") or None,
                        prompt_text=e.get("prompt"), time=e.get("date"))
            legacy_dist[f"mention={e.get('mention', '')},cited={e.get('cited', '')},recommended={e.get('recommended', '')}"] += 1
        else:
            base = dict(brand=e.get("brand"), surface=e.get("llm"), prompt_text=e.get("query"), time=e.get("date"))
            legacy_dist[f"status={e.get('status', '')}"] += 1
        new.append(new_record(provenance="unverified", legacy=e, completed="unknown",
                              source_ref={"file": abs_src, "row_id": row_id, "format": fmt, "sha256": digest}, **base))
    append(path, new)
    return {"source": abs_src, "format": fmt, "input_rows": len(items), "imported": len(new),
            "duplicates_skipped": dup, "provenance": {"unverified": len(new)},
            "legacy_distribution": dict(legacy_dist),
            "note": "все строки в карантине: флаги unknown до проверки по ответам или подтверждения владельца"}


def cmd_import(a) -> int:
    res = import_rows(a.path, a.source, a.format)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


# ------------------------------------------------------------------ отчёт

def shares(rows: list[dict]) -> dict:
    out = {}
    for f in FLAGS:
        known = [r for r in rows if r[f] in ("true", "false")]
        t = sum(r[f] == "true" for r in known)
        out[f] = {"true": t, "denominator": len(known), "share": (t / len(known)) if known else None,
                  "excluded_unknown": len(rows) - len(known)}
    both_known = [r for r in rows if r["citation"] in ("true", "false") and r["mention"] in ("true", "false")]
    cat = collections.Counter()
    for r in both_known:
        c, m = r["citation"] == "true", r["mention"] == "true"
        cat["both" if c and m else "ghost" if c else "mention_only" if m else "neither"] += 1
    den = cat["both"] + cat["ghost"]
    out["outcomes"] = {k: cat[k] for k in ("both", "ghost", "mention_only", "neither")}
    out["outcomes"]["denominator"] = len(both_known)
    out["ghost"] = {"ghost": cat["ghost"], "denominator": den, "share": (cat["ghost"] / den) if den else None}
    return out


def _key_share(rows: list[dict], metric: str) -> tuple[int, int]:
    if metric == "ghost":
        rs = [r for r in rows if r["citation"] == "true" and r["mention"] in ("true", "false")]
        return sum(r["mention"] == "false" for r in rs), len(rs)
    rs = [r for r in rows if r[metric] in ("true", "false")]
    return sum(r[metric] == "true" for r in rs), len(rs)


def _in(r: dict, period: tuple[str, str] | None) -> bool:
    if not period:
        return True
    d = (r.get("time") or "")[:10]
    return period[0] <= d <= period[1]


def dynamics(rows_a: list[dict], rows_b: list[dict]) -> list[dict]:
    """Равный вес каждого общего ключа сравнения внутри неизменного сегмента."""
    def group(rows):
        g = collections.defaultdict(list)
        for r in rows:
            g[(tuple(r.get(s) for s in SEGMENT), tuple(r.get(k) for k in KEY))].append(r)
        return g
    ga, gb = group(rows_a), group(rows_b)
    segs = sorted({k[0] for k in ga} | {k[0] for k in gb}, key=str)
    out = []
    for seg in segs:
        for metric in (*FLAGS, "ghost"):
            sa, sb, common, excluded = [], [], [], []
            keys = sorted({k[1] for k in ga if k[0] == seg} | {k[1] for k in gb if k[0] == seg}, key=str)
            ra = rb = 0
            for key in keys:
                na, da = _key_share(ga.get((seg, key), []), metric)
                nb, db = _key_share(gb.get((seg, key), []), metric)
                if da and db:
                    sa.append(na / da)
                    sb.append(nb / db)
                    common.append(dict(zip(KEY, key)))
                    ra += da
                    rb += db
                else:
                    excluded.append({"key": dict(zip(KEY, key)), "denominator_a": da, "denominator_b": db,
                                     "reason": "нет валидных повторов в одном из периодов (новый/изменённый ключ — новая базовая линия)"})
            row = {"segment": dict(zip(SEGMENT, seg)), "metric": metric, "common_keys": len(common),
                   "valid_repeats_a": ra, "valid_repeats_b": rb, "excluded_keys": excluded}
            if common:
                a_mean, b_mean = sum(sa) / len(sa), sum(sb) / len(sb)
                row.update(share_a=a_mean, share_b=b_mean, delta_pp=round(100 * (b_mean - a_mean), 2))
            else:
                row.update(share_a=None, share_b=None, delta_pp=None, note="общих ключей нет: только срезы, без вывода о динамике")
            out.append(row)
    return out


def _period(s: str | None):
    if not s:
        return None
    a, sep, b = s.partition(":")
    if not sep:
        raise SystemExit("период: ГГГГ-ММ-ДД:ГГГГ-ММ-ДД")
    return a, b


def build_report(rows: list[dict], period_a=None, period_b=None, since=None, until=None) -> dict:
    sel = [r for r in rows if (not since or (r.get("time") or "")[:10] >= since)
           and (not until or (r.get("time") or "")[:10] <= until)]
    prov = collections.Counter(r.get("provenance") or "unknown" for r in sel)
    valid = [r for r in sel if r.get("provenance") == "observed" and r.get("completed") == "true"]
    excl = {"not_observed": sum(1 for r in sel if r.get("provenance") != "observed"),
            "not_completed": sum(1 for r in sel if r.get("provenance") == "observed" and r.get("completed") != "true")}
    segs = collections.defaultdict(list)
    for r in valid:
        segs[tuple(r.get(s) for s in SEGMENT)].append(r)
    by_prompt = collections.defaultdict(list)
    for r in valid:
        by_prompt[(tuple(r.get(s) for s in SEGMENT), tuple(r.get(k) for k in KEY))].append(r)
    per_prompt = {}
    for f in (*FLAGS, "ghost"):
        vals = [n / d for n, d in (_key_share(rs, f) for rs in by_prompt.values()) if d]
        per_prompt[f] = {"keys": len(vals), "mean_share": (sum(vals) / len(vals)) if vals else None}
    rep = {"schema_version": SCHEMA_VERSION, "rows_total": len(sel), "provenance": dict(prov),
           "rows_in_metrics": len(valid), "excluded": excl, "by_response": shares(valid),
           "by_prompt_equal_weight": per_prompt,
           "segments": [{"segment": dict(zip(SEGMENT, k)), **shares(v)} for k, v in segs.items()]}
    if period_a and period_b:
        rep["dynamics"] = {"period_a": period_a, "period_b": period_b,
                           "results": dynamics([r for r in valid if _in(r, period_a)],
                                               [r for r in valid if _in(r, period_b)])}
    return rep


def _pct(x):
    return "—" if x is None else f"{100 * x:.0f}%"


def cmd_report(a) -> int:
    _, rows = load(a.path)
    rep = build_report(rows, _period(a.period_a), _period(a.period_b), a.since, a.until)
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        return 0
    print(f"Строк: {rep['rows_total']}; в метриках: {rep['rows_in_metrics']}; происхождение: {rep['provenance']}; "
          f"исключено: {rep['excluded']}")
    s = rep["by_response"]
    for f in FLAGS:
        print(f"  {f:<18}{_pct(s[f]['share']):>6}  ({s[f]['true']}/{s[f]['denominator']}, unknown {s[f]['excluded_unknown']})")
    g = s["ghost"]
    print(f"  ghost / (both + ghost): {_pct(g['share'])} ({g['ghost']}/{g['denominator']}); исходы: {s['outcomes']}")
    for d in rep.get("dynamics", {}).get("results", []):
        if d["common_keys"]:
            print(f"  динамика {d['metric']} {d['segment']}: {_pct(d['share_a'])} → {_pct(d['share_b'])} "
                  f"({d['delta_pp']:+} п.п., общих ключей {d['common_keys']}, исключено {len(d['excluded_keys'])})")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Журнал наблюдений AI-видимости")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("--path", required=True)
    p.add_argument("--brand", required=True)
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("add")
    p.add_argument("--path", required=True)
    for f in ("brand", "surface", "scenario-id", "prompt-id", "prompt-text"):
        p.add_argument("--" + f, required=True)
    p.add_argument("--scenario-version", required=True)
    p.add_argument("--prompt-version", required=True)
    p.add_argument("--turn", type=int, default=1)
    p.add_argument("--completed", required=True, help="true/false: ответ получен целиком")
    for f in ("run-id", "session-id", "branch", "cohort", "stage", "language", "geo", "mode", "time",
              "history-ref", "answer-ref", "attitude"):
        p.add_argument("--" + f)
    p.add_argument("--classification-version", default="1")
    p.add_argument("--shortlisted", default="unknown")
    for f in FLAGS:
        p.add_argument("--" + f.replace("_", "-"), dest=f, default="unknown")
    p.add_argument("--basis", action="append", default=[], help="направление|условие|выдержка|позиция")
    p.add_argument("--provenance", choices=["observed", "demo"], default="observed")
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("report")
    p.add_argument("--path", required=True)
    p.add_argument("--since")
    p.add_argument("--until")
    p.add_argument("--period-a", help="ГГГГ-ММ-ДД:ГГГГ-ММ-ДД")
    p.add_argument("--period-b", help="ГГГГ-ММ-ДД:ГГГГ-ММ-ДД")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_report)
    p = sub.add_parser("import")
    p.add_argument("--path", required=True)
    p.add_argument("--source", required=True, help="старый CSV visibility_tracker или JSON citation_tracker")
    p.add_argument("--format", choices=["auto", "csv", "citation-json"], default="auto")
    p.set_defaults(fn=cmd_import)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
