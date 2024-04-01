#!/usr/bin/env bash

timestamp=$(date +"%Y-%m-%d-%H-%M")

droplet_id=$(doctl compute droplet create "quick-$timestamp" \
  --image ubuntu-23-04-x64 --size s-2vcpu-4gb --ssh-keys 30878672 --format ID --no-header)
echo "Created Droplet with ID $droplet_id"

while :; do
  ip_address=$(doctl compute droplet get $droplet_id --format PublicIPv4 --no-header)
  if [[ $ip_address ]]; then
    break
  else
    echo "Waiting for IP address..."
    sleep 5
  fi
done

while :; do
  if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$ip_address "echo 'SSH connection established'"; then
    break
  else
    echo "Waiting for SSH service..."
    sleep 5
  fi
done

echo "Droplet is ready at IP: $ip_address"
