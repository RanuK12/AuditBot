#!/usr/bin/env python3
"""Transformador de resultados de axe-core al formato de generate_report.py para ADA-AUDITS."""

import json
from datetime import datetime
from typing import Dict, List, Any


def transform_axe_to_report_format(axe_results: Dict[str, Any], url: str = "") -> Dict[str, Any]:
    """
    Transforma resultados de axe-core al formato esperado por generate_report.py.
    
    Parameters
    ----------
    axe_results : dict
        Resultados de axe-core (formato original del bot)
    url : str, optional
        La URL auditada (para usar como nombre de cliente si no se proporciona)
        
    Returns
    -------
    dict
        Formato compatible con generate_report.py
    """
    violations = axe_results.get('violations', [])
    
    # Extraer información de la URL para usar como nombre de cliente
    client_name = "Cliente Anónimo"
    if url:
        # Usar el dominio como nombre de cliente
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.netloc:
            client_name = parsed.netloc.replace('www.', '').replace('.com', '').replace('.org', '').replace('.net', '')
    
    # Generar fecha actual
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Generar resumen ejecutivo
    total_violations = len(violations)
    if total_violations == 0:
        summary = "Auditoría de accesibilidad WCAG 2.1 AA — no se encontraron barreras. El sitio cumple con los estándares de accesibilidad."
    else:
        summary = f"Auditoría de accesibilidad WCAG 2.1 AA — se detectaron {total_violations} barreras que afectan la experiencia de usuarios con discapacidad y exponen a la empresa a riesgos legales."
    
    # Transformar violaciones al formato esperado
    findings = []
    for violation in violations:
        # Mapear impacto a severidad
        impact = violation.get('impact', 'unknown')
        severity_map = {
            'critical': 'Critical',
            'serious': 'High',
            'moderate': 'Medium',
            'minor': 'Low',
            'unknown': 'Unknown'
        }
        severity = severity_map.get(impact, 'Unknown')
        
        # Generar descripción del hallazgo
        issue_id = violation.get('id', 'unknown-issue')
        description = violation.get('description', f'Issue {issue_id}')
        help_text = violation.get('help', '')
        
        # Combinar description y help para el issue completo
        if help_text and help_text != description:
            issue = f"{description}: {help_text}"
        else:
            issue = description
        
        # Generar impacto en el negocio (estimado basado en el impacto)
        business_impact_map = {
            'critical': '–15-30% conversión / demanda ADA Title III / riesgo legal',
            'serious': '–5-15% conversión / posible demanda',
            'moderate': '–1-5% experiencia de usuario / mejora UX',
            'minor': 'Mejora general de accesibilidad',
            'unknown': 'Requiere revisión manual'
        }
        business_impact = business_impact_map.get(impact, 'Requiere revisión manual')
        
        # Generar antes/después (ejemplos genéricos basados en el tipo de violación)
        before_after_map = {
            'color-contrast': (
                '`<div style="color: #333; background: #FFF;">Texto</div>` (contraste bajo)',
                '`<div style="color: #333; background: #000;">Texto</div>` (contraste 21:1)'
            ),
            'image-alt': (
                '`<img src="imagen.jpg">` (sin texto alternativo)',
                '`<img src="imagen.jpg" alt="Descripción de la imagen">`'
            ),
            'button-name': (
                '`<button>Enviar</button>` (sin nombre accesible)',
                '`<button aria-label="Enviar formulario">Enviar</button>`'
            ),
            'link-name': (
                '`<a href="#">Leer más</a>` (texto descriptivo faltante)',
                '`<a href="/articulo" aria-label="Leer más sobre el artículo">Leer más</a>`'
            )
        }
        
        # Usar ID de violation para determinar antes/después
        before = "Elemento no accesible (ejemplo genérico)"
        after = "Elemento accesible (ejemplo genérico)"
        
        for key, (b, a) in before_after_map.items():
            if key in violation.get('id', '').lower():
                before, after = b, a
                break
        
        finding = {
            'issue': issue,
            'severity': severity,
            'business_impact': business_impact,
            'before': before,
            'after': after
        }
        findings.append(finding)
    
    # Generar recomendaciones basadas en las violaciones encontradas
    recommendations = []
    if total_violations > 0:
        recommendations = [
            "Implementar correcciones progresivas, priorizando violaciones críticas y graves.",
            "Realizar auditorías periódicas para mantener la conformidad WCAG 2.1 AA.",
            "Capacitar al equipo de desarrollo en prácticas de accesibilidad web.",
            "Utilizar herramientas automatizadas como axe-core en el proceso de desarrollo.",
            "Considerar auditorías manuales para casos complejos y dinámicos."
        ]
    else:
        recommendations = [
            "Mantener las buenas prácticas de accesibilidad web.",
            "Continuar utilizando herramientas automatizadas en el desarrollo.",
            "Realizar auditorías periódicas para detectar nuevas barreras."
        ]
    
    # Construir el resultado final
    result = {
        'client_name': client_name,
        'date': current_date,
        'summary': summary,
        'findings': findings,
        'recommendations': recommendations
    }
    
    return result


def main():
    """Ejemplo de uso del transformador."""
    # Datos de ejemplo axe-core (simulados)
    sample_axe_data = {
        "url": "https://example.com",
        "totalViolations": 2,
        "violations": [
            {
                "id": "color-contrast",
                "impact": "serious",
                "description": "Elements do not have sufficient color contrast ratio",
                "help": "Ensures text has sufficient contrast against background colors",
                "nodes": [
                    {
                        "target": ["body"],
                        "html": "<body style='color: #666; background: #fff;'>",
                        "failureSummary": "Element has insufficient color contrast"
                    }
                ]
            },
            {
                "id": "image-alt",
                "impact": "critical",
                "description": "Images must have alternate text",
                "help": "All img elements must have an alt attribute",
                "nodes": [
                    {
                        "target": ["img"],
                        "html": "<img src='logo.png'>",
                        "failureSummary": "Image lacks descriptive alt text"
                    }
                ]
            }
        ]
    }
    
    # Transformar
    transformed = transform_axe_to_report_format(sample_axe_data, "https://example.com")
    
    # Guardar resultado
    with open("transformed_report_example.json", "w") as f:
        json.dump(transformed, f, indent=2)
    
    print("Reporte transformado guardado en transformed_report_example.json")
    print("Formato compatible con generate_report.py de ADA-AUDITS")


if __name__ == "__main__":
    main()