FROM python:3.13-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install dependencies
RUN apt-get update -y && apt-get install --no-install-suggests --no-install-recommends --yes \
    # Curl needed for AWS health checks
    curl \
    netcat-traditional \
    # cleaning up unused files
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

# Upgrade Pip
RUN python3 -m pip install --upgrade pip

WORKDIR /app

FROM base AS builder

# Create arg to install dev dependencies
ARG INSTALL_DEV_DEPS=false
# Set the env variable to use in the next stage
ENV INSTALL_DEV_DEPS=${INSTALL_DEV_DEPS}

# --- Install Poetry ---
ARG POETRY_VERSION=2.0

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
COPY ./pyproject.toml ./poetry.lock ./

# Install the dependencies and clear the cache afterwards.
#   This may save some MBs.
RUN if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
    poetry install --with dev --no-root  && rm -rf $POETRY_CACHE_DIR; \
    else \
    poetry install --only main --no-root  && rm -rf $POETRY_CACHE_DIR; \
    fi



# Now let's build the runtime image from the builder.
#   We'll just copy the env and the PATH reference.
FROM builder AS my_app_code

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy app src files
COPY ./src ./src
COPY ./README.md ./README.md

# Install our package and clear the cache afterwards.
#   This may save some MBs.
RUN if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
    poetry install --with dev && rm -rf $POETRY_CACHE_DIR; \
    else \
    poetry install --only main && rm -rf $POETRY_CACHE_DIR; \
    fi

FROM my_app_code AS final

# Copy and set permissions for entrypoint and other scripts
COPY ./compose/local/entrypoint /entrypoint
COPY ./compose/local/wait-for-it /wait-for-it
COPY ./compose/local/streamlit/start /start-streamlit
COPY ./compose/local/fastapi/start /start-fastapi
COPY ./compose/local/fastapi/start-cloud /start-fastapi-cloud
COPY ./compose/local/celery/worker/start /start-celeryworker
COPY ./compose/local/celery/worker/start-solo-pool /start-celeryworker-solo
COPY ./compose/local/celery/beat/start /start-celerybeat
COPY ./compose/local/celery/flower/start /start-flower
COPY ./compose/local/celery/flower/start-no-wait /start-flower-no-wait

# Set permissions and create logs directory
RUN chmod +x /entrypoint /wait-for-it /start-streamlit /start-fastapi \
    /start-fastapi-cloud /start-celeryworker /start-celeryworker-solo \
    /start-celerybeat /start-flower /start-flower-no-wait && \
    mkdir -p /app/logs

ENTRYPOINT ["/entrypoint"]