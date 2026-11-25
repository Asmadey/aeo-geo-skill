import contextlib
import io
import json
import os
import tempfile
import unittest

from helpers import LocalServer, page
import bots
import page_audit

HTML = page(
    "<header><nav><a href='/'>Главная</a> › <a href='/blog/'>Блог</a></nav></header>"
    "<main><h1>Как выбрать CRM</h1><p>Acme CRM подходит командам до 50 человек.</p>"
    "<h2>Сколько стоит?</h2><p>Цена зависит от тарифа.</p>"
    "<img src='/hero.png' alt='Экран отчёта Acme'><img src='/divider.svg' alt=''><img src='/x.jpg'></main>"
    "<script type='application/ld+json'>{\"@type\": \"Article\", \"author\": {\"@type\": \"Person\"}}</script>",
    title="Как выбрать CRM — Acme")


def run(argv):
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        code = page_audit.main(argv)
    return code, buf.getvalue()


class PageAudit(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".html")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(HTML)

    def test_observations_and_heuristics_without_scores(self):
        code, out = run(["--file", self.path, "--brand", "Acme", "--json"])
        res = json.loads(out)
        self.assertEqual(res["schema_version"], "page_audit/1")
        o = res["observations"]
        self.assertEqual(o["h1"], ["Как выбрать CRM"])
        self.assertTrue(o["lede_after_h1"].startswith("Acme CRM"))
        self.assertEqual(o["images"], {"total": 3, "with_alt_text": 1, "decorative_empty_alt": 1,
                                       "missing_alt_attribute": 1, "missing_alt_src": ["/x.jpg"]})
        self.assertEqual(o["jsonld_types"], ["Article", "Person"])
        h = {x["id"]: x for x in res["heuristics"]}
        self.assertEqual(h["img_alt"]["status"], "warn")
        self.assertIn("1 из 3", h["img_alt"]["reason"])
        self.assertEqual(h["brand_named"]["status"], "pass")
        self.assertNotIn("score", out)
        self.assertNotIn("bytes", o)
        for x in res["heuristics"]:
            self.assertNotIn("40", x["reason"])
            self.assertNotIn("МБ", x["reason"])

    def test_decorative_empty_alt_accepted(self):
        res = page_audit.analyze(page("<main><h1>X</h1><p>Y</p><img src='a' alt=''></main>"))
        h = {x["id"]: x for x in res["heuristics"]}
        self.assertEqual(h["img_alt"]["status"], "pass")

    def test_breadcrumbs_before_lede_are_not_noise(self):
        res = page_audit.analyze(HTML)
        h = {x["id"]: x for x in res["heuristics"]}
        self.assertEqual(h["answer_after_h1"]["status"], "info")

    def test_default_ua_is_typical_client(self):
        seen = []

        def handler(ua):
            seen.append(ua)
            return (200, {}, HTML)
        with LocalServer({"/p": handler}) as srv:
            code, out = run([srv.base + "/p", "--json", "--allow-private-targets"])
        self.assertEqual(code, 0)
        self.assertEqual(seen, [bots.TYPICAL_CLIENT_UA])
        self.assertEqual(json.loads(out)["source"]["ua_kind"], "typical_client")

    def test_loopback_refused_without_flag(self):
        code, out = run(["http://127.0.0.1:9/p", "--json"])
        self.assertEqual(code, 1)
        self.assertIn("не публичный", json.loads(out)["error"])


if __name__ == "__main__":
    unittest.main()
