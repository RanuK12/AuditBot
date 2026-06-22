"""Tests for AuditBot URL validation."""
import pytest
from app import validate_url, app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch
import tempfile
import os

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


def test_audit_report_returns_pdf():
    """Test that /audit/report returns a PDF file."""
    # Create a temporary PDF file to simulate generation
    tmp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_pdf.write(b"%PDF-1.4 fake pdf content")
    tmp_pdf.close()

    async def mock_axe_audit(url):
        return {"url": url, "totalViolations": 0, "violations": []}

    async def mock_acc_violations(url):
        return []

    def mock_generate_pdf(data, url):
        return tmp_pdf.name

    with patch("app.run_axe_audit", side_effect=mock_axe_audit):
        with patch("app.get_accessibility_violations", side_effect=mock_acc_violations):
            with patch("app.generate_audit_pdf", side_effect=mock_generate_pdf):
                with TestClient(app) as client:
                    response = client.get("/audit/report?url=https://example.com")
                    assert response.status_code == 200
                    assert response.headers["content-type"] == "application/pdf"
                    # Verify PDF magic bytes
                    assert response.content[:4] == b"%PDF"

    # Clean up temporary file
    os.unlink(tmp_pdf.name)


def test_validate_url_invalid_no_domain():
    """URLs with no domain should raise 400."""
    with pytest.raises(HTTPException) as exc:
        validate_url("ftp://example.com")
    assert exc.value.status_code == 400


def test_audit_report_endpoint():
    """Test /audit/report GET endpoint returns PDF with correct content-type."""
    tmp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_pdf.write(b"%PDF-1.4 test")
    tmp_pdf.close()

    async def mock_axe(url):
        return {"url": url, "totalViolations": 1, "violations": [{"id": "test"}]}

    async def mock_acc(url):
        return [{"violation": "test"}]

    def mock_pdf(data, url):
        return tmp_pdf.name

    with patch("app.run_axe_audit", side_effect=mock_axe):
        with patch("app.get_accessibility_violations", side_effect=mock_acc):
            with patch("app.generate_audit_pdf", side_effect=mock_pdf):
                with TestClient(app) as client:
                    response = client.get("/audit/report?url=https://example.org")
                    assert response.status_code == 200
                    assert response.headers["content-type"] == "application/pdf"
                    assert response.content[:4] == b"%PDF"

    os.unlink(tmp_pdf.name)
