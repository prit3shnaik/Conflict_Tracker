"""
Our own news aggregator -- no third-party conflict database, no API key.

Combines two sources:
  1. Direct RSS feeds from named Pakistani and Indian news outlets
     (full control over which sources count, including explicit Indian
     coverage, which was the whole point of moving away from GDELT/ACLED/SATP)
  2. Google News RSS search as a broader supplementary net, to catch
     coverage from outlets not in our curated list

Both are free, public, and require no signup or credentials.

IMPORTANT LIMITATION: RSS feeds -- from any publisher, and from Google News
-- only ever expose a rolling window of RECENT items (typically the last
few days to a few weeks). This is not something any aggregator design can
get around; it's how live feeds work. This script cannot retrieve articles
from 2020-2023 today. See README for options if deep historical coverage
is required (Wayback Machine snapshots, GDELT's BigQuery full archive, or
a permissioned pull from SATP).
"""

import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

REQUEST_DELAY_SECONDS = 1.0
USER_AGENT = "pak-conflict-tracker/1.0 (personal research project)"

# --- Curated direct feeds -----------------------------------------------
# name -> (feed url, country context)
# Verify/update these periodically -- outlets occasionally change RSS paths.
SOURCES = {
    "Dawn":              ("https://www.dawn.com/feeds/home", "Pakistan"),
    "Express Tribune":   ("https://tribune.com.pk/feed/home", "Pakistan"),
    "The News International": ("https://www.thenews.com.pk/rss/1/1", "Pakistan"),
    "The Nation (PK)":   ("https://www.nation.com.pk/rss/top-stories", "Pakistan"),
    "The Hindu":         ("https://www.thehindu.com/news/national/feeder/default.rss", "India"),
    "Hindustan Times":   ("https://www.hindustantimes.com/rss/india-news/rssfeed.xml", "India"),
}

GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"

KEYWORDS = [
    "unidentified gunmen",
    "unknown gunmen",
    "unidentified assailants",
    "unknown assailants",
]


def _matches_keywords(text):
    text_lower = (text or "").lower()
    return any(k in text_lower for k in KEYWORDS)


def _strip_html(text):
    return re.sub("<[^<]+?>", "", text or "").strip()


def _parse_pubdate(raw):
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def fetch_direct_feeds(require_pakistan_mention_for_country="India"):
    """
    Pull all curated feeds, keep only items whose title/description mention
    one of our keyword phrases. For non-Pakistani outlets (e.g. Indian
    papers, which cover many countries), also require "Pakistan" to appear,
    since otherwise we'd catch unrelated "unidentified gunmen" stories from
    elsewhere in the world.
    """
    results = []
    for source_name, (url, country) in SOURCES.items():
        try:
            resp = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as e:
            print(f"  WARNING: failed to fetch/parse feed for {source_name} ({url}): {e}")
            continue

        items = root.findall(".//item")
        matched = 0
        for item in items:
            title = (item.findtext("title") or "").strip()
            description = _strip_html(item.findtext("description") or "")
            link = (item.findtext("link") or "").strip()
            pub_date = _parse_pubdate(item.findtext("pubDate"))

            combined_text = f"{title} {description}"
            if not _matches_keywords(combined_text):
                continue
            if country == require_pakistan_mention_for_country and "pakistan" not in combined_text.lower():
                continue

            results.append({
                "event_id": link,
                "date": pub_date,
                "name": None,
                "location": None,
                "title": title,
                "url": link,
                "domain": source_name,
                "source_country": country,
                "language": "en",
            })
            matched += 1

        print(f"  {source_name}: {matched} matching item(s) out of {len(items)} in feed")
        time.sleep(REQUEST_DELAY_SECONDS)

    return results


def fetch_google_news(extra_query_terms="Pakistan", region_hl="en-PK", region_gl="PK", region_ceid="PK:en"):
    """
    Broader supplementary search via Google News RSS. No API key needed.
    Returns items from any outlet Google has indexed, not just our curated list.
    """
    query = f'({" OR ".join(chr(34)+k+chr(34) for k in KEYWORDS)}) {extra_query_terms}'
    params = {
        "q": query,
        "hl": region_hl,
        "gl": region_gl,
        "ceid": region_ceid,
    }
    try:
        resp = requests.get(GOOGLE_NEWS_RSS_URL, params=params, timeout=20,
                             headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        print(f"  WARNING: Google News RSS fetch failed: {e}")
        return []

    results = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = _parse_pubdate(item.findtext("pubDate"))
        source_el = item.find("source")
        domain = source_el.text.strip() if source_el is not None and source_el.text else None

        results.append({
            "event_id": link,
            "date": pub_date,
            "name": None,
            "location": None,
            "title": title,
            "url": link,
            "domain": domain,
            "source_country": None,  # unknown mix from Google's index
            "language": "en",
        })

    print(f"  Google News RSS: {len(results)} matching item(s)")
    return results


def fetch_all():
    """Run direct RSS feeds, Google News, and configured Telegram channels, merged."""
    print("Fetching curated direct feeds (Pakistani + Indian outlets)...")
    direct = fetch_direct_feeds()

    print("Fetching Google News RSS as a supplementary net...")
    google = fetch_google_news()

    print("Fetching configured Telegram channels (if any)...")
    try:
        from telegram_client import fetch_all_channels
        telegram = fetch_all_channels()
    except Exception as e:
        print(f"  WARNING: Telegram fetch step failed: {e}")
        telegram = []

    # de-dupe by URL. Order matters for which version "wins" on conflict:
    # google first, then telegram, then direct feeds last (most trusted
    # source_country labeling), so direct-feed data overwrites duplicates.
    by_url = {}
    for item in google + telegram + direct:
        if item.get("event_id"):
            by_url[item["event_id"]] = item

    return list(by_url.values())
