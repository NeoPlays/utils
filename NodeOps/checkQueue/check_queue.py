import requests
import math

NODE_URL = "localhost:5052"

get_queue = lambda: requests.get(f"http://{NODE_URL}/eth/v1/beacon/states/head/pending_deposits").json()
get_active_validators = lambda: requests.get(f"http://{NODE_URL}/eth/v1/beacon/states/head/validators").json()
get_chain_spec = lambda: requests.get(f"http://{NODE_URL}/eth/v1/config/spec").json()   

print("Checking validator queue...")    
queue_json = get_queue()

print("Checking active validators...")
validators_json = get_active_validators()

print("Get specs...")
spec_json = get_chain_spec()


active_validators = len(validators_json['data'])
min_churn_limit = int(spec_json["data"]['MIN_PER_EPOCH_CHURN_LIMIT'])
churn_limit_quotient = int(spec_json["data"]['CHURN_LIMIT_QUOTIENT'])
seconds_per_slot = int(spec_json["data"]['SECONDS_PER_SLOT'])
slots_per_epoch = int(spec_json["data"]['SLOTS_PER_EPOCH'])

in_queue = len(queue_json['data'])
churn_limit = max(min_churn_limit, math.floor(active_validators / churn_limit_quotient))

waiting_epochs = in_queue / churn_limit
waiting_seconds = waiting_epochs * seconds_per_slot * slots_per_epoch
waiting_minutes = waiting_seconds / 60
waiting_hours = waiting_seconds / 3600
waiting_days = waiting_seconds / 86400

# Times do not include the time it takes to recognize the deposit on the execution layer (~14 hours)
# https://docs.rated.network/documentation/explorer/ethereum/network-views/network-overview/activation-queue-length
print(f"Number of validators in queue: {in_queue}")
print(f"Epochs to wait: {waiting_epochs}")
print(f"Seconds to wait: {waiting_seconds}")
print(f"Minutes to wait: {waiting_minutes}")
print(f"Hours to wait: {waiting_hours}")
print(f"Days to wait: {waiting_days}")

