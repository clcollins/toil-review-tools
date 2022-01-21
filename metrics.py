#!/usr/bin/env python3

# NOTES:
# API and CSV return some different headers
# | CSV              | API
# | ['created_at']   | ['created_on']
# | ['service_name'] | ['service']['summary']

from email.policy import default
import sys
import argparse
import csv
import re
import yaml

from pdpyras import APISession, PDClientError

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

default_token_file = Path.home().joinpath('.config', 'pagerduty', 'pd.yml')
# default_csv_name = 'incidents.csv'
default_result_count = 5
pd_time_format = '%Y-%m-%dT%H:%M:%SZ'

sre_team_ids = ['PASPK4G']

layers = {
	1: '22:30',
	2: '3:30',
	3: '8:30',
	4: '13:30',
	5: '18:00',
}


def populate_args(parser):

	parser.add_argument('-c', '--count', type=int, required=False, default=default_result_count,
		help=f'Number of results to display (default: {default_result_count})')
	# parser.add_argument('-f', '--file', type=str, required=True, default=default_csv_name,
	#	help=f'PagerDuty CSV formatted incident file (default: {default_csv_name})')
	parser.add_argument('-l', '--layer', type=int, required=True,
		choices=layers.keys(), help='Layer (region) to filter')

	auth_group = parser.add_mutually_exclusive_group()
	auth_group.add_argument('-a', '--token_file',
		type=lambda p: Path(p).absolute(),
		required=False, default=default_token_file,
		help='Path to PagerDuty token YAML file')
	auth_group.add_argument('-t', '--token', type=str, required=False,
		help='PagerDuty API token')

	return parser

def main():
	parser = argparse.ArgumentParser()
	subparser = parser.add_subparsers(dest='command')

	alerts_parser = subparser.add_parser('alerts', help="whatsinaname")
	populate_args(alerts_parser)

	clusters_parser = subparser.add_parser('clusters', help="whatsinaname")
	populate_args(clusters_parser)

	args = parser.parse_args()

	# Retrieve incidents from PagerDuty API
	incidents = get_incidents(args)

	# Read incidents from the file, for the specified layer
	# incidents = read_file(args.file, args.layer)

	if incidents is None:
		print('No incidents found')
		return

	if args.command == 'alerts':
		alerts(incidents, args.count)
	if args.command == 'clusters':
		clusters(incidents, args.count)


# clusters returns a dict of top alerting clusters and the count of each
def clusters(incidents, count):
	cluster_list = ([
		parse_description_for_cluster(item['service']['summary']) for item in incidents
		if item['service']['summary'] != 'prod-deadmanssnitch' and
		item['service']['summary'] != 'Zabbix Service' and
		item['service']['summary'] != "app-sre-alertmanager"
	])

	print(f'COUNT\tCLUSTER')
	for k, v in Counter(cluster_list).most_common(count):
		print(f'{v}\t{k}')


# parse_description_for_cluster parses the description of an incident to
# remove unique data and extraneous text
def parse_description_for_cluster(description):
	strings_to_remove = [
		# Clean SRE-added '[SOMETHING]' prefixes
		r'\[.*\]\s',
		# ClusterHasGoneMissing
		r'\shas\sgone\smissing',
		# docker.ping failed
		r'docker.ping\sfailed\son\s',
		r'-compute.*$',
		# ClusterProvisioningDelay
		r'ClusterProvisioningDelay\s.*\shive\s\(',
		r'\sProvisionFailed.*$',
		# Disk Free
		r'Filesystem.*free\sdisk\sspace\son\s',
		# Strip leading 'osd-'
		r'^osd-',
		# Strip trailing '-hive-cluster'
		r'-hive-cluster$'
	]

	for i in strings_to_remove:
		description = re.sub(i, '', description)

	return description


# alerts returns a dict of top alerts and the count of each
def alerts(incidents, count):
	alert_list = ([
		parse_description_for_alerts(item['description']) for item in incidents
	])

	print(f'COUNT\tINCIDENT')
	for k, v in Counter(alert_list).most_common(count):
		print(f'{v}\t{k}')


# parse_description_for_alerts parses the description of an incident to
# remove unique values or extraneous text
def parse_description_for_alerts(description):
	strings_to_remove = {
		# Clean SRE-added '[SOMETHING]' prefixes, with optional dash
		r'\[.*\]\s(-\s)?': '',
		# Combine "CRITICAL (1)" and "CRITICAL (2)" alerts
		r'(CRITICAL|WARNING)\s\(\d*\)$': '',
		# Combine all ClusterHasGoneMissing alerts
		r'.*has\sgone\smissing$': 'ClusterHasGoneMissing',
		# Zabbix-style (?) alerts
		r'\son\s.*\s\:\s.*$': '',
	}

	strings_to_match = [
		r'^ClusterProvisioningDelay',
	]

	# Removes extraneous information from the description
	for k,v in strings_to_remove.items():
		description = re.sub(k, v, description)

	# Selects the relevant information from the description
	for i in strings_to_match:
		match = re.compile(i).match(description)
		description = match.group() if match else description


	return description


# read_file reads a csv file and returns a list of alerts, filtering out
# incidents from other layers and low urgency incidents
def read_file(file, layer):
	with open(file, newline='') as csv_file:
		for row in csv.DictReader(csv_file, delimiter=','):
			if (
				is_in_layer(row['created_on'], layer) and
				row['urgency'] == 'high'
			):
				yield row


# is_time_between checks if a time is between two other times
def is_time_between(startTime, endTime, checkTime):
	if startTime < endTime:
		return startTime <= checkTime <= endTime
	else: # over midnight e.g., 23:30-04:15
		return checkTime >= startTime or checkTime <= endTime


# is_in_layer checks if a datetime is in the shift covered by the layer
def is_in_layer(time_string, layer):
	return is_time_between(
		convert_time_from_string(layers[layer]),
		convert_time_from_string(layers[layer_plus_one(layer)]),
		datetime.strptime(time_string, pd_time_format).time()
	)


# layer_plus_one handles the edge case where the layer is the last layer
def layer_plus_one(layer):
	return layer + 1 if layer < len(layers) else 1


# convert_time_from_string converts a string of the form 'HH:MM' to a datetime
def convert_time_from_string(time_string):
	return datetime.strptime(time_string, '%H:%M').time()


def auth(token, token_file):
	if token is None:
		with open (token_file, 'r') as yaml_data:
			try:
				data = yaml.safe_load(yaml_data)
				return data['authtoken']

			except yaml.YAMLError as err:
				print(err)

	return token


def get_incidents(args):
	request_params = {
		'urgencies[]': ['high'],
		'team_ids[]': sre_team_ids,
		'since': datetime.now() - timedelta(days=7),
		'until': datetime.now()
	}
	# Retrieve incidents from PagerDuty API
	api_token = auth(args.token, args.token_file)
	session = APISession(api_token)

	# Read incidents from the file, for the specified layer
	# incidents = read_file(args.file, args.layer)
	try:
		return [
			i for i in session.list_all(
				'incidents',
				params=request_params
				) if (
					is_in_layer(
						i['created_at'],
						args.layer
					) and (
					i['urgency'] == 'high'
					)
				)
			]

	except PDClientError as e:
		if e.response:
			if e.response.status_code == 404:
				print("User not found")
			elif e.response.status_code == 401:
				raise e
		else:
			raise e


if __name__ == '__main__':
	main()
