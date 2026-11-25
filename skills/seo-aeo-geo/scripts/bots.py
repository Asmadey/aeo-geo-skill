"""Общий реестр агентов для site_audit.py и log_bots.py.

Роль агента (search/training/user/other) берётся из исходных скриптов и сверяется
с platforms.md. Запись с needs_verification=True — карточка «требует проверки»:
её политика robots выводится, но поисковый вывод по ней остаётся unknown.
"""
from __future__ import annotations

TYPICAL_CLIENT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")

# token — имя в robots.txt; ua — строка диагностической пробы (None: токен только для robots);
# log — подстроки User-agent в логах; rdns — суффиксы для проверки обратным DNS (пусто: не реализовано).
BOTS = [
    {"token": "GPTBot", "vendor": "OpenAI", "role": "training",
     "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)",
     "log": ["gptbot"], "rdns": []},
    {"token": "OAI-SearchBot", "vendor": "OpenAI", "role": "search",
     "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)",
     "log": ["oai-searchbot"], "rdns": []},
    {"token": "ChatGPT-User", "vendor": "OpenAI", "role": "user",
     "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot",
     "log": ["chatgpt-user"], "rdns": []},
    {"token": "ClaudeBot", "vendor": "Anthropic", "role": "training",
     "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
     "log": ["claudebot"], "rdns": []},
    {"token": "Claude-SearchBot", "vendor": "Anthropic", "role": "search",
     "ua": "Mozilla/5.0 (compatible; Claude-SearchBot/1.0; +https://www.anthropic.com)",
     "log": ["claude-searchbot"], "rdns": []},
    {"token": "Claude-User", "vendor": "Anthropic", "role": "user",
     "ua": "Mozilla/5.0 (compatible; Claude-User/1.0; +https://www.anthropic.com)",
     "log": ["claude-user"], "rdns": []},
    {"token": "PerplexityBot", "vendor": "Perplexity", "role": "search",
     "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
     "log": ["perplexitybot"], "rdns": []},
    {"token": "Perplexity-User", "vendor": "Perplexity", "role": "user",
     "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Perplexity-User/1.0; +https://perplexity.ai/perplexity-user)",
     "log": ["perplexity-user"], "rdns": []},
    {"token": "Google-Extended", "vendor": "Google", "role": "training", "ua": None, "log": [], "rdns": []},
    {"token": "Googlebot", "vendor": "Google", "role": "search",
     "ua": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
     "log": ["googlebot"], "rdns": ["googlebot.com", "google.com"]},
    {"token": "GoogleOther", "vendor": "Google", "role": "other", "ua": None,
     "log": ["googleother"], "rdns": ["googlebot.com", "google.com"]},
    {"token": "Bingbot", "vendor": "Microsoft", "role": "search",
     "ua": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
     "log": ["bingbot"], "rdns": ["search.msn.com"]},
    {"token": "Applebot-Extended", "vendor": "Apple", "role": "training", "ua": None, "log": [], "rdns": []},
    {"token": "Applebot", "vendor": "Apple", "role": "other", "ua": None,
     "log": ["applebot"], "rdns": ["applebot.apple.com"]},
    {"token": "Meta-ExternalAgent", "vendor": "Meta", "role": "other",
     "ua": "meta-externalagent/1.1 (+https://developers.facebook.com/docs/sharing/webmasters/crawler)",
     "log": ["meta-externalagent"], "rdns": []},
    {"token": "Amazonbot", "vendor": "Amazon", "role": "other",
     "ua": "Mozilla/5.0 (compatible; Amazonbot/0.1; +https://developer.amazon.com/support/amazonbot)",
     "log": ["amazonbot"], "rdns": []},
    {"token": "CCBot", "vendor": "Common Crawl", "role": "training",
     "ua": "CCBot/2.0 (https://commoncrawl.org/faq/)", "log": ["ccbot"], "rdns": []},
    {"token": "Bytespider", "vendor": "ByteDance", "role": "other", "ua": None, "log": ["bytespider"], "rdns": []},
    {"token": "DuckAssistBot", "vendor": "DuckDuckGo", "role": "other", "ua": None, "log": ["duckassistbot"], "rdns": []},
    # Карточка Яндекса «требует проверки» (spec: Новые карточки поверхностей).
    {"token": "YandexBot", "vendor": "Yandex", "role": "search", "ua": None,
     "log": ["yandexbot"], "rdns": [], "needs_verification": True},
]

# Хосты AI-ассистентов для рефералов: точное совпадение или поддомен.
AI_REFERRER_HOSTS = {
    "chatgpt.com": "OpenAI", "chat.openai.com": "OpenAI", "perplexity.ai": "Perplexity",
    "claude.ai": "Anthropic", "gemini.google.com": "Google", "copilot.microsoft.com": "Microsoft",
    "you.com": "You.com", "deepseek.com": "DeepSeek", "grok.com": "xAI",
}


def by_token(token: str) -> dict | None:
    t = token.lower()
    for b in BOTS:
        if b["token"].lower() == t:
            return b
    return None


def match_ua(ua: str) -> dict | None:
    """Совпадение подстроки User-agent; длинные шаблоны проверяются первыми."""
    low = (ua or "").lower()
    pairs = sorted(((p, b) for b in BOTS for p in b["log"]), key=lambda x: -len(x[0]))
    for pat, b in pairs:
        if pat in low:
            return b
    return None


def ai_referrer(host: str) -> str | None:
    h = (host or "").lower().rstrip(".")
    if h.startswith("www."):
        h = h[4:]
    for dom in AI_REFERRER_HOSTS:
        if h == dom or h.endswith("." + dom):
            return dom
    return None
