#!/usr/bin/env python

# Will attempt to find all the licensing information for public repositories in a Github organisation.

# To use this script:
# * Setup 'Licensee' in a Docker container: https://github.com/licensee/licensee
# * Create and activate a virtualenv
# * pip install jq
# * pip install PyGithub
# * pip install prettytable
# * pip install toml
# * export GITHUB_PAT=<pat> (retrieve from your Github account)
# * export BASE_DEV_PATH=<path> (e.g. /home/chris/dev)

import argparse
import jq
import os
import re
import subprocess
import sys
from pathlib import Path

import toml
from github import Github, UnknownObjectException
from prettytable import PrettyTable


class RepoLicenseInfo:
    def __init__(self, organisation, name, is_fork, crate_exclusions):
        self.organisation = organisation
        self.name = name
        self.is_fork = is_fork
        self.licenses = {}
        self.crate_exclusions = crate_exclusions
        self.crate_manifest_licenses = {}
        # These are the type and name of license for the repo as reported by the Github API.
        self.github_license_key = ""
        self.github_license_name = ""
        self.files_copyright_notice_years = []
        self.files_without_copyright_notice = []

        base_dev_path = os.getenv("BASE_DEV_PATH")
        if not base_dev_path:
            raise ValueError("The BASE_DEV_PATH environment variable must be set")
        self.repo_path = Path(os.path.join(base_dev_path, "github", organisation, name))

        self.license_cache_path = Path.home().joinpath(
            ".license_cache", "github", organisation, name
        )
        if not self.license_cache_path.exists():
            self.license_cache_path.mkdir(parents=True)
        self.cargo_cache_path = Path.home().joinpath(
            ".license_cache", "cargo", organisation, name
        )
        if not self.cargo_cache_path.exists():
            self.cargo_cache_path.mkdir(parents=True)

        github_pat = os.getenv("GITHUB_PAT")
        if not github_pat:
            raise ValueError("The GITHUB_PAT environment variable must be set")
        self.github = Github(github_pat)

    def is_rust_repo(self):
        for _, _, files in os.walk(self.repo_path):
            for name in files:
                if name == "Cargo.toml":
                    return True

    def is_cargo_workspace(self):
        if not self.is_rust_repo():
            return False
        count = 0
        for _, _, files in os.walk(self.repo_path):
            for name in files:
                if name == "Cargo.toml":
                    count += 1
        return count > 1

    def is_root_manifest(self, path):
        root_manifest_path = Path(os.path.join(self.repo_path, "Cargo.toml"))
        return root_manifest_path == path

    def run_licensee(self, path, with_json_output=False):
        print(f"Running licensee on {self.name}...")
        docker_command = [
            "docker",
            "run",
            "--rm",
            "--volume",
            f"{self.repo_path}:/usr/src/target",
            "licensee",
            "detect",
            path,
        ]
        if with_json_output:
            docker_command.append("--json")
        result = subprocess.run(
            docker_command,
            capture_output=True,
            text=True,
        )
        return result.stdout

    def get_license_from_readme(self, path):
        readme_container_path = Path("/usr/src/target")
        if path == self.repo_path.joinpath("README.md"):
            # Non-workspace repo: README is at the root of the repo.
            readme_container_path = readme_container_path.joinpath("README.md")
        else:
            # Workspace repo: README is in the crate directory.
            i = len(path.parent.parts) - 1
            readme_container_path = readme_container_path.joinpath(
                path.parent.parts[i], "README.md"
            )
        if path.exists():
            licensee_output = self.run_licensee(readme_container_path)
            license_line = licensee_output.splitlines()[0]
            split = license_line.split(":")
            return split[1].strip()
        return "No README"

    def parse_crate_licensing(self):
        if not self.is_rust_repo():
            return None
        for path, _, files in os.walk(self.repo_path):
            for name in files:
                if name == "Cargo.toml":
                    manifest_path = Path(os.path.join(path, name))
                    readme_path = Path(os.path.join(path, "README.md"))
                    manifest = toml.load(manifest_path)
                    if self.is_cargo_workspace():
                        if self.is_root_manifest(manifest_path):
                            continue
                    crate_name = manifest["package"]["name"]
                    if crate_name in self.crate_exclusions:
                        continue
                    print(f"Obtaining licensing info for {crate_name} crate...")
                    manifest_license = "None"
                    if "license" in manifest["package"]:
                        manifest_license = manifest["package"]["license"]
                    readme_license = self.get_license_from_readme(readme_path)
                    self.crate_manifest_licenses[crate_name] = (
                        manifest_license,
                        readme_license,
                    )

    def parse_github_license_info(self):
        cached_license_info_path = self.license_cache_path.joinpath("info")
        if cached_license_info_path.exists():
            print(f"Reading Github license info for {self.name} from cache...")
            with open(cached_license_info_path, "r") as fp:
                content = fp.readlines()
                split = content[0].split(":")
                key = split[1].strip()
                split = content[1].split(":")
                name = split[1].strip()
                self.github_license_key = key
                self.github_license_name = name
                return
        print(f"Reading Github license info for {self.name} from API...")
        try:
            license_info = self.github.get_repo(
                f"{self.organisation}/{self.name}"
            ).get_license()
            key = license_info.license.key
            name = license_info.license.name
        except UnknownObjectException:
            key = "None"
            name = "None"
        with open(cached_license_info_path, "w") as fp:
            fp.write(f"key: {key}\n")
            fp.write(f"name: {name}\n")
        self.github_license_key = key
        self.github_license_name = name

    def parse_repo_license_info(self):
        licensee_output = self.run_licensee("/usr/src/target", with_json_output=True)
        # It's possible to exclude the "Cargo.toml" with jq, but it results in None being included
        # in the list, which would need to be filtered anyway.
        found_license_files = [
            x
            for x in jq.compile(".matched_files[].filename")
            .input(text=licensee_output)
            .all()
            if x != "Cargo.toml"
        ]
        # The README is a special case that never has an attribution key.
        for license in [x for x in found_license_files if x != "README.md"]:
            attribution = (
                jq.compile(
                    f'.matched_files[] | select(.filename == "{license}") | .attribution'
                )
                .input(text=licensee_output)
                .first()
            )
            # Capture year from text like "Copyright 2020 MaidSafe.net limited."
            if attribution:
                match = re.search("(\\d{4})", attribution)
                if match:
                    self.licenses[license] = match.group()
                else:
                    self.licenses[license] = "No year"
            else:
                self.licenses[license] = "No year"
        if "README.md" in found_license_files:
            license = (
                jq.compile(
                    '.matched_files[] | select(.filename == "README.md") | .matched_license'
                )
                .input(text=licensee_output)
                .first()
            )
            if license:
                self.licenses["README.md"] = license

    def parse_source_files_license_info(self):
        if not self.is_rust_repo():
            return
        print(f"Examining {self.name} source files for copyright notices...")
        for path, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(".rs"):
                    source_file_path = os.path.join(path, file)
                    with open(source_file_path) as fp:
                        first_line = fp.readlines()[0]
                        match = re.match(".*Copyright (\\d{4}).*", first_line)
                        if match:
                            year = match.group(1)
                            if year not in self.files_copyright_notice_years:
                                self.files_copyright_notice_years.append(year)
                        else:
                            self.files_without_copyright_notice.append(source_file_path)

    def get_crate_license_info(self):
        info = []
        for key in self.crate_manifest_licenses:
            manifest_license = self.crate_manifest_licenses[key][0]
            readme_license = self.crate_manifest_licenses[key][1]
            info.append((key, manifest_license, readme_license))
        return info


