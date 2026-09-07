"""
Public Telegram channel monitor -- no bot token, no API key, no login.

Uses Telegram's own server-rendered web preview at https://t.me/s/<channel>,
which is publicly exposed for every public channel (it's the same page
Telegram serves to search engine crawlers for link previews). This is a
well-established, no-auth OSINT technique.

IMPORTANT: only add verified, legitimate channels here -- established news
outlets' own official channels. Do not add militant-affiliated or unverified
channels. To verify a channel before adding it:
  1. Find the outlet's official Telegram link (usually in their site footer
     or "follow us" section)
  2. Open https://t.me/s/<username> in a browser and confirm it shows real,
     recognizable posts from that outlet
  3. Only then add it to CHANNELS below

This file ships with an EMPTY channel list by design -- fill it in with
usernames you've personally verified.
"""

import re
import time
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup

REQUEST_DELAY_SECONDS = 1.5
USER_AGENT = "Mozilla/5.0 (compatible; pak-conflict-tracker/1.0; +personal research project)"

# username -> country/source label. Fill in only channels you've verified
# belong to a legitimate news outlet. Example (verify before uncommenting):
# CHANNELS = {
#     "dawn_com": "Pakistan",
#     "geonews_official": "Pakistan",
#     "ANI_Digital": "India",
# }
CHANNELS = {
    # "channel_username": "Pakistan" | "India",
}

KEYWORDS = [
    "unidentified gunmen",
    "unknown gunmen",
    "unidentified assailants",
    "unknown assailants",
    "نامعلوم مسلح",  # "unidentified armed" -- common Urdu phrasing, optional
]


def _matches_keywords(text):
    text_lower = (text or "").lower()
    return any(k.lower() in text_lower for k in KEYWORDS)


def fetch_channel_posts(username, country_label):
    """Fetch recent public posts from a single Telegram channel."""
    url = f"https://t.me/s/{username}"
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except Exception as e:
        print(f"  WARNING: failed to fetch Telegram channel '{username}': {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    message_blocks = soup.select("div.tgme_widget_message")

    results = []
    for block in message_blocks:
        text_el = block.select_one(".tgme_widget_message_text")
        text = text_el.get_text(" ", strip=True) if text_el else ""

        if not _matches_keywords(text):
            continue
        if country_label != "Pakistan" and "pakistan" not in text.lower():
            # For non-Pakistani channels, require an explicit Pakistan mention
            continue

        # Post link + date
        link_el = block.select_one("a.tgme_widget_message_date")
        post_url = link_el["href"] if link_el and link_el.has_attr("href") else url
        time_el = block.select_one("time")
        date_str = None
        if time_el and time_el.has_attr("datetime"):
            try:
                dt = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
                date_str = dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
            except ValueError:
                pass

        results.append({
            "event_id": post_url,
            "date": date_str,
            "name": None,
            "location": None,
            "title": text[:300],
            "url": post_url,
            "domain": f"Telegram: @{username}",
            "source_country": country_label,
            "language": None,
        })

    print(f"  @{username}: {len(results)} matching post(s) out of {len(message_blocks)} fetched")
    return results


def fetch_all_channels():
    if not CHANNELS:
        print("  No Telegram channels configured (CHANNELS is empty) -- skipping.")
        return []

    all_results = []
    for username, country_label in CHANNELS.items():
        all_results.extend(fetch_channel_posts(username, country_label))
        time.sleep(REQUEST_DELAY_SECONDS)

    return all_results
