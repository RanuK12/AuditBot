#!/usr/bin/env python3
"""Generador de reportes de accesibilidad en formato compatible con ADA-AUDITS."""

import json
from datetime import datetime
from typing import Dict, List, Any


def generate_report(axe_results: Dict[str, Any], url: str = "") -> str:
    """
    Genera un reporte de accesibilidad en formato compatible con ADA-AUDITS.
    
    Parameters
    ----------
    axe_results : dict
        Resultados de axe-core (formato original del bot)
    url : str, optional
        La URL auditada (para usar como nombre de cliente si no se proporciona)
        
    Returns
    -------
    str
        Reporte de accesibilidad en formato Markdown
    """
    # Transformar los resultados al formato esperado
    from report_transformer import transform_axe_to_report_format
    report_data = transform_axe_to_report_format(axe_results, url)
    
    # Generar el reporte en formato Markdown
    report_lines = []
    
    # Encabezado
    report_lines.append(f"# Reporte de Accesibilidad - {report_data['client_name']}")
    report_lines.append(f"**Fecha:** {report_data['date']}")
    report_lines.append(f"**URL:** {url if url else 'No especificada'}")
    report_lines.append("")
    
    # Resumen ejecutivo
    report_lines.append("## Resumen Ejecutivo")
    report_lines.append("")
    report_lines.append(report_data['summary'])
    report_lines.append("")
    
    # Hallazgos
    if report_data['findings']:
        report_lines.append("## Hallazgos de Accesibilidad")
        report_lines.append("")
        
        for i, finding in enumerate(report_data['findings'], 1):
            report_lines.append(f"### {i}. {finding['issue']}")
            report_lines.append(f"**Severidad:** {finding['severity']}")
            report_lines.append(f"**Impacto en el Negocio:** {finding['business_impact']}")
            report_lines.append("")
            report_lines.append("#### Antes")
            report_lines.append(finding['before'])
            report_lines.append("")
            report_lines.append("#### Después")
            report_lines.append(finding['after'])
            report_lines.append("")
    
    # Recomendaciones
    report_lines.append("## Recomendaciones")
    report_lines.append("")
    
    for i, recommendation in enumerate(report_data['recommendations'], 1):
        report_lines.append(f"{i}. {recommendation}")
    report_lines.append("")
    
    # Información adicional
    report_lines.append("## Información Adicional")
    report_lines.append("")
    report_lines.append("Este reporte fue generado por AuditBot utilizando axe-core para la detección automática de barreras de accesibilidad.")
    report_lines.append("Para obtener información más detallada sobre las normas WCAG 2.1 AA, visite: https://www.w3.org/WAI/WCAG21/quickref/")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("*Generado automáticamente por AuditBot*")
    
    return "\n".join(report_lines)