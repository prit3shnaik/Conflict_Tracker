# Pakistan Conflict & Incident Record

A static site + daily-updating dataset tracking:

1. **India–Pakistan conflict history, 1947→present** — hand-curated, static (`data/india_pakistan_history.json`)
2. **News coverage of civilians killed by unidentified/unknown gunmen in Pakistan** — auto-updated, our own aggregator (`data/unknown_gunmen_civilians.json`)
3. **News coverage of suspected militants/terrorists killed by unidentified/unknown gunmen** — auto-updated, our own aggregator (`data/unknown_gunmen_terrorists.json`)

The site (`index.html`) reads these JSON files directly — no backend needed.

## Data source: our own RSS aggregator (no signup, no API key, no third party)

This project does **not** depend on ACLED, GDELT, SATP, or any other third-party conflict database. Instead, `scripts/news_client.py` pulls directly from named news outlets:

**Pakistani outlets:** Dawn, Express Tribune, The News International, The Nation
**Indian outlets:** The Hindu, Hindustan Times
**Supplementary net:** Google News RSS search (catches coverage from outlets outside the curated list)

All of these are free, public RSS feeds — no registration, no key, no password. You fully control which sources count by editing the `SOURCES` dict in `scripts/news_client.py`.

### Why this instead of a third-party database?

- **ACLED** now requires an account and OAuth login with your account password — more friction, and storing a real password as a secret is less clean than an API key.
- **GDELT** has no auth, but its public API only indexes a rolling ~3-month window and gives you no control over which specific outlets are represented.
- **SATP** (South Asia Terrorism Portal, India-based) explicitly prohibits reproducing their content without prior consent — their disclaimer states "No matter contained in this website may be reproduced or copied by any means without prior consent." Scraping it into this dataset would violate that.
- Building our own means: no credentials, no third-party terms-of-use conflicts, and explicit control over including both Pakistani and Indian sourcing side by side.

### The unavoidable limitation: RSS = recent items only

This is true of any live RSS feed, from any publisher, or from Google News — they only expose a rolling window of recent items (typically days to a few weeks, publisher-dependent). This is not a workaround-able limitation; it's how RSS works.

**What this means in practice:**
- The `unknown_gunmen_*` datasets will only ever contain recent coverage at first backfill, and will grow forward in time as the daily Action runs.
- They will not reach back to 2020 on their own.

**If you need full 2020→present depth**, realistic options are:
1. **GDELT's BigQuery export** — free tier available, covers the full historical archive, but requires a Google Cloud account and basic SQL.
2. **The Wayback Machine** — manually pull archived snapshots of Dawn/Tribune search-result pages from 2020–2023 and hand-extract matching headlines.
3. **Request permission from SATP** — email them (contact info on satp.org), explain the project, and ask to use their Pakistan fatality datasheets. If granted, this can be wired in separately.
4. **HRCP annual reports** — Human Rights Commission of Pakistan publishes yearly PDF reports with incident-level detail; these could be manually transcribed into a supplementary static JSON file (similar to how `india_pakistan_history.json` is handled).

The static `india_pakistan_history.json` file is unaffected by any of this — it's hand-curated and already covers 1947→present.

## Telegram and Twitter/X coverage

**Telegram: supported, opt-in, empty by default.** `scripts/telegram_client.py` reads public channels via Telegram's own `t.me/s/<channel>` web preview — no bot token, no API key, no login. This is the same page Telegram serves to search engines for link previews, and it's a well-established no-auth technique.

The channel list ships **empty on purpose**. To add a channel:
1. Confirm the outlet's official Telegram username — usually linked in their website footer or "follow us" section.
2. Open `https://t.me/s/<username>` in a browser and confirm it shows real, recognizable posts from that outlet.
3. Add it to the `CHANNELS` dict in `scripts/telegram_client.py`:
   ```python
   CHANNELS = {
       "dawn_com": "Pakistan",       # example -- verify before using
       "ani_digital": "India",       # example -- verify before using
   }
   ```

Only add verified, legitimate news-outlet channels — not militant-affiliated or unverified ones. This keeps the dataset clean and avoids amplifying unverified or propaganda content.

