#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы бота с новым функционалом
"""

import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def test_environment():
    """Тестирует переменные окружения"""
    print("🧪 Тестирование переменных окружения...")
    
    required_vars = ['TELEGRAM_BOT_TOKEN', 'GIGACHAT_CLIENT_ID', 'GIGACHAT_CLIENT_SECRET']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ Все необходимые переменные окружения установлены")
        return True

def test_post_generation():
    """Тестирует генерацию поста"""
    print("\n🧪 Тестирование генерации поста...")
    
    try:
        from agent_core import create_telegram_post
        
        # Тестовая тема
        test_topic = "подготовка к походу"
        
        print(f"Генерируем пост на тему: '{test_topic}'")
        
        # Генерируем пост
        post = create_telegram_post(test_topic)
        
        if post and len(post) > 50:
            print("✅ Пост успешно сгенерирован!")
            print(f"Длина поста: {len(post)} символов")
            return True
        else:
            print(f"❌ Агент не смог сгенерировать пост (ответ: '{post}')")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании генерации поста: {e}")
        return False

def test_message_analysis():
    """Тестирует анализ сообщений"""
    print("\n🧪 Тестирование анализа сообщений...")
    
    try:
        from agent_core import analyze_message
        
        # Тестовые сообщения
        test_messages = [
            "Привет всем! Как дела?",
            "Это спам реклама купите сейчас",
            "Как работает TON блокчейн?"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"Тест {i}: Анализируем сообщение: '{message[:30]}...'")
            analysis = analyze_message(message)
            
            if analysis and len(analysis) > 10:
                print(f"✅ Анализ успешен: {analysis[:100]}...")
            else:
                print(f"❌ Ошибка анализа для сообщения {i}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании анализа сообщений: {e}")
        return False

def test_question_answering():
    """Тестирует ответы на вопросы"""
    print("\n🧪 Тестирование ответов на вопросы...")
    
    try:
        from agent_core import answer_question
        
        # Тестовые вопросы
        test_questions = [
            "Что такое JK Coin?",
            "Как работает TON блокчейн?",
            "Какие преимущества у TON?"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"Тест {i}: Отвечаем на вопрос: '{question}'")
            answer = answer_question(question)
            
            if answer and len(answer) > 20:
                print(f"✅ Ответ получен: {answer[:100]}...")
            else:
                print(f"❌ Ошибка ответа для вопроса {i}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании ответов на вопросы: {e}")
        return False

def test_statistics():
    """Тестирует функции статистики"""
    print("\n🧪 Тестирование функций статистики...")
    
    try:
        from agent_core import get_user_stats, get_community_rating
        
        # Тестируем статистику пользователя
        print("Тестируем статистику пользователя...")
        user_stats = get_user_stats("test_user_123")
        if user_stats and "Статистика пользователя" in user_stats:
            print("✅ Статистика пользователя работает")
        else:
            print("❌ Ошибка статистики пользователя")
            return False
        
        # Тестируем рейтинг сообщества
        print("Тестируем рейтинг сообщества...")
        community_rating = get_community_rating()
        if community_rating and "Рейтинг сообщества" in community_rating:
            print("✅ Рейтинг сообщества работает")
        else:
            print("❌ Ошибка рейтинга сообщества")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании статистики: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование бота с новым функционалом\n")
    
    # Запускаем тесты
    tests = [
        test_environment,
        test_post_generation,
        test_message_analysis,
        test_question_answering,
        test_statistics
    ]
    
    results = []
    
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Ошибка в тесте {test.__name__}: {e}")
            results.append(False)
    
    print("\n" + "="*50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("🎉 Все тесты пройдены! Бот готов к работе с новым функционалом.")
        print("\nДля запуска бота используйте:")
        print("  python telegram_bot.py")
        print("\nДоступные команды:")
        print("  /help - Справка")
        print("  /generate [тема] - Создание поста")
        print("  /stats - Ваша статистика")
        print("  /rating - Рейтинг сообщества")
        print("  /ask [вопрос] - Задать вопрос")
        print("  /analyze [текст] - Анализ сообщения")
    else:
        print(f"⚠️  Пройдено {passed} из {total} тестов")
        print("\nИсправьте ошибки и запустите тест снова:")
        print("  python test_bot.py")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 