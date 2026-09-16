#!/usr/bin/env python3
"""Count most-visited domains from a pipe-delimited browser history export.

Expected line format:  URL|Title|YYYY-MM-DD HH:MM:SS
Usage:                 python history_stats.py history.csv [top_n]
"""

import collections
import sys
from datetime import datetime
from urllib.parse import urlparse

try:
    import tldextract
    _extract = tldextract.TLDExtract(suffix_list_urls=())  # offline, bundled list
except ImportError:
    _extract = None

# Genuine rebrands only — there's no algorithmic way to know these.
ALIASES = {"twitter.com": "x.com"}

TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M")


def registered_domain(url):
    """Return the registered domain, or None if this isn't a real web page."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None                      # chrome://, about:, file://, extensions
    host = parsed.netloc.lower().split(":")[0]
    if not host or host in ("localhost", "127.0.0.1", "[::1]"):
        return None

    if _extract:
        ext = _extract(host)
        host = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
    else:
        host = host.removeprefix("www.")  # crude fallback

    return ALIASES.get(host, host) or None


def parse_time(stamp):
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(stamp, fmt)
        except ValueError:
            continue
    return None


def main(path, top_n=40):
    counts = collections.Counter()
    by_hour = collections.Counter()
    by_weekday = collections.Counter()
    seen = set()

    total_lines = skipped_malformed = skipped_scheme = skipped_dupe = 0
    bad_timestamps = 0

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            total_lines += 1

            parts = line.split("|")
            if len(parts) < 3:
                skipped_malformed += 1
                continue

            url, stamp = parts[0].strip(), parts[-1].strip()

            host = registered_domain(url)
            if not host:
                skipped_scheme += 1
                continue

            # Same host at the same second = redirect chain, not two visits.
            if (host, stamp) in seen:
                skipped_dupe += 1
                continue
            seen.add((host, stamp))

            counts[host] += 1

            when = parse_time(stamp)
            if when:
                by_hour[when.hour] += 1
                by_weekday[when.weekday()] += 1
            else:
                bad_timestamps += 1

    if not counts:
        print("No usable rows found — check the delimiter and column order.")
        return

    total = sum(counts.values())
    ranked = counts.most_common()

    print(f"{total:,} visits across {len(counts):,} domains\n")

    width = max(len(h) for h, _ in ranked[:top_n])
    for host, n in ranked[:top_n]:
        bar = "#" * (n * 30 // ranked[0][1])
        print(f"{n:7,}  {100 * n / total:5.1f}%  {host:<{width}}  {bar}")

    tail = ranked[top_n:]
    if tail:
        tail_visits = sum(n for _, n in tail)
        print(f"\n… plus {len(tail):,} more domains "
              f"({tail_visits:,} visits, {100 * tail_visits / total:.1f}%), "
              f"{sum(1 for _, n in tail if n == 1):,} of them visited once")

    if by_hour:
        peak = max(by_hour.values())
        print("\nVisits by hour")
        for h in range(24):
            n = by_hour[h]
            print(f"  {h:02d}  {'#' * (n * 40 // peak):<40} {n:,}")

    if by_weekday:
        peak = max(by_weekday.values())
        print("\nVisits by weekday")
        for i, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            n = by_weekday[i]
            print(f"  {name} {'#' * (n * 40 // peak):<40} {n:,}")

    print(f"\nSkipped: {skipped_malformed:,} malformed, "
          f"{skipped_scheme:,} non-web, {skipped_dupe:,} redirect duplicates")
    if bad_timestamps:
        print(f"Warning: {bad_timestamps:,} unparseable timestamps "
              f"(not counted in the hour/weekday charts)")
    if total_lines and skipped_malformed / total_lines > 0.01:
        print("Warning: >1% of lines malformed — the delimiter assumption may be wrong.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 40)
