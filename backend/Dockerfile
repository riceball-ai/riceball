FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

# Copy the project and sync
COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


# Runtime stage
FROM python:3.13-slim-trixie AS pro

RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

# Copy only the virtual environment from builder
COPY --from=builder --chown=nonroot:nonroot /app/.venv /app/.venv

COPY --chown=nonroot:nonroot . /app/

ENV PATH="/app/.venv/bin:$PATH"

USER nonroot

WORKDIR /app

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT  ["/app/entrypoint.sh"]

CMD [ "fastapi", "run", "src/main.py" ]



FROM python:3.13-slim-trixie AS dev

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && \
    apt-get install -y --no-install-recommends just git sudo && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Configure non-root user parameters
ARG UID=1000
ARG GID=1000
ARG USERNAME=nonroot
# Create a non-root user to run the application
RUN groupadd --gid $GID $USERNAME && \
    useradd --uid $UID --gid $GID --create-home --shell /bin/bash $USERNAME

# Compile bytecode
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0

USER $USERNAME

WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=~/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the project into the image
COPY --chown=$USERNAME:$USERNAME . /app

# Sync the project
RUN --mount=type=cache,target=~/.cache/uv \
    uv sync --locked --no-dev \
    && chmod +x entrypoint.sh

# Place executables in the environment at the front of the path
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT  ["/app/entrypoint.sh"]

CMD ["fastapi", "dev", "--host=0.0.0.0", "src/main.py"]
