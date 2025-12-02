"""
Built-in calculator tool
"""
import re
from langchain.tools import tool


@tool
async def calculator(expression: str) -> str:
    """Useful for performing mathematical calculations. Input should be a valid mathematical expression.
    
    Args:
        expression: A valid mathematical expression (e.g., "2 + 2", "10 * 5 + 3")
        
    Returns:
        The calculation result as a string
    """
    try:
        # Clean the expression - remove any non-mathematical characters
        clean_expr = re.sub(r'[^0-9+\-*/().\s]', '', expression)
        
        # Evaluate the expression safely
        result = eval(clean_expr, {"__builtins__": {}}, {})
        
        return f"The result of {expression} is {result}"
    except Exception as e:
        return f"Error calculating expression: {str(e)}"
