# Reads a stereum "Get Keys" output file to get public keys, checks the status
# of each key against the beacon chain, lists them and prints a summary of all
# statuses and their occurrence.
#
# The stereum file has a few header lines followed by a JSON array:
#   TASK: Get Keys
#   ACTION: Get Keys
#   CATEGORY: OK
#   DATA: [ { "validating_pubkey": "0x...", ... }, ... ]
#
# Usage: python checkStatus.py <keys_file> [beacon_node_url]
# Example: python checkStatus.py keys.txt http://127.0.0.1:5052

import argparse
import json
from collections import Counter

import requests

# Number of pubkeys to query per request (beacon nodes limit request/URL sizes)
BATCH_SIZE = 100


def read_pubkeys(keys_file: str):
    """Read pubkeys from a stereum 'Get Keys' output file.

    The file has header lines (TASK/ACTION/CATEGORY/DATA) followed by a JSON
    array of objects with a 'validating_pubkey' field (already 0x-prefixed).
    """
    with open(keys_file, "r") as f:
        text = f.read()

    # everything after the first "DATA:" marker is the JSON payload
    marker = "DATA:"
    if marker in text:
        text = text.split(marker, 1)[1]

    # be lenient: grab from the first '[' so any stray leading text is ignored
    start = text.find("[")
    if start != -1:
        text = text[start:]

    content = json.loads(text)
    return [entry["validating_pubkey"] for entry in content]


def fetch_validator_states(pubkeys, beacon_node_url: str):
    """Return a dict mapping pubkey -> status string for the given pubkeys."""
    states = {}
    url = f"{beacon_node_url}/eth/v1/beacon/states/head/validators"

    for start in range(0, len(pubkeys), BATCH_SIZE):
        batch = pubkeys[start:start + BATCH_SIZE]
        response = requests.post(url, json={"ids": batch})
        response.raise_for_status()
        data = response.json().get("data", [])
        for validator in data:
            states[validator["validator"]["pubkey"]] = validator["status"]

    return states


def main():
    ap = argparse.ArgumentParser(
        description="Check beacon chain status of pubkeys from a stereum 'Get Keys' file."
    )
    ap.add_argument("keys_file", help="Path to the stereum 'Get Keys' output file.")
    ap.add_argument(
        "beacon_node_url",
        nargs="?",
        default="http://127.0.0.1:5052",
        help="URL of the beacon node (default: http://127.0.0.1:5052).",
    )
    args = ap.parse_args()

    pubkeys = read_pubkeys(args.keys_file)
    print(f"Loaded {len(pubkeys)} pubkeys from {args.keys_file}")

    states = fetch_validator_states(pubkeys, args.beacon_node_url)

    print("\nValidator statuses:")
    summary = Counter()
    for pubkey in pubkeys:
        status = states.get(pubkey, "not_found")
        summary[status] += 1
        print(f"  {pubkey}  {status}")

    print("\nSummary:")
    for status, count in summary.most_common():
        print(f"  {status}: {count}")
    print(f"  total: {len(pubkeys)}")


if __name__ == "__main__":
    main()
