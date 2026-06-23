import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app import run_axe_audit as run_audit
from logger_config import logger

# Token del bot desde variable de entorno
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Diccionario para almacenar resultados de auditorías en curso
audit_results = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start"""
    logger.info(f"Command /start received from user {update.effective_user.id}")
    await update.message.reply_text(
        "🤖 ¡Hola! Soy AuditBot.\n\n"
        "Envíame una URL para auditar y te devolveré un reporte detallado.\n"
        "Ejemplo: https://ejemplo.com\n\n"
        "Comandos disponibles:\n"
        "/start - Iniciar el bot\n"
        "/help - Ayuda\n"
        "/status - Ver estado de auditorías"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /help"""
    logger.info(f"Command /help received from user {update.effective_user.id}")
    await update.message.reply_text(
        "📋 **Ayuda de AuditBot**\n\n"
        "Para auditar un sitio web, simplemente envíame la URL completa.\n\n"
        "**Formato:** https://ejemplo.com\n\n"
        "**Requisitos:**\n"
        "- La URL debe comenzar con http:// o https://\n"
        "- El sitio debe ser accesible públicamente\n\n"
        "**Comandos:**\n"
        "/start - Iniciar el bot\n"
        "/help - Mostrar esta ayuda\n"
        "/status - Ver estado de auditorías activas"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /status"""
    logger.info(f"Command /status received from user {update.effective_user.id}")
    user_id = update.effective_user.id
    # Count active audits for this user
    user_audits = [url for url, uid in audit_results.items() if uid == user_id]
    count = len(user_audits)
    if count == 0:
        await update.message.reply_text("No tienes auditorías activas en este momento.")
    else:
        await update.message.reply_text(
            f"Tienes {count} auditoría(s) activa(s).\n"
            "Usa /status de nuevo para verificar más tarde."
        )


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes que contienen una URL"""
    url = update.message.text.strip()
    logger.info(f"URL received from user {update.effective_user.id}: {url}")
    # Validate URL format
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text(
            "❌ La URL debe comenzar con http:// o https://\n"
            "Por favor, envíame una URL válida."
        )
        return
    # Notify user that audit is starting
    await update.message.reply_text(f"🔍 Iniciando auditoría de {url}...\nEsto puede tomar unos segundos.")
    try:
        # Run the audit (this is async)
        result = await run_audit(url)
        # Store result for status tracking
        audit_results[url] = update.effective_user.id
        # Build a summary message
        if result and "violations" in result:
            violations = result["violations"]
            num_violations = len(violations)
            # Count by impact level
            critical = sum(1 for v in violations if v.get("impact") == "critical")
            serious = sum(1 for v in violations if v.get("impact") == "serious")
            moderate = sum(1 for v in violations if v.get("impact") == "moderate")
            minor = sum(1 for v in violations if v.get("impact") == "minor")
            summary = (
                f"✅ Auditoría completada para {url}\n\n"
                f"**Resumen de violaciones:**\n"
                f"- Críticas: {critical}\n"
                f"- Graves: {serious}\n"
                f"- Moderadas: {moderate}\n"
                f"- Menores: {minor}\n"
                f"Total: {num_violations}\n\n"
                "Para un reporte detallado, usa el endpoint /audit/report en la API web."
            )
        else:
            summary = f"✅ Auditoría completada para {url}\nNo se encontraron violaciones de accesibilidad."
        await update.message.reply_text(summary)
    except Exception as e:
        logger.error(f"Error auditing {url}: {e}")
        await update.message.reply_text(
            f"❌ Ocurrió un error al auditar {url}.\n"
            "Por favor, verifica que la URL sea accesible e intenta de nuevo."
        )


def main():
    """Punto de entrada principal del bot"""
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN no está configurado en las variables de entorno.")
        return
    # Create the Application
    application = Application.builder().token(TOKEN).build()
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    # Register message handler for URLs (non-command messages)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    # Start polling
    logger.info("Starting AuditBot polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
