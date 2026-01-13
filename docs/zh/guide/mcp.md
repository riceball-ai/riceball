# Model Context Protocol (MCP)

RiceBall 作为一个 **通用 MCP 主机 (Universal MCP Host)**，完整实现了 [Model Context Protocol](https://modelcontextprotocol.io/) 规范。这使得 RiceBall 智能体能够以标准化、安全的方式连接外部工具、数据源和服务。

## 概览 (Overview)

MCP 允许你在不修改核心代码的情况下扩展 RiceBall 的能力。你可以运行 "MCP 服务器" 来暴露工具（例如 "read_file"、"search_web"、"query_database"），RiceBall 会自动让智能体发现并使用这些工具。

RiceBall 支持两种传输协议：

1.  **Stdio (标准输入输出)**：用于本地进程。适合本地开发，或者当你直接在宿主机运行 RiceBall 时使用。
2.  **HTTP (SSE)**：用于远程服务或 Docker 容器化部署。适合生产环境，以及将不安全的操作隔离在独立容器中（Sidecar 模式）。

## 📦 使用预设 (Using Presets)

最简单的上手方式是使用 **预设 (Presets)**。请前往 `管理后台 -> MCP 服务器 -> 预设库`。

RiceBall 内置了常用 MCP 服务器的配置：

-   **Filesystem (文件系统)**：安全地读写文件。
-   **Brave Search**：执行网络搜索（需要 API Key）。
-   **Fetch**：获取网页内容。

点击预设卡片上的 **安装** 按钮即可启用。部分预设（如 Brave Search）在安装时可能会要求输入配置覆盖（如 API Key）。

## 🐳 Docker Sidecar 模式 (推荐)

在容器化环境 (Docker) 中，RiceBall 无法直接通过 Stdio 启动宿主机上的进程。因此，我们采用 "Sidecar (边车)" 模式：MCP 服务器运行在独立的容器中，通过 HTTP/SSE 与 RiceBall 通信。

### 1. 启用 Sidecar 服务

项目根目录提供了一个 `docker-compose.mcp.example.yml` 文件。你可以将其包含在你的部署中，或合并到主 `docker-compose.yml`。

启用 **Filesystem** 服务器的示例：

```yaml
# docker-compose.yml
services:
  # ... 其他服务 ...

  # MCP Filesystem Server
  mcp-filesystem:
    build:
      context: ./extra/mcp-servers/filesystem
      dockerfile: Dockerfile
    volumes:
      - ./storage/files:/data  # 挂载通过 MCP 暴露的目录
    ports:
      - 8999:8000
```

### 2. 通过预设连接

1.  启动容器：`docker compose up -d`。
2.  进入 **管理后台 -> 预设库**。
3.  安装 **Filesystem (Docker Sidecar)**。
    -   Host 连接地址默认为：`http://mcp-filesystem:8000/sse` (Docker 内部 DNS)。

## 🛠️ 手动配置 (Manual Configuration)

你也可以手动添加任何自定义的 MCP 服务器。

### 添加 Stdio 服务器

适用于本地开发调试（例如运行 `fastapi dev` 时）。

**配置示例：**

-   **名称**: `local-git`
-   **类型**: `STDIO`
-   **配置 (Config)**:
    ```json
    {
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "/path/to/repo"],
      "env": {
        "PATH": "/usr/bin"
      }
    }
    ```

### 添加 HTTP/SSE 服务器

适用于连接远程 Agent 或 Docker 容器。

**配置示例：**

-   **名称**: `remote-filesystem`
-   **类型**: `HTTP` (或 `SSE`)
-   **配置 (Config)**:
    ```json
    {
      "url": "http://localhost:8999/sse",
      "headers": {
        "Authorization": "Bearer optional-token"
      }
    }
    ```

## 故障排除

-   **Connection Refused (连接被拒绝)**：确保 MCP 服务器容器正在运行，并且与 RiceBall 处于同一个 Docker 网络中。
-   **Stdio Error**：确保命令在 RiceBall 后端容器内存在（如果在 Docker 中运行，Stdio 只能调用 *容器内部* 的命令，无法调用宿主机工具）。
