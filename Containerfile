FROM python:3.9 as builder

# Install patchelf for static linking
RUN apt-get update && apt-get install patchelf -y

COPY . /app
WORKDIR /app

# Install dependencies
RUN python3 -m pip install -r requirements.txt

# Create a single binary
RUN pyinstaller --onefile metrics.py

# Statically link the binary deps
RUN staticx dist/metrics dist/metrics_app

# Need to create a tmp dir to allow the pyinstaller to extract files as needed
# This needs to be copied into the scratch image, because mkdir doesn't exist
RUN mkdir tmp

FROM scratch

ENTRYPOINT ["/metrics"]
CMD ["--help"]

USER 1000

# Need to create a tmp dir to allow the pyinstaller to extract files as needed
COPY --from=builder --chmod=0755 --chown=1000:1000 /app/tmp /tmp
COPY --from=builder --chmod=0755 --chown=1000:1000 /app/dist/metrics_app /metrics

