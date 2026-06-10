
import glob
import json
import re
import requests

HEADER_PATTERN = r'TASK: Get Keys\nACTION: Get Keys\nCATEGORY: OK\nDATA:\s*'
MAX_TARGET_BALANCE_GWEI = 2048 * 10**9
MAX_SOURCES_PER_BATCH = 63
MAX_CONSOLIDATIONS_PER_FILE = 4
BEACON_NODE = "http://127.0.0.1:5545"

# "fill"   — pack each target up to its remaining capacity (2048 ETH - current balance)
# "spread" — divide source ETH evenly across all targets
MODE = "spread"


def check_beacon_node():
    resp = requests.get(f"{BEACON_NODE}/eth/v1/node/syncing")
    resp.raise_for_status()
    data = resp.json()["data"]
    if data["is_syncing"]:
        raise RuntimeError(
            f"Beacon node is still syncing — head slot {data['head_slot']}, "
            f"distance {data['sync_distance']} slots behind"
        )
    print(f"Beacon node is synced at slot {data['head_slot']}")


def readFile(file_path: str):
    with open(file_path) as f:
        raw = f.read()
        keys = re.sub(HEADER_PATTERN, '', raw)
        data = json.loads(keys)
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data


FETCH_CHUNK_SIZE = 20

def fetch_validators(pubkeys: list[str]) -> list[dict]:
    result = []
    for i in range(0, len(pubkeys), FETCH_CHUNK_SIZE):
        chunk = pubkeys[i : i + FETCH_CHUNK_SIZE]
        resp = requests.get(
            f"{BEACON_NODE}/eth/v1/beacon/states/head/validators",
            params={"id": ",".join(chunk)},
        )
        resp.raise_for_status()
        result.extend(resp.json()["data"])
    return result


def get_active_sources(pubkeys: list[str]) -> list[tuple[str, int]]:
    """Returns (pubkey, balance_gwei) for active source validators only."""
    result = []
    for v in fetch_validators(pubkeys):
        if v["status"].startswith("active"):
            result.append((v["validator"]["pubkey"], int(v["balance"])))
    return result


def get_target_capacities(pubkeys: list[str]) -> list[tuple[str, int]]:
    """Returns (pubkey, remaining_capacity_gwei) for each target validator."""
    data = {v["validator"]["pubkey"]: int(v["balance"]) for v in fetch_validators(pubkeys)}
    result = []
    for pubkey in pubkeys:
        current = data.get(pubkey, 0)
        remaining = MAX_TARGET_BALANCE_GWEI - current
        result.append((pubkey, remaining))
        print(f"  target {pubkey[:12]}… balance {current / 10**9:.2f} ETH, capacity {remaining / 10**9:.2f} ETH")
    return result


def assign_fill(
    sources: list[tuple[str, int]],
    targets: list[tuple[str, int]],
) -> list[dict]:
    """Pack each target up to its remaining capacity."""
    consolidations = []
    source_idx = 0
    for target_pubkey, capacity in targets:
        if source_idx >= len(sources):
            break
        batch = []
        batch_total = 0
        while source_idx < len(sources) and len(batch) < MAX_SOURCES_PER_BATCH:
            if batch_total >= capacity:
                break
            pubkey, balance = sources[source_idx]
            batch.append(pubkey)
            batch_total += balance
            source_idx += 1
        if batch:
            consolidations.append({"sourcePubkeys": batch, "targetPubkey": target_pubkey})
    if source_idx < len(sources):
        print(f"Warning: {len(sources) - source_idx} source keys could not be assigned (not enough target capacity)")
    return consolidations


def assign_spread(
    sources: list[tuple[str, int]],
    targets: list[tuple[str, int]],
) -> list[dict]:
    """Distribute source ETH evenly across all targets."""
    total_source_balance = sum(b for _, b in sources)
    per_target = total_source_balance // len(targets)
    print(f"  spread target per target: {per_target / 10**9:.2f} ETH")

    consolidations = []
    source_idx = 0
    for i, (target_pubkey, capacity) in enumerate(targets):
        if source_idx >= len(sources):
            break
        # last target gets all remaining sources
        quota = per_target if i < len(targets) - 1 else total_source_balance
        batch = []
        batch_total = 0
        while source_idx < len(sources) and len(batch) < MAX_SOURCES_PER_BATCH:
            if batch_total >= quota or batch_total >= capacity:
                break
            pubkey, balance = sources[source_idx]
            batch.append(pubkey)
            batch_total += balance
            source_idx += 1
        if batch:
            consolidations.append({"sourcePubkeys": batch, "targetPubkey": target_pubkey})
    if source_idx < len(sources):
        print(f"Warning: {len(sources) - source_idx} source keys could not be assigned")
    return consolidations


def build_consolidations(source_keys, target_keys, source_operator_id=0, target_operator_id=0):
    source_pubkeys = [k["validating_pubkey"] for k in source_keys]
    target_pubkeys = [k["validating_pubkey"] for k in target_keys]

    print(f"Fetching {len(source_pubkeys)} source validators from beacon node...")
    active_sources = get_active_sources(source_pubkeys)
    print(f"{len(active_sources)} active, {len(source_pubkeys) - len(active_sources)} exited/skipped")

    print(f"Fetching {len(target_pubkeys)} target validator balances...")
    target_capacities = get_target_capacities(target_pubkeys)

    print(f"Mode: {MODE}")
    if MODE == "spread":
        all_requests = assign_spread(active_sources, target_capacities)
    else:
        all_requests = assign_fill(active_sources, target_capacities)

    print(f"{len(all_requests)} consolidation batches generated")

    files = []
    for i in range(0, max(len(all_requests), 1), MAX_CONSOLIDATIONS_PER_FILE):
        files.append({
            "sourceOperatorId": source_operator_id,
            "targetOperatorId": target_operator_id,
            "consolidationsRequests": all_requests[i : i + MAX_CONSOLIDATIONS_PER_FILE],
        })
    return files


def load_keys(pattern: str) -> list:
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No files found matching: {pattern}")
    keys = []
    for path in paths:
        keys.extend(readFile(path))
    print(f"  loaded {len(keys)} keys from {paths}")
    return keys


def main():
    check_beacon_node()

    print("Loading source keys...")
    source_keys = load_keys("./keys/source*")

    print("Loading target keys...")
    target_keys = load_keys("./keys/target*")

    results = build_consolidations(source_keys, target_keys)

    for i, result in enumerate(results):
        out_path = f"consolidations_{i + 1}.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Written {len(result['consolidationsRequests'])} consolidation requests to {out_path}")


if __name__ == "__main__":
    main()
