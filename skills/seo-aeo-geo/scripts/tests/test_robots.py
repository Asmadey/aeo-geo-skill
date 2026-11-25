import unittest

import helpers  # noqa: F401
import robots

EVAL1 = """User-agent: GPTBot
User-agent: ClaudeBot
Disallow: /

User-agent: *
Disallow: /private/
"""


def pol(text, agent, path):
    return robots.Robots(text).decide(agent, "https://example.com" + path).policy


class Eval1Groups(unittest.TestCase):
    def test_consecutive_user_agents_form_one_group(self):
        for agent in ("GPTBot", "ClaudeBot"):
            self.assertEqual(pol(EVAL1, agent, "/"), "block")
            self.assertEqual(pol(EVAL1, agent, "/private/x"), "block")
            self.assertEqual(pol(EVAL1, agent, "/blog/post"), "block")

    def test_unnamed_agents_use_star_group(self):
        for agent in ("OAI-SearchBot", "Googlebot", "Claude-SearchBot"):
            self.assertEqual(pol(EVAL1, agent, "/private/x"), "block")
            self.assertEqual(pol(EVAL1, agent, "/blog/post"), "allow")

    def test_named_group_loses_star_fallback(self):
        text = EVAL1 + "\nUser-agent: OAI-SearchBot\nDisallow: /tmp/\n"
        self.assertEqual(pol(text, "OAI-SearchBot", "/private/x"), "allow")
        self.assertEqual(pol(text, "OAI-SearchBot", "/tmp/a"), "block")


class Parser(unittest.TestCase):
    def test_repeated_sections_merge(self):
        text = "User-agent: Bot\nDisallow: /a/\n\nUser-agent: Other\nDisallow: /\n\nUser-agent: bot\nDisallow: /b/\n"
        self.assertEqual(pol(text, "Bot", "/a/1"), "block")
        self.assertEqual(pol(text, "Bot", "/b/1"), "block")
        self.assertEqual(pol(text, "Bot", "/c/1"), "allow")

    def test_wildcard_and_end_anchor(self):
        text = "User-agent: *\nDisallow: /*.pdf$\nDisallow: /*/print\n"
        self.assertEqual(pol(text, "X", "/docs/a.pdf"), "block")
        self.assertEqual(pol(text, "X", "/docs/a.pdf?x=1"), "allow")
        self.assertEqual(pol(text, "X", "/blog/print/1"), "block")
        self.assertEqual(pol(text, "X", "/print"), "allow")

    def test_longest_match_and_allow_on_tie(self):
        text = "User-agent: *\nDisallow: /a\nAllow: /a/b\nAllow: /p\nDisallow: /p\n"
        self.assertEqual(pol(text, "X", "/a/b/c"), "allow")
        self.assertEqual(pol(text, "X", "/a/c"), "block")
        self.assertEqual(pol(text, "X", "/p/1"), "allow")

    def test_empty_disallow_allows(self):
        self.assertEqual(pol("User-agent: *\nDisallow:\n", "GPTBot", "/x"), "allow")

    def test_sitemaps_collected(self):
        r = robots.Robots("Sitemap: https://e.com/s.xml\nUser-agent: *\nDisallow:\n")
        self.assertEqual(r.sitemaps, ["https://e.com/s.xml"])


class FetchStatus(unittest.TestCase):
    def test_status_to_policy(self):
        cases = {404: "allow", 410: "allow", 403: "unknown", 401: "unknown", 429: "unknown", 500: "unknown", 503: "unknown"}
        for st, exp in cases.items():
            r = robots.from_response(st, b"User-agent: *\nDisallow: /\n")
            self.assertEqual(r.decide("Googlebot", "https://e.com/").policy, exp, st)
        net = robots.from_response(None, None, "timeout")
        d = net.decide("Googlebot", "https://e.com/")
        self.assertEqual(d.policy, "unknown")
        self.assertIn("сетев", d.reason)
        self.assertEqual(net.fetch_status, "network")


if __name__ == "__main__":
    unittest.main()
