import requests
import time
import json
import os
import logging
from datetime import datetime

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# --- Environment Configuration ---
BEACON_API = os.getenv("BEACON_API", "http://localhost:5052")
PUBKEYS_FILE = os.getenv("PUBKEYS_FILE", "/data/pubkeys")

PUBKEYS = []
VALIDATORS = []

# --- Functions ---
def get_spec_and_genesis():
    try:
        spec = requests.get(f"{BEACON_API}/eth/v1/config/spec").json()["data"]
        genesis = requests.get(f"{BEACON_API}/eth/v1/beacon/genesis").json()["data"]
        return int(genesis["genesis_time"]), int(spec["SECONDS_PER_SLOT"]), int(spec["SLOTS_PER_EPOCH"])
    except requests.exceptions.RequestException as e:
        log.error(f"Error fetching spec: {e}")
        exit(1)

def get_current_epoch_and_slot():
    genesis_time, seconds_per_slot, slots_per_epoch = get_spec_and_genesis()
    now = int(time.time())
    current_slot = (now - genesis_time) // seconds_per_slot
    current_epoch = current_slot // slots_per_epoch
    return current_epoch, current_slot

def get_pubkeys():
    log.info(f"Reading pubkeys from {PUBKEYS_FILE}...")
    with open(PUBKEYS_FILE, "r") as f:
        pubkeys = [line.strip() for line in f.readlines()]
    return pubkeys

def init_pubkeys():
    global PUBKEYS
    log.info("Initializing pubkeys...")

    if not os.path.exists(PUBKEYS_FILE):
        log.error(f"Pubkey file does not exist: {PUBKEYS_FILE}")
        exit(1)

    PUBKEYS = get_pubkeys()
    if not PUBKEYS:
        log.error(f"Pubkey file is empty: {PUBKEYS_FILE}")
        exit(1)

    log.info(f"Loaded {len(PUBKEYS)} pubkeys from {PUBKEYS_FILE}.")

def get_validators():
    global VALIDATORS
    log.info("Fetching validator states...")

    try:
        response = requests.post(f"{BEACON_API}/eth/v1/beacon/states/head/validators", json={"ids": PUBKEYS})
        data = response.json()
        log.info(f"Fetched {len(data.get('data', []))} validators from Beacon API.")

        VALIDATORS = data.get("data", [])
        with open("/data/validators.json", "w") as f:
            json.dump(data.get("data", []), f, indent=2)
        log.info(f"Saved validators to /data/validators.json.")
    except requests.exceptions.RequestException as e:
        log.error(f"Error fetching indices: {e}")
        exit(1)

def check_node():
    log.info("Checking node status...")
    if not BEACON_API.startswith(("http://", "https://")):
        log.error(f"Invalid BEACON_API URL: {BEACON_API}")
        exit(1)

    is_syncing = True
    while is_syncing:
        try:
            response = requests.get(f"{BEACON_API}/eth/v1/node/syncing")
            is_syncing = response.json()["data"]["is_syncing"]
            if is_syncing:
                log.info(f"Node is syncing... {response.json()}")
                time.sleep(60)
            else:
                log.info(f"Node is synced. {response.json()}")
        except requests.exceptions.RequestException as e:
            log.error(f"Error connecting to node: {e}")
            time.sleep(60)

def appendDutiesToFile(duties: dict | list, filename: str):
    try:
        # Check if the file exists and read existing duties
        if os.path.exists(filename):
            with open(filename, "r") as f:
                existing_duties = json.load(f)
        else:
            existing_duties = []
        
        # Append new duties to the existing list
        if isinstance(existing_duties, list):
            existing_duties.extend(duties)
        else:
            existing_duties.append(duties)

        # Write the updated list back to the file
        with open(filename, "w") as f:
            json.dump(existing_duties, f, indent=2)
    except (IOError, json.JSONDecodeError) as e:
        log.error(f"Error writing duties to file: {e}")
        exit(1)

def check_proposer_duties(current_epoch):
    log.info("Checking proposer duties...")
    try:
        response = requests.get(f"{BEACON_API}/eth/v1/validator/duties/proposer/{current_epoch}")
        duties = response.json().get("data", [])

        matching_duties = [d for d in duties if d["validator_index"] in VALIDATORS]
        if matching_duties:
            log.info(f"Found {len(matching_duties)} matching proposer duties for validators.")
            appendDutiesToFile(matching_duties, "/data/proposer_duties.json")
        else:
            log.info("No matching duties found for validators.")


    except requests.exceptions.RequestException as e:
        log.error(f"Error fetching proposer duties: {e}")
        exit(1)

def check_sync_duties(current_epoch):
    log.info("Checking sync duties...")
    try:
        response = requests.post(f"{BEACON_API}/eth/v1/validator/duties/sync/{current_epoch}", json=[v["index"] for v in VALIDATORS])
        duties = response.json().get("data", [])
        if duties and len(duties) > 0:
            log.info(f"Found {len(duties)} sync duties for validators.")
            appendDutiesToFile(duties, "/data/sync_duties.json")
        else:
            log.info("No sync duties found for validators.")

    except requests.exceptions.RequestException as e:
        log.error(f"Error fetching sync duties: {e}")
        exit(1)


def start_loop():
    last_proposer_check = -1
    last_sync_check = -1
    while True:
        current_epoch, current_slot = get_current_epoch_and_slot()

        # Check for proposers every epoch (32 slots) in the 16th slot
        if current_slot % 32 == 16 and current_epoch != last_proposer_check:
            log.info("New Epoch, Checking Proposer Duties...")
            last_proposer_check = current_epoch
            check_proposer_duties(current_epoch)

        # Check for sync duties every 256 epochs with a 1-epoch offset
        if current_epoch % 256 == 1 and current_epoch != last_sync_check:
            log.info("New Sync, Checking Node...")
            last_sync_check = current_epoch
            check_sync_duties(current_epoch)

        # Refresh validators every 32 slots (1 epoch) if the number of pubkeys is not equal to the number of active validators
        if current_slot % 32 == 0 and len(PUBKEYS) != len(VALIDATORS):
            get_validators()
        time.sleep(6)

def monitor():
    log.info("Starting duty monitor...")
    log.info(f"Beacon API: {BEACON_API}")
    log.info(f"Pubkeys file: {PUBKEYS_FILE}")
    init_pubkeys()
    check_node()
    get_validators()
    start_loop()
