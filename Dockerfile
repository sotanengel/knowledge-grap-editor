# BuildKit is required (it is the default in modern Docker). No `# syntax=`
# directive: pinning the frontend would mean fetching it from Docker Hub on
# every build, and the features used here are in the bundled frontend already.

# ---------------------------------------------------------------- web UI
FROM node:22-alpine AS frontend

WORKDIR /build
RUN corepack enable

# The Takumi Guard registry is baked into the repo .npmrc; the token, if any,
# arrives as a build secret and never lands in a layer.
COPY .npmrc ./
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./frontend/
RUN --mount=type=secret,id=takumi_guard_token,required=false \
    if [ -f /run/secrets/takumi_guard_token ]; then \
      printf '//npm.flatt.tech/:_authToken=%s\n' "$(cat /run/secrets/takumi_guard_token)" >> .npmrc; \
    fi && \
    cd frontend && pnpm install --frozen-lockfile

COPY frontend/ ./frontend/
RUN cd frontend && pnpm build


# ---------------------------------------------------------------- python deps
FROM python:3.12-slim AS backend

# The virtualenv is built at its *final* path, so the console script's shebang
# points somewhere that still exists in the runtime image.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY backend/ ./backend/

RUN --mount=type=secret,id=takumi_guard_token,required=false \
    if [ -f /run/secrets/takumi_guard_token ]; then \
      export UV_INDEX_TAKUMI_GUARD_USERNAME=token; \
      export UV_INDEX_TAKUMI_GUARD_PASSWORD="$(cat /run/secrets/takumi_guard_token)"; \
    fi && \
    uv sync --frozen --no-dev

# The embedding model ships inside the image so that similar-label search works
# with the network unplugged (NFR-06). 512MB of float32 is compressed to about
# 83MB here -- int8, and 128 of its 256 dimensions, which measured as well as
# the full width on a ranking task.
#
# A failure stops the build: falling back silently would leave the image
# measuring surface similarity while claiming to measure meaning. Pass
# --allow-missing to build the fallback-only image on purpose.
COPY scripts/fetch_embedding_model.py ./scripts/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv run --no-sync python scripts/fetch_embedding_model.py \
      --out backend/src/ontoforge/semantic/model


# ---------------------------------------------------------------- runtime
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="OntoForge" \
      org.opencontainers.image.description="Ontology and knowledge graph authoring with read-only MCP access" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/sotanengel/knowledge-grap-editor"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    ONTOFORGE_DATA_DIR=/data \
    HOME=/tmp

# Non-root, and no shell for the account that runs the process (§13).
RUN groupadd --system --gid 10001 ontoforge \
 && useradd --system --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin ontoforge \
 && mkdir -p /data \
 && chown 10001:10001 /data

WORKDIR /app
COPY --from=backend --chown=root:root /app/.venv /app/.venv
COPY --from=backend --chown=root:root /app/backend /app/backend
COPY --from=frontend --chown=root:root /build/frontend/dist /app/backend/src/ontoforge/static

USER 10001:10001
VOLUME ["/data"]
EXPOSE 8080

# Inside a container the loopback-only default would make the published port
# unreachable, so the bind address is widened here and only here. The port is
# still only exposed if you publish it, and ONTOFORGE_AUTH_TOKEN is what you set
# when you do (§13).
ENTRYPOINT ["ontoforge"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8080"]

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/v1/health', timeout=2).status == 200 else 1)"]
