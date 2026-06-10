# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Build and start
docker compose up --build -d

# Rebuild after code changes
docker compose up --build -d

# Logs
docker compose logs -f

# Stop (data in ./data/ is preserved)
docker compose down
```

There is no test suite and no linter configured.

## Architecture

A single-container Docker app: **FastAPI backend** + **vanilla JS frontend**. No database — all state lives in `./data/ips.json` (mounted as a volume).

### Backend (`app/`)

- **`main.py`** — FastAPI app, all routes, and an APScheduler job that triggers `run_scan()` daily at 03:00 UTC. The scan logic is duplicated between `run_scan()` and `api_scan()` — keep them in sync.
- **`scanner.py`** — Builds a flat list of IPs from all configured ranges, pings them concurrently via `ThreadPoolExecutor` (50 workers). Requires `NET_RAW` capability (set in `docker-compose.yml`).
- **`storage.py`** — All JSON reads/writes go through a single `threading.Lock`. Contains a migration path: on load, old single-range config (`{base, start, end}`) is transparently converted to the current multi-range format (`{ranges: [...]}`).

### Config schema (`ips.json`)

```json
{
  "config": { "ranges": [{ "base": "192.168.1", "start": 1, "end": 254 }] },
  "ips": { "192.168.1.1": { "reachable": true, "last_seen": "...", "comment": "", "label": "server" } },
  "last_scan": "2024-01-01T03:00:00Z"
}
```

### Frontend (`static/index.html`)

Single self-contained file — all CSS, HTML, and JS inline. Communicates with the backend via:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/data` | Load all state |
| POST | `/api/config` | Save ranges `{ ranges: [{base, start, end}] }` |
| POST | `/api/scan` | Trigger immediate scan, returns full state |
| PATCH | `/api/ip/:ip` | Update label/comment for one IP (dashes used instead of dots in URL) |

The frontend holds the full data snapshot in `allData` and re-renders in-place on changes — no page reloads.
