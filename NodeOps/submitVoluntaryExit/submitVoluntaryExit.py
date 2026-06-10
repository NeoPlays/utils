

import argparse
import json
import http.client

def read_presigned_exit_messages(file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("Presigned exit messages file must contain a list of messages.")
            return data
    except Exception as e:
        raise RuntimeError(f"Error reading presigned exit messages: {e}")

def submit_voluntary_exit(message, node_url: str):
    print(f"Submitting voluntary exit for validator index: {message['message'].get('validator_index')} to node: {node_url}")
    try:
        host = node_url.replace("http://", "").replace("https://", "").split(":")[0]
        port = node_url.split(":")[-1] if ":" in node_url else 5052
        port = int(port)

        conn = http.client.HTTPConnection(host, port)
        headers = {'Content-Type': 'application/json'}
        body = json.dumps(message)
        conn.request("POST", "/eth/v1/beacon/pool/voluntary_exits", headers=headers, body=body)
        response = conn.getresponse()
        resp_data = response.read().decode()
        if response.status != 200:
            print(f"Failed to submit exit: {response.status} {response.reason} - {resp_data}")
        else:
            print(f"Successfully submitted exit: {resp_data}")
    except Exception as e:
        print(f"Error submitting voluntary exit: {e}")

def main():
    ap = argparse.ArgumentParser(description="Submit a voluntary exit for a validator.")
    ap.add_argument("presigned_exit_messages", help="File containing presigned exit messages (JSON format).")
    ap.add_argument("node_url", default="http://localhost:5052", help="URL of the Beacon Node.", nargs="?")
    args = ap.parse_args()
    messages = read_presigned_exit_messages(args.presigned_exit_messages)
    print(f"Loaded {len(messages)} presigned exit messages.")

    for message in messages:
        submit_voluntary_exit(message, args.node_url)

if __name__ == "__main__":
    main()