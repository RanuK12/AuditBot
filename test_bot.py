"""Tests for AuditBot Telegram bot (bot.py)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes

import sys
import os
import tempfile

# Mock token so bot.py doesn't fail on import
os.environ["TELEGRAM_BOT_TOKEN"] = "test:fake_token_12345"

from bot import start, help_command, status, handle_url, report_command, audit_results


@pytest.fixture
def mock_update():
    """Create a mock Update — we use a MagicMock to avoid frozen Message."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    update.message.reply_document = AsyncMock()
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


# ──────────────────────────────────────────────────────────────
# report_command tests  (previously untested)
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_command_no_args(mock_update, mock_context):
    """Test /report without URL argument shows usage message."""
    mock_context.args = []
    await report_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once()
    args, _ = mock_update.message.reply_text.await_args
    assert "proporcionar" in args[0].lower() or "url" in args[0].lower()


@pytest.mark.asyncio
async def test_report_command_invalid_url(mock_update, mock_context):
    """Test /report with non-http URL shows format error."""
    mock_context.args = ["not-a-url"]
    await report_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once()
    args, _ = mock_update.message.reply_text.await_args
    assert "http" in args[0].lower()


@pytest.mark.asyncio
async def test_report_command_audit_success_sends_pdf(mock_update, mock_context):
    """Test /report generates PDF and sends it as a document."""
    mock_context.args = ["https://example.com"]

    async def mock_axe(url):
        return {"url": url, "totalViolations": 0, "violations": []}

    def mock_pdf_gen(violations, output_path=None):
        """Simulate PDF generation by writing fake bytes to output_path."""
        if output_path:
            with open(output_path, "wb") as f:
                f.write(b"%PDF-1.4 fake pdf content")

    with patch("bot.run_audit", side_effect=mock_axe):
        with patch("bot.generate_pdf_report", side_effect=mock_pdf_gen):
            await report_command(mock_update, mock_context)

    # First call: "Iniciando auditoría"
    first_text = mock_update.message.reply_text.await_args_list[0][0][0]
    assert "Iniciando" in first_text

    # Should have sent a document (the PDF)
    mock_update.message.reply_document.assert_awaited_once()
    doc_kwargs = mock_update.message.reply_document.await_args.kwargs
    assert "caption" in doc_kwargs
    assert "example.com" in doc_kwargs["caption"]
    assert doc_kwargs["filename"].endswith(".pdf")


@pytest.mark.asyncio
async def test_report_command_audit_error(mock_update, mock_context):
    """Test /report shows error when the audit itself fails."""
    mock_context.args = ["https://example.com"]

    with patch("bot.run_audit", new=AsyncMock()) as mock_run_audit:
        mock_run_audit.side_effect = Exception("Connection failed")
        await report_command(mock_update, mock_context)

    assert mock_update.message.reply_text.await_count == 2
    second_text = mock_update.message.reply_text.await_args_list[1][0][0]
    assert "error" in second_text.lower()
    mock_update.message.reply_document.assert_not_awaited()


@pytest.mark.asyncio
async def test_report_command_pdf_generation_error(mock_update, mock_context):
    """Test /report handles PDF generation failure gracefully."""
    mock_context.args = ["https://example.com"]

    async def mock_axe(url):
        return {"url": url, "totalViolations": 0, "violations": []}

    def mock_pdf_gen_broken(violations, output_path=None):
        raise RuntimeError("PDF engine crashed")

    with patch("bot.run_audit", side_effect=mock_axe):
        with patch("bot.generate_pdf_report", side_effect=mock_pdf_gen_broken):
            await report_command(mock_update, mock_context)

    # Should still get the "Iniciando" message + an error about PDF
    assert mock_update.message.reply_text.await_count >= 2
    all_texts = " ".join(
        call[0][0] for call in mock_update.message.reply_text.await_args_list
    )
    assert "pdf" in all_texts.lower() or "error" in all_texts.lower()
    mock_update.message.reply_document.assert_not_awaited()
