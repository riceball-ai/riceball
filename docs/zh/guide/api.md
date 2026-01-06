# API 访问

RiceBall 提供了兼容 OpenAI 格式的 API 接口，允许您使用标准的工具（如 OpenAI SDK）将配置好的助手无缝集成到第三方应用或脚本中。

## 鉴权 (Authentication)

### 管理 API 密钥

1. 登录 RiceBall 管理后台。
2. 在侧边栏导航至 **API 密钥 (API Keys)**。
3. 点击 **创建密钥**，输入名称后复制生成的密钥 (`sk-...`)。
   > **注意**: 密钥仅在创建时显示一次，请妥善保存。

### 使用密钥

在请求的 HTTP Header 中携带密钥：

```http
Authorization: Bearer sk-your-api-key
```

## 聊天补全接口 (Chat Completion)

RiceBall 的聊天接口兼容 OpenAI Chat Completion API 规范。该接口是**无状态**的，即您需要在每次请求中提供完整的对话历史 (`messages`)。后端会自动注入助手配置的 **System Prompt** 和 **模型参数**（如 Temperature）。

### 接口地址 (Endpoint)

```
POST /api/v1/assistants/{assistant_id}/v1/chat/completions
```

- **assistant_id**: 您要调用的具体助手的 UUID。

### 请求体 (Request Body)

标准的 OpenAI 格式：

| 字段 | 类型 | 说明 |
|-------|------|-------------|
| `model` | string | (可选) 该字段会被后端忽略，实际使用的是助手绑定的模型。 |
| `messages` | array | 包含历史记录的消息列表。 |
| `stream` | boolean | (可选) 是否开启流式响应。默认为 `false`。 |

### Python SDK 示例

您可以使用官方的 `openai` Python 库：

```bash
pip install openai
```

```python
from openai import OpenAI

# 1. 配置
API_KEY = "sk-your-generated-key"
ASSISTANT_ID = "your-assistant-uuid" 
# Base URL 结构: {host}/api/v1/assistants/{assistant_id}/v1
BASE_URL = f"http://localhost:8000/api/v1/assistants/{ASSISTANT_ID}/v1"

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

# 2. 调用 API
response = client.chat.completions.create(
    model="default", # 后端会忽略此字段
    messages=[
        {"role": "user", "content": "你好，请介绍一下你自己"}
    ],
    # stream=True # 开启流式响应
)

print(response.choices[0].message.content)
```

## 特性说明

- **配置注入**: 系统会自动应用助手的 System Prompt 和模型配置（Temperature, Max Tokens）。
- **无状态**: 该 API 不会读写 RiceBall 内部的 `conversations` 表。您拥有对上下文窗口的完全控制权。
- **流式支持**: 完整支持 Server-Sent Events (SSE)流式输出。
