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
    penalties =