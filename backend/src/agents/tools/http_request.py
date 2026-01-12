"""
HTTP Request Tool - Make HTTP requests to external APIs
"""
import json
import logging
from typing import Any, Dict, Optional, Literal, Union
import httpx
from markitdown import MarkItDown

from .base import AgentTool
from .registry import tool_registry

logger = logging.getLogger(__name__)

# Initialize MarkItDown for HTML conversion
_markitdown = MarkItDown()


def _extract_html_text(html_content: str, max_length: int = 2000) -> str:
    """
    Extract main text content from HTML using MarkItDown
    
    Args:
        html_content: Raw HTML string
        max_length: Maximum length of extracted text
        
    Returns:
        Extracted text content in markdown format
    """
    try:
        # Use MarkItDown to convert HTML to markdown
        # This extracts main content and removes script/style tags
        import tempfile
        import os
        import re
        
        # Create a temporary file for MarkItDown
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_path = f.name
        
        try:
            # Convert HTML to markdown
            result = _markitdown.convert(temp_path)
            text_content = result.text_content.strip()
            
            # Remove markdown image syntax: ![alt](url)
            text_content = re.sub(r'!\[.*?\]\(.*?\)', '', text_content)
            
            # Clean up multiple empty lines
            text_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', text_content)
            
            # Clean up lines with only whitespace
            text_content = '\n'.join(line.rstrip() for line in text_content.split('\n'))
            
            # Remove leading/trailing whitespace
            text_content = text_content.strip()
            
            # Limit length
            if len(text_content) > max_length:
                text_content = text_content[:max_length] + "\n... (truncated)"
            
            return text_content
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        logger.warning(f"Failed to extract HTML text: {e}, falling back to raw text")
        # Fallback: return raw text with length limit
        return html_content[:max_length] + ("\n... (truncated)" if len(html_content) > max_length else "")


