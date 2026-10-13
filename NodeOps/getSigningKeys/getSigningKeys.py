# Reads signing keys from a Lido curated staking module and writes them to a
# JSON file, parsing the packed byte output into individual keys.
#
# Two module versions are supported (--cm-version):
#   v1  Curated Module v1 — the legacy NodeOperatorsRegistry. Its
#       `getSigningKeys(id, offset, limit)` (readProxyContract #F7) returns
#       (bytes pubkeys, bytes signatures, bool[] used).
#   v2  Curated Module v2 — the new CuratedModule (CSM-derived). It exposes
#       `getSigningKeysWithSignatures(id, startIndex, keysCount)` returning
#       (bytes keys, bytes signatures). There is no `used` flag in this
#       interface, so v2 records report `used: null`.
#
# In both cases pubkeys are 48-byte BLS public keys and signatures are 96-byte
# BLS signatures, concatenated back to back.
#
# Usage: python getSigningKeys.py <nodeOperatorId> <offset> <limit>
#                                 [--network mainnet|hoodi] [--cm-version v1|v2]
#                                 [--output FILE]
# Example: python getSigningKeys.py 0 0 100 --network mainnet --cm-version v2

import argparse
import json

from web3 import Web3

# BLS key sizes (bytes) as packed by the modules.
PUBKEY_LENGTH = 48
SIGNATURE_LENGTH = 96

# Per network: RPC endpoint and the curated module address for each version.
NETWORKS = {
    "mainnet": {
        "rpc": "https://ethereum-rpc.publicnode.com",
        "v1": "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5",
        "v2": "0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1",
    },
    "hoodi": {
        "rpc": "https://ethereum-hoodi-rpc.publicnode.com",
        "v1": "0x682E94d2630846a503BDeE8b6810DF71C9806891",
        "v2": "0x87EB69Ae51317405FD285efD2326a4a11f6173b9",
    },
}

# CMv1 (NodeOperatorsRegistry): getSigningKeys → (pubkeys, signatures, used).
ABI_V1 = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "_nodeOperatorId", "type": "uint256"},
            {"internalType": "uint256", "name": "_offset", "type": "uint256"},
            {"internalType": "uint256", "name": "_limit", "type": "uint256"},
        ],
        "name": "getSigningKeys",
        "outputs": [
            {"internalType": "bytes", "name": "pubkeys", "type": "bytes"},
            {"internalType": "bytes", "name": "signatures", "type": "bytes"},
            {"internalType": "bool[]", "name": "used", "type": "bool[]"},
        ],
        "stateMutability": "view",
        "type": "function",
    }
]

# CMv2 (CuratedModule): getSigningKeysWithSignatures → (keys, signatures).
ABI_V2 = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "nodeOperatorId", "type": "uint256"},
            {"internalType": "uint256", "name": "startIndex", "type": "uint256"},
            {"internalType": "uint256", "name": "keysCount", "type": "uint256"},
        ],
        "name": "getSigningKeysWithSignatures",
        "outputs": [
            {"internalType": "bytes", "name": "keys", "type": "bytes"},
            {"internalType": "bytes", "name": "signatures", "type": "bytes"},
        ],
        "stateMutability": "view",
        "type": "function",
    }
]


def chunk(data: bytes, size: int):
    """Split raw bytes into fixed-size chunks."""
    return [data[i:i + size] for i in range(0, len(data), size)]


def parse_keys(pubkeys: bytes, signatures: bytes, offset: int, used=None):
    """Split the packed pubkeys/signatures into per-key records.

    `used` is the parallel bool array from CMv1; pass None for CMv2, which has
    no such flag, and each record's `used` will be null.
    """
    pubkey_chunks = chunk(pubkeys, PUBKEY_LENGTH)
    signature_chunks = chunk(signatures, SIGNATURE_LENGTH)

    if len(pubkey_chunks) != len(signature_chunks):
        raise ValueError(
            f"Mismatched lengths: {len(pubkey_chunks)} pubkeys, "
            f"{len(signature_chunks)} signatures"
        )
    if used is not None and len(used) != len(pubkey_chunks):
        raise ValueError(
            f"Mismatched lengths: {len(pubkey_chunks)} pubkeys, {len(used)} used flags"
        )

    keys = []
    for i, (pubkey, signature) in enumerate(zip(pubkey_chunks, signature_chunks)):
        keys.append(
            {
                "index": offset + i,
                "pubkey": "0x" + pubkey.hex(),
                "signature": "0x" + signature.hex(),
                "used": bool(used[i]) if used is not None else None,
            }
        )
    return keys


def fetch_keys(contract, cm_version: str, node_operator_id: int, offset: int, limit: int):
    """Call the appropriate read method and return (pubkeys, signatures, used)."""
    if cm_version == "v1":
        pubkeys, signatures, used = contract.functions.getSigningKeys(
            node_operator_id, offset, limit
        ).call()
        return pubkeys, signatures, used
    # v2: no `used` array in the CSM-derived interface.
    pubkeys, signatures = contract.functions.getSigningKeysWithSignatures(
        node_operator_id, offset, limit
    ).call()
    return pubkeys, signatures, None


def main():
    ap = argparse.ArgumentParser(
        description="Fetch and parse Lido curated module signing keys "
        "(CMv1 getSigningKeys / CMv2 getSigningKeysWithSignatures)."
    )
    ap.add_argument("nodeOperatorId", type=int, help="Node operator id.")
    ap.add_argument("offset", type=int, help="Index of the first key to return.")
    ap.add_argument("limit", type=int, help="Maximum number of keys to return.")
    ap.add_argument(
        "--network",
        choices=NETWORKS.keys(),
        default="mainnet",
        help="Network to query (default: mainnet).",
    )
    ap.add_argument(
        "--cm-version",
        choices=["v1", "v2"],
        default="v1",
        help="Curated module version: v1 (legacy NodeOperatorsRegistry) or "
        "v2 (new CuratedModule). Default: v1.",
    )
    ap.add_argument(
        "--output",
        default=None,
        help="Output JSON file "
        "(default: signingKeys_<network>_<cmVersion>_op<id>_<offset>_<limit>.json).",
    )
    args = ap.parse_args()

    network = NETWORKS[args.network]
    web3 = Web3(Web3.HTTPProvider(network["rpc"]))
    address = web3.to_checksum_address(network[args.cm_version])
    abi = ABI_V1 if args.cm_version == "v1" else ABI_V2
    contract = web3.eth.contract(address=address, abi=abi)

    method = "getSigningKeys" if args.cm_version == "v1" else "getSigningKeysWithSignatures"
    print(
        f"Querying {method}(nodeOperatorId={args.nodeOperatorId}, "
        f"offset={args.offset}, limit={args.limit}) on {args.network} "
        f"CM{args.cm_version} ({address})..."
    )
    pubkeys, signatures, used = fetch_keys(
        contract, args.cm_version, args.nodeOperatorId, args.offset, args.limit
    )

    keys = parse_keys(pubkeys, signatures, args.offset, used)
    print(f"Parsed {len(keys)} keys.")

    output = {
        "network": args.network,
        "cmVersion": args.cm_version,
        "contract": address,
        "nodeOperatorId": args.nodeOperatorId,
        "offset": args.offset,
        "limit": args.limit,
        "count": len(keys),
        "keys": keys,
    }

    output_file = args.output or (
        f"signingKeys_{args.network}_{args.cm_version}_op{args.nodeOperatorId}"
        f"_{args.offset}_{args.limit}.json"
    )
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(keys)} keys to {output_file}")


if __name__ == "__main__":
    main()
