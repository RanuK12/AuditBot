import asyncio
import subprocess
import json
import tempfile
import os
import argparse
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn
from pdf_report import generate_pdf_report as generate_audit_pdf
from accessibility_scraper import scrape_site as get_accessibility_violations
from report_transformer import transform_axe_to_report_format
import time
import jwt
from datetime import datetime, timedelta

app = FastAPI(title="AuditBot API")

# OAuth token management
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# In-memory token storage
token_store = {}

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        
        # Create new token
        new_token = create_access_token(data={"sub": username})
        return new_token
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

async def get_current_user(token: str):
    try:
        payload = verify_token(token)
        username = payload.get("sub")
        return username
    except HTTPException:
        # Try to refresh the token
        try:
            new_token = refresh_token(token)
            # Store the new token
            token_store[new_token] = {
                "sub": payload.get("sub"),
                "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            }
            # Return the original token with refreshed payload
            return await get_current_user(new_token)
        except HTTPException:
            raise HTTPException(status_code=401, detail="Could not refresh token")

def get_token_from_headers(authorization: str):
    if authorization.startswith("Bearer "):
        return authorization.split(" ")[1]
    return None

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
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output_path = f.name

    try:
        command = f"npx axe {url} --save {output_path} --quiet"
        result = await asyncio.to_thread(
            subprocess.run, command,
            shell=True, capture_output=True, text=True, timeout=120
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
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(output_path):
            os.unlink(output_path)
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

@app.post("/auth/login")
async def login(username: str, password: str):
    # In a real application, you would verify the username and password against a database
    # For this example, we'll accept any non-empty username and password
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    # Store the token
    token_store[access_token] = {
        "sub": username,
        "exp": datetime.utcnow() + access_token_expires
    }
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/refresh")
async def refresh_token_endpoint(authorization: str = Query(...)):
    token = get_token_from_headers(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    try:
        new_token = refresh_token(token)
        return {"access_token": new_token, "token_type": "bearer"}
    except HTTPException:
        raise HTTPException(status_code=401, detail="Could not refresh token")

@app.middleware("http")
async def auth_middleware(request, call_next):
    # Skip authentication for certain endpoints
    public_paths = ["/", "/health", "/auth/login", "/auth/refresh"]
    if request.url.path in public_paths:
        response = await call_next(request)
        return response
    
    # Check for Authorization header
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        token = get_token_from_headers(authorization)
        if not token:
            raise HTTPException(status_code=401, detail="Invalid token format")
        
        # Verify the token
        await get_current_user(token)
        
        # Add token to request state for use in endpoint
        request.state.token = token
        
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    
    response = await call_next(request)
    return response


def main():
    """Command line interface for AuditBot."""
    parser = argparse.ArgumentParser(description='AuditBot - Web Accessibility Audit Tool')
    parser.add_argument('url', help='URL to audit')
    parser.add_argument('--format', choices=['json', 'pdf'], default='json',
                        help='Output format (default: json)')
    parser.add_argument('--output', help='Output file path (optional)')
    parser.add_argument('--host', default='127.0.0.1', help='Host for API server')
    parser.add_argument('--port', type=int, default=8000, help='Port for API server')
    parser.add_argument('--token', help='Authentication token (required for non-public endpoints)')
    
    args = parser.parse_args()
    
    # Validate URL
    try:
        validated_url = validate_url(args.url)
    except HTTPException as e:
        print(f"Error: {e.detail}")
        return 1
    
    # Run audit
    try:
        if args.format == 'pdf':
            # Generate PDF report
            pdf_path = generate_audit_pdf([], url=validated_url)
            if pdf_path:
                print(f"PDF report generated: {pdf_path}")
                return 0
            else:
                print("Error generating PDF report")
                return 1
        else:
            # Generate JSON report
            # This would normally call the audit endpoint, but for CLI we'll simulate
            print(f"Auditing {validated_url}...")
            print("Note: CLI audit functionality requires running API server")
            print(f"Start server: python app.py --host {args.host} --port {args.port}")
            print(f"Then call: curl http://{args.host}:{args.port}/audit?url={validated_url}")
            return 0
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1


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
