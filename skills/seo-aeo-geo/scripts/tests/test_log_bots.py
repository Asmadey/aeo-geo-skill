import unittest

import helpers  # noqa: F401
import log_bots

LOG = [
    '66.249.66.1 - - [10/Nov/2026:10:00:00 +0000] "GET /a HTTP/1.1" 200 512 "-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"\n',
    '6.6.6.6 - - [10/Nov/2026:10:00:01 +0000] "GET /b HTTP/1.1" 403 0 "-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"\n',
    '1.1.1.1 - - [10/Nov/2026:10:00:02 +0000] "GET /c HTTP/1.1" 200 1 "https://chatgpt.com/" "Mozilla/5.0 Chrome/131"\n',
    '1.1.1.2 - - [10/Nov/2026:10:00:03 +0000] "GET /d HTTP/1.1" 200 1 "https://chatgpt.com.evil.net/x" "Mozilla/5.0 Chrome/131"\n',
    '1.1.1.3 - - [10/Nov/2026:10:00:04 +0000] "GET /e HTTP/1.1" 200 1 "https://chatgpt.com/" "Mozilla/5.0; compatible; ChatGPT-User/1.0; +https://openai.com/bot"\n',
    '1.1.1.4 - - [10/Nov/2026:10:00:05 +0000] "GET /f HTTP/1.1" 200 1 "https://www.perplexity.ai/search" "Mozilla/5.0 Safari"\n',
    'garbage line\n',
]


class FakeDNS:
    def reverse(self, ip):
        return {"66.249.66.1": "crawl-66-249-66-1.googlebot.com", "6.6.6.6": "spoof.example.net"}[ip]

    def forward(self, name):
        return {"crawl-66-249-66-1.googlebot.com": {"66.249.66.1"}}.get(name, set())


class LogBots(unittest.TestCase):
    def test_ua_match_separate_from_identity(self):
        res = log_bots.analyze(LOG)
        g = next(b for b in res["bots"] if b["bot"] == "Googlebot")
        self.assertEqual(g["ua_match_hits"], 2)
        self.assertEqual(g["verified_identity"], {"unknown": 2})
        self.assertEqual(res["parsed"], 6)

    def test_spoofed_ua_fails_dns_verification(self):
        res = log_bots.analyze(LOG, verify_dns=True, resolver=FakeDNS())
        g = next(b for b in res["bots"] if b["bot"] == "Googlebot")
        self.assertEqual(g["verified_identity"], {"confirmed": 1, "failed": 1})

    def test_referrals_by_parsed_host_and_agents_excluded(self):
        res = log_bots.analyze(LOG)
        self.assertEqual(res["ai_referrals"], {"chatgpt.com": 1, "perplexity.ai": 1})
        u = next(b for b in res["bots"] if b["bot"] == "ChatGPT-User")
        self.assertEqual(u["role"], "user")

    def test_no_unverified_ratio_claims(self):
        res = log_bots.analyze(LOG)
        self.assertFalse(any("соотношение" in f or "рассуждения" in f for f in res["findings"]))


if __name__ == "__main__":
    unittest.main()
