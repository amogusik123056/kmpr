import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext
from telegram.error import TelegramError

# Настройки бота
TOKEN = "8089566253:AAGJSzNBhjgoEK5ZolkgIqH8a8Q99iPuu44"
ANON_GROUP_LINK = "https://t.me/+Ql0IZosRRu82YTQy"
ANON_GROUP_ID = -1002514617765
FORWARD_GROUP_ID = -1002698558394
VIDEO_LINK = "https://youtu.be/PQH1W_DRA7E"

# Словарь для хранения соответствия сообщений бота и отправителей
user_message_map = {}

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'
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
    # Обработка сообщений только из личного чата
    if update.message.chat.type == "private":
        try:
            user = update.message.from_user
            logger.info(f"Новое сообщение от {user.id}: {update.message.text or 'Медиа-файл'}")

            test_msg = await context.bot.send_message(
                chat_id=update.message.chat.id,
                text="🔄 Проверка связи..."
            )
            await test_msg.delete()

            # Отправка в анонимную группу
            sent_msg = await context.bot.send_message(
                chat_id=ANON_GROUP_ID,
                text=f"✉️ Новое анонимное сообщение:\n\n{update.message.text}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 пасматряiмо:", url=ANON_GROUP_LINK)]])
            )
            
            # Сохраняем соответствие между сообщением бота и отправителем
            user_message_map[sent_msg.message_id] = user.id
            logger.info(f"Сообщение {sent_msg.message_id} сохранено для пользователя {user.id}")

            # Пересылка в другую группу с информацией об отправителе
            sender_info = f"@{user.username} (ID: {user.id})" if user.username else f"ID: {user.id}"
            full_message = f"Отправитель: {sender_info}\n\n{update.message.text}" if update.message.text else f"Отправитель: {sender_info}"

            await context.bot.send_message(
                chat_id=FORWARD_GROUP_ID,
                text=full_message
            )
            
            await update.message.forward(FORWARD_GROUP_ID)
            await update.message.reply_text("✅ Сообщение успешно отправлено админам! (есле чота нада то @kmpr0)")

        except TelegramError as e:
            logger.error(f"Ошибка Telegram: {e}")
            await update.message.reply_text(f"❌ Ошибка: {e}")
        except Exception as e:
            logger.critical(f"Критическая ошибка: {e}")
            await update.message.reply_text("⚠️ Произошла непредвиденная ошибка")

async def handle_reply(update: Update, context: CallbackContext):
    # Обработка ответов на сообщения бота в группах
    if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
        replied_msg_id = update.message.reply_to_message.message_id
        
        # Ищем отправителя оригинального сообщения
        if replied_msg_id in user_message_map:
            original_sender_id = user_message_map[replied_msg_id]
            
            try:
                # Отправляем ответ пользователю
                reply_text = f"🔔 Ответ на ваше сообщение:\n\n{update.message.text}"
                await context.bot.send_message(
                    chat_id=original_sender_id,
                    text=reply_text
                )
                
                # Если это медиа-сообщение, пересылаем его
                if not update.message.text:
                    await context.bot.forward_message(
                        chat_id=original_sender_id,
                        from_chat_id=update.message.chat.id,
                        message_id=update.message.message_id
                    )
                
                logger.info(f"Ответ переслан пользователю {original_sender_id}")
                
            except TelegramError as e:
                logger.error(f"Не удалось отправить ответ пользователю {original_sender_id}: {e}")
                if "bot was blocked by the user" in str(e):
                    await update.message.reply_text("❌ Не удалось отправить ответ - пользователь заблокировал бота")

if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("debug", debug))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчик для ответов на сообщения бота
    application.add_handler(MessageHandler(
        filters.Chat([ANON_GROUP_ID, FORWARD_GROUP_ID]) & 
        filters.REPLY, 
        handle_reply
    ))
    
    logger.info("Бот запущен")
    application.run_polling()
