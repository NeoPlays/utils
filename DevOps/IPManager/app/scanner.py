import subprocess
from concurrent.futures import ThreadPoolExecutor


def ping(ip: str) -> tuple[str, bool]:
    result = subprocess.run(
        ["ping", "-c", "1", "-W", "1", ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return ip, result.returncode == 0


def scan_ips(ips: list[str], max_workers: int = 50) -> dict[str, bool]:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(ping, ips)
    return {ip: is_up for ip, is_up in results}
