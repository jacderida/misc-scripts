#!/usr/bin/env bash

set -e

function usage() {
  echo "Usage: $0 -p/--path <path-of-repo-list-file>"
  exit 1
}

opts=$(getopt --name "make-repositories-private" --options p: --longoptions path: -- "$@")
eval set -- "$opts"
while true; do
  case "$1" in
    -p | --path)
      path="$2"
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

if [[ ! -n "$path" ]]; then usage; fi

declare -a repos
while IFS= read -r repo; do repos+=("$repo"); done < $path
echo "${repos[@]}"
read -p "Proceed to make these repositories private? [y/n] " confirm
if [[ $confirm == "y" ]]; then
  for repo in "${repos[@]}"
  do
    echo -n "Making $repo private..."
    gh repo edit $repo --visibility private
    echo "done"
    gh repo archive $repo --confirm
  done
fi
