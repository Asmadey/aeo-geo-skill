import contextlib
import csv
import hashlib
import io
import json
import os
import tempfile
import unittest

import helpers  # noqa: F401
import visibility_tracker as vt


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run(argv):
    with contextlib.redirect_stdout(io.StringIO()) as buf, contextlib.redirect_stderr(io.StringIO()):
        code = vt.main(argv)
    return code, buf.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.j = os.path.join(self.dir, "journal.jsonl")
        run(["init", "--path", self.j, "--brand", "Acme"])

    def rows(self):
        return vt.load(self.j)[1]


class Import(Base):
    def test_old_csv_quarantined_and_idempotent(self):
        src = os.path.join(self.dir, "aeo-visibility.csv")
        fields = ["date", "brand", "engine", "stage", "prompt", "mention", "cited", "position", "recommended",
                  "sentiment", "accurate", "rivals", "sources", "note"]
        with open(src, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fields)
            w.writeheader()
            w.writerow({"date": "2026-10-01", "brand": "Acme", "engine": "chatgpt", "prompt": "лучшие CRM",
                        "mention": "y", "cited": "n", "position": "3", "recommended": "y"})
            w.writerow({"date": "2026-10-02", "brand": "Acme", "engine": "perplexity", "prompt": "CRM для банка",
                        "mention": "n", "cited": "y", "position": "", "recommended": ""})
        before = sha(src)
        r1 = vt.import_rows(self.j, src)
        r2 = vt.import_rows(self.j, src)
        self.assertEqual(sha(src), before)
        self.assertEqual((r1["input_rows"], r1["imported"]), (2, 2))
        self.assertEqual((r2["imported"], r2["duplicates_skipped"]), (0, 2))
        rows = self.rows()
        self.assertEqual(len(rows), 2)
        for r in rows:
            self.assertEqual(r["provenance"], "unverified")
            self.assertEqual({f: r[f] for f in vt.FLAGS}, {f: "unknown" for f in vt.FLAGS})
        self.assertEqual(rows[0]["legacy"]["recommended"], "y")
        self.assertEqual(rows[0]["legacy"]["position"], "3")

    def test_citation_tracker_json_all_unverified(self):
        src = os.path.join(self.dir, "citations.json")
        data = {"schema_version": 2, "citations": [
            {"id": "1", "url": "https://acme.com/a", "llm": "chatgpt", "query": "q1", "status": "both", "brand": "Acme",
             "date": "2026-10-01", "notes": "явный both", "position": ""},
            {"id": "2", "url": "https://acme.com/a", "llm": "claude", "query": "q2", "status": "both", "brand": "Acme",
             "date": "2026-10-02", "notes": "", "position": ""},
            {"id": "3", "url": "https://example.com/blog/aeo-guide", "llm": "perplexity",
             "query": "what is answer engine optimization", "status": "both", "brand": "Acme", "date": "2026-10-03",
             "notes": "", "position": ""},
            {"id": "4", "url": "https://acme.com/b", "llm": "chatgpt", "query": "q4", "status": "ghost", "brand": "Acme",
             "date": "2026-10-04", "notes": "реальный ответ, ссылка #2", "position": "2"},
        ]}
        with open(src, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        before = sha(src)
        res = vt.import_rows(self.j, src)
        self.assertEqual(sha(src), before)
        self.assertEqual(res["legacy_distribution"], {"status=both": 3, "status=ghost": 1})
        self.assertEqual(vt.import_rows(self.j, src)["imported"], 0)
        for r in self.rows():
            self.assertEqual(r["provenance"], "unverified")
            self.assertTrue(all(r[f] == "unknown" for f in vt.FLAGS))
        rep = vt.build_report(self.rows())
        self.assertEqual(rep["rows_in_metrics"], 0)
        self.assertEqual(rep["provenance"], {"unverified": 4})
        self.assertIsNone(rep["by_response"]["ghost"]["share"])


def rec(prompt_id, rec_for, day, **kw):
    return vt.new_record(brand="Acme", surface="chatgpt", mode="search", scenario_id="s-" + prompt_id,
                         scenario_version="1", turn=1, prompt_id=prompt_id, prompt_version="1",
                         classification_version="1", completed="true", provenance="observed",
                         time=f"{day}T10:00:00+00:00", recommend_for=rec_for, citation="false", mention="true", **kw)


class Report(Base):
    def test_dynamics_equal_weight_per_key(self):
        rows = ([rec("A", "true", "2026-10-05") for _ in range(3)] + [rec("B", "false", "2026-10-06") for _ in range(9)]
                + [rec("A", "true", "2026-11-05") for _ in range(9)] + [rec("B", "false", "2026-11-06") for _ in range(3)])
        vt.append(self.j, rows)
        rep = vt.build_report(self.rows(), ("2026-10-01", "2026-10-31"), ("2026-11-01", "2026-11-30"))
        d = next(x for x in rep["dynamics"]["results"] if x["metric"] == "recommend_for")
        self.assertEqual(d["common_keys"], 2)
        self.assertAlmostEqual(d["share_a"], 0.5)
        self.assertAlmostEqual(d["share_b"], 0.5)
        self.assertEqual(d["delta_pp"], 0)
        self.assertEqual((d["valid_repeats_a"], d["valid_repeats_b"]), (12, 12))

    def test_ghost_share_and_denominators(self):
        rows = [rec("A", "false", "2026-10-01", ) for _ in range(1)]
        rows[0].update(citation="true", mention="true")
        g = rec("B", "false", "2026-10-01")
        g.update(citation="true", mention="false")
        m = rec("C", "unknown", "2026-10-01")
        m.update(citation="unknown")
        vt.append(self.j, rows + [g, m])
        s = vt.build_report(self.rows())["by_response"]
        self.assertEqual((s["ghost"]["ghost"], s["ghost"]["denominator"]), (1, 2))
        self.assertEqual(s["recommend_for"]["denominator"], 2)
        self.assertEqual(s["recommend_for"]["excluded_unknown"], 1)

    def test_two_directions_both_true_one_row(self):
        code, _ = run(["add", "--path", self.j, "--brand", "Acme", "--surface", "chatgpt", "--scenario-id", "s",
                       "--scenario-version", "1", "--prompt-id", "p", "--prompt-version", "1", "--prompt-text", "CRM?",
                       "--completed", "true", "--citation", "false", "--mention", "true",
                       "--recommend-for", "true", "--recommend-against", "true",
                       "--basis", "for|для команды|Для команды выбирайте Acme|",
                       "--basis", "against|для банка|для банка избегайте Acme: нет SSO|"])
        self.assertEqual(code, 0)
        s = vt.build_report(self.rows())["by_response"]
        self.assertEqual((s["recommend_for"]["true"], s["recommend_for"]["denominator"]), (1, 1))
        self.assertEqual((s["recommend_against"]["true"], s["recommend_against"]["denominator"]), (1, 1))
        self.assertEqual(len(self.rows()[0]["bases"]), 2)

    def test_position_must_be_integer_or_empty(self):
        base = ["add", "--path", self.j, "--brand", "Acme", "--surface", "chatgpt", "--scenario-id", "s",
                "--scenario-version", "1", "--prompt-id", "p", "--prompt-version", "1", "--prompt-text", "q",
                "--completed", "true", "--recommend-for", "true"]
        with self.assertRaises(SystemExit):
            run(base + ["--basis", "for|x|y|первый"])
        with self.assertRaises(SystemExit):
            run(base)  # true без основания
        self.assertEqual(run(base + ["--basis", "for|x|y|2"])[0], 0)
        self.assertEqual(self.rows()[0]["bases"][0]["position"], 2)

    def test_path_required(self):
        with self.assertRaises(SystemExit):
            run(["init", "--brand", "Acme"])


if __name__ == "__main__":
    unittest.main()
