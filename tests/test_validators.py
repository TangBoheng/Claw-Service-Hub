"""Tests for input validators."""

import pytest
from server.utils.validators import (
    ValidationError,
    Validator,
    validate_api_key,
    validate_port,
    validate_pagination,
    validate_rating,
    validate_service_name,
    validate_service_registration,
    validate_url,
    validate_user_id,
    sanitize_string,
)


class TestValidateServiceName:
    def test_valid_name(self):
        assert validate_service_name("my-service") == (None, None)
        assert validate_service_name("service_123") == (None, None)
        assert validate_service_name("Service") == (None, None)
    
    def test_empty_name(self):
        valid, err = validate_service_name("")
        assert valid is False
        assert err is not None
    
    def test_name_too_long(self):
        valid, err = validate_service_name("a" * 65)
        assert valid is False
        assert "too long" in err
    
    def test_invalid_characters(self):
        valid, err = validate_service_name("my service")
        assert valid is False
        assert "can only contain" in err


class TestValidateUrl:
    def test_valid_http_url(self):
        assert validate_url("http://localhost:8080") == (None, None)
    
    def test_valid_https_url(self):
        assert validate_url("https://example.com") == (None, None)
    
    def test_valid_url_with_path(self):
        assert validate_url("https://api.example.com/v1/service") == (None, None)
    
    def test_empty_url(self):
        valid, err = validate_url("")
        assert valid is False
    
    def test_invalid_url(self):
        valid, err = validate_url("not-a-url")
        assert valid is False


class TestValidateApiKey:
    def test_valid_key(self):
        assert validate_api_key("test-key-12345678") == (None, None)
    
    def test_key_too_short(self):
        valid, err = validate_api_key("short")
        assert valid is False
        assert "too short" in err
    
    def test_empty_key(self):
        valid, err = validate_api_key("")
        assert valid is False


class TestValidatePort:
    def test_valid_port(self):
        assert validate_port(8080) == (None, None)
        assert validate_port("8080") == (None, None)
    
    def test_port_out_of_range(self):
        valid, err = validate_port(70000)
        assert valid is False
        assert err is not None
    
    def test_invalid_port(self):
        valid, err = validate_port("abc")
        assert valid is False
        assert err is not None


class TestValidateRating:
    def test_valid_rating(self):
        assert validate_rating(5) == (None, None)
        assert validate_rating(3.5) == (None, None)
    
    def test_rating_out_of_range(self):
        valid, err = validate_rating(6)
        assert valid is False
        assert err is not None
        valid, err = validate_rating(-1)
        assert valid is False
        assert err is not None


class TestValidatePagination:
    def test_valid_pagination(self):
        assert validate_pagination(1, 20) == (None, None)
        assert validate_pagination("1", "20") == (None, None)
    
    def test_page_too_low(self):
        valid, err = validate_pagination(0, 20)
        assert valid is False
        assert err is not None
    
    def test_page_size_too_high(self):
        valid, err = validate_pagination(1, 200, max_page_size=100)
        assert valid is False
        assert err is not None


class TestSanitizeString:
    def test_basic_sanitization(self):
        assert sanitize_string("  hello  ") == "hello"
    
    def test_strips_html(self):
        assert sanitize_string("<script>alert(1)</script>test") == "alert(1)test"
    
    def test_truncates_long_string(self):
        long_str = "a" * 2000
        assert len(sanitize_string(long_str, max_length=100)) == 100
    
    def test_removes_null_bytes(self):
        assert sanitize_string("test\x00") == "test"


class TestValidator:
    def test_add_error(self):
        v = Validator()
        v.add_error("Error 1")
        assert not v.is_valid()
        assert "Error 1" in v.get_errors()
    
    def test_clear(self):
        v = Validator()
        v.add_error("Error")
        v.clear()
        assert v.is_valid()


class TestValidateServiceRegistration:
    def test_valid_registration(self):
        data = {
            "name": "test-service",
            "url": "http://localhost:8080",
        }
        valid, errors = validate_service_registration(data)
        assert valid is True
        assert len(errors) == 0
    
    def test_missing_name(self):
        data = {"url": "http://localhost:8080"}
        valid, errors = validate_service_registration(data)
        assert valid is False
        assert any("name" in e.lower() for e in errors)
    
    def test_missing_url(self):
        data = {"name": "test"}
        valid, errors = validate_service_registration(data)
        assert valid is False
        assert any("url" in e.lower() for e in errors)