#!/usr/bin/env python3

from pathlib import Path
from datetime import date, datetime

from unittest.mock import MagicMock
from unittest import TestCase

from metrics import helpers

from metrics import next_layer, percent_change, is_time_between, is_in_layer
from metrics import parse_description_for_alerts, parse_description_for_cluster
from metrics import clusters, alerts
from metrics import split_incidents_by_period, get_incidents
from metrics import select_cache_file

test_incidents = [
    {
        "incident_number": 123456,
        "title": "IncidentTitle",
        "description": "IncidentTitle",
        "created_at": "2022-02-22T18:18:46Z",
        "status": "resolved",
        "incident_key": None,
        "service": {
            "id": "SRVCID0",
            "type": "service_reference",
            "summary": "Service Summary",
            "self": "https://api.pagerduty.com/services/SRVCID0",
            "html_url": "https://subdomain.pagerduty.com/service-directory/SRVCID0",
        },
        "assignments": [],
        "assigned_via": "escalation_policy",
        "last_status_change_at": "2022-02-22T22:03:46Z",
        "first_trigger_log_entry": {
            "id": "LOGENTRYID123456",
            "type": "trigger_log_entry_reference",
            "summary": "Triggered through the API",
            "self": "https://api.pagerduty.com/log_entries/LOGENTRYID123456",
            "html_url": "https://subdomain.pagerduty.com/incidents/INCIDENTIDNUM/log_entries/LOGENTRYID123456",
        },
        "alert_counts": {"all": 1, "triggered": 0, "resolved": 1},
        "is_mergeable": True,
        "escalation_policy": {
            "id": "EPOLID0",
            "type": "escalation_policy_reference",
            "summary": "Escalation Policy Summary",
            "self": "https://api.pagerduty.com/escalation_policies/EPOLID0",
            "html_url": "https://subdomain.pagerduty.com/escalation_policies/EPOLID0",
        },
        "teams": [
            {
                "id": "TEAMID0",
                "type": "team_reference",
                "summary": "Team Summary",
                "self": "https://api.pagerduty.com/teams/TEAMID0",
                "html_url": "https://subdomain.pagerduty.com/teams/TEAMID0",
            }
        ],
        "pending_actions": [],
        "acknowledgements": [],
        "basic_alert_grouping": None,
        "alert_grouping": None,
        "last_status_change_by": {
            "id": "SRVCID0",
            "type": "service_reference",
            "summary": "Service Summary",
            "self": "https://api.pagerduty.com/services/SRVCID0",
            "html_url": "https://subdomain.pagerduty.com/service-directory/SRVCID0",
        },
        "priority": None,
        "resolve_reason": None,
        "incidents_responders": [],
        "responder_requests": [],
        "subscriber_requests": [],
        "urgency": "high",
        "id": "INCIDENTIDNUM",
        "type": "incident",
        "summary": "[#123456] Incident Title",
        "self": "https://api.pagerduty.com/incidents/INCIDENTIDNUM",
        "html_url": "https://subdomain.pagerduty.com/incidents/INCIDENTIDNUM",
    }
]


class TestSelectCacheFile(TestCase):
    def test_select_cache_file(self):

        mock_path = Path
        mock_path.home = MagicMock(return_value=Path("/home/user"))

        mock_date = helpers
        mock_date.today = MagicMock(return_value=datetime(2020, 1, 1, 1, 30, 0))

        testcases = [
            {
                "name": "test_select_cache_file_custom",
                "cache_file": "/tmp/test",
                "layers": [1, 2],
                "days": 1,
                "expect": (Path("/tmp"), Path("/tmp/test")),
            },
            {
                "name": "test_select_cache_file_custom",
                "cache_file": None,
                "layers": [1, 2],
                "days": 1,
                "expect": (
                    Path("/home/user/.cache/toil-review-metrics"),
                    Path(
                        "/home/user/.cache/toil-review-metrics/incident-cache_2020-01-01_1-2_1-day.json"
                    ),
                ),
            },
            {
                "name": "test_select_cache_file_custom",
                "cache_file": None,
                "layers": [2],
                "days": 3,
                "expect": (
                    Path("/home/user/.cache/toil-review-metrics"),
                    Path(
                        "/home/user/.cache/toil-review-metrics/incident-cache_2020-01-01_2_3-day.json"
                    ),
                ),
            },
            {
                "name": "test_select_cache_file_custom",
                "cache_file": None,
                "layers": [5, 1, 2],
                "days": 3,
                "expect": (
                    Path("/home/user/.cache/toil-review-metrics"),
                    Path(
                        "/home/user/.cache/toil-review-metrics/incident-cache_2020-01-01_5-1-2_3-day.json"
                    ),
                ),
            },
        ]

        for testcase in testcases:
            self.assertEqual(
                select_cache_file(
                    testcase["cache_file"], testcase["layers"], testcase["days"]
                ),
                testcase["expect"],
                "{} should be: {}".format(testcase["name"], testcase["expect"]),
            )


