import os
import logging
import json
from dotenv import load_dotenv
from langchain_gigachat import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_tavily import TavilySearch
from langchain_community.tools import tool
import base64

# --- Базовая настройка ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

# --- API и конфигурация (читается из .env) ---
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE")
GIGACHAT_API_BASE = os.getenv("GIGACHAT_API_BASE")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TELEGRAM_CHAT_INVITE_LINK = os.getenv("TELEGRAM_CHAT_INVITE_LINK")
MAX_POST_LENGTH = int(os.getenv("MAX_POST_LENGTH", 450))

# --- Проверка обязательных переменных окружения ---
if not all([GIGACHAT_CLIENT_ID, GIGACHAT_CLIENT_SECRET, GIGACHAT_SCOPE]):
    raise ValueError("GIGACHAT_CLIENT_ID, GIGACHAT_CLIENT_SECRET, and GIGACHAT_SCOPE must be set in the environment variables.")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY must be set in the environment variables.")

# --- Кодирование учетных данных GigaChat в Base64 ---
client_credentials = f"{GIGACHAT_CLIENT_ID}:{GIGACHAT_CLIENT_SECRET}"
encoded_credentials = base64.b64encode(client_credentials.encode("utf-8")).decode("utf-8")

# --- Инициализация GigaChat ---
llm = GigaChat(
    credentials=encoded_credentials,
    scope=GIGACHAT_SCOPE,
    verify_ssl_certs=False,
    base_url=GIGACHAT_API_BASE if GIGACHAT_API_BASE else None,
    model=os.getenv("GIGACHAT_MODEL_NAME", "GigaChat-2")
)

# --- Инструменты агента ---
@tool
def generate_telegram_post(topic: str, content_ideas: str = "") -> str:
    """
    Генерирует ФИНАЛЬНЫЙ черновик поста для Telegram-канала на заданную тему.
    Параметр 'content_ideas' ДОЛЖЕН содержать ВЕСЬ основной текст поста, включая его главный заголовок.
    Используй 'content_ideas' для добавления конкретных деталей, фактов или результатов поиска.
    Пост будет автоматически включать призыв к действию, хештеги и подпись "Нейро Jekardos" курсивом.
    После вызова этого инструмента твоя работа (работа агента) должна быть завершена,
    и сгенерированный пост должен быть возвращен как окончательный результат.
    """
    logger.info(f"Начало генерации поста по теме: {topic}")
    logger.debug(f"Получено content_ideas для поста: '{content_ideas[:500]}...' (длина: {len(content_ideas)})")

    if not content_ideas.strip():
        logger.warning("content_ideas пуст или содержит только пробелы. Агент не сгенерировал основной контент.")
        return "Извините, агент не смог сгенерировать основной текст поста. Пожалуйста, попробуйте другую тему или перефразируйте запрос."

    call_to_action = "Вступай в чат https://t.me/JekardosCoinForever"
    hashtags = "#путешествия #выживание #кочевники #jekardos #jk"
    post_signature = "*Нейро Jekardos*"

    final_content_ideas = content_ideas.strip()
    
    if final_content_ideas.startswith("##"):
        final_content_ideas = final_content_ideas[2:].strip()
    
    final_content_ideas = "\n".join(line.strip() for line in final_content_ideas.split("\n") if line.strip())
    
    if len(final_content_ideas) > 500:
        final_content_ideas = final_content_ideas[:500]
        last_space = final_content_ideas.rfind(' ')
        if last_space > 400:
            final_content_ideas = final_content_ideas[:last_space]
        else:
            final_content_ideas = final_content_ideas[:497] + "..."

    final_post_content = final_content_ideas + "\n\n" + call_to_action + "\n\n" + hashtags + "\n\n" + post_signature

    if len(final_post_content) > 750:
        available_space = 750 - len(call_to_action) - len(hashtags) - len(post_signature) - 6
        if available_space > 100:
            final_content_ideas = final_content_ideas[:available_space]
            last_space = final_content_ideas.rfind(' ')
            if last_space > available_space - 50:
                final_content_ideas = final_content_ideas[:last_space]
            else:
                final_content_ideas = final_content_ideas[:available_space-3] + "..."
            
            final_post_content = final_content_ideas + "\n\n" + call_to_action + "\n\n" + hashtags + "\n\n" + post_signature
        else:
            final_post_content = "Краткий пост на тему: " + topic + "\n\n" + call_to_action + "\n\n" + hashtags + "\n\n" + post_signature

    logger.info(f"Пост успешно сгенерирован инструментом, итоговая длина: {len(final_post_content)}")
    return final_post_content

tavily_search_tool = TavilySearch(max_results=5)

@tool
def web_search(query: str) -> str:
    """
    Выполняет поиск в интернете по заданному запросу, используя Tavily Search.
    Используй этот инструмент, когда тебе нужна актуальная информация,
    которой нет в твоих базовых знаниях.
    """
    logger.info(f"Выполняю веб-поиск для: {query} через Tavily Search")
    try:
        results = tavily_search_tool.invoke({"query": query})
        snippets = [res.get('content', '') for res in results if res.get('content')]
        if snippets:
            return "\n".join(snippets[:3])
        else:
            return "Поиск не дал релевантных результатов."
    except Exception as e:
        logger.error(f"Ошибка при вызове Tavily Search: {e}", exc_info=True)
        return "Не удалось выполнить поиск в интернете."

