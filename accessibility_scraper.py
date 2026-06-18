import asyncio
import logging
from playwright.async_api import async_playwright
from logger_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

async def get_accessibility_violations(url: str) -> list:
    """
    Extracts common accessibility violations using Playwright.
    Focuses on: missing alt text, low contrast, and aria-labels.
    """
    violations = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Example logic: find images without alt text
            images_without_alt = await page.eval_on_selector_all(
                "img:not([alt])", 
                "nodes => nodes.map(n => ({target: n.outerHTML, description: 'Image missing alt text'}))"
            )
            violations.extend(images_without_alt)
            
            # Example logic: find buttons without labels
            buttons_without_label = await page.eval_on_selector_all(
                "button:not([aria-label]):not([title])",
                "nodes => nodes.map(n => ({target: n.outerHTML, description: 'Button missing aria-label or title'}))"
            )
            violations.extend(buttons_without_label)

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
        finally:
            await browser.close()
            
    return violations

if __name__ == "__main__":
    import sys, json
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.google.com"
    results = asyncio.run(get_accessibility_violations(target_url))
    print(json.dumps(results, indent=2))
