#!/usr/bin/env python3
"""PDF Report Generator for AuditBot - Professional accessibility audit reports."""
import json, os, sys, datetime, subprocess, tempfile
from typing import Optional, List, Dict, Any

REPORT_SCRIPT = os.path.expanduser("~/Apps/ranukita-bridge/scripts/ranukita_report.py")
IMPACT_LABELS = {"critical": "Critical", "serious": "Serious", "moderate": "Moderate", "minor": "Minor", "unknown": "Unknown"}

def _impact_sort_key(impact):
    return {"critical": 0, "serious": 1, "moderate": 2, "minor": 3, "unknown": 4}.get(impact, 5)

def _compute_summary(violations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics from a list of violations."""
    total = len(violations)
    if total == 0:
        return {"total": 0, "by_impact": {}, "total_nodes": 0, "score": 100, "grade": "A+", "status": "Excellent"}
    by_impact: Dict[str, int] = {}
    total_nodes = 0
    for v in violations:
        impact = v.get("impact", "unknown")
        by_impact[impact] = by_impact.get(impact, 0) + 1
        total_nodes += len(v.get("nodes", []))
    # Penalty weights per impact
    weights = {"critical": 10, "serious": 5, "moderate": 2, "minor": 1, "unknown": 0.5}
    penalties = sum(weights.get(impact, 0.5) for impact in by_impact)
    score = max(0, 100 - penalties)
    # Grade mapping
    if score >= 90:
        grade = "A+"
        status = "Excellent"
    elif score >= 80:
        grade = "A"
        status = "Good"
    elif score >= 70:
        grade = "B"
        status = "Fair"
    elif score >= 60:
        grade = "C"
        status = "Poor"
    elif score >= 50:
        grade = "D"
        status = "Very Poor"
    else:
        grade = "F"
        status = "Critical"
    return {
        "total": total,
        "by_impact": by_impact,
        "total_nodes": total_nodes,
        "score": score,
        "grade": grade,
        "status": status,
    }

def _generate_simple_pdf(summary: Dict[str, Any], violations: List[Dict[str, Any]],
                         output_path: str, url: str = "") -> str:
    """Fallback PDF generation using reportlab (if available)."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
    except ImportError:
        raise RuntimeError(
            "reportlab is not installed and ranukita_report.py is not available. "
            "Install reportlab with: pip install reportlab"
        )
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    # Title
    elements.append(Paragraph(f"Accessibility Audit Report", styles['Title']))
    if url:
        elements.append(Paragraph(f"URL: {url}", styles['Normal']))
    elements.append(Spacer(1, 12))
    # Summary table
    data = [
        ["Metric", "Value"],
        ["Total Violations", str(summary["total"])],
        ["Total Nodes Affected", str(summary["total_nodes"])],
        ["Score", f"{summary['score']:.1f}"],
        ["Grade", summary["grade"]],
        ["Status", summary["status"]],
    ]
    for impact, count in sorted(summary["by_impact"].items(), key=lambda x: _impact_sort_key(x[0])):
        label = IMPACT_LABELS.get(impact, impact)
        data.append([f"{label} Violations", str(count)])
    table = Table(data, colWidths=[200, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 24))
    # Violations details
    for idx, v in enumerate(violations, 1):
        impact = v.get("impact", "unknown")
        label = IMPACT_LABELS.get(impact, impact)
        desc = v.get("description", v.get("id", "No description"))
        elements.append(Paragraph(f"<b>{idx}. [{label}] {desc}</b>", styles['Heading4']))
        nodes = v.get("nodes", [])
        for n in nodes:
            target = n.get("target", ["unknown"])[0] if isinstance(n.get("target"), list) else n.get("target", "unknown")
            elements.append(Paragraph(f"&nbsp;&nbsp;Element: {target}", styles['Normal']))
        elements.append(Spacer(1, 6))
    doc.build(elements)
    return output_path

def generate_pdf_report(violations: List[Dict[str, Any]],
                        output_path: Optional[str] = None,
                        url: str = "") -> str:
    """
    Generate a professional PDF report from a list of accessibility violations.

    Parameters
    ----------
    violations : list of dict
        Each dict should contain at least 'impact', 'description'/'id', and 'nodes'.
    output_path : str, optional
        Path where the PDF will be saved. If None, a temporary file is created.
    url : str, optional
        The audited URL (included in the report).

    Returns
    -------
    str
        The absolute path to the generated PDF file.
    """
    summary = _compute_summary(violations)
    if output_path is None:
        output_path = tempfile.mktemp(suffix=".pdf")
    # Prepare data for the external script
    data = {
        "summary": summary,
        "violations": violations,
        "url": url,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "output_path": output_path,
    }
    # Try to use the external ranukita_report.py script
    if os.path.isfile(REPORT_SCRIPT):
        try:
            result = subprocess.run(
                [sys.executable, REPORT_SCRIPT],
                input=json.dumps(data),
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            )
            # The script is expected to print the final PDF path on stdout
            stdout = result.stdout.strip()
            if stdout and os.path.isfile(stdout):
                return stdout
            # If stdout doesn't contain a valid path, fall back to output_path
            if os.path.isfile(output_path):
                return output_path
            # Otherwise raise
            raise RuntimeError(
                f"ranukita_report.py did not produce a valid PDF. "
                f"stdout: {stdout}, stderr: {result.stderr}"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("ranukita_report.py timed out after 120 seconds.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"ranukita_report.py failed with exit code {e.returncode}: {e.stderr}"
            )
    else:
        # Fallback to reportlab-based generation
        return _generate_simple_pdf(summary, violations, output_path, url)

if __name__ == "__main__":
    # Simple test with dummy data
    dummy_violations = [
        {
            "impact": "critical",
            "description": "Missing alt text on image",
            "nodes": [{"target": ["<img>"]}],
        },
        {
            "impact": "serious",
            "description": "Low contrast text",
            "nodes": [{"target": ["<p>"]}, {"target": ["<span>"]}],
        },
    ]
    pdf_path = generate_pdf_report(dummy_violations, url="https://example.com")
    print(f"PDF generated at: {pdf_path}")