class CrateLicenseReport:
    def __init__(self, repo_license_info_list):
        self.repo_license_info_list = repo_license_info_list

    def print_table(self):
        table = PrettyTable()
        table.field_names = ["CRATE", "MANIFEST LICENSE", "README LICENSE"]
        for repo in self.repo_license_info_list:
            for license_info in repo.get_crate_license_info():
                table.add_row(license_info)
        table.align = "l"
        print(table.get_string(sortby="CRATE"))


class RepoLicenseReport:
    def __init__(self, repo_license_info_list):
        self.repo_license_info_list = repo_license_info_list

    def get_license_column_value(self, licenses, license_file):
        if license_file in licenses:
            return licenses[license_file]
        return "None"

    def print_table(self):
        table = PrettyTable()
        table.field_names = [
            "REPO",
            "GITHUB",
            "README",
            "COPYRIGHT",
            "LICENSE",
            "LICENSE-APACHE",
            "LICENSE-BSD",
            "LICENSE-MIT",
        ]
        for repo in self.repo_license_info_list:
            name = f"{repo.name}*" if repo.is_fork else f"{repo.name}"
            row = [name, repo.github_license_key]
            row.append(self.get_license_column_value(repo.licenses, "README.md"))
            row.append(self.get_license_column_value(repo.licenses, "COPYRIGHT"))
            row.append(self.get_license_column_value(repo.licenses, "LICENSE"))
            row.append(self.get_license_column_value(repo.licenses, "LICENSE-APACHE"))
            row.append(self.get_license_column_value(repo.licenses, "LICENSE-BSD"))
            row.append(self.get_license_column_value(repo.licenses, "LICENSE-MIT"))
            table.add_row(row)
        table.align = "l"
        print(table.get_string(sortby="REPO"))


