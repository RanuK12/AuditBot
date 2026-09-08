import asyncio
import subprocess
import json
import tempfile
import os
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn
from pdf_report import generate_pdf_report as generate_audit_pdf
from accessibility_scraper import scrape_site as get_accessibility_violations
from report_transformer import transform_axe_to_report_format

app = FastAPI(title="AuditBot API")

# Serve the landing page
@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    with open(html_path, "r") as f:
        return HTMLResponse(content=f.read())

class AuditRequest(BaseModel):
    url: str

def validate_url(url: str) -> str:
    """Validate and normalize a URL. Returns the URL if valid, raises HTTPException if not."""
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail=f"Invalid URL: '{url}' has no domain")
    if "." not in parsed.netloc and parsed.netloc not in ("localhost",):
        raise HTTPException(status_code=400, detail=f"Invalid domain: '{parsed.netloc}'")
    return url

async def run_axe_audit(url: str) -> dict:
    url = validate_url(url)
    try:
        command = f"npx axe {url} --stdout"
        result = await asyncio.to_thread(
            subprocess.run, command,
            shell=True, capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Error ejecutando axe-core: {result.stderr}")

        stdout = result.stdout.strip()
        if not stdout:
            raise HTTPException(status_code=500, detail="No output from axe-core")

        data = json.loads(stdout)
        # axe --stdout returns a list with one result object per URL
        if isinstance(data, list):
            if not data:
                raise HTTPException(status_code=500, detail="Empty axe output")
            data = data[0]

        violations = data.get('violations', [])
        processed = []
        for v in violations:
            processed.append({
                "id": v.get("id"),
                "impact": v.get("impact"),
                "description": v.get("description"),
                "help": v.get("help"),
                "helpUrl": v.get("helpUrl"),
                "tags": v.get("tags", []),
                "nodes": [
                    {
                        "target": n.get("target"),
                        "html": n.get("html"),
                        "failureSummary": n.get("failureSummary")
                    }
                    for n in v.get("nodes", [])
                ]
            })

        return {
            "url": url,
            "totalViolations": len(processed),
            "violations": processed
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout al ejecutar axe-core")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit")
async def audit_get(url: str = Query(..., description="URL a auditar")):
    url = validate_url(url)
    axe_results = await run_axe_audit(url)
    acc_violations = await get_accessibility_violations(url)
    
    axe_results["accessibility_violations"] = acc_violations
    return axe_results

@app.post("/audit")
async def audit_post(request: AuditRequest):
    url = validate_url(request.url)
    axe_results = await run_axe_audit(url)
    acc_violations = await get_accessibility_violations(url)
    
    axe_results["accessibility_violations"] = acc_violations
    return axe_results

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/audit/report")
async def audit_report_get(url: str = Query(..., description="URL to audit")):
    """Run audit and return a professional PDF report as download."""
    url = validate_url(url)
    axe_results = await run_axe_audit(url)
    acc_violations = await get_accessibility_violations(url)
    
    # Merge data for report
    axe_results["accessibility_violations"] = acc_violations
    
    pdf_path = generate_audit_pdf(axe_results, url=url)
    if not pdf_path:
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")
    filename = os.path.basename(pdf_path)
    return FileResponse(pdf_path, media_type='application/pdf', filename=filename)

@app.get("/audit/report/json")
async def audit_report_json_get(url: str = Query(..., description="URL to audit")):
    """Run audit and return a JSON report compatible with generate_report.py format."""
    url = validate_url(url)
    axe_results = await run_axe_audit(url)
    acc_violations = await get_accessibility_violations(url)
    
    # Merge data for report
    axe_results["accessibility_violations"] = acc_violations
    
    # Transform to ADA-AUDITS format
    report_data = transform_axe_to_report_format(axe_results, url=url)
    
    return report_data

@app.post("/audit/report/json")
async def audit_report_json_post(request: AuditRequest):
    """Run audit and return a JSON report compatible with generate_report.py format."""
    url = validate_url(request.url)
    axe_results = await run_axe_audit(url)
    acc_violations = await get_accessibility_violations(url)
    
    # Merge data for report
    axe_results["accessibility_violations"] = acc_violations
    
    # Transform to ADA-AUDITS format
    report_data = transform_axe_to_report_format(axe_results, url=url)
    
    return report_data
