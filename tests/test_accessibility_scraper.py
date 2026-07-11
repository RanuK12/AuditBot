import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from accessibility_scraper import scrape_site

@pytest.mark.asyncio
async def test_scrape_site_timeout_error():
    with patch('accessibility_scraper.aiohttp.ClientSession.get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = asyncio.TimeoutError()
        result = await scrape_site('https://example.com')
        assert result == []  # Verifica que devuelve una lista vacía en caso de timeout