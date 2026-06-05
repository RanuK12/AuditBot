#!/usr/bin/env python3
"""PDF Report Generator for AuditBot - Professional accessibility audit reports."""
import json, os, sys, datetime, subprocess
from typing import Optional

REPORT_SCRIPT = os.path.expanduser("~/Apps/ranukita-bridge/scripts/ranukita_report.py")
IMPACT_LABELS = {"critical": "Critical", "serious": "Serious", "moderate": "Moderate", "minor": "Minor", "unknown": "Unknown"}

def _impact_sort_key(impact):
    return {"critical": 0, "serious": 1, "moderate": 2, "minor": 3, "unknown": 4}.get(impact, 5)

def _compute_summary(violations):
    total = len(violations)
    if total == 0:
        return {"total": 0, "by_impact": {}, "total_nodes": 0, "score": 100, "grade": "A+", "status": "Excellent"}
    by_impact = {}
    total_nodes = 0
    for v in violations:
        impact = v.get("impact", "unknown")
        by_impact[impact] = by_impact.get(impact, 0) + 1
        total_nodes += len(v.get("nodes", []))
    penalties = {"critical": 30, "serious": 15, "moderate": 5, "minor": 1}
    penalty = sum(penalties.get(imp, 0) * c for imp, c in by_impact.items())
    score = max(0, 100 - penalty)
    if score >= 90: grade = "A+"
    elif score >= 80: grade = "A"
    elif score >= 70: grade = "B"
    elif score >= 60: grade = "C"
    elif score >= 50: grade = "D"
    else: grade = "F"
    sm = {"A+": "Excellent", "A": "Good", "B": "Fair", "C": "Needs work", "D": "Poor", "F": "Critical"}
    return {"total": total, "by_impact": by_impact, "total_nodes": total_nodes, "score": score, "grade": grade, "status": sm.get(grade, "Unknown")}

def _build_recommendations(violations):
    recs, seen = [], set()
    for v in violations:
        vid = v.get("id", "")
        if vid in seen: continue
        seen.add(vid)
        impact = v.get("impact", "unknown")
        help_text = v.get("help", "")
        help_url = v.get("helpUrl", "")
        priority = "HIGH" if impact in ("critical", "serious") else ("MEDIUM" if impact == "moderate" else "LOW")
        rec = f"[{priority}] {help_text or vid}"
        if help_url: rec += f" -- See: {help_url}"
        recs.append(rec)
    po = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    recs.sort(key=lambda r: po.get(r.split("]")[0].replace("[", ""), 3))
    return recs[:20]

def build_audit_spec(audit_result, url=None):
    violations = audit_result.get("violations", [])
    url = url or audit_result.get("url", "Unknown URL")
    summary = _compute_summary(violations)
    recommendations = _build_recommendations(violations)

    impact_bullets = []
    for impact in sorted(summary["by_impact"].keys(), key=_impact_sort_key):
        label = IMPACT_LABELS.get(impact, impact.title())
        count = summary["by_impact"][impact]
        impact_bullets.append(f"{label}: {count} violation{'s' if count != 1 else ''}")
    if not impact_bullets:
        impact_bullets.append("No violations detected")

    sections = [{
        "heading": "1. Executive Summary",
        "paragraphs": [
            f"Accessibility Audit Report for {url}",
            f"Date: {datetime.date.today().isoformat()}",
            "Standard: WCAG 2.1 AA (via axe-core)",
            f"Accessibility Score: {summary['score']}/100 (Grade: {summary['grade']})",
            f"Overall Status: {summary['status']}",
            f"Total Violations: {summary['total']}",
            f"Affected Elements: {summary['total_nodes']}",
        ],
        "bullets": impact_bullets,
    }]

    sorted_v = sorted(violations, key=lambda v: _impact_sort_key(v.get("impact", "unknown")))
    sec_map = {"critical": "2", "serious": "3", "moderate": "4", "minor": "5"}
    for impact in ["critical", "serious", "moderate", "minor"]:
        iv = [v for v in sorted_v if v.get("impact") == impact]
        if not iv: continue
        label = IMPACT_LABELS.get(impact, impact.title())
        bullets, rows = [], []
        for v in iv:
            vid = v.get("id", "unknown")
            desc = v.get("description", "No description")
            nodes = v.get("nodes", [])
            nc = len(nodes)
            bullets.append(f"{vid}: {desc} ({nc} element{'s' if nc != 1 else ''} affected)")
            for n in nodes[:5]:
                target = str(n.get("target", ""))
                html = (n.get("html", "") or "")[:120]
                failure = (n.get("failureSummary", "") or "")[:80]
                rows.append([vid, target[:60], failure])
            if nc > 5:
                rows.append(["", f"...and {nc - 5} more", ""])
        sec = {
            "heading": f"{sec_map.get(impact, '2')}. {label} Issues ({len(iv)})",
            "paragraphs": [f"{len(iv)} violation{'s were' if len(iv) != 1 else ' was'} found:"],
            "bullets": bullets[:15],
        }
        if rows:
            sec["table"] = {"headers": ["Rule", "Element", "Failure Summary"], "rows": rows[:20]}
        sections.append(sec)

    sections.append({"heading": "6. Recommendations", "paragraphs": ["Prioritized improvements:"], "bullets": recommendations or ["No recommendations needed"]})
    sections.append({"heading": "7. Methodology", "paragraphs": [
        "Audit performed using axe-core, the industry-standard accessibility testing engine.",
        "Checks against WCAG 2.1 Level AA. Automated testing covers ~30-40% of issues.",
    ], "bullets": ["Engine: axe-core (Deque Systems)", "Standard: WCAG 2.1 Level AA", "Scope: Automated only", "Score: 100 - (critical*30 + serious*15 + moderate*5 + minor*1)"]})

    return {"title": "AuditBot - Accessibility Audit Report", "subtitle": url, "date": datetime.date.today().isoformat(), "sections": sections}

def generate_audit_pdf(audit_result, output_path=None, url=None):
    if output_path is None:
        domain = (url or audit_result.get("url", "site")).replace("https://", "").replace("http://", "").replace("/", "_").replace(".", "_")[:40]
        output_path = f"/tmp/auditbot_{domain}_{datetime.date.today().isoformat()}.pdf"
    spec = build_audit_spec(audit_result, url)
    spec_path = output_path + ".spec.json"
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    try:
        result = subprocess.run(["python3", REPORT_SCRIPT, spec_path, output_path, "--theme", "dark"], capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and os.path.exists(output_path):
            os.unlink(spec_path)
            return output_path
        else:
            print(f"PDF generation failed: {result.stderr}", file=sys.stderr)
            os.unlink(spec_path)
            return None
    except Exception as e:
        print(f"PDF generation error: {e}", file=sys.stderr)
        if os.path.exists(spec_path):
            os.unlink(spec_path)
        return None
