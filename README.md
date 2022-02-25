# TOIL Review Tools

Tools to help with analytics and reporting for TOIL review.

## Usage

Example 1: Download alert metrics from PagerDuty for layer 5, 1 day worth (with one previous day to compare against)

```shell
./metrics alerts --layers 5 --days 1

Including incidents from layers: 5
High incidents in the last 1 days before today: 22
Percent Change from the previous period: 83.33%

COUNT   INCIDENT
5       DNSErrors10MinSRE
5       ClusterHasGoneMissing
3       ClusterProvisioningDelay
2       PruningCronjobErrorSRE
2       etcdGRPCRequestsSlow
```

Example 2: Show cluster metrics for layers 4 and 5, 3 days (with three previous days to compare against),
refreshing the data from PagerDuty instead of  using a cache file

```shell
./metrics clusters --layers 4 5 --days 3 --no-cache

Including incidents from layers: 4, 5
High incidents in the last 3 days before today: 187
Percent Change from the previous period: 201.61%

COUNT   CLUSTER
10     cluster-name.one.example.org
5      cluster-name.three.example.org
5      cluster-name.six.example.org
5      cluster-name.four.example.org
5      cluster-name.two.example.org
```

Example 3: Show both alert and cluster metrics for layer 1, for the past week,
and list only the top three of each

```shell
./metrics.py all --layers 4 5 --days 3 --count 3
Including incidents from layers: 4, 5
High incidents in the last 3 days before today: 187
Percent Change from the previous period: 201.61%

COUNT   INCIDENT
108     PrometheusRemoteWriteBehind
14      ClusterProvisioningDelay
13      console-ErrorBudgetBurn

COUNT   CLUSTER
10      cluster-name.one.example.org
5       cluster-name.three.example.org
5       cluster-name.six.example.org
```

## Caching

`metrics.py` will cache PagerDuty data by default to `~/.cache/toil-review-metrics/`. Existing cache data can be ignore with the `--no-cache` flag.  The cache will be ignored if the file is stale (older than 1 day), or if it cannot be found.

You can also specify a specific cache file to be used, with the `--cache-file` flag. A specified cache file that does not exist will be created, and PagerDuty data will be downloaded and stored into it.

**Warning:** Cache data _will_ be overwritten if the `--no-cache` flag is used.

## Building

The binaries can be built locally, or within a container.

### Containerized

```shell
# Using Make, just run the `make` command
make

# Or alternatively, specifying your container engine:
CONTAINER_SYBSYS='podman' make all
```

### Locally

```shell
# Using a virtual environment
python3 -m venv ./venv-toil-review-tools
./venv-toil-review-tools/bin/python3 -m pip install -r requirements.txt

# Or alternatively, installing directly
python3 -m pip install -r requirements.txt
```
