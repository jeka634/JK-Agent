import os
from dotenv import load_dotenv
# ИСПРАВЛЕНИЕ: НОВАЯ, КОРРЕКТНАЯ СТРОКА ИМПОРТА GigaChat
from langchain_gigachat import GigaChat

from auth_gigachat import get_gigachat_access_token

# Загружаем переменные окружения
load_dotenv()

class GigaChatLLM:
    def __init__(self):
        self.model_name = os.getenv("GIGACHAT_MODEL_NAME", "GigaChat-2")
        self.scope = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
        self.llm = self._initialize_gigachat()

    def _initialize_gigachat(self):
        """
        Инициализирует объект GigaChat с актуальным токеном.
        """
        access_token = get_gigachat_access_token()
        # ИСПРАВЛЕНИЕ: Используем GigaChat с правильными параметрами
        return GigaChat(
            access_token=access_token,
            model=self.model_name,
            scope=self.scope,
            verify_ssl_certs=False
        )

    def get_llm(self):
        """
        Возвращает инициализированную модель GigaChat.
        """
        return self.llm

    def refresh_token_and_reinitialize(self):
        """
        Обновляет токен и повторно инициализирует модель GigaChat.
        Вызывается, если текущий токен истек.
        """
        print("Токен GigaChat мог истечь, переинициализируем модель.")
        # Удаляем кэшированный токен, чтобы get_gigachat_access_token гарантированно получил новый
        if os.path.exists("gigachat_token_cache.json"):
            os.remove("gigachat_token_cache.json")
            print("Кэшированный токен удален.")
        self.llm = self._initialize_gigachat()
        return self.llm

# Пример использования:
if __name__ == "__main__":
    gigachat_manager = GigaChatLLM()
    llm = gigachat_manager.get_llm()

    from langchain_core.messages import HumanMessage, AIMessage

    # Пример простого промпта
    messages = [
        HumanMessage(content="Привет! Как дела?"),
    ]

    print(f"Отправляем запрос к {gigachat_manager.model_name}...")
    try:
        response = llm.invoke(messages)
        print("Ответ GigaChat:")
        print(response.content)

        # Пример повторного вызова, чтобы убедиться, что токен работает
        messages_2 = [
            HumanMessage(content="Расскажи что-нибудь интересное о космосе."),
        ]
        response_2 = llm.invoke(messages_2)
        print("\nВторой ответ GigaChat:")
        print(response_2.content)

    except Exception as e:
        print(f"Произошла ошибка при вызове GigaChat: {e}")
        error_message = str(e)
        # Улучшенная проверка на истечение токена
        if "Authentication failed" in error_message or "invalid_token" in error_message or "Token has expired" in error_message or "401 Client Error" in error_message:
            print("Обнаружена ошибка аутентификации или истечения токена.")
            print("Попытка обновить токен и повторить запрос...")
            llm = gigachat_manager.refresh_token_and_reinitialize()
            try:
                response = llm.invoke(messages)
                print("\nОтвет GigaChat после обновления токена:")
                print(response.content)
            except Exception as e_retry:
                print(f"Повторная попытка после обновления токена также завершилась ошибкой: {e_retry}")
        else:
            print("Произошла неисправимая ошибка.")