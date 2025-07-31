import os
import requests
import json
import time
import uuid
import base64 # Добавлен импорт base64
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем учетные данные GigaChat из переменных окружения
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

# ИСПРАВЛЕНИЕ: Проверка обязательных переменных окружения
if not GIGACHAT_CLIENT_ID or not GIGACHAT_CLIENT_SECRET:
    raise ValueError("GIGACHAT_CLIENT_ID и GIGACHAT_CLIENT_SECRET должны быть установлены в переменных окружения.")

# Путь к файлу для кэширования токена
TOKEN_CACHE_FILE = "gigachat_token_cache.json"

def get_gigachat_access_token():
    """
    Получает или обновляет токен доступа GigaChat, используя кэширование.
    """
    current_time = time.time()

    # Проверяем, существует ли кэш-файл и содержит ли он действительный токен
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, 'r') as f:
            try:
                cache_data = json.load(f)
                access_token = cache_data.get("access_token")
                expires_at = cache_data.get("expires_at")

                if access_token and expires_at and current_time < expires_at:
                    print("Используем кэшированный токен GigaChat.")
                    return access_token
            except json.JSONDecodeError:
                # Файл поврежден, сгенерируем новый токен
                pass

    print("Получаем новый токен GigaChat...")
    # URL для получения токена
    token_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    print(f"Попытка запроса токена к URL: {token_url}")

    # Формируем строку client_id:client_secret и кодируем ее в Base64
    credentials_str = f"{GIGACHAT_CLIENT_ID}:{GIGACHAT_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials_str.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {encoded_credentials}" # Используем Base64-кодированные credentials
    }

    payload = {
        "scope": GIGACHAT_SCOPE
    }

    try:
        # verify=False для обхода проблем с SSL-сертификатами, в продакшене рекомендуется True
        response = requests.post(token_url, headers=headers, data=payload, verify=False)
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data.get("access_token")
        # GigaChat API возвращает expires_at в формате timestamp Unix (количество секунд с эпохи)
        # Если API вдруг начнет возвращать expires_in (секунды до истечения), нужно будет добавить:
        # expires_at = current_time + token_data.get("expires_in") - 60 # для запаса
        expires_at = token_data.get("expires_at")


        if access_token and expires_at:
            with open(TOKEN_CACHE_FILE, 'w') as f:
                json.dump({"access_token": access_token, "expires_at": expires_at}, f)
            print("Токен GigaChat успешно получен и кэширован.")
            return access_token
        else:
            raise ValueError("Не удалось получить access_token или expires_at из ответа GigaChat API.")

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе токена GigaChat: {e}")
        print(f"Ответ сервера: {response.text if 'response' in locals() else 'Нет ответа'}")
        raise
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")
        raise

if __name__ == "__main__":
    try:
        token = get_gigachat_access_token()
        print(f"Полученный токен (первые 10 символов): {token[:10]}...")
    except Exception as e:
        print(f"Не удалось получить токен: {e}")