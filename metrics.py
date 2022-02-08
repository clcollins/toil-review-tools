#!/usr/bin/env python3

import argparse
import re
import yaml

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from pdpyras import APISession, PDClientError

default_result_count = 5
default_days_count = 7
default_token_file = Path.home().joinpath(".config", "pagerduty", "pd.yml")
pd_time_format = "%Y-%m-%dT%H:%M:%SZ"

sre_team_ids = ["PASPK4G"]
pd_layers = {
    1: "22:30",
    2: "3:30",
    3: "8:30",
    4: "13:30",
    5: "18:00",
}


def main():
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest="subcommand", required=True)

    alerts_parser = subparser.add_parser("alerts", help="retrieve alert metrics")
    populate_args(alerts_parser)

    clusters_parser = subparser.add_parser("clusters", help="retrieve cluster metrics")
    populate_args(clusters_parser)

    args = parser.parse_args()

    if args.layers is None:
        args.layers = pd_layers.keys()

    print(
        f"Including incidents from layers: {', '.join(str(item) for item in args.layers)}"
    )

    # Retrieve incidents from PagerDuty API
    incidents, previous_incidents = get_incidents(args)

    if incidents is None:
        print("No incidents found")
        return

    if previous_incidents is None:
        print("No previous incidents found")
        return

    debug(
        args.verbose,
        f"Current period incidents ({args.days} days): {len(incidents)}",
        f"Previous period incidents ({args.days} days): {len(previous_incidents)}",
    )

    print(f"High incidents in the last {args.days} days: {len(incidents)}")
    print(
        f"Percent Change from the previous period: {percent_change(len(incidents), len(previous_incidents))}%\n"
    )

    if args.subcommand == "alerts":
        alerts(incidents, args.count)
    elif args.subcommand == "clusters":
        clusters(incidents, args.count)


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

    return parser


def get_incidents(args):
    request_params = {
        "urgencies[]": ["high"],
        "team_ids[]": sre_team_ids,
    }

    this_period_request_params = {
        "since": datetime.now() - timedelta(days=args.days),
        "until": datetime.now(),
    }

    previous_period_request_params = {
        "since": datetime.now() - timedelta(days=args.days * 2),
        "until": datetime.now() - timedelta(days=args.days),
    }

    # Retrieve incidents from PagerDuty API
    api_token = authenticate_to_pd(args.token, args.token_file)
    session = APISession(api_token)

    try:
        request_params.update(this_period_request_params)
        debug(args.verbose, f"Requesting current period incidents for {args.days} days")
        debug(args.verbose, f"Request parameters: {request_params}")

        incidents = [
            i
            for i in session.list_all("incidents", params=request_params)
            if (is_in_layer(i["created_at"], args.layers) and (i["urgency"] == "high"))
        ]

    except PDClientError as e:
        if e.response:
            if e.response.status_code == 404:
                print("User not found")
            elif e.response.status_code == 401:
                raise e
        else:
            raise e

    # Now get the previous period incidents
    try:
        request_params.update(previous_period_request_params)
        debug(
            args.verbose, f"Requesting previous period incidents for {args.days} days"
        )
        debug(args.verbose, f"Request parameters: {request_params}")

        previous_incidents = [
            i
            for i in session.list_all("incidents", params=request_params)
            if (is_in_layer(i["created_at"], args.layers) and (i["urgency"] == "high"))
        ]

    except PDClientError as e:
        if e.response:
            if e.response.status_code == 404:
                print("User not found")
            elif e.response.status_code == 401:
                raise e
        else:
            raise e

    return incidents, previous_incidents


# alerts returns a dict of top alerts and the count of each
def alerts(incidents, count):
    alert_list = [
        parse_description_for_alerts(item["description"]) for item in incidents
    ]

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
        r"(CRITICAL|WARNING)\s\(\d*\)$": "",
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
        if is_time_between(
            convert_time_from_string(pd_layers[layer]),
            convert_time_from_string(pd_layers[layer_plus_one(layer)]),
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


# layer_plus_one handles the edge case where the layer is the last layer
def layer_plus_one(layer):
    return layer + 1 if layer < len(pd_layers) else 1


# convert_time_from_string converts a string of the form 'HH:MM' to a datetime
def convert_time_from_string(time_string):
    return datetime.strptime(time_string, "%H:%M").time()


# authenticate_to_pd authenticates to PagerDuty API using the provided token,
# or the token in the token file as a fallback
def authenticate_to_pd(token, token_file):
    if token is None:
        with open(token_file, "r") as yaml_data:
            try:
                data = yaml.safe_load(yaml_data)
                return data["authtoken"]

            except yaml.YAMLError as err:
                print(err)

    return token


def percent_change(current, previous):
    return round(((current - previous) / previous) * 100, 2)


def debug(verbose, *args):
    if verbose:
        for i in args:
            print(f"[DEBUG] {i}")


if __name__ == "__main__":
    main()
