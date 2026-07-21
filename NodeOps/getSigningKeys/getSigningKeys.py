# Reads signing keys from the Lido NodeOperatorsRegistry contract via its
# `getSigningKeys` method (readProxyContract #F7), parses the packed output into
# individual keys (pubkey, signature, used) and writes them to a JSON file.
#
# The contract packs keys as concatenated byte strings: pubkeys are 48-byte BLS
# public keys and signatures are 96-byte BLS signatures, both concatenated back
# to back. `used` is a parallel bool array (one per key).
#
# Usage: python getSigningKeys.py <nodeOperatorId> <offset> <limit> [--network mainnet|hoodi] [--output FILE]
# Example: python getSigningKeys.py 0 0 100 --network hoodi

import argparse
import json

from web3 import Web3

# BLS key sizes (bytes) as packed by the NodeOperatorsRegistry.
PUBKEY_LENGTH = 48
SIGNATURE_LENGTH = 96

NETWORKS = {
    "mainnet": {
        "rpc": "https://ethereum-rpc.publicnode.com",
        "address": "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5",
    },
    "hoodi": {
        "rpc": "https://ethereum-hoodi-rpc.publicnode.com",
        "address": "0x682E94d2630846a503BDeE8b6810DF71C9806891",
    },
}

# Minimal ABI: only the getSigningKeys read method (readProxyContract #F7).
ABI = [
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


def chunk(data: bytes, size: int):
    """Split raw bytes into fixed-size chunks."""
    return [data[i:i + size] for i in range(0, len(data), size)]


def parse_keys(pubkeys: bytes, signatures: bytes, used, offset: int):
    """Split the packed pubkeys/signatures into per-key records."""
    pubkey_chunks = chunk(pubkeys, PUBKEY_LENGTH)
    signature_chunks = chunk(signatures, SIGNATURE_LENGTH)

    if not (len(pubkey_chunks) == len(signature_chunks) == len(used)):
        raise ValueError(
            f"Mismatched lengths: {len(pubkey_chunks)} pubkeys, "
            f"{len(signature_chunks)} signatures, {len(used)} used flags"
        )

    keys = []
    for i, (pubkey, signature, is_used) in enumerate(
        zip(pubkey_chunks, signature_chunks, used)
    ):
        keys.append(
            {
                "index": offset + i,
                "pubkey": "0x" + pubkey.hex(),
                "signature": "0x" + signature.hex(),
                "used": bool(is_used),
            }
        )
    return keys


def main():
    ap = argparse.ArgumentParser(
        description="Fetch and parse Lido NodeOperatorsRegistry signing keys "
        "(getSigningKeys / readProxyContract #F7)."
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
        "--output",
        default=None,
        help="Output JSON file (default: signingKeys_<network>_op<id>_<offset>_<limit>.json).",
    )
    args = ap.parse_args()

    network = NETWORKS[args.network]
    web3 = Web3(Web3.HTTPProvider(network["rpc"]))
    address = web3.to_checksum_address(network["address"])
    contract = web3.eth.contract(address=address, abi=ABI)

    print(
        f"Querying getSigningKeys(nodeOperatorId={args.nodeOperatorId}, "
        f"offset={args.offset}, limit={args.limit}) on {args.network} ({address})..."
    )
    pubkeys, signatures, used = contract.functions.getSigningKeys(
        args.nodeOperatorId, args.offset, args.limit
    ).call()

    keys = parse_keys(pubkeys, signatures, used, args.offset)
    print(f"Parsed {len(keys)} keys.")

    output = {
        "network": args.network,
        "contract": address,
        "nodeOperatorId": args.nodeOperatorId,
        "offset": args.offset,
        "limit": args.limit,
        "count": len(keys),
        "keys": keys,
    }

    output_file = args.output or (
        f"signingKeys_{args.network}_op{args.nodeOperatorId}"
        f"_{args.offset}_{args.limit}.json"
    )
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(keys)} keys to {output_file}")


if __name__ == "__main__":
    main()
