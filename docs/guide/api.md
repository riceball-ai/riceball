# API Access

RiceBall provides an OpenAI-compatible API interface, allowing you to seamlessly integrate your configured assistants into third-party applications or scripts using standard tools like the OpenAI SDK.

## Authentication

### Managing API Keys

1. Log in to the RiceBall Admin Panel.
2. Navigate to **API Keys** in the sidebar.
3. Click **Create Key**, enter a name, and copy the generated key (`sk-...`).
   > **Note**: The key is only displayed once upon creation. Please save it securely.

### Using the Key

Include the key in the HTTP Header of your requests:

```http
Authorization: Bearer sk-your-api-key
```

## Chat Completion API

RiceBall's chat interface is compatible with the OpenAI Chat Completion API specification. It is stateless, meaning you need to provide the full conversation history (`messages`) with each request. The backend will automatically inject the assistant's configured **System Prompt** and **Model Parameters** (e.g., Temperature).

### Endpoint

```
POST /api/v1/assistants/{assistant_id}/v1/chat/completions
```

- **assistant_id**: The UUID of the specific assistant you want to invoke.

### Request Body

Standard OpenAI format:

| Field | Type | Description |
|-------|------|-------------|
| `model` | string | (Optional) Ignored, as the assistant's bound model is used. |
| `messages` | array | List of messages including history. |
| `stream` | boolean | (Optional) Whether to stream the response. Default is `false`. |

### Python SDK Example

You can use the official `openai` Python library:

```bash
pip install openai
```

```python
from openai import OpenAI

# 1. Configuration
API_KEY = "sk-your-generated-key"
ASSISTANT_ID = "your-assistant-uuid" 
# Base URL format: {host}/api/v1/assistants/{assistant_id}/v1
BASE_URL = f"http://localhost:8000/api/v1/assistants/{ASSISTANT_ID}/v1"

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

# 2. Call the API
response = client.chat.completions.create(
    model="default", # This field is ignored by backend
    messages=[
        {"role": "user", "content": "Hello, who are you?"}
    ],
    # stream=True # Enable for streaming response
)

print(response.choices[0].message.content)
```

## Features

- **Configuration Injection**: The system automatically applies the Assistant's system prompt and model configuration (Temperature, Max Tokens).
- **Stateless**: The API does not read or write to RiceBall's internal `conversations` table. You have full control over the context window.
- **Streaming Support**: Full Server-Sent Events (SSE) support for real-time output.
