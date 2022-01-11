#!/usr/bin/env python3

import argparse
import csv
import re
import time

from collections import Counter
from datetime import datetime

default_csv_name = 'incidents.csv'
pd_time_format = '%Y-%m-%dT%H:%M:%S+00:00'

layers = {
	1: '22:30',
	2: '3:30',
	3: '8:30',
	4: '13:30',
	5: '18:00',
}


def main():
	parser = argparse.ArgumentParser()

	required_file = parser.add_argument_group('required arguments')
	required_file.add_argument('--file', '-f', type=str, required=False,
		default=default_csv_name, help='File to read')

	subparsers = parser.add_subparsers(dest='command', required=True)

	alert_cmd = subparsers.add_parser('alerts',
		help='List top alerts')
	alert_cmd.add_argument('--count', '-c', type=int, required=False,
		default=5, help='Number of results to return')

	cluster_cmd = subparsers.add_parser('clusters',
		help='List top clusters')
	cluster_cmd.add_argument('--count', '-c', type=int, required=False,
		default=5, help='Number of results to return')

	args = parser.parse_args()

	incidents = read_file(args.file)

	if args.command == 'alerts':
		alerts(incidents, args.count)
	if args.command == 'clusters':
		clusters(incidents, args.count)


def clusters(incidents, count):
	cluster_list = ([
		re.sub(r'-hive-cluster$', '', item['service_name'])
		if item['service_name'] != 'prod-deadmanssnitch' and
		item['service_name'] != 'Zabbix Service' and
		item['service_name'] != "app-sre-alertmanager"
		else parse_description_for_cluster(item['description']) for item in incidents
	])

	print(f'COUNT\tCLUSTER')
	for k, v in Counter(cluster_list).most_common(count):
		print(f'{v}\t{k}')


def parse_description_for_cluster(description):
	# Clean SRE-added '[SOMETHING]' prefixes
	prefix = [r'\[.*\]\s']

	# ClusterHasGoneMissing
	chgm = [r'\shas\sgone\smissing']

	# docker.ping failed
	dp = [r'docker.ping\sfailed\son\s', r'-compute.*$']

	# ClusterProvisioningDelay
	cpd = [r'ClusterProvisioningDelay\s.*\shive\s\(', r'\sProvisionFailed.*$']

	# Disk Free
	df = [r'Filesystem.*free\sdisk\sspace\son\s']

	strings_to_remove = prefix + chgm + dp + cpd + df
	for i in strings_to_remove:
		description = re.sub(i, '', description)

	return description


def alerts(incidents, count):
	alert_list = ([
		parse_description_for_alerts(item['description']) for item in incidents
	])

	print(f'COUNT\tCLUSTER')
	for k, v in Counter(alert_list).most_common(count):
		print(f'{v}\t{k}')


def parse_description_for_alerts(description):
	# Clean SRE-added '[SOMETHING]' prefixes
	prefix = [r'\[.*\]\s']

	# Combine "CRITICAL (1)" and "CRITICAL (2)" alerts
	crit = [r'CRITICAL\s\(\d\)$']

	# NOTE: Add more lists of regexes here, and combine them in the
	# "strings_to_remove" list below as more alerts are added.

	strings_to_remove = prefix + crit
	for i in strings_to_remove:
		description= re.sub(i, '', description)

	return description


def read_file(file):
	with open(file, newline='') as csv_file:
		for row in csv.DictReader(csv_file, delimiter=','):
			if is_layer_5(row['created_on']):
				yield row


def is_time_between(startTime, endTime, checkTime):
	if startTime < endTime:
		return startTime <= checkTime <= endTime
	else: # over midnight e.g., 23:30-04:15
		return checkTime >= startTime or checkTime <= endTime


def is_layer_5(time_string):
	# TODO: currently handles only created_on, not handed over or silenced
	return is_time_between(
		convert_time_from_string(layers[5]),
		convert_time_from_string(layers[1]),
		datetime.strptime(time_string, pd_time_format).time()
	)


def convert_time_from_string(time_string):
	return datetime.strptime(time_string, '%H:%M').time()


if __name__ == '__main__':
	main()