**Twitter/X: not included, and not realistically free anymore.** As of February 2026, X moved entirely to pay-per-use API pricing — there is no free tier for reading or searching posts at any volume (roughly $5 per 1,000 reads, full-archive search requires an Enterprise contract starting around $42,000/month). Free scraping workarounds like Nitter have become unreliable as X has cracked down on them. If you want X coverage later, the realistic path is budgeting for the official pay-per-use API — I can wire that in if you decide it's worth the cost, but it's not something this free pipeline includes by default.

## 1. Set up the repo

```bash
git init
git add .
git commit -m "Initial scaffold"
git remote add origin <your-repo-url>
git push -u origin main
```

## 2. No secrets needed

Nothing to add under Settings → Secrets and variables → Actions — the aggregator needs no authentication at all.

## 3. Run the one-time backfill

**Via GitHub Actions (works from mobile, no computer needed):**
Go to Actions → Backfill / manual refresh → Run workflow.

**Or locally:**
```bash
cd scripts
pip install -r requirements.txt
python backfill.py
cd ..
git add data/*.json
git commit -m "Backfill data"
git push
```

Check the two JSON files afterward. Classification of "civilian" vs "militant/terrorist" context is simple keyword matching on the headline, in `scripts/backfill.py` (`MILITANT_MARKERS` list) — adjust as needed, then re-run.

**If a feed looks empty:** outlets occasionally change their RSS paths. Check the run log (Actions tab → the run → expand "Run backfill") for any `WARNING: failed to fetch/parse feed for ...` lines, and update that outlet's URL in `scripts/news_client.py`'s `SOURCES` dict.

## 4. Enable the daily Action

`.github/workflows/update.yml` runs daily at 03:00 UTC and can also be triggered manually from the Actions tab. It re-runs the same aggregator, de-duplicates by article URL, and commits/pushes any new matches automatically.

No further setup needed — just make sure Actions are enabled (Settings → Actions → General → Allow all actions).

## 5. Turn on GitHub Pages

Settings → Pages → Source: Deploy from a branch → Branch: `main` / root

Your site will be live at `https://<your-username>.github.io/<repo-name>/` and will reflect new data automatically after every Actions run.

## Updating the historical (1947→) dataset

`data/india_pakistan_history.json` is not touched by the automated script — it's meant for major, discrete events (wars, standoffs, cross-border strikes). Edit it by hand when something new happens.

## Notes & limitations

- **Recent-window only** — see above. This is the main tradeoff of moving away from a third-party historical database.
- Records are articles, not incidents — the same real-world event is often covered by several outlets, so counts reflect news coverage volume, not a deduplicated incident count. The `name` field is always `null`; extracting victim names would require either manual reading or an added text-extraction step (e.g. an LLM call per headline) as a future enhancement.
- The militant-vs-civilian split is a heuristic based on headline keywords, not a verified legal classification. Treat it as a starting filter, not a definitive record — especially for anything you plan to publish or cite.
- Respect each outlet's terms of use. This aggregator stores headlines, links, dates, and source names only — not full article text — which is the same pattern used by legitimate news aggregators and search engines. If you ever want to display more than that (e.g. full snippets), check the individual outlet's terms first.
- RSS feed URLs can change. If a source stops returning results, check `scripts/news_client.py`'s `SOURCES` dict and update the URL.

## Repo structure

```
.
├── index.html                          # static site, reads data/*.json
├── data/
│   ├── india_pakistan_history.json     # static, manually maintained
│   ├── unknown_gunmen_civilians.json   # auto-updated
│   ├── unknown_gunmen_terrorists.json  # auto-updated
│   └── last_run.json                   # written by update.py each run (debug log)
├── scripts/
│   ├── news_client.py                  # our own RSS + Google News aggregator (calls telegram_client too)
│   ├── telegram_client.py              # public Telegram channel monitor (opt-in, empty by default)
│   ├── backfill.py                     # one-time/manual refresh
│   ├── update.py                       # daily incremental fetch (run by Actions)
│   └── requirements.txt
└── .github/workflows/
    ├── update.yml                      # scheduled daily Action
    └── backfill.yml                    # manually-triggered refresh Action
```
