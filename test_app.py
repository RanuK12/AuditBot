"""Tests for AuditBot URL validation."""
import pytest
from app import validate_url
from fastapi import HTTPException

def test_validate_url_valid():
    """Valid URLs should be accepted and normalized."""
    assert validate_url("https://example.com") == "https://example.com"
    assert validate_url("http://example.com") == "http://example.com"
    assert validate_url("example.com") == "https://example.com"
    assert validate_url("https://example.com/path?q=1") == "https://example.com/path?q=1"
    assert validate_url("localhost") == "https://localhost"

def test_validate_url_invalid():
    """Invalid URLs should raise HTTPException 400."""
    with pytest.raises(HTTPException) as exc:
        validate_url("")
    assert exc.value.status_code == 400
    
    with pytest.raises(HTTPException) as exc:
        validate_url("   ")
    assert exc.value.status_code == 400
    
    with pytest.raises(HTTPException) as exc:
        validate_url("not-a-domain")
    assert exc.value.status_code == 400
    
    with pytest.raises(HTTPException) as exc:
        validate_url("ftp://example.com")
    assert exc.value.status_code == 400
