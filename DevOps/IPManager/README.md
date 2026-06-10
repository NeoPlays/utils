# IP Manager

A local web app for managing and monitoring IP addresses on your network. Runs in Docker, stores data in a JSON file, and pings your configured IP range on a daily schedule or on demand.

## Features

- Concurrent ping scan across a configurable IP range
- Per-IP labels (`free`, `in-use`, `reserved`, `vm`, `device`, `server`)
- Inline comment editing
- Filter and search by IP, comment, status, or label
- Manual scan trigger button + automatic daily scan at 03:00 UTC
- Persistent storage in `./data/ips.json`

## Requirements

- Docker
- Docker Compose

## Setup

```bash
git clone <repo>
cd IPManager
docker compose up --build -d
```

Open **http://localhost:8080** in your browser.

## Usage

1. Enter your IP range in the toolbar (e.g. base `192.168.1`, from `1` to `254`) and click **Save range**
2. Click **Scan now** to run an immediate scan
3. Use the label dropdown and comment field on each row to annotate IPs
4. Use the filter bar to search by IP/comment or filter by status/label

## Configuration

| Setting | Default | Description |
|---|---|---|
| Port | `8080` | Change in `docker-compose.yml` |
| Auto-scan time | 03:00 UTC | Change `hour`/`minute` in `app/main.py` |
| Data file | `./data/ips.json` | Mounted volume, persists across restarts |
| Scan threads | 50 | Change `max_workers` in `app/scanner.py` |

## File Structure

```
IPManager/
├── app/
│   ├── main.py          # FastAPI app, routes, scheduler
│   ├── scanner.py       # Concurrent ping scanner
│   └── storage.py       # Thread-safe JSON storage
├── static/
│   └── index.html       # Frontend UI
├── data/                # Auto-created, holds ips.json
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Stopping

```bash
docker compose down
```

Data in `./data/` is preserved.
