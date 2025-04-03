import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from math import radians, sin, cos, sqrt, atan2

# Конфигурация
TOKEN = "8089566253:AAGJSzNBhjgoEK5ZolkgIqH8a8Q99iPuu44"
ANON_GROUP_LINK = "https://t.me/+Ql0IZosRRu82YTQy"
ANON_GROUP_ID = -1002514617765
FORWARD_GROUP_ID = -1002698558394

# Геопараметры Таганрога
TAGANROG_CENTER = (47.2364, 38.8953)
ALLOWED_RADIUS_KM = 50

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'
)
logger = logging.getLogger(__name__)

# Клавиатура для запроса гео
geo_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("📍 Отправить текущую геолокацию", request_location=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

def calculate_distance(lat1, lon1, lat2, lon2):
    """Вычисление расстояния между точками (в км)"""
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return R * (2 * atan2(sqrt(a), sqrt(1-a)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение"""
    await update.message.reply_text(
        "Привет! Для отправки сообщения сначала поделись своей геолокацией:",
        reply_markup=geo_keyboard
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученной геолокации"""
    user = update.message.from_user
    location = update.message.location
    
    # Сохраняем геоданные в контексте
    context.user_data['location'] = {
        'lat': location.latitude,
        'lon': location.longitude,
        'distance': calculate_distance(
            TAGANROG_CENTER[0], TAGANROG_CENTER[1],
            location.latitude, location.longitude
        )
    }
    
    # Удаляем клавиатуру
    await update.message.reply_text(
        "✅ Геолокация получена! Теперь отправь текст сообщения.",
        reply_markup=ReplyKeyboardMarkup.remove_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    if update.message.chat.type != "private":
        return
    
    # Проверяем наличие геолокации
    if 'location' not in context.user_data:
        await update.message.reply_text(
            "⚠️ Сначала отправь свою геолокацию:",
            reply_markup=geo_keyboard
        )
        return
    
    user = update.message.from_user
    location_data = context.user_data['location']
    distance = location_data['distance']
    
    # Формируем сообщение для админов
    admin_msg = (
        f"👤 Отправитель: @{user.username or 'N/A'} (ID: {user.id})\n"
        f"📍 Гео: https://maps.google.com/?q={location_data['lat']},{location_data['lon']}\n"
        f"📏 Расстояние: {distance:.1f} км\n\n"
        f"📝 Сообщение:\n{update.message.text}"
    )
    
    # Отправляем админам в любом случае
    await context.bot.send_message(FORWARD_GROUP_ID, admin_msg)
    
    # Отправляем в анонимный чат только если в радиусе
    if distance <= ALLOWED_RADIUS_KM:
        await context.bot.send_message(
            ANON_GROUP_ID,
            f"✉️ Анонимное сообщение:\n\n{update.message.text}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Открыть", url=ANON_GROUP_LINK)]])
        )
        await update.message.reply_text("✅ Сообщение опубликовано!")
    else:
        await update.message.reply_text("❌ Вы вне зоны Таганрога. Сообщение не опубликовано.")
    
    # Удаляем геоданные для следующего сообщения
    del context.user_data['location']
    await update.message.reply_text(
        "Для отправки нового сообщения снова отправь геолокацию:",
        reply_markup=geo_keyboard
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Ошибка: {context.error}")
    if update and update.message:
        await update.message.reply_text("⚠️ Ошибка обработки. Попробуйте позже.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    logger.info("Бот запущен")
    app.run_polling()
