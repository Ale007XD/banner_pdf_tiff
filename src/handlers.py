import logging
import asyncio
from typing import Optional, Tuple
from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

from .config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
    ADMIN_TELEGRAM_ID,
    MAX_FILE_SIZE_MB,
    DEFAULT_DPI,
)
from .convert import pdf_to_tiff_ghostscript


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    message = (
        "📄 *Конвертер PDF в TIFF*\n\n"
        "Отправьте PDF-файл для конвертации в TIFF.\n\n"
        "⚙️ *Настройки:*\n"
        f"• DPI по умолчанию: {DEFAULT_DPI}\n"
        "• Страницы по умолчанию: первая страница\n\n"
        "🔧 *Команды:*\n"
        "• `/dpi <число>` - установить DPI (72-1200)\n"
        "• `/pages N` - конвертировать N-ю страницу\n"
        "• `/pages A-B` - конвертировать страницы от A до B\n\n"
        "💡 *Совет:* PDF в кривых обрабатывается корректно; "
        "для тонких линий/мелкого текста используйте `/dpi 300`."
    )
    await update.message.reply_text(message, parse_mode="Markdown")


async def dpi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /dpi command."""
    if not context.args:
        await update.message.reply_text(
            "Укажите значение DPI:\n`/dpi <число>`\n\nПример: `/dpi 300`",
            parse_mode="Markdown"
        )
        return
    
    try:
        dpi = int(context.args[0])
        if not 72 <= dpi <= 1200:
            await update.message.reply_text(
                "❌ DPI должно быть в диапазоне от 72 до 1200."
            )
            return
        
        context.user_data["dpi"] = dpi
        await update.message.reply_text(
            f"✅ DPI установлено на {dpi}"
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ Некорректное значение DPI. Укажите число от 72 до 1200."
        )


async def pages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pages command."""
    if not context.args:
        await update.message.reply_text(
            "Укажите диапазон страниц:\n"
            "`/pages N` - одна страница\n"
            "`/pages A-B` - диапазон страниц\n\n"
            "Примеры:\n• `/pages 1`\n• `/pages 1-5`",
            parse_mode="Markdown"
        )
        return
    
    page_arg = context.args[0]
    
    try:
        if "-" in page_arg:
            # Range: A-B
            start_str, end_str = page_arg.split("-", 1)
            start_page = int(start_str)
            end_page = int(end_str)
            
            if start_page < 1 or end_page < 1 or start_page > end_page:
                await update.message.reply_text(
                    "❌ Некорректный диапазон страниц. "
                    "Страницы должны быть положительными числами, "
                    "и начальная страница не должна превышать конечную."
                )
                return
                
            context.user_data["pages"] = (start_page, end_page)
            await update.message.reply_text(
                f"✅ Установлен диапазон страниц: {start_page}-{end_page}"
            )
        else:
            # Single page: N
            page_num = int(page_arg)
            if page_num < 1:
                await update.message.reply_text(
                    "❌ Номер страницы должен быть положительным числом."
                )
                return
                
            context.user_data["pages"] = (page_num, page_num)
            await update.message.reply_text(
                f"✅ Установлена страница: {page_num}"
            )
            
    except ValueError:
        await update.message.reply_text(
            "❌ Некорректный формат. Используйте:\n"
            "• `/pages 5` для одной страницы\n"
            "• `/pages 1-10` для диапазона",
            parse_mode="Markdown"
        )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command (admin only)."""
    user_id = update.effective_user.id
    if user_id != ADMIN_TELEGRAM_ID:
        return  # Ignore non-admin users
    
    await update.message.reply_text("бот активен")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle PDF documents."""
    document = update.message.document
    
    # Validate MIME type
    if not document.mime_type or "pdf" not in document.mime_type.lower():
        await update.message.reply_text(
            "❌ Пожалуйста, отправьте PDF-файл."
        )
        return
    
    # Validate file size
    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if document.file_size > max_size_bytes:
        await update.message.reply_text(
            f"❌ Размер файла превышает {MAX_FILE_SIZE_MB} MB. "
            f"Размер вашего файла: {document.file_size / (1024 * 1024):.1f} MB"
        )
        return
    
    # Send progress message
    progress_message = await update.message.reply_text("Конвертирую…")
    
    try:
        # Get user settings
        dpi = context.user_data.get("dpi", DEFAULT_DPI)
        pages = context.user_data.get("pages", (1, 1))
        first_page, last_page = pages
        
        # Download PDF file
        file = await document.get_file()
        pdf_bytes = await file.download_as_bytearray()
        
        logger.info(
            f"Converting PDF: size={len(pdf_bytes)} bytes, "
            f"dpi={dpi}, pages={first_page}-{last_page}"
        )
        
        # Convert PDF to TIFF
        tiff_bytes, output_filename = pdf_to_tiff_ghostscript(
            input_pdf_bytes=bytes(pdf_bytes),
            dpi=dpi,
            first_page=first_page,
            last_page=last_page
        )
        
        # Generate filename with settings
        base_name = document.file_name.rsplit('.', 1)[0] if document.file_name else "document"
        if first_page == last_page:
            filename = f"{base_name}_p{first_page}_{dpi}dpi.tiff"
        else:
            filename = f"{base_name}_p{first_page}-{last_page}_{dpi}dpi.tiff"
        
        # Create InputFile object
        tiff_file = InputFile(
            obj=tiff_bytes,
            filename=filename
        )
        
        # Send to user
        await update.message.reply_document(
            document=tiff_file,
            caption=f"✅ PDF конвертирован\n📊 DPI: {dpi}\n📄 Страницы: {first_page}-{last_page}"
        )
        
        # Send to channel
        try:
            await context.bot.send_document(
                chat_id=TELEGRAM_CHANNEL_ID,
                document=InputFile(
                    obj=tiff_bytes,
                    filename=filename
                ),
                caption=f"PDF → TIFF\nDPI: {dpi}, Страницы: {first_page}-{last_page}"
            )
        except TelegramError as e:
            logger.error(f"Failed to send to channel: {e}")
        
        logger.info(f"Conversion completed: {filename}")
        
    except RuntimeError as e:
        logger.error(f"Conversion failed: {str(e)[:500]}")
        await update.message.reply_text(
            f"❌ Ошибка конвертации: {str(e)[:200]}..."
        )
    except Exception as e:
        logger.error(f"Unexpected error during conversion: {str(e)[:500]}")
        await update.message.reply_text(
            "❌ Произошла неожиданная ошибка при конвертации. Попробуйте еще раз."
        )
    finally:
        # Delete progress message
        try:
            await progress_message.delete()
        except TelegramError:
            pass  # Ignore if message was already deleted


def setup_handlers(application: Application) -> None:
    """Set up bot handlers."""
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("dpi", dpi_command))
    application.add_handler(CommandHandler("pages", pages_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Document handler for PDFs
    application.add_handler(MessageHandler(
        filters.Document.PDF | filters.Document.MimeType("application/pdf"),
        handle_document
    ))


async def main() -> None:
    """Main function to run the bot."""
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Set up handlers
    setup_handlers(application)
    
    # Run bot
    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
