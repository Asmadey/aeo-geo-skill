"""Сетевой слой утилит: только публичные HTTP(S)-цели, пауза, Retry-After, стоп по 429/5xx.

Редиректы проходятся вручную: каждая цель проверяется до запроса.
Приватные, loopback и прочие не глобальные адреса отклоняются,
кроме явного allow_private (только для тестов).
"""
from __future__ import annotations

import gzip
import io
import ipaddress
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

MAX_BYTES = 10_000_000
MAX_RETRY_AFTER = 300
REDIRECTS = {301, 302, 303, 307, 308}


class TargetError(ValueError):
    pass


@dataclass
class Response:
    url: str
    final_url: str
    status: int | None = None
    headers: dict = field(default_factory=dict)
    body: bytes = b""
    redirects: list = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300

    def text(self) -> str:
        ctype = self.headers.get("content-type", "")
        charset = "utf-8"
        if "charset=" in ctype:
            charset = ctype.split("charset=", 1)[1].split(";")[0].strip() or "utf-8"
        try:
            return self.body.decode(charset, "replace")
        except LookupError:
            return self.body.decode("utf-8", "replace")


def host_key(host: str) -> str:
    h = (host or "").lower().rstrip(".")
    return h[4:] if h.startswith("www.") else h


def check_public(url: str, allow_private: bool = False) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise TargetError(f"схема {parts.scheme or '-'} не поддерживается: только http(s)")
    host = parts.hostname
    if not host:
        raise TargetError("в URL нет хоста")
    try:
        infos = socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80),
                                   proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise TargetError(f"имя {host} не разрешается: {e}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%", 1)[0])
        if not ip.is_global and not allow_private:
            raise TargetError(f"{host} → {ip}: не публичный адрес, запрос отклонён")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


class Fetcher:
    def __init__(self, delay: float = 1.0, allow_private: bool = False, timeout: float = 20,
                 max_redirects: int = 5, max_bytes: int = MAX_BYTES, sleep=time.sleep, clock=time.monotonic):
        self.delay = delay
        self.allow_private = allow_private
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.max_bytes = max_bytes
        self.sleep = sleep
        self.clock = clock
        self.requests: list[dict] = []
        self.consecutive_fail = 0
        self.stopped: str | None = None
        self._next_at = 0.0
        self._opener = urllib.request.build_opener(_NoRedirect())

    def _wait(self) -> None:
        now = self.clock()
        if now < self._next_at:
            self.sleep(self._next_at - now)

    def _account(self, status: int | None, headers: dict) -> None:
        extra = 0.0
        if status is not None and (status == 429 or status >= 500):
            self.consecutive_fail += 1
            ra = headers.get("retry-after")
            if ra:
                try:
                    extra = float(ra)
                except ValueError:
                    try:
                        extra = max(0.0, parsedate_to_datetime(ra).timestamp() - time.time())
                    except (TypeError, ValueError):
                        extra = 0.0
            if extra > MAX_RETRY_AFTER:
                self.stopped = f"Retry-After {int(extra)} с больше лимита {MAX_RETRY_AFTER} с"
            if self.consecutive_fail >= 3:
                self.stopped = "три ответа 429/5xx подряд"
        elif status is not None:
            self.consecutive_fail = 0
        self._next_at = self.clock() + max(self.delay, extra)

    def _one(self, url: str, ua: str) -> Response:
        req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "text/html,application/xhtml+xml,*/*",
                                                   "Accept-Encoding": "gzip, identity"})
        try:
            with self._opener.open(req, timeout=self.timeout) as r:
                status, headers, body = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read(self.max_bytes)
        except urllib.error.HTTPError as e:
            status, headers = e.code, {k.lower(): v for k, v in (e.headers or {}).items()}
            try:
                body = e.read(self.max_bytes)
            except Exception:  # noqa: BLE001
                body = b""
        except Exception as e:  # noqa: BLE001 — сеть, TLS, таймаут
            return Response(url, url, None, {}, b"", [], f"{type(e).__name__}: {e}")
        if headers.get("content-encoding", "").lower() == "gzip" and body[:2] == b"\x1f\x8b":
            try:
                body = gzip.GzipFile(fileobj=io.BytesIO(body)).read(self.max_bytes)
            except OSError:
                pass
        return Response(url, url, status, headers, body)

    def fetch(self, url: str, ua: str, scope_host: str | None = None) -> Response:
        """GET с ручными редиректами. scope_host ограничивает переходы хостом (± www)."""
        redirects: list = []
        cur = url
        for _ in range(self.max_redirects + 1):
            if self.stopped:
                return Response(url, cur, None, {}, b"", redirects, f"обход остановлен: {self.stopped}")
            try:
                check_public(cur, self.allow_private)
            except TargetError as e:
                return Response(url, cur, None, {}, b"", redirects, f"цель отклонена: {e}")
            self._wait()
            resp = self._one(cur, ua)
            self.requests.append({"url": cur, "ua": ua, "status": resp.status, "error": resp.error})
            self._account(resp.status, resp.headers)
            loc = resp.headers.get("location")
            if resp.status in REDIRECTS and loc:
                nxt = urljoin(cur, loc)
                redirects.append({"status": resp.status, "from": cur, "to": nxt})
                if scope_host and host_key(urlsplit(nxt).hostname or "") != host_key(scope_host):
                    return Response(url, nxt, resp.status, resp.headers, b"", redirects,
                                    "редирект за пределы обследуемого хоста не выполнялся")
                cur = nxt
                continue
            resp.url, resp.final_url, resp.redirects = url, cur, redirects
            return resp
        return Response(url, cur, None, {}, b"", redirects, f"больше {self.max_redirects} редиректов")
