# Pakistan Conflict & Incident Record

A static site + daily-updating dataset tracking:

1. **India–Pakistan conflict history, 1947→present** — hand-curated, static (`data/india_pakistan_history.json`)
2. **Civilians killed by unidentified/unknown gunmen in Pakistan, 2020→present** — auto-updated from ACLED (`data/unknown_gunmen_civilians.json`)
3. **Suspected militants/terrorists killed by unidentified/unknown gunmen, 2020→present** — auto-updated from ACLED (`data/unknown_gunmen_terrorists.json`)

The site (`index.html`) reads these JSON files directly — no backend needed.

## 1. Get an ACLED API key (free)

1. Register at https://acleddata.com/register/ (academic / journalist / nonprofit registration gets higher rate limits — pick whichever applies to you).
2. Confirm your email. You'll get an **access key**; your **registered email** is the second credential the API needs.

## 2. Set up the repo

```bash
git init
git add .
git commit -m "Initial scaffold"
git remote add origin <your-repo-url>
git push -u origin main
```

## 3. Add GitHub Secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `ACLED_EMAIL` | the email you registered with ACLED |
| `ACLED_ACCESS_KEY` | your ACLED API key |

## 4. Run the one-time backfill (locally)

This seeds 2020→today into the two JSON files. Run it on your own machine (not in Actions), then commit and push the result.

```bash
cd scripts
pip install -r requirements.txt
ACLED_EMAIL="you@example.com" ACLED_ACCESS_KEY="xxxx" python backfill.py
cd ..
git add data/*.json
git commit -m "Backfill 2020-2026 data"
git push
```

Check the two JSON files afterward — the classification of "civilian" vs "militant/terrorist" target is done with simple keyword matching in `scripts/backfill.py` (`MILITANT_MARKERS` list). Adjust that list to better match how you want cases categorized, then re-run.

## 5. Enable the daily Action

The workflow at `.github/workflows/update.yml` is already set to run daily at 03:00 UTC and can also be triggered manually from the **Actions** tab (**Run workflow** button). It:

- Fetches new ACLED events since the last recorded date (with a 10-day overlap window, since ACLED sometimes revises recent entries)
- De-duplicates against existing records by ACLED's `event_id_cnty`
- Commits and pushes the updated JSON files automatically

No further action needed once secrets are set — just make sure Actions are enabled for the repo (**Settings → Actions → General → Allow all actions**).

## 6. Turn on GitHub Pages

**Settings → Pages → Source: Deploy from a branch → Branch: `main` / root**

Your site will be live at `https://<your-username>.github.io/<repo-name>/` within a minute or two, and will reflect new data automatically after every Actions run (GitHub Pages rebuilds on push).

## Updating the historical (1947→) dataset

`data/india_pakistan_history.json` is **not** touched by the automated script — it's meant for major, discrete events (wars, standoffs, cross-border strikes), which don't need daily polling. Edit it by hand when something new happens.

## Notes & limitations

- ACLED logs **incidents**, not always **named victims** — the `name` field in the civilian/militant datasets will typically be `null` unless a name happens to appear in ACLED's notes field. If you need named-victim records, that requires manual research/cross-referencing against news reports (HRCP annual reports and Dawn/CPJ archives are good starting points) — happy to help build a separate manually-curated file for that if useful.
- The militant-vs-civilian split is a **heuristic**, not a verified legal classification. Treat it as a starting filter, not a definitive record — especially for anything you plan to publish or cite.
- Respect ACLED's terms of use (https://acleddata.com/terms-of-use/) — attribution is required when displaying their data, which `index.html` and this README already include.

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
│   ├── acled_client.py                 # shared API fetch/normalize logic
│   ├── backfill.py                     # one-time historical seed (run locally)
│   ├── update.py                       # daily incremental fetch (run by Actions)
│   └── requirements.txt
└── .github/workflows/update.yml        # scheduled GitHub Action
```
