import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.error import TelegramError

# Настройки бота
TOKEN = "8089566253:AAGJSzNBhjgoEK5ZolkgIqH8a8Q99iPuu44"  # Замените на токен вашего бота
ANON_GROUP_LINK = "https://t.me/+Ql0IZosRRu82YTQy"  # Ссылка на группу для анонимных постов
ANON_GROUP_ID = -1002514617765  # ID анонимной группы (должно начинаться с -100)
FORWARD_GROUP_ID = -1002698558394  # ID группы для пересылки (тоже с -100)

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'  # Логи сохраняются в файл
)
logger = logging.getLogger(__name__)

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для проверки работоспособности бота"""
    await update.message.reply_text(
        f"🛠 Тест бота:\n"
        f"• ID этого чата: {update.message.chat.id}\n"
        f"• Бот жив и реагирует на команды"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Логируем входящее сообщение
        logger.info(f"Новое сообщение от {update.message.from_user.id}: {update.message.text or 'Медиа-файл'}")

        # Проверяем, что бот может отправлять сообщения
        test_msg = await context.bot.send_message(
            chat_id=update.message.chat.id,
            text="🔄 Проверка связи..."
        )
        await test_msg.delete()

        # Отправка в анонимную группу
        sent_msg = await context.bot.send_message(
            chat_id=ANON_GROUP_ID,
            text=f"✉️ Новое анонимное сообщение:\n\n{update.message.text}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Открыть", url=ANON_GROUP_LINK)]])
        )
        logger.info(f"Сообщение отправлено в анонимную группу. ID: {sent_msg.message_id}")

        # Пересылка в другую группу
        forwarded_msg = await update.message.forward(FORWARD_GROUP_ID)
        logger.info(f"Сообщение переслано. ID: {forwarded_msg.message_id}")

        await update.message.reply_text("✅ Сообщение успешно опубликовано!")

    except TelegramError as e:
        logger.error(f"Ошибка Telegram: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
        await update.message.reply_text("⚠️ Произошла непредвиденная ошибка")

if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Добавляем команду для отладки
    application.add_handler(CommandHandler("debug", debug))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    logger.info("Бот запущен")
    application.run_polling()