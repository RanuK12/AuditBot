"""
SEO Analyzer — Simple on-page SEO checks.
"""
import re
from typing import Dict
import aiohttp
from bs4 import BeautifulSoup  # We'll need to add beautifulsoup4 to requirements? Let's use html.parser to avoid extra dep.


def _parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, 'html.parser')


async def analyze_seo(url: str, session: aiohttp.ClientSession) -> Dict:
    """
    Perform basic SEO checks on the given URL.
    Returns a dict with SEO findings.
    """
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status != 200:
                return {"error": f"HTTP {resp.status}", "status": resp.status}
            html = await resp.text()
    except Exception as e:
        return {"error": str(e)}

    soup = _parse_html(html)

    # Title
    title_tag = soup.find('title')
    title = title_tag.string.strip() if title_tag and title_tag.string else ""
    title_len = len(title)

    # Meta description
    meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
    meta_desc = meta_desc_tag.get('content', '').strip() if meta_desc_tag else ""
    meta_desc_len = len(meta_desc)

    # H1 count
    h1_tags = soup.find_all('h1')
    h1_count = len(h1_tags)
    h1_text = [h1.get_text(strip=True) for h1 in h1_tags]

    # Meta viewport (for mobile)
    viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
    has_viewport = bool(viewport_tag)

    # Canonical link
    canonical_tag = soup.find('link', attrs={'rel': 'canonical'})
    canonical = canonical_tag.get('href') if canonical_tag else ""

    # Structured data (JSON-LD)
    json_ld_tags = soup.find_all('script', attrs={'type': 'application/ld+json'})
    structured_data_count = len(json_ld_tags)

    # Images without alt
    images = soup.find_all('img')
    images_total = len(images)
    images_missing_alt = sum(1 for img in images if not img.get('alt'))

    # Internal vs external links (simplified)
    links = soup.find_all('a', href=True)
    internal_links = 0
    external_links = 0
    from urllib.parse import urlparse
    try:
        base_domain = urlparse(url).netloc
    except Exception:
        base_domain = ""
    for link in links:
        href = link['href']
        if href.startswith('#') or not href:
            continue
        try:
            link_domain = urlparse(href).netloc
        except Exception:
            link_domain = ""
        if not link_domain or link_domain == base_domain:
            internal_links += 1
        else:
            external_links += 1

    # Build findings list (similar to accessibility format)
    findings = []

    if title_len == 0:
        findings.append({
            "id": "SEO_TITLE_MISSING",
            "impact": "high",
            "message": "Missing <title> tag",
            "help": "A descriptive title helps search engines understand the page content.",
            "context": {"selector": "head > title"}
        })
    elif title_len < 10:
        findings.append({
            "id": "SEO_TITLE_TOO_SHORT",
            "impact": "medium",
            "message": f"Title tag is too short ({title_len} characters)",
            "help": "Consider making your title more descriptive (aim for 10-60 characters).",
            "context": {"selector": "head > title", "excerpt": title}
        })
    elif title_len > 60:
        findings.append({
            "id": "SEO_TITLE_TOO_LONG",
            "impact": "medium",
            "message": f"Title tag is too long ({title_len} characters)",
            "help": "Titles over 60 characters may be truncated in search results.",
            "context": {"selector": "head > title", "excerpt": title[:50] + "..."}
        })

    if meta_desc_len == 0:
        findings.append({
            "id": "SEO_META_DESCRIPTION_MISSING",
            "impact": "medium",
            "message": "Missing meta description",
            "help": "A meta description provides a summary of the page for search results.",
            "context": {"selector": "head > meta[name='description']"}
        })
    elif meta_desc_len < 50:
        findings.append({
            "id": "SEO_META_DESCRIPTION_TOO_SHORT",
            "impact": "low",
            "message": f"Meta description is too short ({meta_desc_len} characters)",
            "help": "Consider expanding the meta description (aim for 50-160 characters).",
            "context": {"selector": "head > meta[name='description']", "excerpt": meta_desc}
        })
    elif meta_desc_len > 160:
        findings.append({
            "id": "SEO_META_DESCRIPTION_TOO_LONG",
            "impact": "low",
            "message": f"Meta description is too long ({meta_desc_len} characters)",
            "help": "Meta descriptions over 160 characters may be truncated in search results.",
            "context": {"selector": "head > meta[name='description']", "excerpt": meta_desc[:50] + "..."}
        })

    if h1_count == 0:
        findings.append({
            "id": "SEO_H1_MISSING",
            "impact": "high",
            "message": "Missing H1 tag",
            "help": "An H1 tag indicates the main heading of the page and helps with content structure.",
            "context": {"selector": "body"}
        })
    elif h1_count > 1:
        findings.append({
            "id": "SEO_H1_MULTIPLE",
            "impact": "medium",
            "message": f"Multiple H1 tags found ({h1_count})",
            "help": "It's recommended to have only one H1 per page for clear content hierarchy.",
            "context": {"selector": "h1", "excerpt": "; ".join(h1_text[:3])}
        })

    if not has_viewport:
        findings.append({
            "id": "SEO_VIEWPORT_MISSING",
            "impact": "medium",
            "message": "Missing viewport meta tag",
            "help": "The viewport meta tag is essential for proper rendering on mobile devices.",
            "context": {"selector": "head > meta[name='viewport']"}
        })

    if images_missing_alt > 0:
        findings.append({
            "id": "SEO_IMAGE_MISSING_ALT",
            "impact": "medium",
            "message": f"{images_missing_alt} image(s) missing alt attribute",
            "help": "Alt text improves accessibility and helps search engines understand image content.",
            "context": {"selector": "img", "count": images_missing_alt}
        })

    # If no issues, add a success finding? Usually we only report issues.
    # We'll also return raw data for potential reporting.

    seo_data = {
        "title": title,
        "title_length": title_len,
        "meta_description": meta_desc,
        "meta_description_length": meta_desc_len,
        "h1_count": h1_count,
        "h1_text": h1_text,
        "has_viewport": has_viewport,
        "canonical": canonical,
        "structured_data_count": structured_data_count,
        "images_total": images_total,
        "images_missing_alt": images_missing_alt,
        "internal_links": internal_links,
        "external_links": external_links,
    }

    return {"findings": findings, "data": seo_data}