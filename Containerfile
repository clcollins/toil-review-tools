FROM scratch 

ENTRYPOINT ["/metrics"]
CMD ["--help"]

USER 1000

COPY --chmod=0755 --chown=1000:1000 tmp /tmp
COPY --chmod=0755 --chown=1000:1000 /dist/metrics_app /metrics