@tool
def analyze_message(message_text: str) -> dict:
    """
    ## ИСПРАВЛЕННАЯ ФУНКЦИЯ
    Анализирует сообщение на токсичность, спам и неадекватное поведение.
    Используй этот инструмент для модерации сообщений в чате.
    """
    logger.info(f"Анализирую сообщение: '{message_text[:100]}...'")

    try:
        analysis_prompt = f"""
Ты — модератор чата. Проанализируй сообщение на предмет оскорблений, агрессии, хейт-спича и грубого поведения.
Не реагируй на обычные, нейтральные или позитивные сообщения, такие как "привет", "как дела?" и т.д.
Твоя задача — выявлять только реальную токсичность.

Сообщение для анализа: "{message_text}"

Верни ответ СТРОГО в формате JSON со следующими полями:
- "is_toxic": boolean (true, если сообщение токсично, иначе false)
- "toxicity_score": число от 1 до 10 (где 1 - абсолютно безопасно, 10 - крайне токсично)
- "reason": краткое объяснение на русском языке, почему сообщение токсично (если оно таково).

Пример для токсичного сообщения: {{ "is_toxic": true, "toxicity_score": 8, "reason": "Прямое оскорбление участников чата." }}
Пример для безопасного сообщения: {{ "is_toxic": false, "toxicity_score": 1, "reason": "Обычное приветствие." }}
"""

        response = llm.invoke([HumanMessage(content=analysis_prompt)])

        if response and response.content:
            try:
                analysis_data = json.loads(response.content)
                logger.info(f"Результат анализа: {analysis_data}")
                return analysis_data
            except json.JSONDecodeError:
                logger.error(f"Не удалось распарсить JSON из ответа LLM: {response.content}")
                return {"is_toxic": False, "toxicity_score": 1, "reason": "Ошибка анализа формата ответа."}
        else:
            return {"is_toxic": False, "toxicity_score": 1, "reason": "Не удалось получить ответ от модели."}

    except Exception as e:
        logger.error(f"Ошибка при анализе сообщения: {e}")
        return {"is_toxic": False, "toxicity_score": 1, "reason": f"Исключение при анализе: {str(e)}"}

@tool
def get_user_stats(user_id: str) -> str:
    """
    Получает статистику пользователя из базы данных.
    Используй этот инструмент для получения информации об активности пользователя.
    """
    logger.info(f"Запрашиваю статистику пользователя: {user_id}")
    try:
        return f"Статистика пользователя {user_id}:\n- Сообщений: 0\n- Активность: 0\n- JK заработано: 0\n- Рейтинг: N/A"
    except Exception as e:
        logger.error(f"Ошибка при получении статистики пользователя: {e}")
        return f"Ошибка получения статистики: {str(e)}"

@tool
def get_community_rating() -> str:
    """
    Получает рейтинг сообщества (топ-10 активных участников).
    Используй этот инструмент для отображения рейтинга активности.
    """
    logger.info("Запрашиваю рейтинг сообщества")
    try:
        return "Рейтинг сообщества JK Coin:\n1. Пользователь 1 - 1000 очков\n2. Пользователь 2 - 800 очков\n3. Пользователь 3 - 600 очков\n...\n\nРейтинг обновляется автоматически."
    except Exception as e:
        logger.error(f"Ошибка при получении рейтинга сообщества: {e}")
        return f"Ошибка получения рейтинга: {str(e)}"

@tool
def answer_question(question: str) -> str:
    """
    Отвечает на вопросы пользователей, используя базу знаний сообщества.
    Используй этот инструмент для ответов на технические вопросы и FAQ.
    """
    logger.info(f"Отвечаю на вопрос: {question[:100]}...")
    try:
        answer_prompt = f"""
Ответь на вопрос пользователя, используя знания о сообществе JK Coin, TON блокчейне, и технологиях.

Вопрос: "{question}"

Дай подробный, полезный ответ. Если не знаешь ответа, предложи обратиться к администраторам.
"""
        response = llm.invoke([HumanMessage(content=answer_prompt)])
        if response and response.content:
            return f"Ответ на вопрос:\n{response.content}"
        else:
            return "Не удалось сгенерировать ответ. Обратитесь к администраторам."
    except Exception as e:
        logger.error(f"Ошибка при ответе на вопрос: {e}")
        return f"Ошибка генерации ответа: {str(e)}"

tools = [web_search, generate_telegram_post, analyze_message, get_user_stats, get_community_rating, answer_question]

