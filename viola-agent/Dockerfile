# Build from repository root (Lolanto monorepo):
#   docker build -f viola-agent/Dockerfile .
#
# Paths below assume context is the repo root, not ``viola-agent/``.
#
# Optional Portfolio MCP package override:
#   --build-arg MCP_PORTFOLIO_PACKAGE=/path/to/local/pkg

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Portfolio Agent only needs the OpenAI-compatible API. Skip Node / WhatsApp
# bridge (sharp-libvips alone is hundreds of MB and blows small VM disks).
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates git bubblewrap gosu && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cached layer)
COPY viola-agent/pyproject.toml viola-agent/README.md viola-agent/LICENSE ./
RUN mkdir -p viola bridge && touch viola/__init__.py && \
    uv pip install --system --no-cache . && \
    rm -rf viola

# Copy the full source and install. Keep an empty bridge/ so hatchling's
# force-include succeeds without shipping the WhatsApp Node tree.
COPY viola-agent/viola/ viola/
COPY viola-agent/main.py ./
RUN mkdir -p bridge && \
    rm -rf /app/viola/skills/github && \
    uv pip install --system --no-cache ".[api]"

# Portfolio MCP package (monorepo default)
ARG MCP_PORTFOLIO_PACKAGE=""
COPY mcp_service/mcp_nanobot /opt/mcp_nanobot_default
RUN if [ -n "$MCP_PORTFOLIO_PACKAGE" ]; then \
      uv pip install --system --no-cache "$MCP_PORTFOLIO_PACKAGE"; \
    else \
      uv pip install --system --no-cache /opt/mcp_nanobot_default; \
    fi && \
    rm -rf /opt/mcp_nanobot_default

# Create non-root user and config directory
RUN useradd -m -u 1000 -s /bin/bash viola && \
    mkdir -p /home/viola/.viola && \
    chown -R viola:viola /home/viola /app

COPY viola-agent/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

USER root
ENV HOME=/home/viola

# Gateway default port
EXPOSE 18790

ENTRYPOINT ["entrypoint.sh"]
CMD ["status"]
