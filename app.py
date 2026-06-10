import subprocess
import json
import tempfile
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn
from pdf_report import generate_audit_pdf
from accessibility_scraper import get_accessibility_violations

app = FastAPI(title="AuditBot API")

# Serve the landing page
@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    with open(html_path, "r") as f:
        return HTMLResponse(content=f.read())

class AuditRequest(BaseModel):
    url: str

def run_axe_audit(url: str) -> dict:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output_path = f.name

    try:
        command = f"npx axe {url} --save {output_path} --quiet"
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0 and not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail=f"Error ejecutando axe-core: {result.stderr}")

        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            os.unlink(output_path)

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
        else:
            raise HTTPException(status_code=500, detail="No se pudo generar el archivo de resultados")

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout al ejecutar axe-core")
    except Exception as e:
        if os.path.exists(output_path):
            os.unlink(output_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit")
async def audit_get(url: str = Query(..., description="URL a auditar")):
    axe_results = await run_axe_audit(url)
    acc_violations = await get_accessibility_violations(url)
    
    axe_results["accessibility_violations"] = acc_violations
    return axe_results

@app.post("/audit")
async def audit_post(request: AuditRequest):
    axe_results = await run_axe_audit(request.url)
    acc_violations = await get_accessibility_violations(request.url)
    
    axe_results["accessibility_violations"] = acc_violations
    return axe_results

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/audit/report")
async def audit_report_get(url: str = Query(..., description="URL to audit")):
    """Run audit and return a professional PDF report as download."""
    axe_results = await run_axe_audit(url)
    acc_violations = await get_accessibility_violations(url)
    
    # Merge data for report
    axe_results["accessibility_violations"] = acc_violations
    
    pdf_path = generate_audit_pdf(axe_results, url=url)
    if not pdf_path:
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")
    filename = os.path.basename(pdf_path)
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)


@app.post("/audit/report")
async def audit_report_post(request: AuditRequest):
    """Run audit and return a professional PDF report as download."""
    axe_results = await run_axe_audit(request.url)
    acc_violations = await get_accessibility_violations(request.url)
    
    # Merge data for report
    axe_results["accessibility_violations"] = acc_violations

    pdf_path = generate_audit_pdf(axe_results, url=request.url)
    if not pdf_path:
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")
    filename = os.path.basename(pdf_path)
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)