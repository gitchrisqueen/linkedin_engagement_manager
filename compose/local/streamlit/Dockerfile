FROM python:3.13-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1


# Install dependencies
RUN apt-get update && apt-get install --no-install-suggests --no-install-recommends --yes \
    #curl \
    #unzip \
    #xvfb \
    #libxi6 \
    #libgconf-2-4 \
    #build-essential \
    # Additional dependencies
    #&& apt-get install -y  \
    telnet  \
    netcat-traditional \
    # cleaning up unused files
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM base AS builder

# --- Install Poetry ---
ARG POETRY_VERSION=1.8

ENV POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    # Tell Poetry where to place its cache and virtual environment
    POETRY_CACHE_DIR=/opt/.cache

# Pip Configuration
ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1


# Install poetry and make sure the export plugin is included
RUN pip install "poetry==$POETRY_VERSION" && poetry self add poetry-plugin-export

# Copy the poetry.lock and pyproject.toml
COPY ../../../pyproject.toml ../../../poetry.lock ./

# Install the dependencies and clear the cache afterwards.
#   This may save some MBs.
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR


# Now let's build the runtime image from the builder.
#   We'll just copy the env and the PATH reference.
FROM builder AS my_app_code

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV USE_DOCKER_BROWSER=True

# Copy app code
# TODO: Can we just copy the needed files and folder instead of everything
COPY ../../../src ./src
COPY ../../../README.md ./

# Install our package and clear the cache afterwards.
#   This may save some MBs.
RUN poetry install && rm -rf $POETRY_CACHE_DIR

FROM my_app_code AS final

# Copy and set permissions for entrypoint and other scripts
COPY ./compose/local/streamlit/entrypoint /entrypoint
COPY ./compose/local/streamlit/wait-for-it /wait-for-it
COPY ./compose/local/streamlit/start /start
COPY ./compose/local/streamlit/celery/worker/start /start-celeryworker
COPY ./compose/local/streamlit/celery/beat/start /start-celerybeat
COPY ./compose/local/streamlit/celery/flower/start /start-flower

RUN chmod +x /entrypoint /wait-for-it /start /start-celeryworker /start-celerybeat /start-flower

# Create a logs folder
RUN mkdir -p /app/logs

ENTRYPOINT ["/entrypoint"]