import os
import requests
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from flask import Flask
import threading
import time

# === Настройки ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
MODEL_NAME = "Qwen/Qwen2.5-1.8B-Instruct"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# Создаем Flask приложение для веб-сервера
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает! 🚀"

@app.route('/health')
def health():
    return "OK", 200

# Храним диалоги
user_conversations = {}

# Создаём бота
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_conversations[message.from_user.id] = [
        {
            "role": "system",
            "content": "Ты — директор онлайн-школы. Ты хочешь создать систему для обучения системному анализу. "
                      "Отвечай как реальный заказчик: кратко, по делу, без технического жаргона. Максимум 2 предложения."
        }
    ]
    await message.answer(
        "👋 Здравствуйте!\n"
        "Я — виртуальный заказчик. Вы можете задавать мне вопросы, чтобы собрать требования к системе.\n\n"
        "Например:\n"
        "- Кто пользователи?\n"
        "- Какие функции нужны?\n"
        "- Есть ли ограничения по безопасности?\n\n"
        "Я отвечу, как настоящий клиент!"
    )

@dp.message_handler()
async def handle_message(message: types.Message):
    user_id = message.from_user.id

    # Инициализация
    if user_id not in user_conversations:
        user_conversations[user_id] = [
            {
                "role": "system",
                "content": "Ты — директор онлайн-школы. Ты хочешь создать систему для обучения системному анализу. "
                      "Отвечай как реальный заказчик: кратко, по делу, без технического жаргона. Максимум 2 предложения."
            }
        ]

    # Добавляем сообщение
    user_conversations[user_id].append({"role": "user", "content": message.text})

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json={
                "inputs": user_conversations[user_id][-6:],
                "parameters": {
                    "max_new_tokens": 200,
                    "temperature": 0.7,
                    "return_full_text": False
                }
            },
            timeout=30
        )

        if response.status_code == 200:
            answer = response.json()[0]["generated_text"]
            user_conversations[user_id].append({"role": "assistant", "content": answer})
            await message.answer(answer)
        elif response.status_code == 503:
            await message.answer("Сервис временно загружается. Подождите 10–20 секунд и повторите вопрос.")
        elif response.status_code == 429:
            await message.answer("Слишком много запросов. Подождите минуту.")
        else:
            await message.answer("Пока не могу ответить. Попробуйте позже.")

    except Exception as e:
        await message.answer("Ошибка соединения. Повторите запрос.")
        print("Ошибка:", e)

# Функция для запуска бота
def run_bot():
    # Создаем новый цикл событий для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Удаляем старые вебхуки перед запуском polling
    loop.run_until_complete(bot.delete_webhook())
    
    # Запускаем бота с повторными попытками
    max_retries = 5
    retry_delay = 10  # секунд
    
    for attempt in range(max_retries):
        try:
            print(f"Попытка запуска бота {attempt + 1}/{max_retries}")
            executor.start_polling(dp, skip_updates=True, relax=1)
            break
        except Exception as e:
            print(f"Ошибка при запуске бота: {e}")
            if attempt < max_retries - 1:
                print(f"Повторная попытка через {retry_delay} секунд...")
                time.sleep(retry_delay)
            else:
                print("Все попытки запуска провалились")

# Функция для запуска Flask
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Запуск и бота, и веб-сервера
if __name__ == '__main__':
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Даем время Flask запуститься
    time.sleep(3)
    
    # Запускаем бота в основном потоке
    run_bot()