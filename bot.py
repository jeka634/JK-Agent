import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ИСПРАВЛЕНИЕ: Импортируем create_telegram_post из agent_core
from agent_core import create_telegram_post
from langchain_core.messages import HumanMessage

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен Telegram бота из .env файла
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Проверяем наличие токена
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не найден в .env файле. Пожалуйста, добавьте его.")
    exit(1)

# --- Обработчики команд и сообщений ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start."""
    user = update.effective_user
    await update.message.reply_html(
        f"Привет, {user.mention_html()}! Я ИИ-агент, работающий на GigaChat. Задайте мне вопрос, и я постараюсь ответить."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /help."""
    await update.message.reply_text("Просто отправьте мне сообщение, и я сгенерирую ответ с помощью GigaChat.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения и передает их агенту LangGraph."""
    user_message = update.message.text
    logger.info(f"Получено сообщение от {update.effective_user.username}: {user_message}")

    await update.message.reply_text("Думаю над вашим запросом...")

    try:
        # ИСПРАВЛЕНИЕ: Используем run_agent_for_post напрямую
        agent_response_content = create_telegram_post(user_message)
        logger.info(f"Ответ агента: {agent_response_content}")

        # Отправляем ответ пользователю Telegram
        await update.message.reply_text(agent_response_content)

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
        )

def main() -> None:
    """Запускает бота."""
    # Создаем Application и передаем токен бота
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота (он будет ждать обновлений)
    logger.info("Бот запущен. Ожидание сообщений...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()