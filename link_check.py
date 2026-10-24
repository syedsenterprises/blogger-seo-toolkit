#!/usr/bin/env python3
"""link_check.py — internal-link report for exported Blogger HTML files.

Point it at a directory of exported post HTML files (Blogger: Settings >
Manage blog > Back up content, or any per-post HTML export) and it reports,
per file:

  * how many internal vs external links the post contains
  * every internal link target
  * internal links whose target file is NOT in the directory ("orphans":
    links that may 404 after an export, a slug change, or a deleted post)

This is deliberately a skeleton, not a crawler: it works on files you already
have, makes no network requests, and never follows links. Extend it by
plugging a real fetcher into fetch_map() if you want live checking.

Usage:
    python3 link_check.py --dir exports/ --domain example.com
    python3 link_check.py --dir exports/ --domain example.com --show-external

Standard library only.
"""

import argparse
import os
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse


class LinkParser(HTMLParser):
    """Collect href values from <a> tags."""

    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict((k.lower(), v) for k, v in attrs).get("href")
            if href:
                self.hrefs.append(href)


def classify(href, domain):
    """Return 'internal', 'external', or 'skip' (anchor / mailto / javascript)."""
    if href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return "skip"
    parsed = urlparse(href)
    if not parsed.netloc:
        return "internal"  # relative link: same site by definition
    host = parsed.netloc.lower()
    if host == domain.lower() or host.endswith("." + domain.lower()):
        return "internal"
    return "external"


def local_target(href):
    """Map an internal href to a probable local filename, or None."""
    parsed = urlparse(href)
    path = parsed.path.strip("/")
    if not path:
        return None
    return path.split("/")[-1] or None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Internal-link report for exported HTML files.")
    ap.add_argument("--dir", required=True, help="directory of exported HTML files")
    ap.add_argument("--domain", required=True, help="your blog's domain, e.g. example.com")
    ap.add_argument("--show-external", action="store_true", help="also list external links")
    args = ap.parse_args(argv)

    files = sorted(f for f in os.listdir(args.dir) if f.endswith((".html", ".htm")))
    if not files:
        print("error: no HTML files found in %s" % args.dir, file=sys.stderr)
        return 2
    known = set(files)

    total_internal = total_external = total_orphans = 0
    for name in files:
        path = os.path.join(args.dir, name)
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            parser = LinkParser()
            parser.feed(fh.read())
        internal, external, orphans = [], [], []
        for href in parser.hrefs:
            kind = classify(href, args.domain)
            if kind == "internal":
                internal.append(href)
                target = local_target(href)
                if target and target not in known and "." in target:
                    orphans.append(href)
            elif kind == "external":
                external.append(href)
        total_internal += len(internal)
        total_external += len(external)
        total_orphans += len(orphans)
        print("== %s: %d internal, %d external%s" % (
            name, len(internal), len(external),
            (", %d orphan(s)" % len(orphans)) if orphans else "",
        ))
        for href in internal:
            mark = "  [ORPHAN] " if href in orphans else "  "
            print("%s%s" % (mark, href))
        if args.show_external:
            for href in external:
                print("  (ext) %s" % href)
    print("-" * 70)
    print("%d files: %d internal links, %d external links, %d orphan(s)" % (
        len(files), total_internal, total_external, total_orphans))
    return 0


if __name__ == "__main__":
    sys.exit(main())
