import gzip
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr

from helpers import BASE, LocalServer, StubFetcher, page
import site_audit
from netfetch import Fetcher

ALLOW_ALL = (200, {"content-type": "text/plain"}, "User-agent: *\nDisallow:\n")
EVAL1 = "User-agent: GPTBot\nUser-agent: ClaudeBot\nDisallow: /\n\nUser-agent: *\nDisallow: /private/\n"


def good(path, links=()):
    a = "".join(f"<a href='{l}'>{l}</a>" for l in links)
    return (200, {}, page(f"<nav>{a}</nav><main><h1>H {path}</h1><p>Ответ на вопрос страницы {path}.</p></main>",
                          head=f"<link rel='canonical' href='{path}'>"))


def urlset(paths, base=BASE):
    locs = "".join(f"<url><loc>{base}{p}</loc></url>" for p in paths)
    return f"<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>{locs}</urlset>"


def tmpfile(text, suffix=".txt"):
    fd, p = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def args(*a):
    return site_audit.parse_args(list(a) + ["--allow-private-targets"])


def obs(rep, check, url=None):
    for o in rep["observations"]:
        if o["check_id"] == check and (url is None or o["url"] == url):
            return o
    raise KeyError((check, url))


def row(rep, agent, url=None):
    return next(r for r in rep["access"] if r["agent"] == agent and (url is None or r["url"] == url))


class CheckAccessTransition(unittest.TestCase):
    """Четыре фикстуры перехода с check_access.py."""

    def test_local_robots_empty_disallow_no_fetch_makes_no_requests(self):
        rf = tmpfile("User-agent: *\nDisallow:\n")
        f = StubFetcher({})
        rep = site_audit.run(args(BASE + "/pricing", "--robots-file", rf, "--no-fetch"), f)
        self.assertEqual(f.requests, [])
        self.assertEqual(rep["schema_version"], "site_audit/1")
        for r in rep["access"]:
            self.assertEqual(r["robots_policy"], "allow")
            self.assertIsNone(r["probe_http_status"])
            self.assertEqual(r["verified_access"], "unknown")

    def test_eval1_groups_per_url_and_agent(self):
        rf = tmpfile(EVAL1)
        for path, exp in (("/private/doc", {"GPTBot": "block", "ClaudeBot": "block", "OAI-SearchBot": "block",
                                            "Googlebot": "block"}),
                          ("/blog/a", {"GPTBot": "block", "ClaudeBot": "block", "OAI-SearchBot": "allow",
                                       "Googlebot": "allow"})):
            rep = site_audit.run(args(BASE + path, "--robots-file", rf, "--no-fetch"), StubFetcher({}))
            for agent, pol in exp.items():
                self.assertEqual(row(rep, agent)["robots_policy"], pol, (path, agent))

    def test_client_200_diagnostic_ua_403_is_finding_without_penalty(self):
        def home(ua):
            if "Googlebot" in ua:
                return (403, {}, "forbidden")
            return good("/")
        routes = {"/robots.txt": ALLOW_ALL, "/": home}
        with LocalServer(routes) as srv:
            f = Fetcher(delay=0, allow_private=True)
            rep = site_audit.run(args(srv.base + "/", "--agents", "Googlebot,GPTBot", "--score"), f)
        g = row(rep, "Googlebot")
        self.assertEqual((g["robots_policy"], g["probe_http_status"], g["verified_access"]), ("allow", 403, "unknown"))
        self.assertEqual(obs(rep, "http_status")["status"], "pass")
        d = [x for x in rep["diagnostics"] if x["agent"] == "Googlebot"]
        self.assertEqual(len(d), 1)
        self.assertIsNone(d[0]["penalty"])
        self.assertIn("требует проверки по логам", d[0]["note"])
        self.assertEqual(rep["score"]["value"], 100)

    def test_robots_network_error_gives_unknown(self):
        f = StubFetcher({"/robots.txt": "NETWORK", "/": good("/")})
        rep = site_audit.run(args(BASE + "/", "--probe", "none"), f)
        self.assertEqual(rep["robots"]["fetch_status"], "network")
        for r in rep["access"]:
            self.assertEqual(r["robots_policy"], "unknown")
            self.assertIn("сетев", r["robots_evidence"]["reason"])
        self.assertEqual(obs(rep, "search_crawl_access")["status"], "unknown")


