#!/usr/bin/env python

import argparse
import os
import sys

from datetime import datetime
from github import Github
from prettytable import PrettyTable


def get_args():
    parser = argparse.ArgumentParser(
        prog="list-licenses-for-repos",
        description="List the licenses for all repositories in an organisation. Has a particular emphasis on Rust projects.",
    )
    parser.add_argument(
        "organisation",
        help="The name of the organisation whose repos you wish to list",
    )
    parser.add_argument(
        "--repo-exclusions-path",
        help="Path to a file containing a list of repositories to exclude",
    )
    args = parser.parse_args()
    args = parser.parse_args()
    return (args.organisation, args.repo_exclusions_path)


def get_exclusion_list(exclusions_path):
    exclusions = []
    if exclusions_path:
        with open(exclusions_path, "r") as fp:
            for line in fp:
                exclusions.append(line.strip())
    return exclusions


def get_repo_list(organisation, exclusions, github):
    print(f"Retrieving list of public repositories for {organisation}...")
    org = github.get_organization(organisation)
    repos = org.get_repos("public")
    sorted_repos = []
    for repo in repos:
        if repo.name not in exclusions and not repo.archived:
            sorted_repos.append(repo)
    return sorted_repos


def main():
    github_pat = os.getenv("GITHUB_PAT")
    github = Github(github_pat)
    organisation, repo_exclusions_path = get_args()
    repo_exclusions = get_exclusion_list(repo_exclusions_path)
    repos = get_repo_list(organisation, repo_exclusions, github)
    for repo in repos:
        table = PrettyTable()
        table.field_names = ["CREATED", "NUMBER", "TITLE", "UPDATED"]
        for issue in repo.get_issues(state="open"):
            created = datetime.strftime(issue.created_at, "%Y-%m-%d")
            updated = datetime.strftime(issue.updated_at, "%Y-%m-%d")
            title = (issue.title[:70] + "...") if len(issue.title) > 70 else issue.title
            table.add_row([created, issue.number, title, updated])
        table.align = "l"
        print(f"{repo.full_name}")
        print(table.get_string(sortby="CREATED"))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
