# Takes a deposit file and a list of pubkeys and creates a new deposit file with only the wanted pubkeys
# Usage: python splitDeposit.py <original_deposit_file> <pubkeys_file>
# Example: python splitDeposit.py deposit.json pubkeys.txt

import sys
import json
# path to deposit file including all various pubkeys
originalDeposit = sys.argv[1]

# path to pubkeys file including the wanted pubkeys with the 0x prefix new-line separated
pubkeys = sys.argv[2]

print("Pubkeys: " + pubkeys)
print("Original deposit: " + originalDeposit)

original_deposit_content = json.load(open(originalDeposit, "r"))

pubkeys_content = [line.strip('"') for line in open(pubkeys, "r").read().splitlines()]

new_deposit_content = [key for key in original_deposit_content if ("0x" + key["pubkey"]) in pubkeys_content]

json.dump(new_deposit_content, open(pubkeys + "_deposit.json", "w"))