class SiteRuns(unittest.TestCase):
    def test_one_404_of_five_scores_98(self):
        paths = ["/a/1", "/a/2", "/b/1", "/b/2"]
        routes = {"/robots.txt": (200, {}, f"User-agent: *\nDisallow:\nSitemap: /sitemap.xml\n"),
                  "/": good("/", paths), "/a/1": good("/a/1"), "/a/2": good("/a/2"), "/b/1": good("/b/1"),
                  "/b/2": (404, {}, "nope")}
        with LocalServer(routes) as srv:
            routes["/sitemap.xml"] = (200, {"content-type": "application/xml"}, urlset(paths, srv.base))
            rep = site_audit.run(args("--site", srv.base, "--score", "--probe", "none"), Fetcher(delay=0, allow_private=True))
        self.assertEqual(len(rep["sample"]["selected"]), 5)
        sc = rep["score"]
        self.assertEqual(sc["status"], "ok", sc)
        self.assertEqual(sc["value"], 98)
        self.assertIsNone(sc["ceiling"])
        b2 = srv.base + "/b/2"
        self.assertEqual(obs(rep, "http_status", b2)["status"], "fail")
        self.assertEqual(obs(rep, "canonical_target", b2)["status"], "not_applicable")
        self.assertIn("internal_reachability", sc["included_optional"])

    def test_all_403_run_invalid_no_score(self):
        routes = {"/robots.txt": ALLOW_ALL, "/sitemap.xml": (200, {}, urlset(["/a/1", "/b/1"]))}
        for p in ("/", "/a/1", "/b/1"):
            routes[p] = (403, {}, "denied")
        rep = site_audit.run(args("--site", BASE, "--score", "--probe", "none"), StubFetcher(routes))
        self.assertFalse(rep["run"]["valid"])
        self.assertIsNone(rep["score"]["value"])
        self.assertEqual(rep["score"]["status"], "invalid")
        self.assertTrue(all(obs(rep, "http_status", u)["status"] == "fail" for u in rep["target_set"]["T"]))

    def test_csr_main_content_unknown_then_fail_with_render(self):
        csr = (200, {}, page("<div id='root'></div><script>render()</script><noscript>Включите JS</noscript>"))
        f = StubFetcher({"/robots.txt": ALLOW_ALL, "/app": csr})
        rep = site_audit.run(args(BASE + "/app", "--probe", "none", "--score"), f)
        self.assertEqual(obs(rep, "main_content_raw")["status"], "unknown")
        self.assertEqual(rep["score"]["status"], "incomplete_coverage")
        rend = tmpfile(page("<main><h1>App</h1><p>Полный текст после рендера страницы.</p></main>"), ".html")
        f = StubFetcher({"/robots.txt": ALLOW_ALL, "/app": csr})
        rep = site_audit.run(args(BASE + "/app", "--probe", "none", "--render", f"{BASE}/app::{rend}"), f)
        self.assertEqual(obs(rep, "main_content_raw")["status"], "fail")

    def test_relative_canonical_resolved_from_final_url(self):
        body = page("<main><h1>X</h1><p>Текст.</p></main>", head="<link rel='canonical' href='1'>")
        routes = {"/robots.txt": ALLOW_ALL, "/old": (301, {"Location": "/a/1"}, ""), "/a/1": (200, {}, body)}
        rep = site_audit.run(args(BASE + "/old", "--probe", "none"), StubFetcher(routes))
        o = obs(rep, "canonical_target")
        self.assertEqual(o["status"], "pass", o)
        self.assertEqual(o["evidence"]["resolved"], BASE + "/a/1")
        body2 = page("<main><h1>X</h1><p>Текст.</p></main>", head="<base href='/x/'><link rel='canonical' href='1'>")
        routes["/a/1"] = (200, {}, body2)
        rep = site_audit.run(args(BASE + "/old", "--probe", "none"), StubFetcher(routes))
        o = obs(rep, "canonical_target")
        self.assertEqual(o["status"], "fail")
        self.assertEqual(o["evidence"]["resolved"], BASE + "/x/1")

    def test_incomplete_frontier_reachability_not_applicable(self):
        paths = [f"/t{i}/p" for i in range(3)]
        routes = {"/robots.txt": ALLOW_ALL, "/sitemap.xml": (200, {}, urlset(paths)),
                  "/": good("/", paths + ["/hidden/1", "/hidden/2"])}
        for p in paths:
            routes[p] = good(p)
        rep = site_audit.run(args("--site", BASE, "--probe", "none", "--score", "--limit", "2"), StubFetcher(routes))
        o = obs(rep, "internal_reachability", BASE + "/")
        self.assertEqual(o["status"], "not_applicable")
        self.assertIn("фронтир неполный", o["reason"])
        self.assertNotIn("internal_reachability", rep["score"].get("included_optional", []))
        self.assertEqual(rep["sample"]["excluded_templates"][0]["reason"], "бюджет")

    def test_sitemap_index_gzip_and_cycle(self):
        gz = gzip.compress(urlset(["/g/1", "/g/2"]).encode())
        index = (f"<sitemapindex><sitemap><loc>{BASE}/s1.xml.gz</loc></sitemap>"
                 f"<sitemap><loc>{BASE}/s2.xml</loc></sitemap>"
                 f"<sitemap><loc>{BASE}/idx.xml</loc></sitemap></sitemapindex>")
        routes = {"/robots.txt": (200, {}, f"User-agent: *\nDisallow:\nSitemap: {BASE}/idx.xml\n"),
                  "/idx.xml": (200, {}, index), "/s1.xml.gz": (200, {"content-type": "application/gzip"}, gz),
                  "/s2.xml": (200, {}, urlset(["/h/1"])), "/": good("/")}
        for p in ("/g/1", "/g/2", "/h/1"):
            routes[p] = good(p)
        rep = site_audit.run(args("--site", BASE, "--probe", "none"), StubFetcher(routes))
        sm = rep["sitemaps"]
        self.assertTrue(sm["found"])
        self.assertEqual(sm["url_count"], 3)
        self.assertTrue(any(e.get("result") == "skipped_cycle_or_duplicate" for e in sm["entries"]))
        self.assertEqual(obs(rep, "sitemap_discovery")["status"], "pass")

    def test_sitemap_network_error_is_not_absence(self):
        routes = {"/robots.txt": ALLOW_ALL, "/sitemap.xml": "NETWORK", "/": good("/")}
        rep = site_audit.run(args("--site", BASE, "--probe", "none"), StubFetcher(routes))
        self.assertEqual(obs(rep, "sitemap_discovery")["status"], "unknown")
        routes["/sitemap.xml"] = (404, {}, "")
        rep = site_audit.run(args("--site", BASE, "--probe", "none"), StubFetcher(routes))
        self.assertEqual(obs(rep, "sitemap_discovery")["status"], "fail")

    def test_stop_after_three_5xx(self):
        paths = [f"/t{i}/p" for i in range(6)]
        routes = {"/robots.txt": ALLOW_ALL, "/sitemap.xml": (200, {}, urlset(paths)), "/": good("/", paths)}
        for p in paths:
            routes[p] = (503, {}, "")
        f = StubFetcher(routes)
        rep = site_audit.run(args("--site", BASE, "--probe", "none", "--score"), f)
        self.assertEqual(rep["sample"]["stop_reason"], "три ответа 429/5xx подряд")
        self.assertFalse(rep["sample"]["complete"])
        self.assertEqual(sum(1 for r in f.requests if r["status"] == 503), 3)
        self.assertIsNone(rep["score"]["value"])

    def test_retry_after_and_min_delay(self):
        slept = []
        t = [0.0]
        f = StubFetcher({"/": (429, {"Retry-After": "7"}, ""), "/b": (200, {}, "")}, delay=1.0,
                        sleep=lambda s: (slept.append(s), t.__setitem__(0, t[0] + s)), clock=lambda: t[0])
        f.fetch(BASE + "/", "ua")
        f.fetch(BASE + "/b", "ua")
        f.fetch(BASE + "/b", "ua")
        self.assertEqual(slept, [7.0, 1.0])


