import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

def normalize_hex(s: str) -> str:
    if s is None:
        return ""
    s = s.strip()
    if s.startswith("0x") or s.startswith("0X"):
        s = s[2:]
    return s.lower()

def read_pubkeys(pubkeys_path: Path) -> Tuple[List[str], Set[str], List[str]]:
    """
    Returns (all_lines, unique_pubkeys, duplicates_in_input)
    Ignores blank lines and lines beginning with '#'.
    """
    if not pubkeys_path.is_file():
        raise FileNotFoundError(f"Pubkeys file not found: {pubkeys_path}")
    seen = set()
    dups = []
    cleaned_all = []
    with pubkeys_path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            hx = normalize_hex(line)
            if not hx:
                continue
            cleaned_all.append(hx)
            if hx in seen:
                dups.append(hx)
            else:
                seen.add(hx)
    return cleaned_all, set(cleaned_all), dups

def collect_keystore_pubkeys(ks_dir: Path, pattern: str) -> Tuple[Dict[str, List[Path]], List[Tuple[Path, str]]]:
    """
    Returns (pubkey -> [files], bad_files)
    bad_files is a list of (file_path, reason) tuples for files that couldn't be parsed / lacked a pubkey.
    """
    mapping: Dict[str, List[Path]] = {}
    bad: List[Tuple[Path, str]] = []
    if not ks_dir.is_dir():
        raise NotADirectoryError(f"Keystore directory not found: {ks_dir}")

    for p in sorted(ks_dir.glob(pattern)):
        if not p.is_file():
            continue
        # check if file is deposit.json
        if 'deposit_data' in p.name:
            print(f"[WARNING] Skipping deposit.json file: {p}")
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            bad.append((p, f"JSON parse error: {e}"))
            continue

        # EIP-2335 stores 'pubkey' at the root level
        pub = data.get("pubkey")
        if not isinstance(pub, str):
            bad.append((p, "Missing or non-string 'pubkey'"))
            continue

        norm = normalize_hex(pub)
        if not norm:
            bad.append((p, "Empty 'pubkey' after normalization"))
            continue

        mapping.setdefault(norm, []).append(p)

    return mapping, bad

def main():
    ap = argparse.ArgumentParser(description="Verify one-to-one mapping between pubkeys file and keystore files.")
    ap.add_argument("pubkeys_file", type=Path, help="Text file with one pubkey per line (optionally 0x-prefixed).")
    ap.add_argument("keystore_dir", type=Path, help="Directory containing keystore JSON files.")
    ap.add_argument("--pattern", default="*.json", help="Glob pattern for keystore files (default: *.json).")
    args = ap.parse_args()

    # Load inputs
    try:
        all_lines, pubkeys_set, dup_in_input = read_pubkeys(args.pubkeys_file)
    except Exception as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        sys.exit(2)

    ks_map, bad_files = collect_keystore_pubkeys(args.keystore_dir, args.pattern)
    ks_pubkeys_set = set(ks_map.keys())

    # Checks
    missing_pubkeys = sorted(pubkeys_set - ks_pubkeys_set)           # present in file, absent in keystores
    extra_keystores = sorted(ks_pubkeys_set - pubkeys_set)           # present in keystores, absent in file

    duplicated_in_keystores = {k: v for k, v in ks_map.items() if len(v) > 1}

    # Output
    ok = True
    print(f"Pubkeys listed (unique): {len(pubkeys_set)} (raw lines read: {len(all_lines)})")
    print(f"Keystore files matched pattern: '{args.pattern}' in {args.keystore_dir}")

    if dup_in_input:
        ok = False
        print("\n[ERROR] Duplicate pubkeys in input file:")
        for k in dup_in_input:
            print(f"  - {k}")

    if bad_files:
        ok = False
        print("\n[ERROR] Unreadable/invalid keystore files:")
        for p, why in bad_files:
            print(f"  - {p}: {why}")

    if missing_pubkeys:
        ok = False
        print("\n[ERROR] Pubkeys missing corresponding keystore:")
        for k in missing_pubkeys:
            print(f"  - {k}")

    if extra_keystores:
        ok = False
        print("\n[ERROR] Keystores whose pubkey is not listed in the pubkeys file:")
        for k in extra_keystores:
            files = ks_map.get(k, [])
            if files:
                for f in files:
                    print(f"  - {k}  (file: {f})")
            else:
                print(f"  - {k}")

    if duplicated_in_keystores:
        ok = False
        print("\n[ERROR] Duplicate pubkeys across multiple keystore files:")
        for k, files in duplicated_in_keystores.items():
            print(f"  - {k}")
            for f in files:
                print(f"      • {f}")

    if ok:
        print("\n✅ PASS: Perfect 1:1 mapping between pubkeys file and keystore files.")
        sys.exit(0)
    else:
        print("\n❌ FAIL: See errors above. (Non-zero exit for CI.)")
        sys.exit(1)

if __name__ == "__main__":
    main()
