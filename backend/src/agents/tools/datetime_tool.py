"""
DateTime Tool - Get current time and date information
"""
import logging
from datetime import datetime
from typing import Optional
import pytz
from langchain.tools import tool

logger = logging.getLogger(__name__)


@tool
async def get_current_time(timezone: Optional[str] = "Asia/Shanghai") -> str:
    """Get current date and time in ISO format.

Returns current datetime in the specified timezone (default: Asia/Shanghai).
Format: YYYY-MM-DD HH:MM:SS (Timezone Name)

Example: 2025-10-18 13:30:45 (Asia/Shanghai)

Common timezones: Asia/Shanghai, UTC, America/New_York, Europe/London, Asia/Tokyo
        
    Args:
        timezone: Timezone name (default: Asia/Shanghai). 
                 Examples: UTC, America/New_York, Europe/London
        
    Returns:
        ISO format datetime string with timezone
    """
    try:
        # Get timezone
        try:
            tz = pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone: {timezone}, using Asia/Shanghai")
            tz = pytz.timezone("Asia/Shanghai")
            timezone = "Asia/Shanghai"
        
        # Get current time in specified timezone
        now = datetime.now(tz)
        
        # Simple ISO format output
        formatted = now.strftime("%Y-%m-%d %H:%M:%S")
        result = f"{formatted} ({timezone})"
        
        logger.info(f"Get current time: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Failed to get time: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