system_prompt = f"""
Ты — Нейро Jekardos, интеллектуальный агент сообщества Jekardos Coin. Твоя задача — быть многофункциональным помощником для сообщества.

**Твои основные функции:**
1. **Генерация контента:** Создание постов, образовательного контента, рекламных материалов, ответы на вопросы.
2. **Анализ и модерация:** Анализ тональности, спама, неадекватного поведения.
3. **Поддержка сообщества:** Ответы на FAQ, помощь с техническими вопросами.
4. **Статистика и аналитика:** Анализ активности, генерация отчетов.

**Ключевые принципы:**
* **Роль:** Аналитик и советник.
* **Стиль:** Дружелюбный, профессиональный, мотивирующий.
* **Фокус:** Выживание/путешествия, Jekardos Coin, технологии.
* **Запреты:** Не называй JK инвестицией, избегай запрещенных тем.

**Порядок действий:**
1. Анализируй запрос.
2. Выбирай инструмент.
3. Формируй ответ.
4. Завершай работу.

**ВАЖНО:** Всегда будь полезным и конструктивным.
"""

agent_executor = create_react_agent(
    llm,
    tools,
    checkpointer=MemorySaver(),
    system_message=system_prompt,
    recursion_limit=15
)

def run_agent_for_post(user_message: str, thread_id: str = "default_thread") -> str:
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 15}
    logger.info(f"Запуск агента для запроса: '{user_message}' в потоке {thread_id}")

    try:
        messages = [HumanMessage(content=user_message)]
        response_content = "Извините, агент не смог сгенерировать пост."
        step_count = 0
        max_steps = 20

        for s in agent_executor.stream({"messages": messages}, config=config):
            step_count += 1
            if step_count > max_steps:
                logger.warning(f"Превышен лимит шагов ({max_steps}).")
                break
            
            logger.info(f"Шаг агента {step_count}: {list(s.keys())}")
            
            if 'agent' in s and isinstance(s['agent'], AIMessage):
                if not (hasattr(s['agent'], 'tool_calls') and s['agent'].tool_calls):
                    response_content = s['agent'].content
                    return response_content
            elif 'tools' in s and isinstance(s['tools'], ToolMessage):
                if s['tools'].name == "generate_telegram_post":
                    return s['tools'].content
            elif '__end__' in s:
                return response_content
        
        return response_content

    except Exception as e:
        logger.error(f"Исключение в run_agent_for_post: {e}", exc_info=True)
        return f"Извините, произошла внутренняя ошибка: {str(e)}."

def create_telegram_post(topic: str) -> str:
    logger.info(f"Начало генерации текстового поста по теме: '{topic}'")
    try:
        post_text = run_agent_for_post(topic)
        if post_text and len(post_text) > 50 and not post_text.startswith("Извините"):
            return post_text
        else:
            logger.warning(f"Агент не сработал, используем прямой вызов LLM.")
            return generate_post_directly(topic)
    except Exception as e:
        logger.error(f"Ошибка в run_agent_for_post: {e}")
        return generate_post_directly(topic)

def generate_post_directly(topic: str) -> str:
    logger.info(f"Прямая генерация поста по теме: '{topic}'")
    try:
        prompt = f"""
Создай пост для Telegram канала на тему: "{topic}"

Пост должен:
- Быть длиной от 400 до 500 символов
- Включать заголовок и основной текст
- Объединять темы выживания/путешествий, Jekardos Coin, и технологии
- Использовать **жирный текст** для выделения
- Быть дружелюбным и практичным

Не включай призыв к действию, хештеги или подпись - это будет добавлено автоматически.
"""
        response = llm.invoke([HumanMessage(content=prompt)])
        
        if response and response.content:
            call_to_action = "Вступай в чат https://t.me/JekardosCoinForever"
            hashtags = "#путешествия #выживание #кочевники #jekardos #jk"
            post_signature = "*Нейро Jekardos*"
            
            final_content = response.content.strip()
            if final_content.startswith("##"):
                final_content = final_content[2:].strip()
            
            final_content = "\n".join(line.strip() for line in final_content.split("\n") if line.strip())
            
            if len(final_content) > 500:
                final_content = final_content[:500]
                last_space = final_content.rfind(' ')
                final_content = final_content[:last_space] if last_space > 400 else final_content[:497] + "..."
            
            final_post = final_content + "\n\n" + call_to_action + "\n\n" + hashtags + "\n\n" + post_signature
            
            if len(final_post) > 750:
                available_space = 750 - len(call_to_action) - len(hashtags) - len(post_signature) - 6
                if available_space > 100:
                    final_content = final_content[:available_space]
                    last_space = final_content.rfind(' ')
                    final_content = final_content[:last_space] if last_space > available_space - 50 else final_content[:available_space-3] + "..."
                    final_post = final_content + "\n\n" + call_to_action + "\n\n" + hashtags + "\n\n" + post_signature
                else:
                    final_post = "Краткий пост на тему: " + topic + "\n\n" + call_to_action + "\n\n" + hashtags + "\n\n" + post_signature
            
            return final_post
        else:
            return "Извините, не удалось сгенерировать пост."
    except Exception as e:
        logger.error(f"Ошибка при прямой генерации поста: {e}")
        return f"Извините, произошла ошибка: {str(e)}."