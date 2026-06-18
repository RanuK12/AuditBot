import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app import run_audit  # Importamos la función principal de auditoría
from logger_config import setup_logging

# Configurar logging centralizado
setup_logging()
logger = logging.getLogger(__name__)

# Token del bot desde variable de entorno
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Diccionario para almacenar resultados de auditorías en curso
audit_results = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start"""
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
    await update.message.reply_text(
        "📋 **Ayuda de AuditBot**\n\n"
        "Para auditar un sitio web, simplemente envíame la URL completa.\n\n"
        "**Formato:** https://ejemplo.com\n"
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
    user_id = update.effective_user.id
    if user_id in audit_results:
        await update.message.reply_text(
            f"📊 **Estado de auditorías**\n\n"
            f"Tienes {len(audit_results[user_id])} auditoría(s) en curso.\n"
            f"Última URL auditada: {list(audit_results[user_id].keys())[-1]}"
        )
    else:
        await update.message.reply_text("📭 No tienes auditorías activas.")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los mensajes que contienen URLs"""
    url = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Validar URL
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text(
            "⚠️ **URL inválida**\n\n"
            "La URL debe comenzar con http:// o https://\n"
            "Ejemplo: https://ejemplo.com"
        )
        return
    
    # Informar que se está procesando
    await update.message.reply_text(
        f"🔍 **Auditando:** {url}\n\n"
        "⏳ Esto puede tomar unos segundos...\n"
        "Te notificaré cuando termine."
    )
    
    try:
        # Ejecutar auditoría en un hilo separado para no bloquear el bot
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(None, run_audit, url)
        
        # Guardar resultado
        if user_id not in audit_results:
            audit_results[user_id] = {}
        audit_results[user_id][url] = report
        
        # Enviar reporte
        await send_report(update, context, url, report)
        
    except Exception as e:
        logger.error(f"Error auditando {url}: {str(e)}")
        await update.message.reply_text(
            f"❌ **Error al auditar** {url}\n\n"
            f"Detalles: {str(e)}\n\n"
            "Verifica que la URL sea correcta y el sitio esté accesible."
        )

async def send_report(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, report: dict):
    """Envía el reporte de auditoría formateado"""
    
    # Formatear reporte como texto
    report_text = f"📋 **Reporte de Auditoría**\n\n"
    report_text += f"**URL:** {url}\n"
    report_text += f"**Fecha:** {report.get('fecha', 'N/A')}\n"
    report_text += f"**Duración:** {report.get('duracion', 'N/A')}s\n\n"
    
    # Información general
    if 'informacion_general' in report:
        info = report['informacion_general']
        report_text += "**Información General**\n"
        report_text += f"- Título: {info.get('titulo', 'N/A')}\n"
        report_text += f"- Descripción: {info.get('descripcion', 'N/A')[:100]}...\n"
        report_text += f"- Palabras clave: {info.get('palabras_clave', 'N/A')}\n"
        report_text += f"- Encoding: {info.get('encoding', 'N/A')}\n\n"
    
    # Seguridad
    if 'seguridad' in report:
        seg = report['seguridad']
        report_text += "**🔒 Seguridad**\n"
        report_text += f"- HTTPS: {'✅' if seg.get('https', False) else '❌'}\n"
        report_text += f"- HSTS: {'✅' if seg.get('hsts', False) else '❌'}\n"
        report_text += f"- X-Frame-Options: {'✅' if seg.get('x_frame_options', False) else '❌'}\n"
        report_text += f"- Content-Security-Policy: {'✅' if seg.get('csp', False) else '❌'}\n"
        report_text += f"- X-Content-Type-Options: {'✅' if seg.get('x_content_type_options', False) else '❌'}\n\n"
    
    # Rendimiento
    if 'rendimiento' in report:
        rend = report['rendimiento']
        report_text += "**⚡ Rendimiento**\n"
        report_text += f"- Tiempo de carga: {rend.get('tiempo_carga', 'N/A')}s\n"
        report_text += f"- Tamaño página: {rend.get('tamano_pagina', 'N/A')}\n"
        report_text += f"- Número de recursos: {rend.get('num_recursos', 'N/A')}\n\n"
    
    # SEO
    if 'seo' in report:
        seo = report['seo']
        report_text += "**🔍 SEO**\n"
        report_text += f"- Meta tags: {'✅' if seo.get('meta_tags', False) else '❌'}\n"
        report_text += f"- Open Graph: {'✅' if seo.get('open_graph', False) else '❌'}\n"
        report_text += f"- Twitter Cards: {'✅' if seo.get('twitter_cards', False) else '❌'}\n"
        report_text += f"- Sitemap: {'✅' if seo.get('sitemap', False) else '❌'}\n"
        report_text += f"- Robots.txt: {'✅' if seo.get('robots_txt', False) else '❌'}\n\n"
    
    # Enlaces
    if 'enlaces' in report:
        enlaces = report['enlaces']
        report_text += "**🔗 Enlaces**\n"
        report_text += f"- Total enlaces: {enlaces.get('total', 'N/A')}\n"
        report_text += f"- Enlaces internos: {enlaces.get('internos', 'N/A')}\n"
        report_text += f"- Enlaces externos: {enlaces.get('externos', 'N/A')}\n"
        report_text += f"- Enlaces rotos: {enlaces.get('rotos', 'N/A')}\n\n"
    
    # Recomendaciones
    if 'recomendaciones' in report:
        rec = report['recomendaciones']
        report_text += "**💡 Recomendaciones**\n"
        for i, recomendacion in enumerate(rec[:5], 1):
            report_text += f"{i}. {recomendacion}\n"
    
    # Score
    if 'score' in report:
        score = report['score']
        report_text += f"\n**📊 Score: {score}/100**\n"
    
    # Enviar reporte (dividir si es muy largo)
    max_length = 4000
    if len(report_text) > max_length:
        parts = [report_text[i:i+max_length] for i in range(0, len(report_text), max_length)]
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(report_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja errores del bot"""
    logger.error(f"Error en actualización {update}: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Ocurrió un error inesperado. Por favor, intenta de nuevo más tarde."
            )
    except Exception as e:
        logger.error(f"Error al manejar error: {e}")

def main():
    """Función principal del bot"""
    if not TOKEN:
        logger.error("No se encontró TELEGRAM_BOT_TOKEN en variables de entorno")
        return
    
    # Crear aplicación
    application = Application.builder().token(TOKEN).build()
    
    # Registrar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    # Registrar manejador de errores
    application.add_error_handler(error_handler)
    
    # Iniciar bot
    logger.info("Iniciando AuditBot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
