#!/usr/bin/env python3
"""Local backend for the bigram LLM illustrator.

Serves the single-page app and provides URL-scraping (via BeautifulSoup) so the
browser can turn arbitrary web pages into plain training text. Everything else
(pasting text, the bundled standard excerpts, the analysis and animation) runs
client-side; this server only handles the two things the browser cannot:
fetching cross-origin URLs and parsing their HTML to readable text.

Run:  python3 src/server.py   then open  http://localhost:8731/
"""

import ipaddress
import json
import re
import socket
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.stderr.write(
        "BeautifulSoup is required: pip install beautifulsoup4\n"
        "(URL scraping will return an error until it is installed.)\n"
    )
    BeautifulSoup = None

ROOT = Path(__file__).resolve().parent.parent  # project root (holds index.html, dat/)
PORT = 8731
USER_AGENT = "Mozilla/5.0 (bigram-illustrator; educational use)"


def html_to_text(html: str) -> str:
    """Extract human-readable text from an HTML document.

    Drops script/style/nav/footer chrome, collapses whitespace, and keeps
    paragraph breaks so the result reads like prose rather than markup.
    """
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 not installed")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header",
                     "form", "aside", "iframe", "svg"]):
        tag.decompose()
    # Prefer the main/article body if present; else the whole document.
    main = soup.find("article") or soup.find("main") or soup.body or soup
    text = main.get_text(separator="\n")
    # collapse runs of blank lines and trailing spaces
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


# --- SSRF guard ---------------------------------------------------------------
# This server fetches URLs the user types. Without a guard, a user (or a page that
# redirects) could point it at internal hosts: the cloud metadata endpoint
# (169.254.169.254), loopback, or RFC1918 LAN addresses. We therefore (1) allow only
# http/https, (2) resolve the hostname and reject any non-global IP, (3) follow
# redirects manually, re-validating each hop, and (4) cap the bytes read.
ALLOWED_SCHEMES = ("http", "https")
MAX_FETCH_BYTES = 5 * 1024 * 1024  # 5 MB: enough for prose, bounds memory
MAX_REDIRECTS = 5


class UnsafeURLError(ValueError):
    """Raised when a URL targets a non-public address or a disallowed scheme."""


def _ip_is_public(ip_str: str) -> bool:
    """True only for globally-routable unicast addresses. Rejects loopback,
    link-local (incl. the 169.254.169.254 metadata IP), private, reserved, and
    multicast ranges, for both IPv4 and IPv6."""
    ip = ipaddress.ip_address(ip_str)
    return not (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_multicast or ip.is_reserved or ip.is_unspecified)


def validate_public_url(url):
    """Reject any URL that is not an http/https request to a public host, and return
    the (host, [validated public IPs]) for that URL. Resolving here and PINNING the
    result for the connection is what defeats DNS rebinding: without the pin, urllib
    would resolve the name a second time at connect, and a malicious resolver could
    return a public IP now and a private one then. The caller connects only to one of
    the returned IPs."""
    parts = urlparse(url)
    if parts.scheme not in ALLOWED_SCHEMES:
        raise UnsafeURLError(f"scheme not allowed: {parts.scheme or '(none)'}")
    host = parts.hostname
    if not host:
        raise UnsafeURLError("no host in URL")
    try:
        infos = socket.getaddrinfo(host, parts.port or
                                   (443 if parts.scheme == "https" else 80),
                                   proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"cannot resolve host {host!r}: {exc}") from exc
    addrs = {info[4][0] for info in infos}
    if not addrs:
        raise UnsafeURLError(f"host {host!r} resolved to no addresses")
    for addr in addrs:
        if not _ip_is_public(addr):
            raise UnsafeURLError(f"host {host!r} resolves to non-public address {addr}")
    return host, sorted(addrs)


