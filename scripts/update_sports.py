import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ROOT = Path(__file__).resolve().parents[1]
API_BASE = os.getenv("SPORTS_API_BASE", "https://kiwi-sports.mak2st.workers.dev").rstrip("/")
USER_AGENT = "SPORTYNOVA-Global-Sports/1.0 (+https://github.com/)"
TIMEOUT = 25

def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def get_json(url):
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()

def normalize(item, sport):
    if not isinstance(item, dict):
        return None
    home = item.get("home") or {}
    away = item.get("away") or {}
    status = str(item.get("status") or "unknown").lower()
    if status in ("ongoing", "live", "in progress", "in_progress"):
        status = "live"
    elif status in ("done", "finished", "final", "completed"):
        status = "finished"
    elif status in ("upcoming", "scheduled", "pre"):
        status = "upcoming"
    return {
        "id": str(item.get("id") or item.get("eventId") or ""),
        "sport": sport,
        "league": item.get("league") or item.get("competition") or "",
        "country": item.get("country") or "",
        "home": {"id": str(home.get("id") or ""), "name": home.get("name") or item.get("homeTeam") or ""},
        "away": {"id": str(away.get("id") or ""), "name": away.get("name") or item.get("awayTeam") or ""},
        "start_time": item.get("date") or item.get("startTime") or item.get("timestamp"),
        "status": status,
        "status_detail": item.get("statusDetail") or item.get("status_detail") or "",
        "score": item.get("score") or item.get("scores"),
        "venue": item.get("venue") or "",
        "source": "Kiwi Sports API",
        "watch_links": []
    }

def extract_matches(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("matches", "events", "data", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []

def valid_stream(entry):
    if not isinstance(entry, dict) or entry.get("authorized") is not True:
        return False
    url = str(entry.get("url") or "")
    kind = str(entry.get("stream_type") or "").lower()
    return url.startswith("https://") and (
        (kind == "hls" and ".m3u8" in url.lower()) or
        (kind in ("dash", "mpd") and ".mpd" in url.lower())
    )

def attach_streams(matches, streams):
    clean = [s for s in streams if valid_stream(s)]
    for match in matches:
        for stream in clean:
            same_sport = not stream.get("sport") or stream.get("sport","").lower() == match["sport"].lower()
            target = (stream.get("event_name") or "").strip().lower()
            haystack = (match["home"]["name"] + " vs " + match["away"]["name"] + " " + match["league"]).lower()
            if same_sport and target and (target in haystack or haystack in target):
                match["watch_links"].append({
                    "type": stream.get("stream_type"),
                    "url": stream.get("url"),
                    "provider": stream.get("provider") or "Authorized provider"
                })
    return matches

def main():
    sports = read_json(ROOT / "config/sports.json", [])
    streams = read_json(ROOT / "config/streams.json", [])
    all_matches = []
    errors = []
    def fetch(sport):
        url = f"{API_BASE}/api/scoreboard?sport={sport}"
        payload = get_json(url)
        raw = extract_matches(payload)
        return sport, [normalize(x, sport) for x in raw]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch, sport): sport for sport in sports}
        for future in as_completed(futures):
            sport = futures[future]
            try:
                _, rows = future.result()
                all_matches.extend(x for x in rows if x)
            except Exception as exc:
                errors.append({"sport": sport, "error": str(exc)})
    # Deduplicate by provider ID + sport.
    seen, deduped = set(), []
    for match in all_matches:
        key = (match["sport"], match["id"] or json.dumps(match, sort_keys=True))
        if key not in seen:
            seen.add(key)
            deduped.append(match)
    deduped = attach_streams(deduped, streams)
    now = datetime.now(timezone.utc).isoformat()
    live = [m for m in deduped if m["status"] == "live"]
    upcoming = [m for m in deduped if m["status"] == "upcoming"]
    meta = {"updated_at": now, "source": API_BASE, "count": len(deduped),
            "sports_requested": sports, "fetch_errors": errors,
            "notice": "Coverage depends on upstream provider; stream links appear only when manually supplied as authorized."}
    outputs = {
        "sports.json": {**meta, "matches": deduped},
        "live.json": {**meta, "count": len(live), "matches": live},
        "upcoming.json": {**meta, "count": len(upcoming), "matches": upcoming},
        "streams.json": {"updated_at": now, "count": sum(len(m["watch_links"]) for m in deduped),
                         "matches": [{"id":m["id"],"sport":m["sport"],"home":m["home"],"away":m["away"],"watch_links":m["watch_links"]} for m in deduped if m["watch_links"]]}
    }
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    for name, content in outputs.items():
        (data_dir / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {len(deduped)} events; live={len(live)} upcoming={len(upcoming)} errors={len(errors)}")
    if not deduped and errors:
        print("WARNING: no events returned and provider requests failed.", file=sys.stderr)

if __name__ == "__main__":
    main()