class TestShouldReadFromCache(TestCase):
    def test_should_read_from_cache(self):
        # TODO: Need to figure out how to moke the date and fs access
        pass


class TestReadIncidentsFromCache(TestCase):
    def test_read_incidents_from_cache(self):
        # NOTE: Probably don't have to test this - just raw library function
        pass


class TestWriteIncidentsToCache(TestCase):
    def test_write_incidents_to_cache(self):
        # NOTE: TODO
        # Need to figure out how to test the file writing, cache dir creation
        # with mocks, and test reading the file
        pass


class TestCacheToFile(TestCase):
    def test_cache_to_file(self):
        # NOTE: Probably don't have to test this - just raw library function
        pass


class TestGetIncidents(TestCase):
    def test_get_Incidents(self):
        # NOTE: TODO
        # Need to mock a call to the API to get the incidents
        # And the retrieve_token function
        pass


class TestSplitIncidentsByPeriod(TestCase):
    def test_split_incidents_by_period(self):
        testcases = [
            {
                "name": "split_incidents_by_period_0",
                "incidents": [
                    {
                        "incident_number": 0,
                        "title": "IncidentTitle",
                        "created_at": "2022-02-22T18:18:46Z",
                    },
                    {
                        "incident_number": 0,
                        "title": "IncidentTitle",
                        "created_at": "2022-02-22T18:18:46Z",
                    },
                    {
                        "incident_number": 0,
                        "title": "IncidentTitle",
                        "created_at": "2022-02-22T18:18:46Z",
                    },
                ],
                "days": 1,
                "expect": {"current": [], "previous": []},
            }
        ]

        # NOTE: TODO
        pass


class TestAlerts(TestCase):
    def test_alerts(self):
        # NOTE: probably don't need to tst this, as it just runs code
        # tested elsewhere, counts lines, and prints
        pass


class TestClusters(TestCase):
    def test_clusters(self):
        # NOTE: probably don't need to tst this, as it just runs code
        # tested elsewhere, counts lines, and prints
        pass


class TestParseDescriptionForAlerts(TestCase):
    def test_parse_description_for_alerts(self):
        testcases = [
            {
                "name": "test_sre_prefixes_1",
                "description": "[SL Sent] cluster.name.here has gone missing",
                "expect": "ClusterHasGoneMissing",
            },
            {
                "name": "test_suffixes_1",
                "description": "[OHSS-12345] UpgradeConfigSyncFailureOver4HrSRE CRITICAL (1)",
                "expect": "UpgradeConfigSyncFailureOver4HrSRE",
            },
            {
                "name": "test_suffixes_2",
                "description": "UpgradeConfigSyncFailureOver4HrSRE WARNING (2)",
                "expect": "UpgradeConfigSyncFailureOver4HrSRE",
            },
            {
                "name": "test_chgm_1",
                "description": "cluster.name.here has gone missing",
                "expect": "ClusterHasGoneMissing",
            },
            {
                "name": "test_zabbix_style_alerts_1",
                "description": "docker.ping failed on node-name.here-compute.internal : PROBLEM for node-name.here-compute.internal",
                "expect": "docker.ping failed",
            },
            {
                "name": "test_cpd_1",
                "description": "[FIRING:1] ClusterProvisioningDelay - production CCS - hivex00xx0 hivex00x0 some-ns-abcdefg123456789 hive-controllers hive (cluster-name managed-byoc ProvisionFailed metrics production openshift-v4.7.13 0.0.0.0:0000 hive aws hive-controllers-abcde123455-abcde openshift-customer-monitoring/app-sre AuthenticationOperatorDegraded high srep)",
                "expect": "ClusterProvisioningDelay",
            },
        ]

        for testcase in testcases:
            self.assertEqual(
                parse_description_for_alerts(testcase["description"]),
                testcase["expect"],
                "{} should be: {}".format(testcase["name"], testcase["expect"]),
            )


