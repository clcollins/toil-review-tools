#!/usr/bin/env python3

import argparse
import os
import re
import json
import yaml

from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from pdpyras import APISession, PDClientError

default_token_file = Path.home().joinpath(".config", "pagerduty", "pd.yml")

default_result_count = 5
default_days_count = 7
pd_time_format = "%Y-%m-%dT%H:%M:%SZ"

sre_team_ids = ["PASPK4G"]
pd_layers = {
    1: "22:30",
    2: "3:30",
    3: "8:30",
    4: "13:30",
    5: "18:00",
}

# class helpers provides a wrapper around datetime.today() to allow for mocking
class helpers:
    def today():
        return datetime.today()


def main():
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest="subcommand", required=True)

    alerts_parser = subparser.add_parser("alerts", help="retrieve alert metrics")
    populate_args(alerts_parser)

    clusters_parser = subparser.add_parser("clusters", help="retrieve cluster metrics")
    populate_args(clusters_parser)

    all_parser = subparser.add_parser("all", help="retrieve all metrics")
    populate_args(all_parser)

    args = parser.parse_args()

    if args.layers is None:
        args.layers = pd_layers.keys()

    print(
        f"Including incidents from layers: {', '.join(str(item) for item in args.layers)}"
    )

    # Retrieve incidents from PagerDuty API
    incidents = get_incidents(
        args.days,
        args.layers,
        args.token,
        args.token_file,
        args.verbose,
        args.cache_file,
        args.no_cache,
    )

    if incidents is None:
        print("No incidents found")
        return

    current_incidents, previous_incidents = split_incidents_by_period(
        incidents, args.days
    )

    print(
        f"High incidents in the last {args.days} days before today: {len(current_incidents)}"
    )
    print(
        f"Percent Change from the previous period: {percent_change(len(current_incidents), len(previous_incidents))}%\n"
    )

    debug(
        args.verbose,
        f"Current period incidents ({args.days} days): {len(current_incidents)}",
        f"Previous period incidents ({args.days} days): {len(previous_incidents)}\n",
    )

    if args.subcommand == "alerts":
        alerts(current_incidents, args.count)
    elif args.subcommand == "clusters":
        clusters(current_incidents, args.count)
    elif args.subcommand == "all":
        alerts(current_incidents, args.count)
        print("")
        clusters(current_incidents, args.count)


# Add shared args to the subparsers
def populate_args(parser):
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        required=False,
        default=default_result_count,
        help=f"Number of results to display (default: {default_result_count})",
    )
    parser.add_argument(
        "-l",
        "--layers",
        nargs="+",
        type=int,
        required=False,
        choices=pd_layers.keys(),
        help="Layer (region) to filter",
    )
    parser.add_argument(
        "-d",
        "--days",
        type=int,
        required=False,
        default=default_days_count,
        help=f"Number of previous days to include (default: {default_days_count})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        required=False,
        default=False,
        help="Enable verbose output",
    )

    auth_group = parser.add_mutually_exclusive_group()
    auth_group.add_argument(
        "-a",
        "--token_file",
        type=lambda p: Path(p).absolute(),
        required=False,
        default=default_token_file,
        help="Path to PagerDuty token YAML file",
    )
    auth_group.add_argument(
        "-t", "--token", type=str, required=False, help="PagerDuty API token"
    )

    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument(
        "--no-cache",
        action="store_true",
        required=False,
        default=False,
        help="Disable caching",
    )
    cache_group.add_argument(
        "--cache-file",
        type=lambda p: Path(p).absolute(),
        required=False,
        help="Path to alternative cache file, Pagerduty-formatted",
    )

    return parser


# cache_to_file wraps get_incidents and writes the results to a cache file,
# or returns caches results if appropriate
def cache_to_file(get_incidents_func):
    def decorator(days, layers, token, token_file, verbose, cache_file, no_cache):

        cache_dir, cache_file = select_cache_file(cache_file, layers, days)

        # Just read incidents from cache file if appropriate
        if should_read_from_cache(no_cache, cache_file, verbose):
            incidents = read_incidents_from_cache(cache_file, verbose)
            debug(verbose, f"Cache hit; {len(incidents)} items")

            return incidents

        # Retrieve data from PagerDuty API
        # with the get_incidents function
        debug(verbose, f"Cache miss; retrieving data from PagerDuty API")
        incidents = get_incidents_func(days, layers, token, token_file, verbose)

        write_incidents_to_cache(incidents, cache_dir, cache_file, verbose)

        return incidents

    return decorator


