import json
import argparse
import sys

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def read_json_file(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"{bcolors.FAIL}Error reading JSON file: {e}{bcolors.ENDC}")
        sys.exit(1)

def write_json_file(filepath, data):
    try:
        with open(filepath, 'w') as f:
            f.write(data)
    except Exception as e:
        print(f"{bcolors.FAIL}Error writing JSON file: {e}{bcolors.ENDC}")
        sys.exit(1)

def main():
    ap = argparse.ArgumentParser(description="Takes GET/eth/v1/keystores response and outputs pubkeys for given range")
    ap.add_argument("api_response_file", type=str, help="File containing GET/eth/v1/keystores response")
    ap.add_argument("start_index", type=int, help="Start index (inclusive)")
    ap.add_argument("end_index", type=int, help="End index (exclusive)")
    args = ap.parse_args()
    
    print(f"Reading API response from {args.api_response_file}")
    data = read_json_file(args.api_response_file)
    print(f"Total keys in response: {bcolors.OKGREEN}{len(data.get('data', []))}{bcolors.ENDC}")

    print(f"Extracting pubkeys from index {args.start_index} to {args.end_index}")
    result_pubkeys = []
    smallest_index = None
    largest_index = None
    for pubkey in data.get('data', []):
        # 'derivation_path': 'm/12345/3600/0/0/0',
        index = pubkey.get('derivation_path', '').split('/')[3] # index 3 is the account index
        if smallest_index is None or int(index) < smallest_index:
            smallest_index = int(index)
        if largest_index is None or int(index) > largest_index:
            largest_index = int(index)
        if args.start_index <= int(index) < args.end_index:
            result_pubkeys.append(pubkey.get('validating_pubkey'))

    if len(result_pubkeys) == 0:
        print(f"{bcolors.WARNING}No pubkeys found in the specified range.\nSmallest index: {smallest_index}\nLargest index: {largest_index}{bcolors.ENDC}")
        sys.exit(1)
    print(f"Extracted pubkeys: {bcolors.OKGREEN}{len(result_pubkeys)}{bcolors.ENDC}")
    output_file = f"pubkeys_{args.start_index}_{args.end_index}"
    print(f"Writing pubkeys to {output_file}")
    write_json_file(output_file, "\n".join(result_pubkeys))
    print("Done.")

main()