class TestParseDescriptionForClusters(TestCase):
    def test_parse_description_for_cluster(self):
        testcases = [
            {
                "name": "test_sre_prefixes_1",
                "description": "[SL Sent] cluster.name.here has gone missing",
                "expect": "cluster.name.here",
            },
            {
                "name": "test_sre_prefixes_2",
                "description": "[OHSS-12345] UpgradeConfigSyncFailureOver4HrSRE CRITICAL (1)",
                "expect": "UpgradeConfigSyncFailureOver4HrSRE CRITICAL (1)",
            },
            {
                "name": "test_chgm_1",
                "description": "cluster.name.here has gone missing",
                "expect": "cluster.name.here",
            },
            {
                "name": "test_docker_ping_failed_1",
                "description": "docker.ping failed on node-name.here-compute.internal : PROBLEM for node-name.here-compute.internal",
                "expect": "node-name.here",
            },
            {
                "name": "test_cpd_1",
                "description": "[FIRING:1] ClusterProvisioningDelay - production CCS - hivex00xx0 hivex00x0 some-ns-abcdefg123456789 hive-controllers hive (cluster-name managed-byoc ProvisionFailed metrics production openshift-v4.7.13 0.0.0.0:0000 hive aws hive-controllers-abcde123455-abcde openshift-customer-monitoring/app-sre AuthenticationOperatorDegraded high srep)",
                "expect": "cluster-name managed-byoc",
            },
            {
                "name": "test_disk_free_1",
                "description": "[Heal] Filesystem: /dev/mapper/rootvg-var has less than 10% free disk space on clustername-master-abc123: PROBLEM for clustername-master-abc123",
                "expect": "clustername-master-abc123",
            },
            {
                "name": "test_strip_osd_1",
                "description": "osd-cluster.name.here",
                "expect": "cluster.name.here",
            },
            {
                "name": "test_strip_hive_cluster_1",
                "description": "cluster.name.here-hive-cluster",
                "expect": "cluster.name.here",
            },
        ]

        for testcase in testcases:
            self.assertEqual(
                parse_description_for_cluster(testcase["description"]),
                testcase["expect"],
                "{} should be: {}".format(testcase["name"], testcase["expect"]),
            )


class TestIsInLayer(TestCase):
    def test_is_in_layer(self):
        testcases = [
            {
                "name": "test_true",
                "time_string": "2020-01-01T04:00:00Z",
                "requested_layers": [2],
                "expect": True,
            },
            {
                "name": "test_false",
                "time_string": "2020-01-01T00:00:00Z",
                "requested_layers": [2],
                "expect": False,
            },
            {
                "name": "test_over_midnight_true",
                "time_string": "2020-01-01T00:00:00Z",
                "requested_layers": [1],
                "expect": True,
            },
            {
                "name": "test_over_midnight_false",
                "time_string": "2020-01-01T00:00:00Z",
                "requested_layers": [3],
                "expect": False,
            },
            {
                "name": "test_multi_layer_true",
                "time_string": "2020-01-01T00:00:00Z",
                "requested_layers": [5, 1],
                "expect": True,
            },
            {
                "name": "test_multi_layer_false",
                "time_string": "2020-01-01T00:00:00Z",
                "requested_layers": [2, 3],
                "expect": False,
            },
            {
                "name": "test_multi_x3_layer_true",
                "time_string": "2020-01-01T00:00:00Z",
                "requested_layers": [4, 1],
                "expect": True,
            },
            {
                "name": "test_multi_x3_layer_false",
                "time_string": "2020-01-01T00:00:00Z",
                "requested_layers": [2, 3, 4],
                "expect": False,
            },
            {
                "name": "test_multi_layer_over_midnight_true",
                "time_string": "2020-01-01T00:00:00Z",
                "requested_layers": [5, 1],
                "expect": True,
            },
            {
                "name": "test_multi_layer_over_midnight_false",
                "time_string": "2020-01-01T00:00:00Z",
                "requested_layers": [2, 3],
                "expect": False,
            },
        ]

        for testcase in testcases:
            self.assertIs(
                is_in_layer(
                    testcase["time_string"],
                    testcase["requested_layers"],
                ),
                testcase["expect"],
                "{} should be: {}".format(testcase["name"], testcase["expect"]),
            )


