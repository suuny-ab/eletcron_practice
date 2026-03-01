"""
参数验证工具函数
"""
import re

from core.exceptions import ValidationException

# session_id 允许的字符：字母、数字、下划线、连字符
_SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")


def require_param(value: str | None, param_name: str, strip: bool = True) -> str:
    """
    验证参数是否为空，如果为空则抛出 ValidationException
    
    Args:
        value: 参数值
        param_name: 参数名称，用于错误信息
        strip: 是否去除首尾空格，默认 True
        
    Returns:
        处理后的参数值
        
    Raises:
        ValidationException: 当参数为空时
        
    Examples:
        >>> require_param("  hello  ", "filename")
        'hello'
        >>> require_param(None, "filename")
        ValidationException: 必须提供 filename 参数
    """
    if strip and value is not None:
        value = value.strip()
    
    if not value:
        raise ValidationException(f"必须提供 {param_name} 参数")
    
    return value


def validate_session_id(session_id: str) -> str:
    """
    验证 session_id 格式，防止路径穿越等安全问题
    
    Args:
        session_id: 会话 ID
        
    Returns:
        验证通过的 session_id
        
    Raises:
        ValidationException: 当 session_id 格式非法时
    """
    if not session_id or not session_id.strip():
        raise ValidationException("session_id 不能为空")
    
    session_id = session_id.strip()
    
    if len(session_id) > 128:
        raise ValidationException("session_id 长度不能超过 128 字符")
    
    if not _SESSION_ID_PATTERN.match(session_id):
        raise ValidationException("session_id 包含非法字符，仅允许字母、数字、下划线和连字符")
    
    return session_id


def validate_service(service: object | None, service_name: str) -> None:
    """
    验证服务是否已初始化
    
    Args:
        service: 服务实例
        service_name: 服务名称，用于错误信息
        
    Raises:
        ValidationException: 当服务未初始化时
        
    Examples:
        >>> validate_service(None, "RAG")
        ValidationException: RAG 服务未初始化
    """
    if service is None:
        raise ValidationException(f"{service_name} 服务未初始化")
