#!/usr/bin/env bash

set -e

do_pat=$(cat ~/.digital_ocean_settings | head -n 1 | awk '{ print $4 }')

curl --request GET \
  --header "Content-Type: application/json" \
  --header "Authorization: Bearer ${do_pat}" \
  https://api.digitalocean.com/v2/account/keys | jq '.ssh_keys[] | .name, .id'
