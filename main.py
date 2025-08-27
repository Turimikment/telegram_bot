import os
import requests
from aiogram import Bot, Dispatcher, types

# === Настройки ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
MODEL_NAME = "Qwen/Qwen2.5-1.8B-Instruct"

# URL для Inference API
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Простая история диалога (на случай, если нужно)
user_conversations = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    user_conversations[message.from_user.id] = [
        {
            "role": "system",
            "content": "Ты — заказчик системы. Ты хочешь создать онлайн-школу для системного анализа. "
                      "Отвечай как реальный человек: не идеально, но по делу. Говори кратко — 1–2 предложения."
        }
    ]
    await message.answer(
        "👋 Привет! Я — виртуальный заказчик.\n"
        "Задавай мне вопросы о системе, которую я хочу создать.\n\n"
        "Например:\n"
        "- Кто пользователи?\n"
        "- Какие функции нужны?\n"
        "- Есть ли ограничения?\n\n"
        "Я отвечу, как настоящий клиент!"
    )

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id

    # Инициализация истории
    if user_id not in user_conversations:
        user_conversations[user_id] = [
            {
                "role": "system",
                "content": "Ты — заказчик системы. Ты хочешь создать онлайн-школу для системного анализа. "
                          "Отвечай как реальный человек: не идеально, но по делу. Говори кратко — 1–2 предложения."
            }
        ]

    # Добавляем сообщение пользователя
    user_conversations[user_id].append({"role": "user", "content": message.text})

    try:
        # Отправляем весь диалог в модель
        response = requests.post(
            API_URL,
            headers=headers,
            json={
                "inputs": user_conversations[user_id][-10:],  # Ограничиваем контекст
                "parameters": {
                    "max_new_tokens": 200,
                    "temperature": 0.7,
                    "return_full_text": False
                }
            }
        )

        if response.status_code == 200:
            answer = response.json()[0]["generated_text"]
            # Сохраняем ответ
            user_conversations[user_id].append({"role": "assistant", "content": answer})
            await message.answer(answer)
        else:
            # Если ошибка — пробуем краткий ответ
            await message.answer("Сейчас не могу ответить. Попробуйте позже.")
            print("Ошибка Hugging Face:", response.status_code, response.text)

    except Exception as e:
        await message.answer("Произошла ошибка. Повторите запрос.")
        print("Exception:", e)

# Запуск
async def main():
    await dp.start_polling(bot)