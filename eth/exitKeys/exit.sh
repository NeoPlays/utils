#!/usr/bin/env bash

indices="1,2,3"
mnemonic=""

for i in $(echo "$indices" | tr ',' ' '); do
    echo "Running command for index: $i"
    sudo docker run -it wealdtech/ethdo:latest validator exit --mnemonic="" --validator=$i --connection=http://127.0.0.1:5052 --timeout=120s --max-distance=10000 --verbose || echo "Command failed for $i, but continuing..."
    sudo docker run -it wealdtech/ethdo:latest validator info --validator=$i --connection=http://127.0.0.1:5052
done
