# Model Context Protocol (MCP)

RiceBall acts as a **Universal MCP Host**, implementing the full [Model Context Protocol](https://modelcontextprotocol.io/) specification. This allows RiceBall agents to connect to external tools, data sources, and services securely and standardized.

## Overview

MCP allows you to extend RiceBall's capabilities without modifying the core code. You can run "MCP Servers" that expose tools (e.g., "read_file", "search_web", "query_database"), and RiceBall will automatically let your agents use them.

RiceBall supports two transport types:

1.  **Stdio (Standard Input/Output)**: For local processes. Ideal for development or when running RiceBall directly on your machine.
2.  **HTTP (SSE)**: For remote servers or Dockerized setups. Ideal for production and isolating safe/unsafe tools in separate containers.

## 📦 Using Presets

The easiest way to get started is using **Presets**. Navigate to `Admin Panel -> MCP Servers -> Presets`.

RiceBall comes with built-in configurations for popular MCP servers:

-   **Filesystem**: Read and write files securely.
-   **Brave Search**: Perform web searches (requires API key).
-   **Fetch**: Retrieve web page content.

Click **Install** on a preset to enable it. Some presets (like Brave Search) may ask for configuration overrides (e.g., API Key).

## 🐳 Docker Sidecar Pattern (Recommended)

In a containerized environment (Docker), RiceBall cannot directly spawn local processes (Stdio) on your host machine. Instead, we use the "Sidecar" pattern: MCP servers run in their own containers and communicate with RiceBall via HTTP/SSE.

### 1. Enable Sidecar Services

We provide a `docker-compose.mcp.example.yml` file. Include it in your deployment or merge it into your main `docker-compose.yml`.

Example to enable the **Filesystem** server:

```yaml
# docker-compose.yml
services:
  # ... other services ...

  # MCP Filesystem Server
  mcp-filesystem:
    build:
      context: ./extra/mcp-servers/filesystem
      dockerfile: Dockerfile
    volumes:
      - ./storage/files:/data  # Mount the directory you want to expose
    ports:
      - 8999:8000
```

### 2. Connect via Preset

1.  Start the containers: `docker compose up -d`.
2.  Go to **Admin Panel -> Presets**.
3.  Install **Filesystem (Remote)**.
    -   Host connection URL: `http://mcp-filesystem:8000/sse` (Internal Docker DNS)

## 🛠️ Manual Configuration

You can can manually add any custom MCP server.

### Adding a Stdio Server

Suitable for local development (running `fastapi dev`).

**Configuration Example:**

-   **Name**: `local-git`
-   **Type**: `STDIO`
-   **Config**:
    ```json
    {
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "/path/to/repo"],
      "env": {
        "PATH": "/usr/bin"
      }
    }
    ```

### Adding an HTTP/SSE Server

Suitable for connecting to remote agents or docker containers.

**Configuration Example:**

-   **Name**: `remote-filesystem`
-   **Type**: `HTTP` (or `SSE`)
-   **Config**:
    ```json
    {
      "url": "http://localhost:8999/sse",
      "headers": {
        "Authorization": "Bearer optional-token"
      }
    }
    ```

## Troubleshooting

-   **Connection Refused**: Ensure the MCP server container is running and on the same Docker network as RiceBall.
-   **Stdio Error**: Ensure the command exists in the RiceBall backend container (if running in Docker, Stdio only works for commands *inside* the RiceBall container).
