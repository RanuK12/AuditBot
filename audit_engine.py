#!/usr/bin/env python3
"""
Audit Engine — Motor unificado de auditoría de accesibilidad y SEO.
Corre de punta a punta con UNA URL, sin configurar nada.
La salida es el formato exacto que espera generate_report.py de ADA-AUDITS.

Uso:
    python3 audit_engine.py https://example.com
    python3 audit_engine.py https://example.com --output report.json
    python3 audit_engine.py https://example.com --json  # imprime JSON a stdout

Dependencias: las mismas del proyecto (requirements.txt).
"""

import argparse
import asyncio
import json
import os
import sys
import subprocess
import tempfile
from typing import Optional

# ── internal imports ──────────────────────────────────────────
from app import run_axe_audit
from accessibility_scraper import scrape_site as get_accessibility_violations
from report_transformer import transform_axe_to_report_format
from seo_analyzer import analyze_seo
import aiohttp


async def audit_url(url: str) -> dict:
    """
    Corre la auditoría completa: axe-core + scraper de accesibilidad + SEO.
    Retorna el dict exacto que espera generate_report.py de ADA-AUDITS.
    """
    print(f"🔍 Auditando {url}...", file=sys.stderr)

    axe_results = await run_axe_audit(url)
    acc_violations = await get_accessibility_violations(url)

    # SEO analysis
    async with aiohttp.ClientSession() as session:
        seo_result = await analyze_seo(url, session)

    # Combine results
    axe_results["accessibility_violations"] = acc_violations
    axe_results["seo_violations"] = seo_result

    report_data = transform_axe_to_report_format(axe_results, url=url)
    return report_data


def main():
    parser = argparse.ArgumentParser(
        description="Audit Engine — auditoría de accesibilidad de punta a punta"
    )
    parser.add_argument("url", help="URL a auditar (ej: https://example.com)")
    parser.add_argument(
        "--output", "-o",
        help="Archivo JSON de salida (default: stdout)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Imprimir JSON a stdout (alternativa a --output)",
    )
    args = parser.parse_args()

    url = args.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    report_data = asyncio.run(audit_url(url))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Reporte guardado en {args.output}", file=sys.stderr)
    else:
        print(json.dumps(report_data, indent=2, ensure_ascii=False))

    # resumen a stderr
    findings = report_data.get("findings", [])
    print(
        f"📊 {report_data['client_name']}: {len(findings)} hallazgos",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()