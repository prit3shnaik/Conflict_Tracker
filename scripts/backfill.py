"""
One-time (or occasional) backfill script.

Pulls ACLED events for Pakistan from a given start date up to today, splits
them into two datasets:
  1. data/unknown_gunmen_civilians.json  -> civilian victims, unidentified actor
  2. data/unknown_gunmen_terrorists.json -> militant/terrorist-linked actors killed
                                             by unidentified/unknown gunmen

Run this locally (not via GitHub Actions) whenever you need to (re)seed history:
    ACLED_EMAIL=you@example.com ACLED_ACCESS_KEY=xxxx python scripts/backfill.py

Adjust BACKFILL_START_DATE as needed. Pagination + delays are handled in
acled_client.py to stay within ACLED's rate limits.
"""

import json
import os
from datetime import date

from acled_client import fetch_events, normalize_event

BACKFILL_START_DATE = "2020-01-01"
TODAY = date.today().isoformat()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Known unidentified-actor labels ACLED uses for Pakistan events.
# Both actor1 and actor2 fields are checked against these.
UNKNOWN_ACTOR_MARKERS = [
    "Unidentified Armed Group",
    "Unidentified Gunmen",
    "Unknown",
]

# Militant/terrorist group name fragments used to route an event into the
# "terrorists killed" bucket instead of the "civilians killed" bucket.
# Extend this list as needed -- it is intentionally conservative.
MILITANT_MARKERS = [
    "TTP", "Tehreek-i-Taliban", "Taliban",
    "Baloch Liberation", "BLA", "BLF", "BRAS",
    "Islamic State", "ISIS", "ISKP",
    "Lashkar", "Jaish", "Al Qaida", "Al-Qaeda",
    "Militia", "Militant",
]


def is_unknown_actor(raw_event):
    text = " ".join(filter(None, [raw_event.get("actor1", ""), raw_event.get("actor2", "")]))
    return any(marker.lower() in text.lower() for marker in UNKNOWN_ACTOR_MARKERS)


def victim_is_militant(raw_event):
    # Heuristic: check actor2 (the target/victim side) and notes for militant group names.
    text = " ".join(filter(None, [
        raw_event.get("actor2", ""),
        raw_event.get("assoc_actor_2", ""),
        raw_event.get("notes", ""),
    ]))
    return any(marker.lower() in text.lower() for marker in MILITANT_MARKERS)


def load_existing(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"description": "", "last_updated": None, "events": []}


def save(path, dataset):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)


def main():
    print(f"Fetching ACLED events for Pakistan, {BACKFILL_START_DATE} -> {TODAY} ...")
    raw_events = fetch_events(
        country="Pakistan",
        start_date=BACKFILL_START_DATE,
        end_date=TODAY,
        event_type="Violence against civilians",
    )
    print(f"Total raw events fetched: {len(raw_events)}")

    civilians = []
    terrorists = []

    for raw in raw_events:
        if not is_unknown_actor(raw):
            continue  # we only want unidentified/unknown-gunmen cases

        normalized = normalize_event(raw)
        if victim_is_militant(raw):
            terrorists.append(normalized)
        else:
            civilians.append(normalized)

    civilians_path = os.path.join(DATA_DIR, "unknown_gunmen_civilians.json")
    terrorists_path = os.path.join(DATA_DIR, "unknown_gunmen_terrorists.json")

    civilians_dataset = {
        "description": "Civilians killed by unidentified/unknown gunmen in Pakistan, sourced from ACLED.",
        "source": "ACLED (acleddata.com)",
        "last_updated": TODAY,
        "events": civilians,
    }
    terrorists_dataset = {
        "description": "Suspected militants/terrorists killed by unidentified/unknown gunmen in Pakistan, sourced from ACLED. Classification is heuristic (actor-name matching) -- verify before citing.",
        "source": "ACLED (acleddata.com)",
        "last_updated": TODAY,
        "events": terrorists,
    }

    save(civilians_path, civilians_dataset)
    save(terrorists_path, terrorists_dataset)

    print(f"Saved {len(civilians)} civilian-victim events -> {civilians_path}")
    print(f"Saved {len(terrorists)} militant-victim events -> {terrorists_path}")


if __name__ == "__main__":
    main()
