# TOIL Review Tools

Tools to help with analytics and reporting for TOIL review.

## Building

The binaries can be built locally, or within a container.

### Containerized
 
```shell
# Using Make
make all

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
 
