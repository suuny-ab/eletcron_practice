"""
字符串处理工具函数
"""


def mask_api_key(api_key: str | None, visible_chars: int = 4) -> str:
    """
    掩码 API Key，只显示最后几位字符
    
    Args:
        api_key: API Key 字符串
        visible_chars: 可见的字符数，默认 4
        
    Returns:
        掩码后的字符串，如 "****abcd"
        
    Examples:
        >>> mask_api_key("sk-1234567890abcdef")
        '****abcdef'
        >>> mask_api_key(None)
        ''
        >>> mask_api_key("")
        ''
    """
    if not api_key:
        return ""
    return f"****{api_key[-visible_chars:]}"
