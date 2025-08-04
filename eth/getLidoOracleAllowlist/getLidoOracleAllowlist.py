from web3 import Web3

def format_list(allowlist):
    x = '","'.join(allowlist)
    return '\'["' + x + '"]\''


web3_mainnet = Web3(Web3.HTTPProvider("https://ethereum-rpc.publicnode.com"))
web3_holesky = Web3(Web3.HTTPProvider("https://ethereum-holesky-rpc.publicnode.com"))
web3_hoodi = Web3(Web3.HTTPProvider("https://ethereum-hoodi-rpc.publicnode.com"))

mainnet_address = web3_mainnet.to_checksum_address("0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a")
holesky_address = web3_holesky.to_checksum_address("0xe77Cf1A027d7C10Ee6bb7Ede5E922a181FF40E8f")
hoodi_address = web3_hoodi.to_checksum_address("0x30308CD8844fb2DB3ec4D056F1d475a802DCA07c")

abi = [
    {"inputs":[],"name":"getMembers","outputs":[{"internalType":"address[]","name":"addresses","type":"address[]"},{"internalType":"uint256[]","name":"lastReportedRefSlots","type":"uint256[]"}],"stateMutability":"view","type":"function"}
]

mainnet_contract = web3_mainnet.eth.contract(address=mainnet_address, abi=abi)
mainnet_members = mainnet_contract.functions.getMembers().call()

holesky_contract = web3_holesky.eth.contract(address=holesky_address, abi=abi)
holesky_members = holesky_contract.functions.getMembers().call()

hoodi_contract = web3_hoodi.eth.contract(address=hoodi_address, abi=abi)
hoodi_members = hoodi_contract.functions.getMembers().call()

print("Mainnet Members:")
print(format_list(mainnet_members[0]))

print("\nHolesky Members:")
print(format_list(holesky_members[0]))

print("\nHoodi Members:")
print(format_list(hoodi_members[0]))
