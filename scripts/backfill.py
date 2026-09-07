"""
One-time (or occasional) backfill script, using our own news aggregator
(scripts/news_client.py) -- direct Pakistani + Indian outlet RSS feeds,
plus Google News RSS as a broader net. No third-party conflict database,
no API key, no account.

IMPORTANT LIMITATION: RSS feeds only expose a rolling window of RECENT
items (days to a few weeks, publisher-dependent) -- this script cannot
reach back to 2020. Run it periodically (or rely on the daily Action) to
build up history GOING FORWARD from whenever you first run it. See
README for options if true 2020-> historical depth is required.

Run this locally, or via the backfill GitHub Action:
    python scripts/backfill.py
"""

import json
import os
from datetime import date

from news_client import fetch_all

TODAY = date.today().isoformat()
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Extend as needed -- used to route a hit into the "militant/terrorist" bucket
# based on words appearing in the headline/description text.
MILITANT_MARKERS = [
    "militant", "terrorist", "TTP", "Tehreek-i-Taliban", "Taliban",
    "Baloch Liberation", "BLA", "BLF", "BRAS",
    "Islamic State", "ISIS", "ISKP", "Lashkar", "Jaish",
    "Al Qaida", "Al-Qaeda", "insurgent",
]


def title_mentions_militant(article):
    text = (article.get("title") or "")
    return any(marker.lower() in text.lower() for marker in MILITANT_MARKERS)


def save(path, dataset):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)


def dedupe(events):
    by_id = {}
    for e in events:
        if e.get("event_id"):
            by_id[e["event_id"]] = e
    merged = list(by_id.values())
    merged.sort(key=lambda e: e.get("date") or "")
    return merged


def main():
    print("Running our own news aggregator (Pakistani + Indian outlets + Google News)...")
    articles = fetch_all()
    print(f"Total unique matching articles: {len(articles)}")

    civilians = []
    terrorists = []

    for a in articles:
        if title_mentions_militant(a):
            terrorists.append(a)
        else:
            civilians.append(a)

    civilians = dedupe(civilians)
    terrorists = dedupe(terrorists)

    civilians_path = os.path.join(DATA_DIR, "unknown_gunmen_civilians.json")
    terrorists_path = os.path.join(DATA_DIR, "unknown_gunmen_terrorists.json")

    civilians_dataset = {
        "description": "News coverage of civilians killed by unidentified/unknown gunmen in Pakistan, aggregated from named Pakistani and Indian outlet RSS feeds plus Google News RSS as a supplementary net. Each record is an article, not a verified incident.",
        "source": "Custom RSS aggregator (see scripts/news_client.py SOURCES list)",
        "last_updated": TODAY,
        "events": civilians,
    }
    terrorists_dataset = {
        "description": "News coverage of suspected militants/terrorists killed by unidentified/unknown gunmen in Pakistan, aggregated the same way. Classification is heuristic (headline keyword matching) -- verify before citing.",
        "source": "Custom RSS aggregator (see scripts/news_client.py SOURCES list)",
        "last_updated": TODAY,
        "events": terrorists,
    }

    save(civilians_path, civilians_dataset)
    save(terrorists_path, terrorists_dataset)

    print(f"Saved {len(civilians)} civilian-context articles -> {civilians_path}")
    print(f"Saved {len(terrorists)} militant-context articles -> {terrorists_path}")


if __name__ == "__main__":
    main()
