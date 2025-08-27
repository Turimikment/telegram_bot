import os
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# === Настройки ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
MODEL_NAME = "Qwen/Qwen2.5-1.8B-Instruct"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

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

# Запуск
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)