# Build from repository root (Lolanto monorepo):
#   docker build -f viola-agent/Dockerfile .
#
# Paths below assume context is the repo root, not ``viola-agent/``.
#
# Optional Portfolio MCP package override:
#   --build-arg MCP_PORTFOLIO_PACKAGE=/path/to/local/pkg

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install Node.js 20 for the WhatsApp bridge
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg git bubblewrap openssh-client gosu && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get purge -y gnupg && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cached layer)
COPY viola-agent/pyproject.toml viola-agent/README.md viola-agent/LICENSE ./
RUN mkdir -p viola bridge && touch viola/__init__.py && \
    uv pip install --system --no-cache . && \
    rm -rf viola bridge

# Copy the full source and install
COPY viola-agent/viola/ viola/
COPY viola-agent/bridge/ bridge/
COPY viola-agent/main.py ./
RUN rm -rf /app/viola/skills/github && \
    uv pip install --system --no-cache ".[api,twilio,whatsapp_webhook]"

# Portfolio MCP package (monorepo default)
ARG MCP_PORTFOLIO_PACKAGE=""
COPY mcp_service/mcp_nanobot /opt/mcp_nanobot_default
RUN if [ -n "$MCP_PORTFOLIO_PACKAGE" ]; then \
      uv pip install --system --no-cache "$MCP_PORTFOLIO_PACKAGE"; \
    else \
      uv pip install --system --no-cache /opt/mcp_nanobot_default; \
    fi && \
    rm -rf /opt/mcp_nanobot_default

# Build the WhatsApp bridge
WORKDIR /app/bridge
RUN git config --global --add url."https://github.com/".insteadOf ssh://git@github.com/ && \
    git config --global --add url."https://github.com/".insteadOf git@github.com: && \
    npm install && npm run build
WORKDIR /app

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
