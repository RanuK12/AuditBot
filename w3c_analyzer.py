"""
W3C Analyzer — Basic markup validation checks.
"""
import re
from typing import Dict, List
import aiohttp
from html.parser import HTMLParser


class SimpleHTMLChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []
        self.stack = []  # track open tags for nesting
        self.ids = set()
        self.has_doctype = False
        self.html_tag_seen = False
        self.head_tag_seen = False
        self.body_tag_seen = False
        self.in_head = False
        self.in_body = False

    def handle_decl(self, decl):
        if decl.lower().startswith('doctype'):
            self.has_doctype = True

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        # track ids
        for attr, value in attrs:
            if attr == 'id':
                if value in self.ids:
                    self.errors.append({
                        "id": "W3C_DUPLICATE_ID",
                        "impact": "high",
                        "message": f"Duplicate ID '{value}'",
                        "help": "ID attributes must be unique within the document.",
                        "context": {"attribute": "id", "value": value}
                    })
                else:
                    self.ids.add(value)
        # track tag hierarchy
        if tag_lower == 'html':
            self.html_tag_seen = True
        elif tag_lower == 'head':
            self.head_tag_seen = True
            self.in_head = True
        elif tag_lower == 'body':
            self.body_tag_seen = True
            self.in_body = True
        # push to stack for nesting check (simplified)
        self.stack.append(tag_lower)

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower == 'head':
            self.in_head = False
        elif tag_lower == 'body':
            self.in_body = False
        # pop from stack (simplified, not rigorous)
        if self.stack and self.stack[-1] == tag_lower:
            self.stack.pop()

    def handle_data(self, data):
        # We could check for text outside body, but skip for simplicity
        pass


async def validate_w3c(url: str, session: aiohttp.ClientSession) -> Dict:
    """
    Perform basic W3C-like checks on the given URL.
    Returns a dict with findings.
    """
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status != 200:
                return {"error": f"HTTP {resp.status}", "status": resp.status, "findings": []}
            html = await resp.text()
    except Exception as e:
        return {"error": str(e), "findings": []}

    parser = SimpleHTMLChecker()
    try:
        parser.feed(html)
    except Exception as e:
        parser.errors.append({
            "id": "W3C_PARSE_ERROR",
            "impact": "high",
            "message": f"HTML parsing error: {str(e)}",
            "help": "The document contains syntax errors that prevent proper parsing.",
            "context": {}
        })

    findings = []

    # Doctype
    if not parser.has_doctype:
        findings.append({
            "id": "W3C_DOCTYPE_MISSING",
            "impact": "medium",
            "message": "Missing DOCTYPE declaration",
            "help": "Add a DOCTYPE to the start of your document to ensure standards mode.",
            "context": {}
        })

    # HTML tag
    if not parser.html_tag_seen:
        findings.append({
            "id": "W3C_HTML_TAG_MISSING",
            "impact": "high",
            "message": "Missing <html> tag",
            "help": "Every HTML document should have a root <html> element.",
            "context": {}
        })

    # Head tag
    if not parser.head_tag_seen:
        findings.append({
            "id": "W3C_HEAD_TAG_MISSING",
            "impact": "high",
            "message": "Missing <head> tag",
            "help": "The <head> element contains metadata and should be present.",
            "context": {}
        })

    # Body tag
    if not parser.body_tag_seen:
        findings.append({
            "id": "W3C_BODY_TAG_MISSING",
            "impact": "high",
            "message": "Missing <body> tag",
            "help": "The <body> element contains the content and should be present.",
            "context": {}
        })

    # Add any parser errors
    findings.extend(parser.errors)

    # If no issues, we could add a success, but we only report issues.
    w3c_data = {
        "doctype": parser.has_doctype,
        "html_tag": parser.html_tag_seen,
        "head_tag": parser.head_tag_seen,
        "body_tag": parser.body_tag_seen,
        "unique_ids": len(parser.ids),
        "total_ids": len(parser.ids),
    }

    return {"findings": findings, "data": w3c_data}
