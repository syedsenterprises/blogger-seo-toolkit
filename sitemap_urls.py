#!/usr/bin/env python3
"""sitemap_urls.py — list URLs from a Blogger sitemap.

Blogger's sitemap.xml is a sitemap *index*: it points at sub-sitemaps for
posts, pages, and labels. This tool prints every URL it finds, following the
index by default.

Usage:
    python3 sitemap_urls.py sitemap.xml
    python3 sitemap_urls.py https://example.blogspot.com/sitemap.xml
    python3 sitemap_urls.py sitemap.xml --no-follow   # list index entries only
    python3 sitemap_urls.py sitemap.xml --filter /2026/ --count

Standard library only.
"""

import argparse
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def read_text(location, timeout):
    if "://" not in location:
        with open(location, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    req = urllib.request.Request(location, headers={"User-Agent": "blogger-seo-toolkit/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def resolve(loc, base):
    """Resolve a sitemap loc against its parent location (relative paths work).

    Local sitemaps resolve to plain relative paths (run from the directory
    containing the sitemap, or pass an absolute sitemap path); http(s)
    sitemaps resolve with urljoin.
    """
    if "://" in loc:
        return loc
    if "://" in base:
        return urljoin(base, loc)
    return os.path.join(os.path.dirname(base), loc) or loc


def extract(location, follow, timeout, depth=0):
    """Yield (kind, loc) pairs: kind is 'url' or 'sitemap'."""
    if depth > 5:
        return
    text = read_text(location, timeout)
    root = ET.fromstring(text)
    if root.tag.endswith("sitemapindex"):
        for sm in root.findall("sm:sitemap", NS):
            loc = sm.findtext("sm:loc", namespaces=NS)
            if not loc:
                continue
            yield ("sitemap", resolve(loc, location))
            if follow:
                yield from extract(resolve(loc, location), follow, timeout, depth + 1)
    else:
        for url in root.findall("sm:url", NS):
            loc = url.findtext("sm:loc", namespaces=NS)
            if loc:
                yield ("url", resolve(loc, location))


def main(argv=None):
    ap = argparse.ArgumentParser(description="List URLs from a Blogger sitemap.")
    ap.add_argument("sitemap", help="sitemap XML file or URL")
    ap.add_argument("--no-follow", action="store_true",
                    help="do not follow a sitemap index into sub-sitemaps")
    ap.add_argument("--filter", default="", help="only print URLs containing this text")
    ap.add_argument("--count", action="store_true", help="print only the total count")
    ap.add_argument("--timeout", type=int, default=15, help="fetch timeout in seconds")
    args = ap.parse_args(argv)

    try:
        pairs = list(extract(args.sitemap, not args.no_follow, args.timeout))
    except (OSError, urllib.error.URLError, ET.ParseError, ValueError) as exc:
        print("error: cannot read sitemap: %s" % exc, file=sys.stderr)
        return 2

    urls = [loc for kind, loc in pairs
            if kind == "url" or (args.no_follow and kind == "sitemap")]
    if args.filter:
        urls = [u for u in urls if args.filter in u]
    if args.count:
        print(len(urls))
    else:
        for url in urls:
            print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
