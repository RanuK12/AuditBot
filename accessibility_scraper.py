import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from aiohttp import ClientError, ClientConnectorError, ClientResponseError
from logger_config import logger

async def scrape_site(url):
    """Extract basic accessibility violations from a URL using aiohttp and BeautifulSoup."""
    violations = []
    
    try:
        # Validate and normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # Set timeout and headers
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch the page
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"HTTP {response.status} for {url}")
                    return []
                
                # Parse HTML
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 1. Check for missing lang attribute
                html_tag = soup.find('html')
                if html_tag and not html_tag.get('lang'):
                    violations.append({
                        'type': 'missing_lang',
                        'detail': 'HTML element missing lang attribute',
                        'element': str(html_tag)[:100] + '...'
                    })
                
                # 2. Check images without alt attribute
                images = soup.find_all('img')
                for img in images:
                    if not img.get('alt'):
                        violations.append({
                            'type': 'missing_alt',
                            'detail': f'Image missing alt attribute: {img.get("src", "")}',
                            'element': str(img)[:200]
                        })
                
                # 3. Check form inputs without associated labels
                form_inputs = soup.find_all(['input', 'select', 'textarea'])
                for input_elem in form_inputs:
                    # Skip buttons (they usually don't need labels)
                    if input_elem.get('type') == 'button' or input_elem.get('type') == 'submit':
                        continue
                        
                    # Check if input has an associated label via id
                    input_id = input_elem.get('id')
                    if input_id:
                        label = soup.find('label', {'for': input_id})
                        if not label:
                            # Check if input is wrapped in a label
                            parent = input_elem.parent
                            if parent and parent.name != 'label':
                                violations.append({
                                    'type': 'missing_label',
                                    'detail': f'Form input missing label: {input_elem.get("name", input_elem.get("type", "input"))}',
                                    'element': str(input_elem)[:200]
                                })
                    else:
                        # No id, check if wrapped in label
                        parent = input_elem.parent
                        if parent and parent.name != 'label':
                            violations.append({
                                'type': 'missing_label',
                                'detail': f'Form input missing label: {input_elem.get("name", input_elem.get("type", "input"))}',
                                'element': str(input_elem)[:200]
                            })
                
                # 4. Check heading order
                headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if len(headings) > 1:
                    current_level = 1
                    for heading in headings:
                        level = int(heading.name[1])
                        if level > current_level + 1:
                            violations.append({
                                'type': 'heading_order',
                                'detail': f'Heading level {level} skipped after level {current_level}',
                                'element': str(heading)[:100]
                            })
                        current_level = level
                
                # 5. Check ARIA roles with required attributes
                aria_elements = soup.find_all(attrs={'role': True})
                for elem in aria_elements:
                    role = elem.get('role')
                    if role == 'button' and not elem.get('tabindex'):
                        violations.append({
                            'type': 'aria_missing_tabindex',
                            'detail': 'Button role element missing tabindex attribute',
                            'element': str(elem)[:200]
                        })
                    elif role == 'link' and not elem.get('href'):
                        violations.append({
                            'type': 'aria_missing_href',
                            'detail': 'Link role element missing href attribute',
                            'element': str(elem)[:200]
                        })
                
                logger.info(f"Scraped {len(violations)} accessibility issues from {url}")
                
    except asyncio.TimeoutError:
        logger.error(f"TimeoutError scraping {url}: The request timed out.")
    except ClientConnectorError as e:
        logger.error(f"ClientConnectorError scraping {url}: Could not connect to the server. Details: {e}")
    except ClientResponseError as e:
        logger.error(f"ClientResponseError scraping {url}: Received HTTP {e.status} for {e.request_info.real_url}. Details: {e}")
    except ClientError as e:
        logger.error(f"ClientError scraping {url}: An aiohttp client error occurred. Details: {e}")
    except Exception as e:
        logger.error(f"Unexpected error scraping {url}: {type(e).__name__}: {e}")
    finally:
        logger.info(f"Finished scraping for URL: {url}")
    
    return violations