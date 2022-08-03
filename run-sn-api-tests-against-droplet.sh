#!/usr/bin/env bash

set -e

BASE_DEV_PATH="$HOME/dev/github"

opts=$(getopt \
  --name "run-sn-api-tests-against-droplet" --options rlo:n: --longoptions rebuild,local,org:,name: -- "$@")
eval set -- "$opts"
while true; do
  case "$1" in
    -o | --org)
      org="$2"
      shift 2
      ;;
    -n | --name)
      testnet_name="$2"
      shift 2
      ;;
    -l | --local)
      local_bin=1
      shift
      ;;
    -r | --rebuild)
      rebuild=1
      shift
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
  echo "Usage: $0 [-o/--org <string>] [-n/--name <string>] [-l/--local] [-r/--rebuild]"
  echo "org: use either your fork or the main maidsafe repo"
  echo "name: the name of the droplet testnet"
  echo "local: set this flag to build the node binary locally"
  echo "rebuild: set this flat to perform a cargo clean"
  exit 1
}

function build_node() {
  if [[ $local_bin -eq 1 ]]; then
    (
      local path="$BASE_DEV_PATH/$org/safe_network"
      echo "Building sn_node from $path"
      cd "$path"
      if [[ $rebuild -eq 1 ]]; then cargo clean; fi
      cargo build --bin sn_node --release
    )
  fi
}

function drop_current_droplet_testnet() {
  (
    local path="$BASE_DEV_PATH/$org/sn_testnet_tool"
    cd "$path"
    cmd="make clean-$testnet_name "
    echo "Running $cmd"
    eval "$cmd"
  )
}

function create_droplet_testnet() {
  (
    local path="$BASE_DEV_PATH/$org/sn_testnet_tool"
    cd "$path"
    cmd="make $testnet_name "
    if [[ $local_bin -eq 1 ]]; then
      cmd="${cmd}SN_TESTNET_NODE_BIN_PATH=\"$BASE_DEV_PATH/$org/safe_network/target/release/sn_node\" "
    fi
    cmd="${cmd}SN_TESTNET_NODE_COUNT=30"
    echo "Running $cmd"
    eval "$cmd"
  )
}

function run_sn_api_tests() {
  (
    echo "Sleeping for 60 seconds before hitting the network..."
    sleep 60
    local path="$BASE_DEV_PATH/$org/safe_network"
    cd "$path"
    cargo nextest run --profile ci --release --package sn_client --test-threads 2 client --retries 0
    export TEST_ENV_GENESIS_DBC_PATH="$HOME/.safe/genesis_dbc"
    cargo nextest run --profile ci --release --package sn_api --test-threads 10 --retries 0
  )
}

build_node
drop_current_droplet_testnet
create_droplet_testnet
run_sn_api_tests
