"""
Daily/periodic incremental update script, run by GitHub Actions.

Fetches only new events since the last recorded date in each dataset,
de-duplicates by ACLED's event_id_cnty, and appends.

This intentionally reuses the same classification logic as backfill.py.
"""

import json
import os
from datetime import date, timedelta

from acled_client import fetch_events, normalize_event
from backfill import (
    is_unknown_actor,
    victim_is_militant,
    MILITANT_MARKERS,
    UNKNOWN_ACTOR_MARKERS,
)

TODAY = date.today().isoformat()
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

CIVILIANS_PATH = os.path.join(DATA_DIR, "unknown_gunmen_civilians.json")
TERRORISTS_PATH = os.path.join(DATA_DIR, "unknown_gunmen_terrorists.json")

# Overlap window: re-check the last N days too, since ACLED sometimes revises
# or adds records for recent dates after initial publication.
OVERLAP_DAYS = 10


def load(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"description": "", "source": "ACLED (acleddata.com)", "last_updated": None, "events": []}


def save(path, dataset):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)


def determine_fetch_start(dataset):
    if dataset.get("last_updated"):
        last = date.fromisoformat(dataset["last_updated"])
        return (last - timedelta(days=OVERLAP_DAYS)).isoformat()
    # No prior data -- default to a reasonably recent window rather than
    # re-pulling all history (run backfill.py separately for that).
    return (date.today() - timedelta(days=OVERLAP_DAYS)).isoformat()


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

    start_date = min(
        determine_fetch_start(civilians_dataset),
        determine_fetch_start(terrorists_dataset),
    )

    print(f"Fetching ACLED events for Pakistan, {start_date} -> {TODAY} ...")
    raw_events = fetch_events(
        country="Pakistan",
        start_date=start_date,
        end_date=TODAY,
        event_type="Violence against civilians",
    )
    print(f"Total raw events fetched in window: {len(raw_events)}")

    new_civilians = []
    new_terrorists = []

    for raw in raw_events:
        if not is_unknown_actor(raw):
            continue
        normalized = normalize_event(raw)
        if victim_is_militant(raw):
            new_terrorists.append(normalized)
        else:
            new_civilians.append(normalized)

    civilians_dataset["events"], added_c = merge(civilians_dataset["events"], new_civilians)
    terrorists_dataset["events"], added_t = merge(terrorists_dataset["events"], new_terrorists)

    civilians_dataset["last_updated"] = TODAY
    civilians_dataset.setdefault("description", "Civilians killed by unidentified/unknown gunmen in Pakistan, sourced from ACLED.")
    civilians_dataset.setdefault("source", "ACLED (acleddata.com)")

    terrorists_dataset["last_updated"] = TODAY
    terrorists_dataset.setdefault("description", "Suspected militants/terrorists killed by unidentified/unknown gunmen in Pakistan, sourced from ACLED.")
    terrorists_dataset.setdefault("source", "ACLED (acleddata.com)")

    save(CIVILIANS_PATH, civilians_dataset)
    save(TERRORISTS_PATH, terrorists_dataset)

    print(f"Added {added_c} new civilian-victim events (total: {len(civilians_dataset['events'])})")
    print(f"Added {added_t} new militant-victim events (total: {len(terrorists_dataset['events'])})")

    # Write a small run-log for transparency / debugging on the site if wanted
    log_path = os.path.join(DATA_DIR, "last_run.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_date": TODAY,
            "fetch_window_start": start_date,
            "added_civilians": added_c,
            "added_terrorists": added_t,
        }, f, indent=2)


if __name__ == "__main__":
    main()
