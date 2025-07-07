import asyncio
import json
import hashlib
import base64
import aiosqlite
import logging
import requests
from typing import Any
from aiohttp import ClientSession
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.methods import DeleteWebhook
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

# 🔑 ПОЛУЧЕНИЕ АПИ КЛЮЧЕЙ
TOKEN = '7913416215:AAFiE8uW_2ivaOTIJNPINPbJWTzwpslpF4Q'  # ТОКЕН БОТА
MERCHANT_UUID = "72286e95-aef4-498c-8c71-61e2952de92f"    # ID МЕРЧАНТА
API_KEY = ""                                              # ПЛАТЕЖНЫЙ API КЛЮЧ

logging.basicConfig(level=logging.INFO)
bot = Bot(TOKEN)
dp = Dispatcher()


# 📦 СОЗДАНИЕ БАЗЫ ДАННЫХ
async def init_db():
    async with aiosqlite.connect("base.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS main (user_id INTEGER PRIMARY KEY)""")
        await db.commit()


# 🔒 ФУНКЦИЯ СОЗДАНИЯ ПОДПИСИ ДЛЯ ПЛАТЕЖА
def generate_headers(data: str) -> dict[str, Any]:
    sign = hashlib.md5(base64.b64encode(data.encode("ascii")) + API_KEY.encode("ascii")).hexdigest()
    return {"merchant": MERCHANT_UUID, "sign": sign, "Content-Type": "application/json"}


# 🛒 ОБРАБОТЧИК КНОПКИ СОЗДАНИЯ ПЛАТЕЖА
@dp.callback_query(F.data == "create_invoice")
async def create_invoice(callback: types.CallbackQuery):
    await callback.answer()
    async with ClientSession() as session:
        json_dumps = json.dumps({
            "amount": "1",
            "currency": "TON",
            "order_id": f"test-{callback.from_user.id}-02",
        })
        response = await session.post(
            "https://api.heleket.com/v1/payment",
            headers=generate_headers(json_dumps),
            data=json_dumps
        )
        invoice = await response.json()

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="🔎 Проверить оплату",
            callback_data=f"check_invoice_{invoice['result']['uuid']}"
        )
    )
    await callback.message.answer(f"Ссылка на оплату: {invoice['result']['url']}", parse_mode='HTML', reply_markup=builder.as_markup())


# 🔍 ОБРАБОТЧИК ПРОВЕРКИ ПЛАТЕЖА
@dp.callback_query(F.data.startswith("check_invoice_"))
async def check_invoice(callback: types.CallbackQuery):
    await callback.answer()
    async with ClientSession() as session:
        json_dumps = json.dumps({"uuid": callback.data.split("_")[2]})
        response = await session.post(
            "https://api.heleket.com/v1/payment/info",
            headers=generate_headers(json_dumps),
            data=json_dumps
        )
        invoice = await response.json()

    if invoice["result"]["status"] == "paid":
        async with aiosqlite.connect("base.db") as db:
            await db.execute("INSERT OR IGNORE INTO main (user_id) VALUES (?)", (callback.from_user.id,))
            await db.commit()
        await callback.message.answer("✅ Оплата прошла успешно! Теперь вы можете пользоваться ботом.", parse_mode='HTML')
    else:
        await callback.message.answer("⏳ Счет пока не оплачен. Попробуйте позже.", parse_mode='HTML')


# 🎟️ ОБРАБОТЧИК КОМАНДЫ СТАРТ
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🛒 Подписка", callback_data="create_invoice"),
        types.InlineKeyboardButton(text="🎟️ Ввести промокод", callback_data="enter_promocode")
    )
    await message.answer(
        "📰 Чтобы пользоваться ботом, необходимо оформить подписку или ввести промокод.",
        parse_mode='HTML',
        reply_markup=builder.as_markup()
    )


# 🎫 ОБРАБОТЧИК КНОПКИ ПРОМОКОДА
@dp.callback_query(F.data == "enter_promocode")
async def ask_promocode(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("Введите промокод одним сообщением:")


# 📩 ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ
@dp.message(lambda message: message.text)
async def handle_messages(message: Message):
    async with aiosqlite.connect("base.db") as db:
        cursor = await db.execute("SELECT user_id FROM main WHERE user_id = ?", (message.from_user.id,))
        user = await cursor.fetchone()

    # Если пользователь есть в базе, разрешаем использовать бота
    if user:
        await handle_ai_query(message)
        return

    # Проверяем промокод
    if message.text.strip().upper() == "GFR-2025":
        async with aiosqlite.connect("base.db") as db:
            await db.execute("INSERT OR IGNORE INTO main (user_id) VALUES (?)", (message.from_user.id,))
            await db.commit()
        await message.answer("🎉 Промокод активирован! У вас теперь безлимитный доступ к боту.")
        return

    # Если не подписчик и не ввел правильный промокод, предлагаем подписку
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🛒 Подписка", callback_data="create_invoice"),
        types.InlineKeyboardButton(text="🎟️ Ввести промокод", callback_data="enter_promocode")
    )
    await message.answer(
        "❌ У вас нет активной подписки. Для доступа оплатите подписку или введите действующий промокод.",
        reply_markup=builder.as_markup()
    )


# 🔥 ФУНКЦИЯ ЗАПРОСА К НЕЙРОСЕТИ
async def handle_ai_query(message: Message):
    url = "https://api.intelligence.io.solutions/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer io-v2-eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJvd25lciI6Ijg2NTAyY2Q1LTJiYjEtNGUwOS05NDE4LTgyMGY3NmU0MDNiNiIsImV4cCI6NDkwNDk1NTk5NX0.ewq1ZHcwRYnq35nUA4nKBpBpUhBZQ-EMnxsm1zcD4hyl7TGWhd70ikdQGKnCmMsdOWunAgHFDX3878pLpT2QJw"
    }

    

    payload = {
        "model": "meta-llama/Llama-3.3-70B-Instruct",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": message.text}
        ],
    }



    try:
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        if 'choices' in data and isinstance(data['choices'], list) and data['choices']:
            raw_text = data['choices'][0]['message']['content']
            bot_text = raw_text.split('</think>\n\n')[1] if '</think>\n\n' in raw_text else raw_text
            await message.answer(bot_text.strip(), parse_mode="Markdown")
        else:
            await message.answer("⚠️ Ответ от нейросети был неожиданным. Попробуйте снова позже.")
            print(data)

    except Exception as e:
        logging.error(f"Ошибка при обращении к API: {e}")
        await message.answer("❌ Ошибка при запросе к нейросети. Попробуйте позже.")


# 🚀 ЗАПУСК БОТА
async def main():
    await init_db()
    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
