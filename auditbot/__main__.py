#!/usr/bin/env python3
"""
CLI entrypoint para auditbot: toma UNA URL, corre la auditoría con defaults
y emite JSON en el formato exacto que consume generate_report.py.
"""

import sys
import json

# Asegurar que el directorio del proyecto esté en sys.path
sys.path.insert(0, '/Users/emilioranucoli/.ranukita/projects/auditbot')

from audit_engine import main as audit_main


def main():
    if len(sys.argv) != 2:
        print("Uso: python -m auditbot <URL>", file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Simular argumentos para audit_engine: url + --json
    sys.argv = ['audit_engine', url, '--json']
    
    # Ejecutar la auditoría (imprime JSON a stdout)
    audit_main()


if __name__ == "__main__":
    main()