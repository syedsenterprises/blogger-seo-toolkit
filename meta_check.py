#!/usr/bin/env python3
"""meta_check.py — check <meta name="description"> on Blogger posts.

Blogger's search-description field is capped at 150 characters, so this tool
fetches every URL in a sitemap (or a plain URL list) and reports, per URL:

  OK        description present and <= 150 characters
  TOO LONG  description present but > 150 characters (Blogger truncates it)
  MISSING   no meta description found at all
  ERROR     page could not be fetched / parsed

Usage:
    python3 meta_check.py --sitemap sitemap.xml
    python3 meta_check.py --sitemap https://example.blogspot.com/sitemap.xml
    python3 meta_check.py --urls urls.txt
    python3 meta_check.py --sitemap sitemap.xml --limit 20 --timeout 10

URLs in a local sitemap may use file:// locations (handy for testing with
the examples/ fixtures). Output is a plain-text table plus a summary.
Standard library only.
"""

import argparse
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urljoin


MAX_LEN = 150


class DescriptionParser(HTMLParser):
    """Extract the first <meta name="description" content="...">."""

    def __init__(self):
        super().__init__()
        self.description = None

    def handle_starttag(self, tag, attrs):
        if tag != "meta" or self.description is not None:
            return
        d = dict((k.lower(), v) for k, v in attrs)
        if d.get("name", "").lower() == "description":
            self.description = d.get("content", "")


def read_text(location, timeout):
    """Return the text at a http(s):// or file:// location, or a local path."""
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


def urls_from_sitemap(location, timeout):
    """Yield post/page URLs from a sitemap or sitemap index."""
    text = read_text(location, timeout)
    root = ET.fromstring(text)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    if root.tag.endswith("sitemapindex"):
        # A Blogger sitemap.xml is an index: recurse into each sub-sitemap.
        for sm in root.findall("sm:sitemap", ns):
            loc = sm.findtext("sm:loc", namespaces=ns)
            if loc:
                yield from urls_from_sitemap(resolve(loc, location), timeout)
    else:
        for url in root.findall("sm:url", ns):
            loc = url.findtext("sm:loc", namespaces=ns)
            if loc:
                yield resolve(loc, location)


def check_url(url, timeout):
    """Return (status, length, description) for one URL."""
    try:
        html = read_text(url, timeout)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        return ("ERROR", 0, "fetch failed: %s" % exc)
    parser = DescriptionParser()
    try:
        parser.feed(html)
    except Exception as exc:  # malformed HTML should not kill the run
        return ("ERROR", 0, "parse failed: %s" % exc)
    if parser.description is None:
        return ("MISSING", 0, "")
    length = len(parser.description)
    status = "OK" if length <= MAX_LEN else "TOO LONG"
    return (status, length, parser.description)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check meta descriptions for Blogger URLs.")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--sitemap", help="sitemap XML file or URL (index supported)")
    group.add_argument("--urls", help="text file with one URL per line")
    ap.add_argument("--limit", type=int, default=0, help="check at most N URLs (0 = all)")
    ap.add_argument("--timeout", type=int, default=15, help="fetch timeout in seconds")
    args = ap.parse_args(argv)

    if args.sitemap:
        try:
            urls = list(urls_from_sitemap(args.sitemap, args.timeout))
        except (OSError, urllib.error.URLError, ET.ParseError, ValueError) as exc:
            print("error: cannot read sitemap: %s" % exc, file=sys.stderr)
            return 2
    else:
        with open(args.urls, "r", encoding="utf-8") as fh:
            urls = [line.strip() for line in fh if line.strip()]
    if args.limit:
        urls = urls[: args.limit]

    counts = {"OK": 0, "TOO LONG": 0, "MISSING": 0, "ERROR": 0}
    print("%-8s %-6s %s" % ("STATUS", "CHARS", "URL"))
    print("-" * 100)
    for url in urls:
        status, length, desc = check_url(url, args.timeout)
        counts[status] += 1
        extra = ""
        if status == "TOO LONG":
            extra = "  (over by %d chars)" % (length - MAX_LEN)
        elif status == "ERROR":
            extra = "  (%s)" % desc
        print("%-8s %-6s %s%s" % (status, length if status in ("OK", "TOO LONG") else "-", url, extra))
    print("-" * 100)
    print("checked %d URLs: %s" % (
        len(urls),
        ", ".join("%d %s" % (counts[k], k.lower()) for k in ("OK", "TOO LONG", "MISSING", "ERROR")),
    ))
    return 0 if counts["TOO LONG"] + counts["MISSING"] + counts["ERROR"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
