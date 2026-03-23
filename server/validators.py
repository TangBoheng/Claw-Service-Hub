"""
Simple input validation for Claw Service Hub.
Uses standard library only - no external dependencies.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_service_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate service name.
    
    Args:
        name: Service name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Service name cannot be empty"
    
    if len(name) > 64:
        return False, "Service name too long (max 64 characters)"
    
    # Allow alphanumeric, dash, underscore
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False, "Service name can only contain alphanumeric, dash, and underscore"
    
    return None, None


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"
    
    # Basic URL pattern
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        return False, "Invalid URL format"
    
    return None, None


def validate_api_key(key: str) -> Tuple[bool, Optional[str]]:
    """
    Validate API key format.
    
    Args:
        key: API key to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not key:
        return False, "API key cannot be empty"
    
    if len(key) < 16:
        return False, "API key too short (min 16 characters)"
    
    if len(key) > 256:
        return False, "API key too long (max 256 characters)"
    
    # Allow alphanumeric and some special characters
    if not re.match(r'^[a-zA-Z0-9_-]+$', key):
        return False, "API key contains invalid characters"
    
    return None, None


def validate_port(port: Union[int, str]) -> Tuple[bool, Optional[str]]:
    """
    Validate port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        port_int = int(port)
    except (ValueError, TypeError):
        return False, "Port must be a number"
    
    if port_int < 1 or port_int > 65535:
        return False, "Port must be between 1 and 65535"
    
    return None, None


def validate_user_id(user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate user ID format.
    
    Args:
        user_id: User ID to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not user_id:
        return False, "User ID cannot be empty"
    
    if len(user_id) > 128:
        return False, "User ID too long (max 128 characters)"
    
    # Allow alphanumeric, dash, underscore, at sign
    if not re.match(r'^[a-zA-Z0-9_-@]+$', user_id):
        return False, "User ID contains invalid characters"
    
    return None, None


def validate_rating(rating: Union[int, float]) -> Tuple[bool, Optional[str]]:
    """
    Validate rating value.
    
    Args:
        rating: Rating to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        rating_float = float(rating)
    except (ValueError, TypeError):
        return False, "Rating must be a number"
    
    if rating_float < 0 or rating_float > 5:
        return False, "Rating must be between 0 and 5"
    
    return None, None


def validate_pagination(page: Any, page_size: Any, max_page_size: int = 100) -> Tuple[bool, Optional[str]]:
    """
    Validate pagination parameters.
    
    Args:
        page: Page number
        page_size: Items per page
        max_page_size: Maximum allowed page size
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        page_int = int(page) if page is not None else 1
        page_size_int = int(page_size) if page_size is not None else 20
    except (ValueError, TypeError):
        return False, "Page and page_size must be integers"
    
    if page_int < 1:
        return False, "Page must be >= 1"
    
    if page_size_int < 1:
        return False, "Page size must be >= 1"
    
    if page_size_int > max_page_size:
        return False, f"Page size must be <= {max_page_size}"
    
    return None, None


def sanitize_string(s: str, max_length: int = 1000, strip_html: bool = True) -> str:
    """
    Sanitize a string input.
    
    Args:
        s: String to sanitize
        max_length: Maximum allowed length
        strip_html: Whether to strip HTML tags
        
    Returns:
        Sanitized string
    """
    if not s:
        return ""
    
    # Truncate
    s = s[:max_length]
    
    # Strip HTML if requested
    if strip_html:
        s = re.sub(r'<[^>]+>', '', s)
    
    # Remove null bytes
    s = s.replace('\x00', '')
    
    return s.strip()


class Validator:
    """
    Composite validator for request validation.
    """
    
    def __init__(self):
        self.errors: List[str] = []
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
    
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self.errors) == 0
    
    def get_errors(self) -> List[str]:
        """Get all error messages."""
        return self.errors.copy()
    
    def clear(self) -> None:
        """Clear errors."""
        self.errors.clear()


def validate_service_registration(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate service registration request.
    
    Args:
        data: Request data dictionary
        
    Returns:
        Tuple of (is_valid, error_list)
    """
    validator = Validator()
    
    # Validate required fields
    if "name" not in data or not data.get("name"):
        validator.add_error("Missing required field: name")
    else:
        valid, err = validate_service_name(data["name"])
        if valid is False:
            validator.add_error(f"Invalid service name: {err}")
    
    if "url" not in data or not data.get("url"):
        validator.add_error("Missing required field: url")
    else:
        valid, err = validate_url(data["url"])
        if valid is False:
            validator.add_error(f"Invalid URL: {err}")
    
    # Validate optional fields
    if "description" in data:
        desc = data["description"]
        if isinstance(desc, str) and len(desc) > 1000:
            validator.add_error("Description too long (max 1000 characters)")
    
    if "port" in data:
        valid, err = validate_port(data["port"])
        if valid is False:
            validator.add_error(f"Invalid port: {err}")
    
    return validator.is_valid(), validator.get_errors()


def validate_key_creation(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate API key creation request.
    
    Args:
        data: Request data dictionary
        
    Returns:
        Tuple of (is_valid, error_list)
    """
    validator = Validator()
    
    # Validate optional user_id
    if "user_id" in data and data["user_id"]:
        valid, err = validate_user_id(data["user_id"])
        if valid is False:
            validator.add_error(f"Invalid user_id: {err}")
    
    # Validate optional name
    if "name" in data:
        name = data["name"]
        if isinstance(name, str) and len(name) > 64:
            validator.add_error("Key name too long (max 64 characters)")
    
    return validator.is_valid(), validator.get_errors()