"""
Custom MCP Transports
Implements the newer Streamable HTTP transport specification (2025-06-18)
which supports synchronous responses in POST bodies, unlike the legacy SSE-only transport.
Refactored from mcp.client.sse to include Jina AI compatibility fixes.
"""

import logging
from typing import Any, Callable, Optional, AsyncGenerator, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
from contextlib import asynccontextmanager

import anyio
import httpx
from anyio.abc import TaskStatus
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from httpx_sse import aconnect_sse
from httpx_sse._exceptions import SSEError

import mcp.types as types
# Try to import these internal helpers if available, or redefine
from mcp.shared.message import SessionMessage
try:
    from mcp.shared._httpx_utils import McpHttpClientFactory, create_mcp_http_client
except ImportError:
    # Fallback if internal utils are not accessible
    McpHttpClientFactory = Callable[..., httpx.AsyncClient]
    
    @contextlib.asynccontextmanager
    async def create_mcp_http_client(**kwargs) -> AsyncGenerator[httpx.AsyncClient, None]:
        async with httpx.AsyncClient(**kwargs) as client:
            yield client

logger = logging.getLogger(__name__)

def remove_request_params(url: str) -> str:
    return urljoin(url, urlparse(url).path)

def _extract_session_id_from_endpoint(endpoint_url: str) -> str | None:
    query_params = parse_qs(urlparse(endpoint_url).query)
    return query_params.get("sessionId", [None])[0] or query_params.get("session_id", [None])[0]

