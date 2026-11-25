"""Общие средства тестов: путь к scripts/, локальный HTTP-сервер на 127.0.0.1, подменный fetcher.

Внешняя сеть не используется: StubFetcher не открывает соединений, LocalServer слушает только loopback.
"""
from __future__ import annotations

import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

os.environ["no_proxy"] = os.environ["NO_PROXY"] = "127.0.0.1,localhost"
SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from netfetch import Fetcher, Response  # noqa: E402

BASE = "http://127.0.0.1:9"  # адрес-заглушка для StubFetcher: соединение не открывается


def page(body: str, title: str = "T", head: str = "") -> str:
    return f"<html lang='ru'><head><title>{title}</title>{head}</head><body>{body}</body></html>"


def _resolve(route, ua):
    return route(ua) if callable(route) else route


class StubFetcher(Fetcher):
    """Fetcher с настоящей логикой редиректов/паузы/стопа, но без сети: ответы из routes по пути."""

    def __init__(self, routes: dict, **kw):
        kw.setdefault("delay", 0)
        kw.setdefault("allow_private", True)
        super().__init__(**kw)
        self.routes = routes

    def _one(self, url, ua):
        p = urlsplit(url)
        path = p.path + ("?" + p.query if p.query else "")
        route = _resolve(self.routes.get(path, (404, {}, b"not found")), ua)
        if route == "NETWORK":
            return Response(url, url, None, {}, b"", [], "ConnectionRefusedError: stub")
        status, headers, body = route
        if isinstance(body, str):
            body = body.encode("utf-8")
        headers = {k.lower(): v for k, v in headers.items()}
        headers.setdefault("content-type", "text/html; charset=utf-8")
        return Response(url, url, status, headers, body)


class LocalServer:
    """http.server на 127.0.0.1 со случайным портом; routes как у StubFetcher."""

    def __init__(self, routes: dict):
        routes_ref = routes

        class H(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                route = _resolve(routes_ref.get(self.path, (404, {}, b"not found")), self.headers.get("User-Agent", ""))
                status, headers, body = route
                if isinstance(body, str):
                    body = body.encode("utf-8")
                self.send_response(status)
                headers = dict(headers)
                headers.setdefault("Content-Type", "text/html; charset=utf-8")
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