class Guards(unittest.TestCase):
    def test_limit_zero_rejected(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            site_audit.parse_args(["--site", "https://example.com", "--limit", "0"])

    def test_delay_below_one_rejected(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            site_audit.parse_args(["--site", "https://example.com", "--delay", "0.2"])

    def test_loopback_rejected_by_default(self):
        f = Fetcher(delay=0)
        r = f.fetch("http://127.0.0.1:9/", "ua")
        self.assertIsNone(r.status)
        self.assertIn("не публичный", r.error)
        self.assertEqual(f.requests, [])
        r = f.fetch("file:///etc/passwd", "ua")
        self.assertIn("только http(s)", r.error)

    def test_redirect_to_private_rejected(self):
        f = StubFetcher({"/": (302, {"Location": "http://10.0.0.1/"}, "")}, allow_private=False)
        f.allow_private = True  # первый запрос (заглушка 127.0.0.1) допускаем
        orig = f.fetch

        def check():
            import netfetch
            real = netfetch.check_public

            def strict(url, allow_private=False):
                return real(url, allow_private="127.0.0.1" in url)
            netfetch.check_public = strict
            try:
                return orig(BASE + "/", "ua")
            finally:
                netfetch.check_public = real
        r = check()
        self.assertIn("не публичный", r.error)

    def test_sample_selection_deterministic(self):
        cands = [f"https://e.com/t{i}/{j}" for i in range(12) for j in range(2 + (i == 5) * 3)]
        s1 = site_audit.select_sample("https://e.com/", cands, 20)
        s2 = site_audit.select_sample("https://e.com/", list(cands), 20)
        self.assertEqual(s1["selected"], s2["selected"])
        self.assertEqual(len(s1["selected"]), 20)
        self.assertEqual(s1["templates"][0]["template"], "/t5/*")  # больше всего URL
        self.assertEqual(len(s1["templates"][0]["selected"]), 2)
        self.assertEqual(s1["selected"][0], "https://e.com/")
        self.assertEqual([len(t["selected"]) for t in s1["templates"]], [2] * 7 + [1] * 5)
        self.assertEqual(s1["excluded_templates"], [])

    def test_out_file_only_when_requested(self):
        rf = tmpfile("User-agent: *\nDisallow:\n")
        out = tmpfile("", ".json")
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            site_audit.main(["https://example.com/", "--robots-file", rf, "--no-fetch", "--json", "--out", out])
        with open(out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["schema_version"], "site_audit/1")
        self.assertIn("schema_version", buf.getvalue())


def synth(T, fails=(), na=(), home=None, site=True, unknown=()):
    """Синтетические наблюдения: все pass, кроме указанных (check, url)."""
    out = []
    for u in T:
        for c in ("http_status", "search_crawl_access", "index_directive", "canonical_target", "main_content_raw",
                  "internal_reachability"):
            st = "pass"
            if (c, u) in fails:
                st = "fail"
            if (c, u) in na:
                st = "not_applicable"
            if (c, u) in unknown:
                st = "unknown"
            out.append({"check_id": c, "scope": "url", "url": u, "status": st})
    if site:
        out.append({"check_id": "sitemap_discovery", "scope": "site", "url": None, "status": "pass"})
    return out


class Ceilings(unittest.TestCase):
    def test_20_of_20_blocked_gives_0(self):
        T = [f"https://e.com/{i}" if i else "https://e.com/" for i in range(20)]
        fails, na = set(), set()
        for u in T[:8]:  # 8 × 404, включая главную
            fails.add(("http_status", u))
            for c in ("index_directive", "canonical_target", "main_content_raw", "internal_reachability"):
                na.add((c, u))
        for u in T[8:]:  # 12 × 2xx, закрыты robots
            fails.add(("search_crawl_access", u))
            na.add(("index_directive", u))
        sc = site_audit.compute_score(synth(T, fails, na), T, "https://e.com/", True)
        self.assertEqual(sc["blockers"]["B_size"], 20)
        self.assertEqual(sc["value"], 0)

    def test_1_of_1_target_with_19_excluded_gives_0(self):
        sample = [f"https://e.com/{i}" for i in range(20)]
        T = sample[:1]
        sc = site_audit.compute_score(synth(T, {("index_directive", T[0])}), T, "https://e.com/", True, checked=20)
        self.assertEqual(sc["value"], 0)
        self.assertEqual((sc["checked"], sc["target_size"]), (20, 1))

    def test_1_of_20_has_no_zero_ceiling(self):
        T = ["https://e.com/"] + [f"https://e.com/{i}" for i in range(1, 20)]
        sc = site_audit.compute_score(synth(T, {("index_directive", T[5])}), T, "https://e.com/", True)
        self.assertIsNone(sc["ceiling"])
        self.assertGreater(sc["value"], 90)

    def test_home_in_B_caps_50_and_high_everywhere_caps_70(self):
        T = ["https://e.com/"] + [f"https://e.com/{i}" for i in range(1, 5)]
        sc = site_audit.compute_score(synth(T, {("index_directive", T[0])}), T, "https://e.com/", True)
        self.assertEqual(sc["value"], 50)
        sc = site_audit.compute_score(synth(T, {("canonical_target", u) for u in T}), T, "https://e.com/", True)
        self.assertEqual(sc["value"], 70)

    def test_unknown_mandatory_means_no_score(self):
        T = ["https://e.com/"]
        sc = site_audit.compute_score(synth(T, unknown={("main_content_raw", T[0])}), T, "https://e.com/", True)
        self.assertIsNone(sc["value"])
        self.assertEqual(sc["status"], "incomplete_coverage")


if __name__ == "__main__":
    unittest.main()