@asynccontextmanager
async def streamable_http_client(
    url: str,
    headers: dict[str, Any] | None = None,
    timeout: float = 60.0,
    sse_read_timeout: float = 60 * 5,
    httpx_client_factory: McpHttpClientFactory = create_mcp_http_client,
    auth: httpx.Auth | None = None,
    on_session_created: Callable[[str], None] | None = None,
):
    """
    Enhanced Client transport for Streamable HTTP (Jina Compatible).
    Supports:
    1. Legacy SSE behavior (POST -> 202 -> SSE event)
    2. Sync HTTP behavior (POST -> 200 JSON -> process directly)
    3. Non-standard Ping-only servers (Jina)
    """
    read_stream_writer: MemoryObjectSendStream[SessionMessage | Exception]
    read_stream: MemoryObjectReceiveStream[SessionMessage | Exception]
    
    write_stream: MemoryObjectSendStream[SessionMessage]
    write_stream_reader: MemoryObjectReceiveStream[SessionMessage]

    read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

    # FIX 1: Ensure Accept header allows both
    req_headers = headers.copy() if headers else {}
    if "Accept" not in req_headers:
        req_headers["Accept"] = "application/json, text/event-stream"
    # Ensure Content-Type is set for POSTs by default, though httpx handles checking
    
    async with anyio.create_task_group() as tg:
        try:
            logger.debug(f"Connecting to SSE endpoint: {remove_request_params(url)}")
            async with httpx_client_factory(
                headers=req_headers, auth=auth, timeout=httpx.Timeout(timeout, read=sse_read_timeout)
            ) as client:
                async with aconnect_sse(
                    client,
                    "GET",
                    url,
                ) as event_source:
                    event_source.response.raise_for_status()
                    logger.debug("SSE connection established")

                    async def sse_reader(
                        task_status: TaskStatus[str] = anyio.TASK_STATUS_IGNORED,
                    ):
                        try:
                            # Start listening
                            async for sse in event_source.aiter_sse():
                                logger.debug(f"Received SSE event: {sse.event}")
                                match sse.event:
                                    case "endpoint":
                                        endpoint_url = urljoin(url, sse.data)
                                        logger.debug(f"Received endpoint URL: {endpoint_url}")
                                        
                                        # Validate origin
                                        url_parsed = urlparse(url)
                                        endpoint_parsed = urlparse(endpoint_url)
                                        if (
                                            url_parsed.netloc != endpoint_parsed.netloc
                                            or url_parsed.scheme != endpoint_parsed.scheme
                                        ):
                                            error_msg = f"Endpoint origin mismatch: {endpoint_url}"
                                            logger.error(error_msg)
                                            raise ValueError(error_msg)

                                        if on_session_created:
                                            session_id = _extract_session_id_from_endpoint(endpoint_url)
                                            if session_id:
                                                on_session_created(session_id)

                                        task_status.started(endpoint_url)

                                    case "message":
                                        if not sse.data:
                                            continue
                                        try:
                                            message = types.JSONRPCMessage.model_validate_json(sse.data)
                                            logger.debug(f"Received server message: {message}")
                                            await read_stream_writer.send(SessionMessage(message))
                                        except Exception as exc:
                                            logger.exception("Error parsing server message")
                                            await read_stream_writer.send(exc)
                                            continue

                                    case "ping":
                                        # FIX 2: Jina Ping Hack
                                        logger.debug("Received ping event")
                                        try:
                                            task_status.started(url) # Use base URL as endpoint
                                        except RuntimeError:
                                            pass # Already started
                                        continue
                                    
                                    case _:
                                        logger.warning(f"Unknown SSE event: {sse.event}")
                        except SSEError as sse_exc:
                            logger.exception("Encountered SSE exception")
                            raise sse_exc
                        except Exception as exc:
                            logger.exception("Error in sse_reader")
                            await read_stream_writer.send(exc)
                        finally:
                            await read_stream_writer.aclose()

                    # Start reader and wait for endpoint (or ping)
                    endpoint_url = await tg.start(sse_reader)
                    logger.debug(f"Starting post writer with endpoint URL: {endpoint_url}")

                    async def post_writer(endpoint_url: str):
                        try:
                            async with write_stream_reader:
                                async for session_message in write_stream_reader:
                                    logger.debug(f"Sending client message: {session_message}")
                                    
                                    # Use the shared client
                                    response = await client.post(
                                        endpoint_url,
                                        json=session_message.message.model_dump(
                                            by_alias=True,
                                            mode="json",
                                            exclude_none=True,
                                        ),
                                        headers=req_headers # Re-apply Accept header for POST
                                    )
                                    response.raise_for_status()
                                    logger.debug(f"Client message sent successfully: {response.status_code}")

                                    # FIX 3: Trace Synchronous Responses (Jina/Streamable HTTP)
                                    # If the server returns 200 OK with content, it might be the JSON-RPC response directly.
                                    # Standard JSON-RPC over HTTP usually returns application/json.
                                    # Streamable HTTP says: "If the input is a JSON-RPC request, the server MUST either return Content-Type: text/event-stream... or Content-Type: application/json"
                                    
                                    content_type = response.headers.get("Content-Type", "")
                                    if "application/json" in content_type:
                                         try:
                                             message = types.JSONRPCMessage.model_validate_json(response.content)
                                             logger.debug(f"Received synchronous JSON response: {message}")
                                             await read_stream_writer.send(SessionMessage(message))
                                         except Exception as e:
                                             logger.error(f"Failed to parse synchronous JSON: {e}")
                                    
                                    # Jina specifically simulates SSE in the body sometimes even with 200 OK?
                                    # My previous hack detected "event: message" in text. 
                                    # Let's keep that robust check for strict Jina compatibility if they don't use application/json
                                    elif "event: message" in response.text:
                                         logger.debug("Detected embedded SSE in POST response")
                                         content = response.text
                                         data = None
                                         for line in content.splitlines():
                                             if line.startswith("data:"):
                                                 data = line.split(":", 1)[1].strip()
                                                 break
                                         
                                         if data:
                                             try:
                                                 message = types.JSONRPCMessage.model_validate_json(data)
                                                 await read_stream_writer.send(SessionMessage(message))
                                             except Exception as e:
                                                 logger.error(f"Failed to parse embedded SSE: {e}")

                        except Exception:
                            logger.exception("Error in post_writer")
                        finally:
                            await write_stream.aclose()

                    tg.start_soon(post_writer, endpoint_url)

                    try:
                        yield read_stream, write_stream
                    except GeneratorExit:
                        # Handle generator closure gracefully
                        tg.cancel_scope.cancel()
                        raise
                    except Exception:
                        tg.cancel_scope.cancel()
                        raise
                    finally:
                        tg.cancel_scope.cancel()
                        
        except Exception as e:
             logger.error(f"Streamable HTTP Connection Error: {e}")
             raise
