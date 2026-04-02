"""Input validators for the service hub."""

import re
import html
from typing import Any, Optional, Tuple


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


class Validator:
    """Base validator class."""
    
    def __init__(self):
        self._errors = []
    
    def add_error(self, message: str):
        self._errors.append(message)
    
    def is_valid(self) -> bool:
        return len(self._errors) == 0
    
    def get_errors(self) -> list:
        return self._errors
    
    def clear(self):
        self._errors = []


def validate_service_name(name: str) -> Tuple[Optional[bool], Optional[str]]:
    """Validate service name."""
    if not name:
        return False, "Service name cannot be empty"
    
    if len(name) > 64:
        return False, "Service name is too long (max 64 characters)"
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False, "Service name can only contain letters, numbers, hyphens, and underscores"
    
    return None, None


def validate_url(url: str) -> Tuple[Optional[bool], Optional[str]]:
    """Validate URL format."""
    if not url:
        return False, "URL cannot be empty"
    
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(url_pattern, url, re.IGNORECASE):
        return False, "Invalid URL format"
    
    return None, None


def validate_api_key(key: str) -> Tuple[Optional[bool], Optional[str]]:
    """Validate API key format."""
    if not key:
        return False, "API key cannot be empty"
    
    if len(key) < 8:
        return False, "API key is too short (min 8 characters)"
    
    return None, None


def validate_port(port: Any) -> Tuple[Optional[bool], Optional[str]]:
    """Validate port number."""
    try:
        port_int = int(port)
    except (ValueError, TypeError):
        return False, "Port must be a number"
    
    if port_int < 1 or port_int > 65535:
        return False, "Port must be between 1 and 65535"
    
    return None, None


def validate_rating(rating: Any) -> Tuple[Optional[bool], Optional[str]]:
    """Validate rating value."""
    try:
        rating_float = float(rating)
    except (ValueError, TypeError):
        return False, "Rating must be a number"
    
    if rating_float < 0 or rating_float > 5:
        return False, "Rating must be between 0 and 5"
    
    return None, None


def validate_pagination(page: Any, page_size: Any, max_page_size: int = 100) -> Tuple[Optional[bool], Optional[str]]:
    """Validate pagination parameters."""
    try:
        page_int = int(page)
        size_int = int(page_size)
    except (ValueError, TypeError):
        return False, "Page and page_size must be numbers"
    
    if page_int < 1:
        return False, "Page must be at least 1"
    
    if size_int < 1:
        return False, "Page size must be at least 1"
    
    if size_int > max_page_size:
        return False, f"Page size cannot exceed {max_page_size}"
    
    return None, None


def sanitize_string(s: str, max_length: int = 1000) -> str:
    """Sanitize string input."""
    if not s:
        return ""
    
    # Remove null bytes
    s = s.replace('\x00', '')
    
    # Strip leading/trailing whitespace
    s = s.strip()
    
    # Remove HTML tags but keep content
    s = re.sub(r'<[^>]+>', '', s)
    
    # Unescape HTML entities
    s = html.unescape(s)
    
    # Truncate if needed
    if len(s) > max_length:
        s = s[:max_length]
    
    return s


def validate_user_id(user_id: str) -> Tuple[Optional[bool], Optional[str]]:
    """Validate user ID format."""
    if not user_id:
        return False, "User ID cannot be empty"
    
    if len(user_id) > 64:
        return False, "User ID is too long"
    
    return None, None


def validate_service_registration(data: dict) -> Tuple[bool, list]:
    """Validate service registration data."""
    errors = []
    
    if "name" not in data or not data["name"]:
        errors.append("Service name is required")
    else:
        valid, err = validate_service_name(data["name"])
        if valid is False:
            errors.append(f"Service name: {err}")
    
    if "url" not in data or not data["url"]:
        errors.append("Service URL is required")
    else:
        valid, err = validate_url(data["url"])
        if valid is False:
            errors.append(f"Service URL: {err}")
    
    return len(errors) == 0, errors