def _pinned_opener(host, ip):
    """An opener whose http/https connections go to a fixed, already-validated IP,
    while keeping the original hostname for the Host header and TLS SNI. This removes
    the second DNS lookup, closing the resolve-then-connect rebinding window."""
    import http.client
    import ssl

    ctx = ssl.create_default_context()

    class PinnedHTTPConnection(http.client.HTTPConnection):
        def connect(self):
            self.sock = socket.create_connection((ip, self.port), self.timeout)

    class PinnedHTTPSConnection(http.client.HTTPSConnection):
        def connect(self):
            sock = socket.create_connection((ip, self.port), self.timeout)
            # server_hostname keeps SNI + cert validation against the real name.
            self.sock = ctx.wrap_socket(sock, server_hostname=host)

    class PinnedHTTPHandler(urllib.request.HTTPHandler):
        def http_open(self, req):
            return self.do_open(PinnedHTTPConnection, req)

    class PinnedHTTPSHandler(urllib.request.HTTPSHandler):
        def https_open(self, req):
            return self.do_open(PinnedHTTPSConnection, req)

    return urllib.request.build_opener(_NoRedirect, PinnedHTTPHandler, PinnedHTTPSHandler)


def fetch(url, timeout=15):
    """Fetch a URL's body as text. Enforces the SSRF guard on the initial URL and on
    every redirect hop, connects only to the validated IP (anti-rebinding), and caps
    the bytes read."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        host, ips = validate_public_url(current)
        opener = _pinned_opener(host, ips[0])  # connect to a validated IP only
        req = urllib.request.Request(current, headers={"User-Agent": USER_AGENT},
                                     method="GET")
        try:
            resp = opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                loc = exc.headers.get("Location")
                if not loc:
                    raise UnsafeURLError("redirect with no Location") from exc
                current = urljoin(current, loc)
                continue
            raise
        with resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read(MAX_FETCH_BYTES + 1)
        if len(raw) > MAX_FETCH_BYTES:
            raise UnsafeURLError(f"response exceeds {MAX_FETCH_BYTES} bytes")
        try:
            return raw.decode(charset, errors="replace")
        except LookupError:
            return raw.decode("utf-8", errors="replace")
    raise UnsafeURLError(f"too many redirects (> {MAX_REDIRECTS})")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Turn 3xx responses into HTTPError instead of auto-following them, so fetch()
    can re-run the SSRF guard on the redirect target before continuing."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # quieter console
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # No wildcard CORS: the app is same-origin with this server, so it never needs
        # cross-origin access. Dropping "Access-Control-Allow-Origin: *" stops a
        # malicious third-party page from reading /scrape results in the user's
        # browser (the cross-origin half of the SSRF attack surface).
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # --- API: scrape one or more URLs ---
        if path == "/scrape":
            qs = parse_qs(parsed.query)
            urls = qs.get("url", [])
            # also accept a single comma/newline-separated "urls" param
            if "urls" in qs:
                blob = qs["urls"][0]
                urls += [u.strip() for u in re.split(r"[,\n]+", blob) if u.strip()]
            if not urls:
                return self._send(400, {"error": "no url provided"})
            results = []
            for u in urls:
                if not re.match(r"^https?://", u):
                    u = "https://" + u
                try:
                    text = html_to_text(fetch(u))
                    results.append({"url": u, "ok": True, "text": text,
                                    "chars": len(text)})
                except Exception as e:  # report per-URL, never 500 the whole call
                    results.append({"url": u, "ok": False, "error": str(e)})
            combined = "\n\n".join(r["text"] for r in results if r.get("ok"))
            return self._send(200, {"results": results, "combined": combined})

        # --- static files (index.html, dat/*.txt, fig/*, etc.) ---
        rel = path.lstrip("/") or "index.html"
        target = (ROOT / rel).resolve()
        if not str(target).startswith(str(ROOT)) or not target.is_file():
            return self._send(404, {"error": f"not found: {rel}"})
        ctype = {
            ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
            ".txt": "text/plain; charset=utf-8", ".json": "application/json",
            ".png": "image/png", ".svg": "image/svg+xml",
        }.get(target.suffix, "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)


def main():
    print(f"Bigram illustrator running at http://localhost:{PORT}/")
    print(f"Serving from {ROOT}")
    if BeautifulSoup is None:
        print("WARNING: beautifulsoup4 not installed; /scrape will error.")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
