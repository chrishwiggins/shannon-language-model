#!/usr/bin/env python3
"""Build the static publish directory for Cloudflare Pages.

The app normally runs behind src/server.py (Python + BeautifulSoup) so that the
"From URL(s)" tab can scrape arbitrary pages. Cloudflare Pages is static-only and
cannot run Python, so the deployed build keeps every tab that works without a
backend (designed demo, paste-your-own, standard texts served straight from
dat/) and turns the URL-scraping tab into an honest "this tab is local-only"
notice instead of a fetch that fails.

This is deterministic: re-run it after editing index.html and redeploy. It never
edits the source files; it writes a transformed copy into out/site/.

    python3 src/build-static.py
    wrangler pages deploy out/site --project-name shannon-language-model --branch main
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "out" / "site"
NYC = ZoneInfo("America/New_York")

# The placeholder in index.html that we replace with a real last-updated stamp.
# The stamp is the source file's own modification time (when index.html was last
# edited), converted to New York time -- an honest "last updated", not "now".
LASTUPDATED_SRC = '<p class="hint" id="lastUpdated">last updated: run the build to stamp the time</p>'

# Injected once into <head> so it is set before any app code runs. index.html
# reads window.STATIC_DEPLOY and removes the "From URL(s)" tab and its panel: on
# the static build there is no Python backend, so URL scraping cannot work, and a
# removed tab beats a dead button. Served locally by src/server.py the flag is
# unset and the tab stays.
FLAG = "<script>window.STATIC_DEPLOY = true;</script>"


def build() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)

    src = ROOT / "index.html"
    html = src.read_text(encoding="utf-8")

    # Inject the static-deploy flag once, right after <head>.
    assert "<head>" in html, "index.html has no <head> to inject the flag into"
    html = html.replace("<head>", "<head>\n  " + FLAG, 1)

    # Stamp the last-updated time = index.html's modification time, in NYC time.
    # Honest: this is when the source was last edited, not when the page is viewed.
    stamp = datetime.fromtimestamp(src.stat().st_mtime, NYC).strftime("%Y-%m-%dT%H-%M-%S")
    assert LASTUPDATED_SRC in html, "last-updated placeholder not found (did the markup change?)"
    html = html.replace(
        LASTUPDATED_SRC,
        f'<p class="hint" id="lastUpdated">last updated {stamp} NYC time</p>',
        1,
    )

    # (No URL-tab patching needed: the injected flag makes index.html remove the
    # whole tab at runtime, so there is no dead button or stale hint to rewrite.)

    (SITE / "index.html").write_text(html, encoding="utf-8")

    # Publish ONLY the standard-texts catalog and the files it names -- never the
    # whole dat/ tree. dat/ also holds local-only material (copyrighted analysis
    # input, experiment logs, candidate texts) that must NOT reach the public
    # site; copying it wholesale would leak it. So we copy index.json plus exactly
    # the files listed there.
    (SITE / "dat").mkdir(parents=True)
    catalog = ROOT / "dat" / "index.json"
    shutil.copy2(catalog, SITE / "dat" / "index.json")
    items = json.loads(catalog.read_text(encoding="utf-8"))
    for it in items:
        f = it["file"]
        src_f = ROOT / "dat" / f
        assert src_f.is_file(), f"catalog lists missing file: dat/{f}"
        shutil.copy2(src_f, SITE / "dat" / f)
    print(f"Published {len(items)} catalog text(s) from dat/index.json (not the whole dat/ tree).")

    files = sorted(p.relative_to(SITE).as_posix() for p in SITE.rglob("*") if p.is_file())
    print(f"Built {SITE} with {len(files)} files:")
    for f in files:
        print("  " + f)


if __name__ == "__main__":
    build()