@tool_registry.register
class HttpRequestTool(AgentTool):
    """
    Send HTTP requests to external APIs
    
    Supports GET, POST, PUT, DELETE, PATCH methods with custom headers and body.
    Authentication tokens can be configured via tool_config.
    """
    
    @property
    def name(self) -> str:
        return "http_request"
    
    @property
    def description(self) -> str:
        return """Send HTTP request to external API.

Supports GET, POST, PUT, DELETE, PATCH methods.
You can provide custom headers and request body.
Authentication headers can be pre-configured via tool config.

Examples:
- Get GitHub user: url="https://api.github.com/users/octocat", method="GET"
- Search API: url="https://api.example.com/search?q=python", method="GET"
- Create resource: url="https://api.example.com/items", method="POST", body={"name": "test"}
- With headers: url="https://api.example.com/data", headers={"X-API-Key": "xxx"}
- With query params: url="https://api.example.com/search", query_params={"q": "python", "page": "1"}

Parameters:
- url (required): Full URL to request
- method: HTTP method (GET, POST, PUT, DELETE, PATCH), default: GET
- headers: Dictionary of HTTP headers. Example: {"Authorization": "Bearer token", "X-Custom": "value"}
- body: Dictionary for request body (POST/PUT/PATCH). Example: {"name": "test", "value": 123}
- query_params: Dictionary of URL query parameters. Example: {"search": "keyword", "page": "1"}

IMPORTANT: headers, body, and query_params must be dictionaries (objects), NOT JSON strings.
"""
    
    async def execute(
        self,
        url: str,
        method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET",
        headers: Optional[Union[Dict[str, str], str]] = None,
        body: Optional[Union[Dict[str, Any], str]] = None,
        query_params: Optional[Union[Dict[str, str], str]] = None
    ) -> str:
        """
        Execute HTTP request
        
        Args:
            url: Full URL to request (e.g., "https://api.github.com/users/octocat")
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            headers: Additional headers to include in request
            body: Request body for POST/PUT/PATCH (will be JSON encoded)
            query_params: URL query parameters
            
        Returns:
            Formatted response with status, headers, and body
        """
        # Fix: Convert string parameters to dict if needed (LLM sometimes passes JSON strings)
        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
                logger.warning(f"Converted headers from string to dict: {headers}")
            except Exception as e:
                logger.error(f"Failed to parse headers string: {e}")
                headers = None
        
        if isinstance(body, str):
            try:
                body = json.loads(body)
                logger.warning(f"Converted body from string to dict: {body}")
            except Exception as e:
                logger.error(f"Failed to parse body string: {e}")
                body = None
        
        if isinstance(query_params, str):
            try:
                query_params = json.loads(query_params)
                logger.warning(f"Converted query_params from string to dict: {query_params}")
            except Exception as e:
                logger.error(f"Failed to parse query_params string: {e}")
                query_params = None
        
        # Get default configuration from tool config
        default_headers = self.config.parameters.get("default_headers", {})
        timeout = self.config.parameters.get("timeout", 30.0)
        base_url = self.config.parameters.get("base_url", "")
        
        # Build full URL (support base_url in config)
        if base_url and not url.startswith("http"):
            url = base_url.rstrip("/") + "/" + url.lstrip("/")
        
        # Merge headers (tool config + request headers)
        # Use more browser-like default headers to avoid being blocked
        browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        # If the user explicitly asks for JSON, we should respect that or start with JSON accept
        # But if no explicit accept is given, browser-like is safer for general scraping.
        # However, this tool description says "Supports GET... API". APIs usually need JSON.
        # Let's keep JSON priority if it looks like an API call (based on no specific Accept header provided)
        # BUT the user report says "can't request 3rd party websites" -> implies scraping/browse intent.
        
        # Strategy:
        # 1. Base is browser headers (good for sites)
        # 2. If 'content-type' in headers is 'application/json', we assume API intent and adjust Accept.
        # 3. Allow config defaults override.
        
        merged_headers = browser_headers.copy()
        merged_headers.update(default_headers)
        if headers:
            merged_headers.update(headers)
            
        # If sending JSON body but no Content-Type, set it
        if body and "Content-Type" not in merged_headers and "content-type" not in merged_headers:
            merged_headers["Content-Type"] = "application/json"
            
        # If we think it's an API call (JSON body or JSON content type), make sure Accept includes JSON
        is_json_request = (
            merged_headers.get("Content-Type") == "application/json" or 
            merged_headers.get("content-type") == "application/json"
        )
        if is_json_request and "Accept" not in (headers or {}):
             merged_headers["Accept"] = "application/json, */*"

        logger.info(f"HTTP {method} request to {url}")
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=merged_headers,
                    json=body if body else None,
                    params=query_params if query_params else None
                )
                
                # Log response status
                logger.info(f"Response status: {response.status_code}")
                
                # Parse response based on content type
                content_type = response.headers.get("content-type", "")
                
                if "application/json" in content_type:
                    # JSON response: pretty print
                    try:
                        response_data = response.json()
                        data_str = json.dumps(response_data, indent=2, ensure_ascii=False)
                    except Exception:
                        data_str = response.text[:2000]
                        if len(response.text) > 2000:
                            data_str += "\n... (truncated)"
                            
                elif "text/html" in content_type:
                    # HTML response: extract main text content
                    logger.info("HTML content detected, extracting text...")
                    data_str = _extract_html_text(response.text, max_length=2000)
                    
                else:
                    # Other text content: limit length
                    data_str = response.text[:2000]
                    if len(response.text) > 2000:
                        data_str += "\n... (truncated)"
                
                # Format response
                result = f"""HTTP {method} {url}
Status: {response.status_code} {response.reason_phrase}
Content-Type: {content_type}

Response:
{data_str}"""
                
                # Add error info if status >= 400
                if response.status_code >= 400:
                    result += f"\n\n⚠️ Error: HTTP {response.status_code} {response.reason_phrase}"
                
                return result
                
        except httpx.TimeoutException:
            error_msg = f"Request timeout after {timeout} seconds"
            logger.error(error_msg)
            return f"❌ {error_msg}\nURL: {url}"
        
        except httpx.RequestError as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            return f"❌ {error_msg}\nURL: {url}"
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return f"❌ {error_msg}\nURL: {url}"