class SourceFilesLicenseReport:
    def __init__(self, repo_license_info_list):
        self.repo_license_info_list = repo_license_info_list

    def print_table(self):
        table = PrettyTable()
        table.field_names = [
            "REPO",
            "FILES MISSING COPYRIGHT NOTICE",
            "YEAR(S) IN COPYRIGHT NOTICE",
        ]
        for repo in self.repo_license_info_list:
            row = [repo.name, len(repo.files_without_copyright_notice)]
            year_column_value = ""
            if repo.files_copyright_notice_years:
                for year in repo.files_copyright_notice_years:
                    year_column_value += f"{year}, "
                year_column_value = year_column_value.removesuffix(", ")
            else:
                year_column_value = "None"
            row.append(year_column_value)
            table.add_row(row)
        table.align = "l"
        print(table.get_string(sortby="REPO"))


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
    parser.add_argument(
        "--crate-exclusions-path",
        help="Path to a file containing a list of crates to exclude",
    )
    args = parser.parse_args()
    args = parser.parse_args()
    return (args.organisation, args.repo_exclusions_path, args.crate_exclusions_path)


def get_exclusion_list(exclusions_path):
    exclusions = []
    if exclusions_path:
        with open(exclusions_path, "r") as fp:
            for line in fp:
                exclusions.append(line.strip())
    return exclusions


def get_repo_list(organisation, exclusions):
    print(f"Retrieving list of public repositories for {organisation}...")
    github_pat = os.getenv("GITHUB_PAT")
    github = Github(github_pat)
    org = github.get_organization(organisation)
    repos = org.get_repos("public")
    sorted_repos = []
    for repo in repos:
        if repo.name not in exclusions and not repo.archived:
            sorted_repos.append(repo)
    return sorted_repos


def main():
    organisation, repo_exclusions_path, crate_exclusions_path = get_args()
    repo_exclusions = get_exclusion_list(repo_exclusions_path)
    crate_exclusions = get_exclusion_list(crate_exclusions_path)

    repos = get_repo_list(organisation, repo_exclusions)
    license_info_list = []
    for repo in repos:
        license_info = RepoLicenseInfo(
            organisation, repo.name, repo.fork, crate_exclusions
        )
        license_info.parse_crate_licensing()
        license_info.parse_github_license_info()
        license_info.parse_repo_license_info()
        license_info.parse_source_files_license_info()
        license_info_list.append(license_info)
    crate_report = CrateLicenseReport(license_info_list)
    crate_report.print_table()
    repo_report = RepoLicenseReport(license_info_list)
    repo_report.print_table()
    source_files_report = SourceFilesLicenseReport(license_info_list)
    source_files_report.print_table()
    return 0


if __name__ == "__main__":
    sys.exit(main())
