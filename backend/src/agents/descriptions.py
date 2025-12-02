"""
Agent tool action and observation descriptions
"""
from typing import Dict, Any


def get_action_description(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """
    Generate friendly description for tool action
    
    Args:
        tool_name: Name of the tool being used
        tool_input: Input parameters for the tool
        
    Returns:
        Human-friendly description in Chinese
    """
    if tool_name == "calculator":
        expression = tool_input.get('expression', '')
        return f"Calculating: {expression}"
    
    elif tool_name == "knowledge_base_query":
        query = tool_input.get('query', '')
        top_k = tool_input.get('top_k', 5)
        return f"Querying knowledge base (Query: {query[:30]}{'...' if len(query) > 30 else ''}, Fetching {top_k} results)"
    
    elif tool_name == "http_request":
        url = tool_input.get('url', '')
        method = tool_input.get('method', 'GET')
        # Extract domain for display
        domain = url.split('/')[2] if url.startswith('http') else url[:30]
        return f"Sending {method} request to: {domain}"
    
    elif tool_name == "get_current_time":
        timezone = tool_input.get('timezone', 'Asia/Shanghai')
        return f"Getting current time ({timezone})"
    
    else:
        # Generic description for unknown tools
        return f"Using tool: {tool_name}"


def get_observation_description(tool_name: str, observation: str) -> str:
    """
    Generate friendly description for tool observation
    
    Args:
        tool_name: Name of the tool that was executed
        observation: Raw observation result
        
    Returns:
        Human-friendly description in English
    """
    if tool_name == "calculator":
        return f"Calculation result: {observation}"
    
    elif tool_name == "knowledge_base_query":
        # Try to extract document count from observation
        if observation and len(observation) > 0:
            return "Found relevant information, organizing answer..."
        else:
            return "No relevant information found"
    
    elif tool_name == "http_request":
        # Extract status code from observation
        if "Status:" in observation:
            status_line = [line for line in observation.split('\n') if line.startswith("Status:")][0]
            status_code = status_line.split()[1]
            if status_code.startswith('2'):
                return f"Request successful ({status_code}), data received"
            elif status_code.startswith('4'):
                return f"Request failed ({status_code}), client error"
            elif status_code.startswith('5'):
                return f"Request failed ({status_code}), server error"
        elif "❌" in observation:
            return "Request failed, connection error"
        return "Request completed"
    
    elif tool_name == "get_current_time":
        return "Current time retrieved"
    
    else:
        # Generic description for unknown tools
        return f"Tool {tool_name} execution completed"


# Tool name mappings for display
TOOL_DISPLAY_NAMES = {
    "calculator": "Calculator",
    "knowledge_base_query": "Knowledge Base Query",
    "http_request": "HTTP Request",
    "get_current_time": "Time Query",
}


def get_tool_display_name(tool_name: str) -> str:
    """Get friendly display name for tool"""
    return TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
