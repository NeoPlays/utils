# Usage with Stereum
## `getPublicKey.py`
This script takes a file containing a response from this api request: https://ethereum.github.io/keymanager-APIs/#/Local%20Key%20Manager/listKeys
When the validator was installed with Stereum you can log in to the node via Stereum and check the Task Manager. Check the task "Listing Keys" and click on the Sub-Task "Get Keys". From there you can copy the api response.

It uses the derivation path to derive the account (generation index) and writes all pubkeys to a file, falling into the given range.
The given range includes the start index and excludes the end index.

```bash
# Usage
python getPublicKey.py <api_response_file> <start_index> <end_index>
# Example
python getPublicKey.py api_response.json 0 10
```

## `checkKeyStores.py`
This script takes a directory containing keystore files and a file containing a list of public keys (one per line).
It checks for each public key if it has a corresponding keystore file and vice versa. Finally, it prints a summary of the findings.

```bash
# Usage
python checkKeyStores.py <public_keys_file> <keystore_directory>
# Example
python checkKeyStores.py ./pubkeys ./keystores
```