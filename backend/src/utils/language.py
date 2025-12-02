"""
Language detection utility functions
"""
from typing import Optional
from fastapi import Request


# Supported languages list
SUPPORTED_LANGUAGES = ['en', 'zh']
DEFAULT_LANGUAGE = 'en'


def detect_language(
    user_language: Optional[str] = None,
    request: Optional[Request] = None,
    default: str = DEFAULT_LANGUAGE
) -> str:
    """
    Detect user language preference
    
    Priority:
    1. User set language (user.language)
    2. Accept-Language header
    3. Default language
    
    Args:
        user_language: User set language
        request: FastAPI Request object
        default: Default language
        
    Returns:
        Detected language code (en, zh, etc.)
    """
    # 1. Prioritize user set language
    if user_language and user_language in SUPPORTED_LANGUAGES:
        return user_language
    
    # 2. Get from Accept-Language header
    if request:
        accept_language = request.headers.get('accept-language', '')
        if accept_language:
            # Parse Accept-Language: 'zh-CN,zh;q=0.9,en;q=0.8'
            # Take the first language and keep only the primary language code
            lang = accept_language.split(',')[0].split('-')[0].split('_')[0].lower()
            if lang in SUPPORTED_LANGUAGES:
                return lang
    
    # 3. Return default language
    return default


def normalize_language(lang: Optional[str]) -> str:
    """
    Normalize language code
    
    Convert various language code formats to unified format:
    - zh-CN, zh_CN, zh-Hans -> zh
    - en-US, en_US -> en
    
    Args:
        lang: Original language code
        
    Returns:
        Normalized language code
    """
    if not lang:
        return DEFAULT_LANGUAGE
    
    # Convert to lowercase and take primary language code
    lang = lang.lower().split('-')[0].split('_')[0]
    
    # Check if supported
    if lang in SUPPORTED_LANGUAGES:
        return lang
    
    return DEFAULT_LANGUAGE