# select_cache_file returns the cache directory and file name based on the
# provided cache_file input argument, or a default if None
def select_cache_file(cache_file, layers, days):

    prefix_string = "incident-cache"
    date_string = str(helpers.today().date())
    layer_string = "-".join(str(item) for item in layers)
    days_string = f"{days}-day"

    cache_file_name = f"{prefix_string}_{date_string}_{layer_string}_{days_string}.json"

    file = (
        Path(cache_file).absolute()
        if cache_file
        else Path.home().joinpath(".cache", "toil-review-metrics", cache_file_name)
    )

    parent = file.parents[0]

    return parent, file


# should_read_from_cache returns True if the cache file exists and the
# --no-cache flag is set, and the cache file is not stale (older than a day)
def should_read_from_cache(no_cache, cache_file, verbose):
    # Never read from cache if --no-cache is set
    if no_cache is True:
        debug(verbose, f"-no-cache flag set, not reading from cache")
        return False

    # Can't read from cache if cache file doesn't exist
    if cache_file.exists() is False:
        debug(
            verbose, f'Cache file "{cache_file}" does not exist, not reading from cache'
        )
        return False

    # Don't read from cache if cache file is older than 1 day
    cache_file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)

    if cache_file_mtime < (datetime.now() - timedelta(days=1)):
        debug(
            verbose,
            f'Cache file "{cache_file}" is stale ({cache_file_mtime}), '
            f"not reading from cache",
        )
        return False

    return True


# read_incidents_from_cache reads incidents from the cache file
def read_incidents_from_cache(cache_file, verbose):
    debug(verbose, f"Getting incidents from cache file: {cache_file}")
    with cache_file.open() as f:
        return json.load(f)


# write_incidents_to_cache writes incidents to the cache file
def write_incidents_to_cache(incidents, cache_dir, cache_file, verbose):
    if cache_dir.exists() is False:
        debug(verbose, f"Creating cache directory: {cache_dir}")
        cache_dir.mkdir(parents=True, exist_ok=True)

    debug(verbose, f"Writing cache file: {cache_file}")
    with cache_file.open(mode="w+", newline="", encoding="utf-8") as f:
        json.dump(incidents, f)


@cache_to_file
def get_incidents(
    num_days, layers, token, token_file, verbose, cache_file=None, no_cache=True
):
    # TODO: COMBINE REQUESTS INTO ONE AND PARSE
    request_params = {
        "urgencies[]": ["high"],
        "team_ids[]": sre_team_ids,
        "since": helpers.today() - timedelta(days=num_days * 2),
        "until": helpers.today(),
    }

    # Retrieve incidents from PagerDuty API
    api_token = retrieve_token(verbose, token, token_file)
    session = APISession(api_token)

    try:
        request_params.update(request_params)
        debug(verbose, f"Requesting incidents")
        debug(verbose, f"Request parameters: {request_params}")

        incidents = [
            i
            for i in session.list_all("incidents", params=request_params)
            if (is_in_layer(i["created_at"], layers) and (i["urgency"] == "high"))
        ]

        debug(verbose, f"Found {len(incidents)} incidents")

    except PDClientError as e:
        if e.response:
            if e.response.status_code == 404:
                print("User not found")
            elif e.response.status_code == 401:
                raise e
        else:
            raise e

    return incidents


def split_incidents_by_period(incidents, days):
    current, previous = [], []
    for i in incidents:
        if datetime.strptime(i["created_at"], pd_time_format) > (
            helpers.today() - timedelta(days=days)
        ):
            current.append(i)
        else:
            previous.append(i)

    return current, previous


# alerts returns a dict of top alerts and the count of each
def alerts(incidents, count):
    alert_list = [parse_description_for_alerts(item["summary"]) for item in incidents]

    print("COUNT\tINCIDENT")
    for k, v in Counter(alert_list).most_common(count):
        print(f"{v}\t{k}")


