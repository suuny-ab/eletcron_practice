"""
参数验证工具函数
"""
from core.exceptions import ValidationException


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
