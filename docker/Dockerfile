ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

COPY pyproject.toml ./
COPY launchflow ./launchflow
RUN apt-get -y update && apt-get -y install curl zip docker.io

RUN pip install --no-cache-dir .[gcp,aws] && \
    rm pyproject.toml && \
    rm -rf launchflow && \
    rm -rf build && \
    LAUNCHFLOW_TOFU_PATH=/app/bin/tofu lf version && \
    docker --version

ENV LAUNCHFLOW_TOFU_PATH=/app/bin/tofu

ENTRYPOINT [ "bash" ]
