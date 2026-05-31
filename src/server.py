#!/usr/bin/env python3
"""Local backend for the bigram LLM illustrator.

Serves the single-page app and provides URL-scraping (via BeautifulSoup) so the
browser can turn arbitrary web pages into plain training text. Everything else
(pasting text, the bundled standard excerpts, the analysis and animation) runs
client-side; this server only handles the two things the browser cannot:
fetching cross-origin URLs and parsing their HTML to readable text.

Run:  python3 src/server.py   then open  http://localhost:8731/
"""

import json
import re
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

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


def fetch(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        raw = resp.read()
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


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
        self.send_header("Access-Control-Allow-Origin", "*")
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
