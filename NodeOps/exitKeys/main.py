import os
import json
import requests

BEACON_NODE_URL = "http://127.0.0.1:5052"

def getAllExitMessages():
    with open("./files/signed_exit_messages.json", "r") as f:
        exit_keys = f.read()
        return json.loads(exit_keys)
    
def filterExitMessages(index, exit_messages):
    filtered = []
    for msg in exit_messages:
        if int(msg['message']["validator_index"]) >= index:
            filtered.append(msg)
    return filtered

def exitValidator(message):
    url = f"{BEACON_NODE_URL}/eth/v1/beacon/pool/voluntary_exits"
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(message))
    if response.status_code == 200:
        print(f"Successfully submitted exit for validator {message['message']['validator_index']}")
    else:
        print(f"Failed to submit exit for validator {message['message']['validator_index']}: {response.text}")

def main():
    exit_messages = getAllExitMessages()
    filtered_messages = filterExitMessages(1100163, exit_messages)
    print(f"Total exit messages: {len(exit_messages)}")
    print(f"Filtered exit messages: {len(filtered_messages)}")
    print("Exiting Messages one by one...")
    #print(filtered_messages[0])
    indecies = ""
    for msg in filtered_messages:
        indecies += str(msg['message']["validator_index"]) + ","

    print(indecies)
    # for msg in filtered_messages:
    #     exitValidator(msg)

        


if __name__ == "__main__":
    main()