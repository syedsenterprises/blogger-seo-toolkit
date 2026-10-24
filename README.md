<!-- GitHub topics: blogger, seo-tools, sitemap, meta-description, internal-links, python-cli, blogging-tools -->

# 🔍 Blogger SEO Toolkit

Three small, dependency-free Python tools for Blogger blogs. No pip installs,
no API keys — just `python3`.

| Tool | What it does |
| ---- | ------------ |
| `meta_check.py` | Checks every post's `<meta name="description">` against Blogger's 150-character search-description limit |
| `sitemap_urls.py` | Lists URLs from a Blogger sitemap (follows the sitemap index by default) |
| `link_check.py` | Reports internal vs external links per exported HTML file, and flags orphan links |

## Install

```bash
git clone https://github.com/YOUR-USERNAME/blogger-seo-toolkit.git
cd blogger-seo-toolkit
# That's it. Python 3.8+ only, standard library only.
python3 --version
```

## 1. meta_check.py — meta descriptions

Blogger's search-description field is capped at **150 characters**. Anything
longer gets truncated in search results; anything missing leaves Google to
pick its own snippet.

```bash
# From a sitemap (local file or live URL — index sitemaps are followed)
python3 meta_check.py --sitemap https://yourblog.blogspot.com/sitemap.xml

# From a plain list of URLs, one per line
python3 meta_check.py --urls urls.txt

# Check only the first 20 URLs, 10-second fetch timeout
python3 meta_check.py --sitemap sitemap.xml --limit 20 --timeout 10
```

Statuses: `OK` (≤ 150 chars), `TOO LONG` (> 150, with the overage),
`MISSING` (no description tag), `ERROR` (fetch/parse failed). The exit code
is 1 when any post has a problem, so it works in a CI check or a cron job.

## 2. sitemap_urls.py — list sitemap URLs

```bash
# All post/page URLs (follows the index into sub-sitemaps)
python3 sitemap_urls.py https://yourblog.blogspot.com/sitemap.xml

# Only the sub-sitemap entries in an index
python3 sitemap_urls.py sitemap.xml --no-follow

# Only URLs from 2026, or just the count
python3 sitemap_urls.py sitemap.xml --filter /2026/
python3 sitemap_urls.py sitemap.xml --count
```

Pipe it into the other tools, e.g.:

```bash
python3 sitemap_urls.py sitemap.xml > urls.txt
python3 meta_check.py --urls urls.txt
```

## 3. link_check.py — internal links in exported HTML

Export your posts (Blogger → Settings → Manage blog → Back up content, or any
per-post HTML export), then:

```bash
python3 link_check.py --dir exports/ --domain yourblog.com

# Also list the external links, not just counts
python3 link_check.py --dir exports/ --domain yourblog.com --show-external
```

An **orphan** is an internal link whose target file is not in the directory —
the usual sign of a deleted post or a changed slug. This tool makes no network
requests: it is a skeleton you can extend with a live fetcher if you want
real 404 checking.

## Worked example (real output, from `examples/`)

The `examples/` folder has a small sitemap index plus three fixture posts:
one good description, one too long, one missing; plus internal, external,
and one orphan link. Run from the repo root:

```bash
$ python3 sitemap_urls.py examples/sitemap.xml
examples/post-1.html
examples/post-2.html
examples/post-3.html

$ python3 meta_check.py --sitemap examples/sitemap.xml
STATUS   CHARS  URL
----------------------------------------------------------------------------------------------------
OK       111    examples/post-1.html
TOO LONG 221    examples/post-2.html  (over by 71 chars)
MISSING  -      examples/post-3.html
----------------------------------------------------------------------------------------------------
checked 3 URLs: 1 ok, 1 too long, 1 missing, 0 error

$ python3 link_check.py --dir examples --domain example.com
== post-1.html: 3 internal, 1 external, 1 orphan(s)
  post-2.html
  https://example.com/post-3.html
  [ORPHAN] post-99.html
== post-2.html: 1 internal, 0 external
  post-1.html
== post-3.html: 1 internal, 0 external
  post-1.html
----------------------------------------------------------------------
3 files: 5 internal links, 1 external links, 1 orphan(s)
```

## Notes & limits

- Local sitemaps resolve relative locations against the sitemap file itself;
  run from the repo root or pass an absolute sitemap path.
- `meta_check.py` fetches live pages with a plain `urllib` request; sites
  that block bots may return errors — treat `ERROR` as "check by hand", not
  as a content problem.
- `link_check.py` checks files on disk only. It cannot see posts that were
  never exported.

## License

MIT — see [LICENSE](LICENSE).
