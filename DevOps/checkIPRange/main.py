#!/usr/bin/env python3

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

def ping(ip):
    result = subprocess.run(
        ["ping", "-c", "1", "-W", "1", ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return ip, result.returncode == 0

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 pingscan.py 10.0.0 1 254")
        sys.exit(1)

    base = sys.argv[1]
    start = int(sys.argv[2])
    end = int(sys.argv[3])

    ips = [f"{base}.{i}" for i in range(start, end + 1)]

    print(f"Scanning {base}.{start} - {base}.{end}...\n")

    reachable = []
    not_reachable = []

    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(ping, ips)

    for ip, is_up in sorted(results, key=lambda x: int(x[0].split(".")[-1])):
        if is_up:
            reachable.append(ip)
            print(f"✓ {ip} is reachable")
        else:
            not_reachable.append(ip)
            print(f"✗ {ip} is not reachable")

    print(f"\nSummary: {len(reachable)} reachable, {len(not_reachable)} not reachable")

if __name__ == "__main__":
    main()