import os
import logging
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)

# --- Firebase Imports ---
# Убедитесь, что у вас установлен firebase-admin: pip install firebase-admin
import firebase_admin
from firebase_admin import credentials, firestore, auth

# --- Базовая настройка ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

# --- Импорт из agent_core ---
try:
    # Импортируем все необходимые функции из agent_core
    from agent_core import create_telegram_post, get_user_stats, get_community_rating, answer_question, analyze_message
except ImportError:
    logger.critical("Не удалось импортировать функции из agent_core.py. Убедитесь, что файл существует и корректен.")
    raise

# --- Конфигурация (читается из .env) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
POST_HISTORY_FILE = "published_posts.json"

# --- Firebase Initialization ---
db = None # Инициализируем db как None по умолчанию
app_id = os.getenv("__app_id", "default-app-id") # app_id должен быть доступен всегда
try:
    firebase_config_str = os.getenv("__firebase_config")
    if firebase_config_str:
        firebase_config = json.loads(firebase_config_str)
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            logger.info("Firebase успешно инициализирован.")
        else:
            logger.warning("Firebase уже инициализирован.")
            db = firestore.client() # Получаем клиент, если уже инициализирован
    else:
        logger.warning("Firebase не инициализирован: отсутствует __firebase_config в переменных окружения.")
except Exception as e:
    logger.error(f"Ошибка инициализации Firebase: {e}", exc_info=True)
    db = None

