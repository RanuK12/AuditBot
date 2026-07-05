"""Tests for AuditBot URL validation."""
import pytest
from app import validate_url, app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch
import tempfile
import os
import httpx

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


def test_audit_report_returns_pdf(tmp_path):
    """Test that /audit/report returns a PDF file."""
    import os
    # Create a temporary PDF file to simulate generation
    tmp_pdf = tmp_path / "report.pdf"
    tmp_pdf.write_bytes(b"%PDF-1.4 fake pdf content")

    async def mock_axe_audit(url):
        return {"url": url, "totalViolations": 0, "violations": []}

    async def mock_acc_violations(url):
        return []

    def mock_generate_pdf(data, url):
        return str(tmp_pdf)

    with patch("app.run_axe_audit", side_effect=mock_axe_audit):
        with patch("app.get_accessibility_violations", side_effect=mock_acc_violations):
            with patch("app.generate_pdf", side_effect=mock_generate_pdf):
                with TestClient(app) as client:
                    response = client.get("/audit/report?url=https://accessible-site.com")
                    assert response.status_code == 200
                    assert response.headers["content-type"] == "application/pdf"

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


@pytest.mark.asyncio
async def test_audit_get_basic():
    """GET /audit?url=... should return 200 with url_ok, issues and score fields."""

    async def mock_axe_audit(url):
        return {"url": url, "totalViolations": 0, "violations": []}

    async def mock_acc_violations(url):
        return []

    with patch("app.run_axe_audit", side_effect=mock_axe_audit):
        with patch("app.get_accessibility_violations", side_effect=mock_acc_violations):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/audit", params={"url": "https://example.com"})
                assert response.status_code == 200
                data = response.json()
                assert "url_ok" in data
                assert "issues" in data
                assert isinstance(data["issues"], list)
                assert "score" in data
                assert isinstance(data["score"], (int, float))
                assert 0 <= data["score"] <= 100


# Integration tests for audit endpoint

def test_audit_get_integration_valid_url():
    """Integration test: GET /audit with valid URL returns complete audit results."""
    mock_axe_data = {
        "url": "https://example.com",
        "totalViolations": 2,
        "violations": [
            {
                "id": "color-contrast",
                "impact": "serious",
                "description": "Ensures the contrast between foreground and background colors meets WCAG 2 AA contrast ratio thresholds",
                "help": "Elements must have sufficient color contrast",
                "helpUrl": "https://dequeuniversity.com/rules/axe/4.7/color-contrast",
                "tags": ["cat.color", "wcag2aa", "wcag143"],
                "nodes": [
                    {
                        "target": [".low-contrast"],
                        "html": "<span class=\"low-contrast\">Hard to read</span>",
                        "failureSummary": "Fix any of the following: Element has insufficient color contrast"
                    }
                ]
            },
            {
                "id": "image-alt",
                "impact": "critical",
                "description": "Ensures <img> elements have alternate text",
                "help": "Images must have alternate text",
                "helpUrl": "https://dequeuniversity.com/rules/axe/4.7/image-alt",
                "tags": ["cat.text-alternatives", "wcag2a", "wcag111"],
                "nodes": [
                    {
                        "target": ["img.logo"],
                        "html": "<img class=\"logo\" src=\"logo.png\">",
                        "failureSummary": "Fix any of the following: Element does not have an alt attribute"
                    }
                ]
            }
        ]
    }
    
    mock_acc_violations = [
        {"type": "missing_lang", "element": "html", "message": "Missing lang attribute"},
        {"type": "empty_heading", "element": "h2", "message": "Heading is empty"}
    ]

    async def mock_axe_audit(url):
        return mock_axe_data

    async def mock_acc_violations(url):
        return mock_acc_violations

    with patch("app.run_axe_audit", side_effect=mock_axe_audit):
        with patch("app.get_accessibility_violations", side_effect=mock_acc_violations):
            with TestClient(app) as client:
                response = client.get("/audit?url=https://example.com")
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify structure
                assert data["url"] == "https://example.com"
                assert data["totalViolations"] == 2
                assert len(data["violations"]) == 2
                assert "accessibility_violations" in data
                assert len(data["accessibility_violations"]) == 2
                
                # Verify first violation details
                v1 = data["violations"][0]
                assert v1["id"] == "color-contrast"
                assert v1["impact"] == "serious"
                assert len(v1["nodes"]) == 1
                assert v1["nodes"][0]["target"] == [".low-contrast"]