class TestIsTimeBetween(TestCase):
    def assertIsTrue(self, value):
        self.assertIs(value, True)

    def assertIsFalse(self, value):
        self.assertIs(value, False)

    def test_is_time_between(self):
        testcases = [
            {
                "name": "test_hours_between_true",
                "startTime": "2020-01-01T00:00:00Z",
                "endTime": "2020-01-01T02:00:00Z",
                "checkTime": "2020-01-01T01:00:00Z",
                "expect": True,
            },
            {
                "name": "test_hours_between_false",
                "startTime": "2020-01-01T00:00:00Z",
                "endTime": "2020-01-01T02:00:00Z",
                "checkTime": "2020-01-01T03:00:00Z",
                "expect": False,
            },
            {
                "name": "test_minutes_between_true",
                "startTime": "2020-01-01T00:00:00Z",
                "endTime": "2020-01-01T00:59:00Z",
                "checkTime": "2020-01-01T00:30:00Z",
                "expect": True,
            },
            {
                "name": "test_minutes_between_false",
                "startTime": "2020-01-01T00:00:00Z",
                "endTime": "2020-01-01T00:45:00Z",
                "checkTime": "2020-01-01T0:59:00Z",
                "expect": False,
            },
            {
                "name": "test_over_midnight_before_true",
                "startTime": "2020-01-01T22:00:00Z",
                "endTime": "2020-01-02T01:00:00Z",
                "checkTime": "2020-01-01T23:30:00Z",
                "expect": True,
            },
            {
                "name": "test_over_midnight_before_false",
                "startTime": "2020-01-01T23:00:00Z",
                "endTime": "2020-01-02T01:00:00Z",
                "checkTime": "2020-01-01T22:30:00Z",
                "expect": False,
            },
            {
                "name": "test_over_midnight_after_true",
                "startTime": "2020-01-01T22:00:00Z",
                "endTime": "2020-01-02T01:00:00Z",
                "checkTime": "2020-01-02T00:30:00Z",
                "expect": True,
            },
            {
                "name": "test_over_midnight_after_false",
                "startTime": "2020-01-01T23:00:00Z",
                "endTime": "2020-01-02T01:00:00Z",
                "checkTime": "2020-01-02T2:30:00Z",
                "expect": False,
            },
        ]

        for testcase in testcases:
            self.assertIs(
                is_time_between(
                    testcase["startTime"],
                    testcase["endTime"],
                    testcase["checkTime"],
                ),
                testcase["expect"],
                "{} should be: {}".format(testcase["name"], testcase["expect"]),
            )


class TestNextLayer(TestCase):
    def test_next_layer(self):
        testcases = [
            {
                "name": "test_wrap_from_final_layer",
                "input": 5,
                "expect": 1,
            },
            {
                "name": "test_normal_layer_progression_1",
                "input": 1,
                "expect": 2,
            },
            {
                "name": "test_normal_layer_progression_2",
                "input": 2,
                "expect": 3,
            },
        ]

        for testcase in testcases:
            self.assertEqual(
                next_layer(testcase["input"]),
                testcase["expect"],
                "{} should be: {}".format(testcase["name"], testcase["expect"]),
            )


class TestRetrieveToken(TestCase):
    ## TODO: MOCK ENV/TOKEN STUFF
    pass


class TestPercentChange(TestCase):
    def test_percent_change(self):
        testcases = [
            {
                "name": "test_positive_change",
                "current": 200,
                "previous": 100,
                "expect": 100,
            },
            {
                "name": "test_test_negative_change",
                "current": 100,
                "previous": 200,
                "expect": -50,
            },
            {
                "name": "test_no_change",
                "current": 10,
                "previous": 10,
                "expect": 0,
            },
        ]

        for testcase in testcases:
            self.assertEqual(
                percent_change(testcase["current"], testcase["previous"]),
                testcase["expect"],
                "{} should be: {}".format(testcase["name"], testcase["expect"]),
            )
