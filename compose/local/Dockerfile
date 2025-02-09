FROM python:3.13-slim AS base
#FROM public.ecr.aws/docker/library/python:3.13-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install dependencies
RUN apt-get update -y && apt-get install --no-install-suggests --no-install-recommends --yes \
    #curl \
    #unzip \
    #xvfb \
    #libxi6 \
    #libgconf-2-4 \
    #build-essential \
    # Additional dependencies
    #&& apt-get install -y  \
    # Below is needed for pptx - Verify these
    #libgdiplus \
    #pkg-config \
    #libicu-dev \
    #libpython3.13 \
    # Verify above packages are needed or not \
    # Curl needed for AWS health checks
    curl \
    netcat-traditional \
    # cleaning up unused files
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

# Create a symbolic link for libpython if necessary
#RUN ln -s /usr/lib/x86_64-linux-gnu/libpython3.13m.so.1.0 /usr/lib/libpython3.13m.so.1.0 || true

# Upgrade Pip
RUN python3 -m pip install --upgrade pip


WORKDIR /app

FROM base AS builder

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
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR


# Now let's build the runtime image from the builder.
#   We'll just copy the env and the PATH reference.
FROM builder AS my_app_code

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV USE_DOCKER_BROWSER=True

# Copy app src files
COPY ./src ./src
COPY ./README.md ./README.md

# Install our package and clear the cache afterwards.
#   This may save some MBs.
RUN poetry install && rm -rf $POETRY_CACHE_DIR

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

RUN chmod +x /entrypoint /wait-for-it /start-streamlit /start-fastapi /start-fastapi-cloud /start-celeryworker /start-celeryworker-solo /start-celerybeat /start-flower /start-flower-no-wait

# Create a logs folder
RUN mkdir -p /app/logs

ENTRYPOINT ["/entrypoint"]