import requests
import time
import json
import os
import logging

# --- Logging Configuration ---
LOG_FILE = "/app/data/logs/duty_monitor.log"

# Ensure log directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console_handler.setFormatter(console_formatter)

file_handler = logging.FileHandler(LOG_FILE, mode="a")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler.setFormatter(file_formatter)

log.addHandler(console_handler)
log.addHandler(file_handler)

DATA_PATH = "/app/data"
PUBKEYS = []
VALIDATORS = []
SPEC = None
GENESIS = None

# --- Environment Configuration ---
BEACON_API = os.getenv("BEACON_API", "http://localhost:5052")
PUBKEYS_FILE = os.getenv("PUBKEYS_FILE", DATA_PATH + "/pubkeys")


# --- Functions ---
def get_spec_and_genesis():
    global SPEC, GENESIS
    if SPEC and GENESIS:
        return int(GENESIS["genesis_time"]), int(SPEC["SECONDS_PER_SLOT"]), int(SPEC["SLOTS_PER_EPOCH"])
    try:
        spec_response = requests.get(f"{BEACON_API}/eth/v1/config/spec")
        SPEC = spec_response.json()["data"]
        genesis_response = requests.get(f"{BEACON_API}/eth/v1/beacon/genesis")
        GENESIS = genesis_response.json()["data"]
        log.debug(f"Spec response: {SPEC}")
        log.debug(f"Genesis response: {GENESIS}")
        return int(GENESIS["genesis_time"]), int(SPEC["SECONDS_PER_SLOT"]), int(SPEC["SLOTS_PER_EPOCH"])
    except requests.exceptions.RequestException as e:
        log.error(f"Error fetching spec or genesis: {e}")
        exit(1)

def get_current_epoch_and_slot():
    genesis_time, seconds_per_slot, slots_per_epoch = get_spec_and_genesis()
    now = int(time.time())
    current_slot = (now - genesis_time) // seconds_per_slot
    current_epoch = current_slot // slots_per_epoch
    return current_epoch, current_slot

def get_pubkeys():
    log.info(f"Reading pubkeys from {PUBKEYS_FILE}")
    with open(PUBKEYS_FILE, "r") as f:
        pubkeys = [line.strip() for line in f.readlines()]
    log.debug(f"Loaded pubkeys: {pubkeys}")
    return pubkeys

def init_pubkeys():
    global PUBKEYS
    log.info("Initializing pubkeys")

    if not os.path.exists(PUBKEYS_FILE):
        log.error(f"Pubkey file does not exist: {PUBKEYS_FILE}")
        exit(1)

    PUBKEYS = get_pubkeys()
    if not PUBKEYS:
        log.error(f"Pubkey file is empty: {PUBKEYS_FILE}")
        exit(1)

    log.info(f"Loaded {len(PUBKEYS)} pubkeys")

def get_validators():
    global VALIDATORS
    log.info("Fetching validator states")

    try:
        response = requests.post(f"{BEACON_API}/eth/v1/beacon/states/head/validators", json={"ids": PUBKEYS})
        data = response.json()
        VALIDATORS = data.get("data", [])
        log.debug(f"Validator response: {VALIDATORS}")

        with open(DATA_PATH + "/validators.json", "w") as f:
            json.dump(VALIDATORS, f, indent=2)

        log.info(f"Fetched and saved {len(VALIDATORS)} validators")
    except requests.exceptions.RequestException as e:
        log.error(f"Error fetching validator states: {e}")
        exit(1)

def check_node():
    log.info("Checking node status")
    if not BEACON_API.startswith(("http://", "https://")):
        log.error(f"Invalid BEACON_API URL: {BEACON_API}")
        exit(1)

    while True:
        try:
            response = requests.get(f"{BEACON_API}/eth/v1/node/syncing")
            sync_data = response.json()["data"]
            log.debug(f"Sync status response: {sync_data}")
            if sync_data["is_syncing"]:
                log.info("Node still syncing")
                time.sleep(60)
            else:
                log.info("Node is fully synced")
                get_spec_and_genesis()
                break
        except requests.exceptions.RequestException as e:
            log.warning(f"Connection issue while checking sync status: {e}")
            time.sleep(60)

