"""Tests for AuditBot Telegram bot (bot.py)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes

import sys
import os

# Mock token so bot.py doesn't fail on import
os.environ["TELEGRAM_BOT_TOKEN"] = "test:fake_token_12345"

from bot import start, help_command, status, handle_url, audit_results


@pytest.fixture
def mock_update():
    """Create a mock Update — we use a MagicMock to avoid frozen Message."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    return update


@pytest.fixture
def mock_context():
    """Create a mock ContextTypes.DEFAULT_TYPE."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Test /start command replies with welcome message."""
    await start(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once()
    args, _ = mock_update.message.reply_text.await_args
    assert "AuditBot" in args[0]
    assert "/help" in args[0]


@pytest.mark.asyncio
async def test_help_command(mock_update, mock_context):
    """Test /help command replies with help text."""
    await help_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once()
    args, _ = mock_update.message.reply_text.await_args
    assert "Ayuda" in args[0]


@pytest.mark.asyncio
async def test_status_no_active_audits(mock_update, mock_context):
    """Test /status when user has no active audits."""
    audit_results.clear()
    await status(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once()
    args, _ = mock_update.message.reply_text.await_args
    assert "No tienes auditorías activas" in args[0]


@pytest.mark.asyncio
async def test_status_with_active_audits(mock_update, mock_context):
    """Test /status when user has active audits."""
    audit_results.clear()
    audit_results["https://example.com"] = 12345  # same user id
    await status(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once()
    args, _ = mock_update.message.reply_text.await_args
    assert "1 auditoría(s)" in args[0]


@pytest.mark.asyncio
async def test_handle_url_invalid_format(mock_update, mock_context):
    """Test handle_url rejects URLs without http/https."""
    mock_update.message.text = "not-a-url"
    await handle_url(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once()
    args, _ = mock_update.message.reply_text.await_args
    assert "La URL debe comenzar" in args[0]


@pytest.mark.asyncio
async def test_handle_url_valid(mock_update, mock_context):
    """Test handle_url processes a valid URL successfully."""
    mock_update.message.text = "https://example.com"

    with patch("bot.run_audit", new=AsyncMock()) as mock_run_audit:
        mock_run_audit.return_value = {
            "url": "https://example.com",
            "totalViolations": 2,
            "violations": [
                {"impact": "critical", "nodes": [{}]},
                {"impact": "serious", "nodes": [{}]},
            ],
        }
        await handle_url(mock_update, mock_context)

        # Should have called reply_text twice: first "Iniciando", then summary
        assert mock_update.message.reply_text.await_count == 2
        first = mock_update.message.reply_text.await_args_list[0][0][0]
        assert "Iniciando auditoría" in first
        second = mock_update.message.reply_text.await_args_list[1][0][0]
        assert "Auditoría completada" in second
        assert "Críticas: 1" in second
        assert "Graves: 1" in second


@pytest.mark.asyncio
async def test_handle_url_audit_error(mock_update, mock_context):
    """Test handle_url returns error message when audit fails."""
    mock_update.message.text = "https://example.com"

    with patch("bot.run_audit", new=AsyncMock()) as mock_run_audit:
        mock_run_audit.side_effect = Exception("Connection failed")
        await handle_url(mock_update, mock_context)

        assert mock_update.message.reply_text.await_count == 2
        second = mock_update.message.reply_text.await_args_list[1][0][0]
        assert "Ocurrió un error" in second
