from web3 import Web3

# Since LIP-37 (EDF) HashConsensus members are DelegationContracts; reports are sent
# by the contract's delegate EOA (hot key), which is what the ejector allowlist needs.
# Members without contract code are plain EOAs and are used as is.

NETWORKS = {
    "Mainnet": ("https://ethereum-rpc.publicnode.com", "0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a"),
    "Hoodi": ("https://ethereum-hoodi-rpc.publicnode.com", "0x30308CD8844fb2DB3ec4D056F1d475a802DCA07c"),
}

ZERO = "0x0000000000000000000000000000000000000000"

HASH_CONSENSUS_ABI = [
    {"inputs":[],"name":"getMembers","outputs":[{"internalType":"address[]","name":"addresses","type":"address[]"},{"internalType":"uint256[]","name":"lastReportedRefSlots","type":"uint256[]"}],"stateMutability":"view","type":"function"}
]

DELEGATION_ABI = [
    {"inputs":[],"name":"getDelegate","outputs":[{"type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"getPendingDelegate","outputs":[{"type":"address"},{"type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"isTerminated","outputs":[{"type":"bool"}],"stateMutability":"view","type":"function"},
]


def format_list(allowlist):
    x = '","'.join(allowlist)
    return '\'["' + x + '"]\''


def resolve_member(web3, member):
    """Returns (kind, active, pending, activeFrom) for a HashConsensus member."""
    if len(web3.eth.get_code(member)) == 0:
        return "EOA", member, None, 0
    contract = web3.eth.contract(address=member, abi=DELEGATION_ABI)
    if contract.functions.isTerminated().call():
        return "terminated", None, None, 0
    active = contract.functions.getDelegate().call()
    pending, active_from = contract.functions.getPendingDelegate().call()
    return (
        "delegation",
        active if active != ZERO else None,
        pending if pending != ZERO else None,
        active_from,
    )


for name, (rpc, hash_consensus) in NETWORKS.items():
    web3 = Web3(Web3.HTTPProvider(rpc))
    consensus = web3.eth.contract(address=web3.to_checksum_address(hash_consensus), abi=HASH_CONSENSUS_ABI)
    members = consensus.functions.getMembers().call()[0]

    allowlist = []
    print(f"{name} Members ({len(members)}):")
    for member in members:
        kind, active, pending, active_from = resolve_member(web3, member)
        line = f"  {member} [{kind}] active={active}"
        if pending:
            line += f" pending={pending} (active from {active_from})"
        print(line)
        for address in (active, pending):
            if address and address not in allowlist:
                allowlist.append(address)

    print(f"\n{name} Allowlist ({len(allowlist)}):")
    print(format_list(allowlist))
    print()
