import glob
import json
import os
import time

import requests
from prometheus_client import Gauge, start_http_server

BEACON_NODE = os.environ.get("BEACON_NODE", "http://127.0.0.1:5545")
KEYS_DIR = os.environ.get("KEYS_DIR", "./keys")
CONSOLIDATIONS_PATTERN = KEYS_DIR + "/**/consolidations*.json"
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
METRICS_PORT = int(os.environ.get("METRICS_PORT", "8000"))
FETCH_CHUNK_SIZE = 20
MAX_TARGET_BALANCE_GWEI = 2048 * 10**9

g_source_count = Gauge(
    "eth_consolidation_source_count",
    "Number of source validators by status and target",
    ["target", "status"],
)
g_target_balance = Gauge(
    "eth_consolidation_target_balance_gwei",
    "Current balance of target validator in gwei",
    ["target"],
)
g_target_fill_ratio = Gauge(
    "eth_consolidation_target_fill_ratio",
    "Target validator balance as a fraction of max (2048 ETH)",
    ["target"],
)
g_sources_total = Gauge("eth_consolidation_sources_total", "Total number of source validators")
g_sources_exited = Gauge("eth_consolidation_sources_exited", "Number of source validators that have exited")
g_progress = Gauge("eth_consolidation_progress_ratio", "Fraction of total target capacity that has been filled (0–1)")


def load_consolidations() -> list[dict]:
    paths = sorted(glob.glob(CONSOLIDATIONS_PATTERN, recursive=True))
    if not paths:
        raise FileNotFoundError(f"No consolidation files found matching: {CONSOLIDATIONS_PATTERN}")
    pairs = []
    for path in paths:
        with open(path) as f:
            data = json.load(f)
        for req in data.get("consolidationsRequests", []):
            target = req["targetPubkey"]
            for source in req["sourcePubkeys"]:
                pairs.append({"source": source, "target": target})
    return pairs


def fetch_validators_chunked(pubkeys: list[str]) -> dict[str, dict]:
    result = {}
    for i in range(0, len(pubkeys), FETCH_CHUNK_SIZE):
        chunk = pubkeys[i : i + FETCH_CHUNK_SIZE]
        resp = requests.get(
            f"{BEACON_NODE}/eth/v1/beacon/states/head/validators",
            params={"id": ",".join(chunk)},
        )
        resp.raise_for_status()
        for v in resp.json()["data"]:
            result[v["validator"]["pubkey"]] = v
    return result


def short(pubkey: str) -> str:
    return pubkey[:16] + "…"


def update_metrics(pairs: list[dict], validator_data: dict[str, dict]) -> None:
    targets: dict[str, list[str]] = {}
    for p in pairs:
        targets.setdefault(p["target"], []).append(p["source"])

    total = len(pairs)
    exited = 0
    total_balance_gwei = 0

    for target_pubkey, sources in targets.items():
        tv = validator_data.get(target_pubkey)
        balance = int(tv["balance"]) if tv else 0
        total_balance_gwei += balance
        g_target_balance.labels(target=target_pubkey).set(balance)
        g_target_fill_ratio.labels(target=target_pubkey).set(balance / MAX_TARGET_BALANCE_GWEI)

        status_counts: dict[str, int] = {}
        for src_pubkey in sources:
            sv = validator_data.get(src_pubkey)
            src_status = sv["status"] if sv else "unknown"
            status_counts[src_status] = status_counts.get(src_status, 0) + 1
            if src_status.startswith(("exited", "withdrawal")):
                exited += 1

        for status, count in status_counts.items():
            g_source_count.labels(target=target_pubkey, status=status).set(count)

    total_capacity_gwei = len(targets) * MAX_TARGET_BALANCE_GWEI
    g_sources_total.set(total)
    g_sources_exited.set(exited)
    g_progress.set(total_balance_gwei / total_capacity_gwei if total_capacity_gwei else 0)


def render(pairs: list[dict], validator_data: dict[str, dict]) -> None:
    targets: dict[str, list[str]] = {}
    for p in pairs:
        targets.setdefault(p["target"], []).append(p["source"])

    total = len(pairs)
    exited = 0

    print("\033[2J\033[H", end="")  # clear screen
    for target_pubkey, sources in targets.items():
        tv = validator_data.get(target_pubkey)
        balance_eth = int(tv["balance"]) / 10**9 if tv else 0.0
        status = tv["status"] if tv else "unknown"
        print(f"TARGET  {short(target_pubkey)}  {balance_eth:.2f} ETH  [{status}]")

        status_counts: dict[str, int] = {}
        for src_pubkey in sources:
            sv = validator_data.get(src_pubkey)
            src_status = sv["status"] if sv else "unknown"
            status_counts[src_status] = status_counts.get(src_status, 0) + 1
            if src_status.startswith(("exited", "withdrawal")):
                exited += 1

        for s, count in sorted(status_counts.items()):
            print(f"  {count:>4}x  {s}")
        print()

    pct = 100 * exited // total if total else 0
    print(f"Progress: {exited}/{total} sources exited ({pct}%)")
    print(f"Metrics:  http://localhost:{METRICS_PORT}/metrics")
    print(f"Updated:  {time.strftime('%Y-%m-%d %H:%M:%S')}  (every {POLL_INTERVAL}s)")


def main():
    print("Loading consolidation files...")
    pairs = load_consolidations()
    print(f"Loaded {len(pairs)} source→target pairs")

    all_pubkeys = list({p["source"] for p in pairs} | {p["target"] for p in pairs})
    print(f"Monitoring {len(all_pubkeys)} unique validators")

    start_http_server(METRICS_PORT)
    print(f"Prometheus metrics available at http://localhost:{METRICS_PORT}/metrics")

    while True:
        try:
            validator_data = fetch_validators_chunked(all_pubkeys)
            update_metrics(pairs, validator_data)
            render(pairs, validator_data)

            all_done = all(
                validator_data.get(p["source"], {}).get("status", "").startswith(("exited", "withdrawal"))
                for p in pairs
            )
            if all_done:
                print("\nAll source validators have exited. Consolidations complete.")
                break
        except requests.RequestException as e:
            print(f"Beacon node error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
