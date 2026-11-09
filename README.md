# SPORTYNOVA Global Sports Feed

A GitHub Actions starter that refreshes a normalized sports JSON feed every 30 minutes.

## What it does
- Fetches event/scoreboard data from the public Kiwi Sports API (ESPN-based; cricket provider support is described by that project).
- Writes `data/sports.json`, `data/live.json`, `data/upcoming.json`, `data/sports-list.json`.
- Preserves a separate `data/streams.json` file for **authorized** HLS (`.m3u8`) and MPEG-DASH (`.mpd`) stream URLs that you own or are licensed to distribute.
- Runs on a 30-minute GitHub Actions schedule and can also be started manually.

## Important limitations
- Match metadata coverage is not literally every country, local league, or sport. It depends on the upstream provider.
- Match JSON does not mean a legal live video stream exists.
- This repository does not scrape paywalled streams, bypass DRM, or generate stream URLs. Add only authorized stream URLs to `config/streams.json`.
- GitHub scheduled workflows can be delayed and are not guaranteed to start at the exact minute.
- Public API availability, rate limits, terms, and coverage can change. Check the upstream project and its terms before deployment.

## Deploy
1. Create a **new public or private GitHub repository** named `sportynova-global-sports`.
2. Upload all files from this folder, preserving paths.
3. In GitHub: **Settings → Actions → General**, allow Actions if disabled.
4. Open **Actions → Update sports JSON → Run workflow** for the first run.
5. After the workflow completes, enable GitHub Pages (optional) from **Settings → Pages → Deploy from a branch → `main` / root** if you want public JSON URLs.
6. JSON files will be available at:
   - `https://YOUR-USERNAME.github.io/sportynova-global-sports/data/sports.json`
   - `https://YOUR-USERNAME.github.io/sportynova-global-sports/data/live.json`
   - `https://YOUR-USERNAME.github.io/sportynova-global-sports/data/upcoming.json`
   - `https://YOUR-USERNAME.github.io/sportynova-global-sports/data/streams.json`

## Stream format
Edit `config/streams.json`:
```json
[
  {
    "event_name": "Example match",
    "sport": "soccer",
    "country": "Example country",
    "stream_type": "hls",
    "url": "https://your-authorized-provider.example/live/index.m3u8",
    "provider": "Your licensed provider",
    "authorized": true
  },
  {
    "event_name": "Example match",
    "sport": "cricket",
    "country": "Example country",
    "stream_type": "dash",
    "url": "https://your-authorized-provider.example/live/manifest.mpd",
    "provider": "Your licensed provider",
    "authorized": true
  }
]
```
Only entries with `authorized: true` and valid `.m3u8`/`.mpd` URLs are exposed in the generated feed. For DRM-protected services, use the provider's official player/SDK and do not publish license keys.

## API source
The default source is the Kiwi Sports API project:
https://github.com/itsmakmirza/kiwi-sports
The script expects `/api/sports` and `/api/scoreboard?sport=...` endpoints. The public demo may enforce rate limits or change; inspect its README before relying on it in production.
