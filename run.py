#!/usr/bin/env python3
"""
Entrypoint for AuditBot CLI.
"""
import sys
import os

# Add the current directory to the path so we can import audit_engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audit_engine import main

if __name__ == "__main__":
    main()