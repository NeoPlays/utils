import json
import os
from datetime import datetime
from threading import Lock

DATA_FILE = os.environ.get("DATA_FILE", "/data/ips.json")

_lock = Lock()


def _load() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"config": {"ranges": []}, "ips": {}, "last_scan": None}
    with open(DATA_FILE) as f:
        data = json.load(f)
    # migrate old single-range format
    cfg = data.get("config", {})
    if "base" in cfg:
        ranges = [{"base": cfg["base"], "start": cfg.get("start", 1), "end": cfg.get("end", 254)}] if cfg.get("base") else []
        data["config"] = {"ranges": ranges}
    elif "ranges" not in cfg:
        data["config"] = {"ranges": []}
    return data


def _save(data: dict):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_all() -> dict:
    with _lock:
        return _load()


def get_config() -> dict:
    with _lock:
        return _load()["config"]


def save_config(ranges: list[dict]):
    with _lock:
        data = _load()
        data["config"] = {"ranges": ranges}
        _save(data)


def update_scan_results(results: dict[str, bool]):
    with _lock:
        data = _load()
        for ip, is_up in results.items():
            entry = data["ips"].get(ip, {"comment": "", "label": "unknown"})
            entry["reachable"] = is_up
            entry["last_seen"] = datetime.utcnow().isoformat() + "Z" if is_up else entry.get("last_seen")
            if not is_up:
                entry["label"] = "free"
                entry["comment"] = ""
            data["ips"][ip] = entry
        data["last_scan"] = datetime.utcnow().isoformat() + "Z"
        _save(data)


def update_ip_meta(ip: str, comment: str | None, label: str | None):
    with _lock:
        data = _load()
        entry = data["ips"].get(ip, {"reachable": None, "last_seen": None})
        if comment is not None:
            entry["comment"] = comment
        if label is not None:
            entry["label"] = label
        data["ips"][ip] = entry
        _save(data)
