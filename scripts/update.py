"""
Daily/periodic incremental update script, run by GitHub Actions.

Re-runs the same aggregator as backfill.py and appends anything not
already recorded (de-duplicated by article URL).
"""

import json
import os
from datetime import date

from news_client import fetch_all
from backfill import title_mentions_militant, dedupe

TODAY = date.today().isoformat()
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

CIVILIANS_PATH = os.path.join(DATA_DIR, "unknown_gunmen_civilians.json")
TERRORISTS_PATH = os.path.join(DATA_DIR, "unknown_gunmen_terrorists.json")


def load(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "description": "",
        "source": "Custom RSS aggregator (see scripts/news_client.py SOURCES list)",
        "last_updated": None,
        "events": [],
    }


def save(path, dataset):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)


def merge(existing_events, new_events):
    by_id = {e["event_id"]: e for e in existing_events if e.get("event_id")}
    added = 0
    for e in new_events:
        if e.get("event_id") and e["event_id"] not in by_id:
            by_id[e["event_id"]] = e
            added += 1
    merged = list(by_id.values())
    merged.sort(key=lambda e: e.get("date") or "")
    return merged, added


def main():
    civilians_dataset = load(CIVILIANS_PATH)
    terrorists_dataset = load(TERRORISTS_PATH)

    print("Running our own news aggregator (Pakistani + Indian outlets + Google News)...")
    articles = fetch_all()
    print(f"Total unique matching articles fetched this run: {len(articles)}")

    new_civilians = []
    new_terrorists = []

    for a in articles:
        if title_mentions_militant(a):
            new_terrorists.append(a)
        else:
            new_civilians.append(a)

    civilians_dataset["events"], added_c = merge(civilians_dataset["events"], new_civilians)
    terrorists_dataset["events"], added_t = merge(terrorists_dataset["events"], new_terrorists)

    civilians_dataset["last_updated"] = TODAY
    civilians_dataset.setdefault("description", "News coverage of civilians killed by unidentified/unknown gunmen in Pakistan, aggregated from named Pakistani and Indian outlet RSS feeds plus Google News.")
    civilians_dataset.setdefault("source", "Custom RSS aggregator (see scripts/news_client.py SOURCES list)")

    terrorists_dataset["last_updated"] = TODAY
    terrorists_dataset.setdefault("description", "News coverage of suspected militants/terrorists killed by unidentified/unknown gunmen in Pakistan, aggregated the same way.")
    terrorists_dataset.setdefault("source", "Custom RSS aggregator (see scripts/news_client.py SOURCES list)")

    save(CIVILIANS_PATH, civilians_dataset)
    save(TERRORISTS_PATH, terrorists_dataset)

    print(f"Added {added_c} new civilian-context articles (total: {len(civilians_dataset['events'])})")
    print(f"Added {added_t} new militant-context articles (total: {len(terrorists_dataset['events'])})")

    log_path = os.path.join(DATA_DIR, "last_run.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_date": TODAY,
            "added_civilians": added_c,
            "added_terrorists": added_t,
        }, f, indent=2)


if __name__ == "__main__":
    main()