def test_audit_post_integration_valid_url():
    """Integration test: POST /audit with valid URL returns complete audit results."""
    mock_axe_data = {
        "url": "https://example.org",
        "totalViolations": 1,
        "violations": [
            {
                "id": "label",
                "impact": "critical",
                "description": "Ensures every form element has a label",
                "help": "Form elements must have labels",
                "helpUrl": "https://dequeuniversity.com/rules/axe/4.7/label",
                "tags": ["cat.forms", "wcag2a", "wcag412"],
                "nodes": [
                    {
                        "target": ["#email"],
                        "html": "<input id=\"email\" type=\"email\">",
                        "failureSummary": "Fix any of the following: Element does not have an aria-label"
                    }
                ]
            }
        ]
    }
    
    mock_acc_violations = []

    async def mock_axe_audit(url):
        return mock_axe_data

    async def mock_acc_violations(url):
        return mock_acc_violations

    with patch("app.run_axe_audit", side_effect=mock_axe_audit):
        with patch("app.get_accessibility_violations", side_effect=mock_acc_violations):
            with TestClient(app) as client:
                response = client.post(
                    "/audit",
                    json={"url": "https://example.org"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["url"] == "https://example.org"
                assert data["totalViolations"] == 1
                assert data["violations"][0]["id"] == "label"
                assert data["accessibility_violations"] == []


def test_audit_get_integration_invalid_url():
    """Integration test: GET /audit with invalid URL returns 400 error."""
    with TestClient(app) as client:
        response = client.get("/audit?url=not-a-valid-url")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


def test_audit_post_integration_invalid_url():
    """Integration test: POST /audit with invalid URL returns 400 error."""
    with TestClient(app) as client:
        response = client.post(
            "/audit",
            json={"url": ""}
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


def test_audit_get_integration_no_url():
    """Integration test: GET /audit without URL parameter returns 422."""
    with TestClient(app) as client:
        response = client.get("/audit")
        assert response.status_code == 422


def test_audit_integration_with_server_error():
    """Integration test: GET /audit handles axe audit server errors gracefully."""
    async def mock_axe_audit_error(url):
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Error ejecutando axe-core")

    async def mock_acc_violations(url):
        return []

    with patch("app.run_axe_audit", side_effect=mock_axe_audit_error):
        with patch("app.get_accessibility_violations", side_effect=mock_acc_violations):
            with TestClient(app) as client:
                response = client.get("/audit?url=https://example.com")
                assert response.status_code == 500
                data = response.json()
                assert "detail" in data
                assert "axe-core" in data["detail"].lower()


def test_audit_integration_url_normalization():
    """Integration test: URL without protocol gets normalized."""
    mock_axe_data = {
        "url": "https://example.com",
        "totalViolations": 0,
        "violations": []
    }
    mock_acc_violations = []

    async def mock_axe_audit(url):
        return mock_axe_data

    async def mock_acc_violations(url):
        return mock_acc_violations

    with patch("app.run_axe_audit", side_effect=mock_axe_audit):
        with patch("app.get_accessibility_violations", side_effect=mock_acc_violations):
            with TestClient(app) as client:
                response = client.get("/audit?url=example.com")
                assert response.status_code == 200
                data = response.json()
                assert data["url"] == "https://example.com"


def test_audit_integration_no_violations():
    """Integration test: Site with no violations returns empty arrays and zero count."""
    mock_axe_data = {
        "url": "https://accessible-site.com",
        "totalViolations": 0,
        "violations": []
    }
    mock_acc_violations = []

    async def mock_axe_audit(url):
        return mock_axe_data

    async def mock_acc_violations(url):
        return mock_acc_violations

    with patch("app.run_axe_audit", side_effect=mock_axe_audit):
        with patch("app.get_accessibility_violations", side_effect=mock_acc_violations):
            with TestClient(app) as client:
                response = client.get("/audit?url=https://accessible-site.com")
                assert response.status_code == 200
                data = response.json()
                assert data["totalViolations"] == 0
                assert data["violations"] == []
                assert data["accessibility_violations"] == []
