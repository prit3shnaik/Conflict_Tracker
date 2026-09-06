"""
Shared helper for querying the ACLED API and normalizing records.

ACLED API docs: https://apidocs.acleddata.com/

Requires two environment variables (set as GitHub Actions secrets):
  ACLED_EMAIL        - the email you registered with ACLED
  ACLED_ACCESS_KEY   - your ACLED API key

Free registration: https://acleddata.com/register/
"""

import os
import time
import requests

BASE_URL = "https://api.acleddata.com/acled/read"
PAGE_SIZE = 500          # ACLED's typical max per page
REQUEST_DELAY_SECONDS = 1.5  # be polite / avoid rate limiting


def get_credentials():
    email = os.environ.get("ACLED_EMAIL")
    key = os.environ.get("ACLED_ACCESS_KEY")
    if not email or not key:
        raise RuntimeError(
            "Missing ACLED_EMAIL or ACLED_ACCESS_KEY environment variables. "
            "Set them as GitHub Actions secrets (or locally before running)."
        )
    return email, key


def fetch_events(country="Pakistan", start_date=None, end_date=None,
                  event_type=None, extra_params=None):
    """
    Fetch all matching ACLED events across pages, for a given date range.

    start_date / end_date: 'YYYY-MM-DD' strings. ACLED expects a pipe-joined
    range for the 'event_date' field with event_date_where='BETWEEN'.
    event_type: e.g. 'Violence against civilians'
    extra_params: dict of any additional ACLED query filters to merge in
                  (e.g. {'assoc_actor_1': 'Unidentified Armed Group (Pakistan)'})
    """
    email, key = get_credentials()

    params = {
        "email": email,
        "key": key,
        "country": country,
        "limit": PAGE_SIZE,
    }

    if start_date and end_date:
        params["event_date"] = f"{start_date}|{end_date}"
        params["event_date_where"] = "BETWEEN"

    if event_type:
        params["event_type"] = event_type

    if extra_params:
        params.update(extra_params)

    all_events = []
    page = 1

    while True:
        params["page"] = page
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        if not payload.get("success", False):
            raise RuntimeError(f"ACLED API returned an error: {payload}")

        batch = payload.get("data", [])
        if not batch:
            break

        all_events.extend(batch)
        print(f"  fetched page {page}: {len(batch)} records (total so far: {len(all_events)})")

        if len(batch) < PAGE_SIZE:
            break  # last page

        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    return all_events


def normalize_event(raw):
    """
    Map a raw ACLED record to our simplified schema.
    Note: ACLED logs INCIDENTS, not always individual victim names.
    'name' will usually be null unless mentioned in the notes field.
    """
    return {
        "event_id": raw.get("event_id_cnty"),
        "date": raw.get("event_date"),
        "name": None,  # ACLED does not reliably provide victim names
        "location": ", ".join(
            filter(None, [raw.get("location"), raw.get("admin2"), raw.get("admin1")])
        ),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "fatalities": raw.get("fatalities"),
        "actor1": raw.get("actor1"),
        "actor2": raw.get("actor2"),
        "assoc_actor_1": raw.get("assoc_actor_1"),
        "event_type": raw.get("event_type"),
        "sub_event_type": raw.get("sub_event_type"),
        "notes": raw.get("notes"),
        "source": raw.get("source"),
    }
