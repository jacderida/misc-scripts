#!/usr/bin/env bash

# Uses the `doctl` tool to delete Digital Ocean droplets matching a given name. 
# There's a confirm prompt to protect against removing machines you didn't intend to.

set -e

opts=$(getopt --name "delete-droplets" --options n: --longoptions name: -- "$@")
eval set -- "$opts"
while true; do
  case "$1" in
    -n | --name)
      name="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "Unexpected option: $1"
      usage
      ;;
  esac
done

function usage() {
  echo "Usage: $0 -n/--name <string>"
  exit 1
}

if [[ ! -n "$name" ]]; then usage; fi

echo "Query for droplets whose name starts with $name..."
doctl compute droplet list --output json | jq ".[] | select(.name | startswith(\"$name\")) | .name"
read -p "Proceed to remove these? [y/n] " confirm
if [[ $confirm == "y" ]]; then
  list=( $(doctl \
    compute droplet list --output json | jq -r ".[] | select(.name | startswith(\"$name\")) | .id") )
  for droplet in "${list[@]}"
  do
    echo -n "Removing droplet $droplet..."
    doctl compute droplet delete "$droplet" --force
    echo "done"
  done
fi
