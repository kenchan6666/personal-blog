# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

viola is a lightweight, open-source AI agent framework written in Python with a React/TypeScript WebUI. It centers around a small agent loop that receives messages from chat channels, invokes an LLM provider, executes tools, and manages session memory.

## Development Commands

```bash
# Python: run single test / lint
pytest tests/test_openai_api.py::test_function -v
ruff check viola/

# WebUI: dev server (proxies API/WS to gateway :8765), build, test
# Build outputs to ../viola/web/dist (bundled into the Python wheel)
cd webui && bun run dev
cd webui && bun run build
cd webui && bun run test

# Gateway
viola gateway
```

## High-Level Architecture

### Core Data Flow

Messages flow through an async `MessageBus` (`viola/bus/queue.py`) that decouples chat channels from the agent core:

1. **Channels** (`viola/channels/`) receive messages from external platforms and publish `InboundMessage` events to the bus.
2. **`AgentLoop`** (`viola/agent/loop.py`) consumes inbound messages, builds context, and coordinates the turn.
3. **`AgentRunner`** (`viola/agent/runner.py`) handles the actual LLM conversation loop: send messages to the provider, receive tool calls, execute tools, and stream responses.
4. Responses are published as `OutboundMessage` events back to the appropriate channel.

### Key Subsystems

- **Agent Loop** (`viola/agent/loop.py`, `runner.py`): The core processing engine. `AgentLoop` manages session keys, hooks, and context building. `AgentRunner` executes the multi-turn LLM conversation with tool execution.
- **LLM Providers** (`viola/providers/`): Provider implementations (Anthropic, OpenAI-compatible, Azure, GitHub Copilot, etc.) built on a common base (`base.py`). `factory.py` and `registry.py` handle instantiation and model discovery.
- **Channels** (`viola/channels/`): Platform integrations (Telegram, Discord, Slack, Feishu, Matrix, WhatsApp, QQ, WeChat, WebSocket, etc.). `manager.py` discovers and coordinates them. Channels are auto-discovered via `pkgutil` scan + entry-point plugins.
- **Tools** (`viola/agent/tools/`): Agent capabilities exposed to the LLM: grep/glob (code search), shell execution, web search/fetch, MCP servers, cron, notebook editing (when enabled), subagent spawning, and `MyTool` for self-modification. Generic workspace file-write tools are not registered for the interactive agent; Dream uses internal helpers for memory consolidation.
- **Memory** (`viola/agent/memory.py`): Session history persistence with Dream two-phase memory consolidation. Uses atomic writes with fsync for durability.
- **Session Management** (`viola/session/manager.py`): Per-session history, context compaction, and TTL-based auto-compaction.
- **Config** (`viola/config/schema.py`, `loader.py`): Pydantic-based configuration loaded from `~/.viola/config.json`. Supports camelCase aliases for JSON compatibility.
- **Bridge** (`bridge/`): TypeScript services (e.g. WhatsApp bridge) bundled into the wheel via `pyproject.toml` `force-include`.
- **WebUI** (`webui/`): Vite-based React SPA that talks to the gateway over a WebSocket multiplex protocol. The dev server proxies `/api`, `/webui`, `/auth`, and WebSocket traffic to the gateway.

### Entry Points

- **CLI**: `viola/cli/commands.py`
- **Python SDK**: `viola/viola.py`

## Project-Specific Notes

- Architecture constraints: [`.agent/design.md`](.agent/design.md)
- Security boundaries: [`.agent/security.md`](.agent/security.md)
- Common gotchas: [`.agent/gotchas.md`](.agent/gotchas.md)

## Branching Strategy

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the full two-branch model (`main` vs `nightly`) and PR guidelines.

## Code Style

- Python 3.11+, asyncio throughout.
- Line length: 100.
- Linting: `ruff` with rules E, F, I, N, W (E501 ignored).
- pytest with `asyncio_mode = "auto"`.

## Common File Locations

- Config schema: `viola/config/schema.py`
- Provider base / new provider template: `viola/providers/base.py`
- Channel base / new channel template: `viola/channels/base.py`
- Tool registry: `viola/agent/tools/registry.py`
- WebUI dev proxy config: `webui/vite.config.ts`
- Tests mirror the `viola/` package structure.