def appendDutiesToFile(duties: dict | list, filename: str):
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                existing_duties = json.load(f)
        else:
            existing_duties = []

        if isinstance(existing_duties, list):
            existing_duties.extend(duties)
        else:
            existing_duties.append(duties)

        with open(filename, "w") as f:
            json.dump(existing_duties, f, indent=2)
    except (IOError, json.JSONDecodeError) as e:
        log.error(f"Error writing duties to file {filename}: {e}")
        exit(1)

def check_proposer_duties(current_epoch):
    log.info(f"Checking proposer duties for epoch {current_epoch}")
    try:
        response = requests.get(f"{BEACON_API}/eth/v1/validator/duties/proposer/{current_epoch}")
        duties = response.json().get("data", [])
        log.debug(f"Proposer duties response: {duties}")
        validator_indices = {v["index"] for v in VALIDATORS}
        matching_duties = [d for d in duties if d["validator_index"] in validator_indices]

        if matching_duties:
            log.info(f"{len(matching_duties)} proposer duties match our validators")
            appendDutiesToFile(matching_duties, DATA_PATH + "/proposer_duties.json")
        else:
            log.info("No proposer duties found for our validators")

    except requests.exceptions.RequestException as e:
        log.error(f"Error fetching proposer duties: {e}")
        exit(1)

def check_sync_duties(current_epoch):
    log.info(f"Checking sync duties for epoch {current_epoch}")
    try:
        indices = [v["index"] for v in VALIDATORS]
        response = requests.post(f"{BEACON_API}/eth/v1/validator/duties/sync/{current_epoch}", json=indices)
        duties = response.json().get("data", [])
        log.debug(f"Sync duties response: {duties}")

        if duties:
            log.info(f"Found {len(duties)} sync duties")
            appendDutiesToFile(duties, DATA_PATH + "/sync_duties.json")
        else:
            log.info("No sync duties for this epoch")

    except requests.exceptions.RequestException as e:
        log.error(f"Error fetching sync duties: {e}")
        exit(1)

def start_loop():
    last_proposer_check = -1
    last_sync_check = -1
    last_validator_check = -1
    log.info("Starting duty monitor loop")

    while True:
        current_epoch, current_slot = get_current_epoch_and_slot()

        if current_slot % 32 == 16 and current_epoch != last_proposer_check:
            last_proposer_check = current_epoch
            check_proposer_duties(current_epoch)

        if current_epoch % 256 == 1 and current_epoch != last_sync_check:
            last_sync_check = current_epoch
            check_sync_duties(current_epoch)

        if current_slot % 32 == 0 and len(PUBKEYS) != len(VALIDATORS) and last_validator_check != current_epoch:
            last_validator_check = current_epoch
            get_validators()

        time.sleep(6)

def logBanner():
    print("""
    ____        __              __  ___            _ __            
   / __ \\__  __/ /___  __      /  |/  /___  ____  (_) /_____  _____
  / / / / / / / __/ / / /_____/ /|_/ / __ \\/ __ \\/ / __/ __ \\/ ___/
 / /_/ / /_/ / /_/ /_/ /_____/ /  / / /_/ / / / / / /_/ /_/ / /    
/_____/\\__,_/\\__/\\__, /     /_/  /_/\\____/_/ /_/_/\\__/\\____/_/     
                /____/                                             
""",flush=True)
                                                     

def monitor():
    logBanner()
    log.info("Starting duty monitor")
    log.info(f"Beacon API: {BEACON_API}")
    log.info(f"Pubkeys file: {PUBKEYS_FILE}")
    init_pubkeys()
    check_node()
    get_validators()
    start_loop()
