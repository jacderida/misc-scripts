#!/usr/bin/env bash

# Uses the `gh` tool to get a list of public repositories for a given organisation, then sorts them
# by their last commit date. Unfortunately you don't get the last commit date from `gh repo view`,
# so you need to clone all the repositories.

set -e

BASE_DEV_PATH="$HOME/dev/github"

opts=$(getopt \
  --name "list-public-repos-with-activity" --options uo:l: --longoptions update,org:,limit: -- "$@")
eval set -- "$opts"
while true; do
  case "$1" in
    -o | --org)
      org="$2"
      shift 2
      ;;
    -l | --limit)
      limit="$2"
      shift 2
      ;;
    -u | --update)
      update=1
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
  echo "Usage: $0 [-o/--org <string>] [-l/--limit <int>] [-u/--update]"
  exit 1
}

function generate_repo_list() {
  declare -a list=()
  repos=( \
    $(gh repo list \
      ${org} --public --no-archived --limit ${limit} | awk '{print $1}' | awk -F '/' '{print $2}' | sort) )
  cd $BASE_DEV_PATH/$org
  for repo in "${repos[@]}"
  do
    if [[ ! -d "$repo" ]]; then
      git clone git@github.com:${org}/${repo}.git
      cd $repo
      last_commit_date=$(git log --oneline --pretty=format:%as | head -n 1)
      list+=("$last_commit_date $repo")
      cd ..
    fi
    cd $repo
    branch=$(git branch --show-current)
    if [[ $branch != "master" ]] && [[ $branch != "main" ]]; then
      echo "The ${repo} repo has switched to a different branch"
      exit 1
    fi
    if [[ -n "$update" ]]; then git pull; fi
    last_commit_date=$(git log --oneline --pretty=format:%as | head -n 1)
    list+=("$last_commit_date $repo")
    cd ..
  done

  IFS=$'\n' sorted=($(sort <<<"${list[*]}"))
  unset IFS
}

function print_table() {
  printf "%-12s %s\n" "LAST COMMIT" "REPO"
  for item in "${sorted[@]}"
  do
    date=$(echo $item | awk '{print $1}')
    repo=$(echo $item | awk '{print $2}')
    printf "%-12s %s\n" "${date}" "${repo}"
  done
}

generate_repo_list
print_table