# --- Вспомогательные функции ---
def save_post_to_history(post_text: str):
    """Сохраняет текст опубликованного поста в файл истории."""
    history = []
    try:
        with open(POST_HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    history.append(post_text)
    if len(history) > 10: # Ограничиваем историю 10 последними постами
        history = history[-10:]

    with open(POST_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

async def register_user_and_save_message(update: Update, message_text: str):
    """
    Регистрирует пользователя в Firestore (если его нет) и сохраняет сообщение.
    """
    if not db:
        logger.warning("Firestore не инициализирован, пропуск сохранения пользователя и сообщения.")
        return

    user_id = str(update.effective_user.id)
    username = update.effective_user.username or f"user_{user_id}"
    
    user_ref = db.collection(f"artifacts/{app_id}/users/{user_id}/profile").document("data")
    
    try:
        user_doc = user_ref.get()
        if not user_doc.exists:
            user_data = {
                "telegram_id": user_id,
                "username": username,
                "first_name": update.effective_user.first_name or "",
                "last_name": update.effective_user.last_name or "",
                "registration_date": firestore.SERVER_TIMESTAMP,
                "activity_score": 0,
                "jk_earned": 0
            }
            user_ref.set(user_data)
            logger.info(f"Новый пользователь зарегистрирован: {username} ({user_id})")
        
        # Сохранение сообщения
        messages_collection_ref = db.collection(f"artifacts/{app_id}/users/{user_id}/messages")
        message_data = {
            "text": message_text,
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        messages_collection_ref.add(message_data)
        logger.info(f"Сообщение пользователя {user_id} сохранено в Firestore.")

    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя или сохранении сообщения в Firestore: {e}", exc_info=True)


# --- Обработчики команд бота ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение и регистрирует пользователя."""
    await register_user_and_save_message(update, "/start")
    await update.message.reply_text(
        'Привет! Я Нейро Jekardos. Чтобы сгенерировать пост, '
        'используйте команду /generate [тема поста].'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет справочное сообщение и регистрирует сообщение."""
    await register_user_and_save_message(update, "/help")
    help_text = """
🤖 **JK Community Hub Bot** - Интеллектуальный помощник сообщества

**Основные команды:**
/generate [тема] - Создание поста для канала
/stats - Ваша личная статистика
/rating - Рейтинг активных участников
/ask [вопрос] - Задать вопрос боту
/analyze [текст] - Анализ сообщения на токсичность

**Поддержка:** Обращайтесь к администраторам для сложных вопросов.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает личную статистику пользователя."""
    user_id = str(update.effective_user.id)
    await register_user_and_save_message(update, "/stats")
    try:
        stats = get_user_stats(user_id)
        await update.message.reply_text(f"📊 **Ваша статистика:**\n\n{stats}", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await update.message.reply_text("❌ Не удалось получить статистику. Попробуйте позже.")

async def rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает рейтинг активных участников."""
    await register_user_and_save_message(update, "/rating")
    try:
        rating = get_community_rating()
        await update.message.reply_text(f"🏆 **Рейтинг сообщества:**\n\n{rating}", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка при получении рейтинга: {e}")
        await update.message.reply_text("❌ Не удалось получить рейтинг. Попробуйте позже.")

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отвечает на вопросы пользователей."""
    question = " ".join(context.args)
    await register_user_and_save_message(update, f"/ask {question}")
    if not question:
        await update.message.reply_text("Пожалуйста, укажите вопрос. Например: /ask Как работает TON блокчейн?")
        return
    await update.message.reply_text(f"🤔 Обрабатываю ваш вопрос: '{question}'...")
    try:
        answer = answer_question(question)
        await update.message.reply_text(f"💡 **Ответ:**\n\n{answer}", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка при ответе на вопрос: {e}")
        await update.message.reply_text("❌ Не удалось обработать вопрос. Попробуйте позже.")

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Анализирует сообщение на токсичность и спам."""
    text_to_analyze = " ".join(context.args)
    await register_user_and_save_message(update, f"/analyze {text_to_analyze}")
    if not text_to_analyze:
        await update.message.reply_text("Пожалуйста, укажите текст для анализа. Например: /analyze Этот текст нужно проверить")
        return
    await update.message.reply_text(f"🔍 Анализирую текст: '{text_to_analyze[:50]}...'")
    try:
        analysis = analyze_message(text_to_analyze)
        # Форматируем JSON для красивого вывода
        pretty_analysis = json.dumps(analysis, ensure_ascii=False, indent=2)
        await update.message.reply_text(f"📊 **Результат анализа:**\n```json\n{pretty_analysis}\n```", parse_mode='MarkdownV2')
    except Exception as e:
        logger.error(f"Ошибка при анализе текста: {e}")
        await update.message.reply_text("❌ Не удалось проанализировать текст. Попробуйте позже.")

async def generate_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начинает процесс генерации поста."""
    query = " ".join(context.args)
    await register_user_and_save_message(update, f"/generate {query}")
    if not query:
        await update.message.reply_text("Пожалуйста, укажите тему. Например: /generate пост о подготовке к походу в горы.")
        return
    await update.message.reply_text(f"Генерирую пост на тему: '{query}'. Это может занять до минуты...")
    try:
        post_text = create_telegram_post(query)
        context.user_data['post_text'] = post_text
        keyboard = [
            [
                InlineKeyboardButton("✅ Опубликовать", callback_data="publish"),
                InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text=post_text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка во время генерации поста: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка при генерации поста. Попробуйте еще раз.")

async def confirm_publish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подтверждает и публикует пост в канал."""
    query = update.callback_query
    await query.answer()
    post_text = context.user_data.get('post_text')
    if not post_text:
        await query.edit_message_text("Ошибка: Данные поста не найдены.")
        context.user_data.clear()
        return
    if query.data == 'publish':
        channel_id = TELEGRAM_CHANNEL_ID
        if not channel_id:
            await query.edit_message_text("Ошибка: ID канала Telegram не установлен в переменных окружения.")
            return
        try:
            await context.bot.send_message(chat_id=channel_id, text=post_text)
            save_post_to_history(post_text)
            await query.edit_message_text("✅ Пост успешно опубликован в канале!", reply_markup=None)
            if db:
                posts_collection_ref = db.collection(f"artifacts/{app_id}/public/data/published_posts")
                post_data = {
                    "text": post_text,
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "published_by_user_id": str(update.effective_user.id),
                    "published_by_username": update.effective_user.username or f"user_{str(update.effective_user.id)}"
                }
                posts_collection_ref.add(post_data)
        except Exception as e:
            await query.edit_message_text(f"❌ Не удалось опубликовать. Ошибка: {e}", reply_markup=None)
    else: # 'cancel'
        await query.edit_message_text("❌ Генерация поста отменена.", reply_markup=None)
    context.user_data.clear()

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает неизвестные команды и обычные сообщения.
    """
    message_text = update.message.text
    await register_user_and_save_message(update, message_text)

    if message_text.startswith('/'):
        await update.message.reply_text("Извините, я не знаю такой команды. Используйте /help для списка команд.")
        return
    
    try:
        # Анализируем сообщение на токсичность
        analysis_result = analyze_message(message_text)
        
        is_toxic = analysis_result.get("is_toxic", False)
        toxicity_score = analysis_result.get("toxicity_score", 0)

        # Если сообщение токсично и оценка выше порога (7), предупреждаем
        if is_toxic and toxicity_score >= 7:
            reason = analysis_result.get('reason', 'Ваше сообщение может нарушать правила.')
            await update.message.reply_text(f"⚠️ **Внимание:** {reason} Пожалуйста, будьте вежливы и уважительны.", parse_mode='Markdown')
            return
        
        # Если это похоже на вопрос, пытаемся ответить
        if "?" in message_text or any(word in message_text.lower() for word in ["как", "что", "где", "когда", "почему", "помоги", "подскажи"]):
            answer = answer_question(message_text)
            await update.message.reply_text(f"💡 **Ответ:**\n\n{answer}", parse_mode='Markdown')
            return
        
        # Если это обычное сообщение, просто подтверждаем получение
        await update.message.reply_text("✅ Сообщение получено и обработано. Спасибо за активность в сообществе!")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await update.message.reply_text("✅ Сообщение получено. Спасибо за активность в сообществе!")

def main() -> None:
    """Запускает бота."""
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN не найден в .env файле.")
        return
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("generate", generate_start))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("rating", rating_command))
    application.add_handler(CommandHandler("ask", ask_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CallbackQueryHandler(confirm_publish))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("Бот запущен. Ожидание сообщений...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()