# clusters returns a dict of top alerting clusters and the count of each
def clusters(incidents, count):
    cluster_list = [
        parse_description_for_cluster(item["service"]["summary"])
        for item in incidents
        if item["service"]["summary"] != "prod-deadmanssnitch"
        and item["service"]["summary"] != "Zabbix Service"
        and item["service"]["summary"] != "app-sre-alertmanager"
    ]

    print("COUNT\tCLUSTER")
    for k, v in Counter(cluster_list).most_common(count):
        print(f"{v}\t{k}")


# parse_description_for_alerts parses the description of an incident to
# remove unique values or extraneous text
def parse_description_for_alerts(description):
    strings_to_remove = {
        # Clean SRE-added '[SOMETHING]' prefixes, with optional dash
        r"\[.*\]\s(-\s)?": "",
        # Combine "CRITICAL (1)" and "CRITICAL (2)" alerts
        r"\s(CRITICAL|WARNING)\s\(\d*\)$": "",
        # Combine all ClusterHasGoneMissing alerts
        r".*has\sgone\smissing$": "ClusterHasGoneMissing",
        # Zabbix-style (?) alerts
        r"\son\s.*\s\:\s.*$": "",
    }

    strings_to_match = [
        r"^ClusterProvisioningDelay",
    ]

    # Removes extraneous information from the description
    for k, v in strings_to_remove.items():
        description = re.sub(k, v, description)

    # Selects the relevant information from the description
    for i in strings_to_match:
        match = re.compile(i).match(description)
        description = match.group() if match else description

    return description


# parse_description_for_cluster parses the description of an incident to
# remove unique data and extraneous text
def parse_description_for_cluster(description):
    strings_to_remove = [
        # Clean SRE-added '[SOMETHING]' prefixes
        r"\[.*\]\s",
        # ClusterHasGoneMissing
        r"\shas\sgone\smissing",
        # docker.ping failed
        r"docker.ping\sfailed\son\s",
        r"-compute.*$",
        # ClusterProvisioningDelay
        r"ClusterProvisioningDelay\s.*\shive\s\(",
        r"\sProvisionFailed.*$",
        # Disk Free
        r"Filesystem.*free\sdisk\sspace\son\s",
        r":\sPROBLEM\s.*$",
        # Strip leading 'osd-'
        r"^osd-",
        # Strip trailing '-hive-cluster'
        r"-hive-cluster$",
    ]

    for i in strings_to_remove:
        description = re.sub(i, "", description)

    return description


# is_in_layer checks if a datetime is in the shift covered by the layer
def is_in_layer(time_string, requested_layers):
    for layer in requested_layers:
        time_format = "%H:%M"
        if is_time_between(
            datetime.strptime(pd_layers[layer], time_format).time(),
            datetime.strptime(pd_layers[next_layer(layer)], time_format).time(),
            datetime.strptime(time_string, pd_time_format).time(),
        ):
            return True

    # If not in any layers, return False
    return False


# is_time_between checks if a time is between two other times
def is_time_between(startTime, endTime, checkTime):
    if startTime < endTime:
        return startTime <= checkTime <= endTime
    else:  # over midnight e.g., 23:30-04:15
        return checkTime >= startTime or checkTime <= endTime


# next_layer handles the edge case where the layer is the last layer
def next_layer(layer):
    return layer + 1 if layer < len(pd_layers) else 1


# authenticate_to_pd authenticates to PagerDuty API using the provided token,
# or the token in the token file as a fallback
def retrieve_token(verbose, token, token_file):
    if token:
        debug(verbose, "Using provided token")
        return token
    elif os.getenv("PD_TOKEN"):
        debug(verbose, "Using PD_TOKEN environment variable")
        return os.getenv("PD_TOKEN")
    else:
        debug(verbose, "Using provided token_file")
        with open(token_file, "r") as yaml_data:
            try:
                data = yaml.safe_load(yaml_data)
                return data["authtoken"]

            except yaml.YAMLError as err:
                print(err)


def percent_change(current, previous):
    try:
        return round(((current - previous) / previous) * 100, 2)
    except ZeroDivisionError:
        print("ZeroDivisionError: No previous data to compare to")
        print("Are you using a custom cache file?")
        return -0


def debug(verbose, *args):
    if verbose:
        for i in args:
            print(f"[DEBUG] {i}")


if __name__ == "__main__":
    main()
