FROM python:3.10 AS build

# On big cloud machines, we hit connection limits.
ENV POETRY_INSTALLER_MAX_WORKERS 8

COPY pyproject.toml poetry.lock /src/
WORKDIR /src

RUN curl -o /install-poetry.py https://install.python-poetry.org && \
    python /install-poetry.py --preview && \
    python -m venv .venv && \
    apt-get update && \
    apt-get install -y --no-install-recommends libcap2-bin && \
    setcap 'cap_net_bind_service=+ep' /usr/local/bin/python3.10

COPY . /src/
RUN /root/.local/bin/poetry install --without=dev

FROM python:3.10
COPY --from=build /src /src
WORKDIR /src
USER 65534
