#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой Telegram AI-бот (один файл).
Работает через API: https://api.llm7.io/v1 (модель gpt-o3-2025-04-16).
Автор: сгенерировано ChatGPT.
"""

import asyncio
import logging
from typing import Dict

import aiohttp
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ----------------- ВАШИ КЛЮЧИ (УЖЕ ПОДСТАВЛЕНЫ) -----------------
TELEGRAM_TOKEN = "7353263632:AAFgnB3tgRaGitA_Grk05iQ92suyRPNihxM"
AI_API_KEY = "lqSlhzkltuZRT78PW9mT+UhR+9Y/2UcXB3YUqcMrDHvwjIxcnRJ+tP/B8t1Hgh4oHiWx72cFcoDERXz2oPF1GHFFisQ2Q/tg5VNQYfRo7oi/QcPat6jF/RgYTqhq2lMLiydsI1o="
AI_ENDPOINT = "https://api.llm7.io/v1"
AI_MODEL = "gpt-o3-2025-04-16"
# ----------------------------------------------------------------

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Простейший rate-limiter по пользователю (секунды между запросами)
USER_LAST_CALL: Dict[int, float] = {}
MIN_INTERVAL = 1.0


async def call_ai_api(prompt: str, system_prompt: str = "You are a helpful assistant that answers in Russian.") -> str:
    """
    Универсальная отправка запроса к /chat/completions.
    Возвращает строку ответа или сообщение об ошибке.
    """
    url = f"{AI_ENDPOINT}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 800,
        "temperature": 0.7
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=60) as resp:
                text = await resp.text()
                if resp.status != 200:
                    logger.error("AI API error %s: %s", resp.status, text)
                    return f"Ошибка от AI (status {resp.status})."
                data = await resp.json()
    except Exception as e:
        logger.exception("Ошибка при запросе к AI:")
        return f"Ошибка при обращении к AI: {e}"

    # Пытаемся извлечь текст из популярных полей
    try:
        choices = data.get("choices")
        if choices and isinstance(choices, list):
            first = choices[0]
            if isinstance(first, dict):
                # формат: {"message": {"content": "..."}}
                if "message" in first and isinstance(first["message"], dict) and "content" in first["message"]:
                    return first["message"]["content"].strip()
                # формат: {"text": "..."}
                if "text" in first:
                    return first["text"].strip()
        # fallback: если нет ожидаемой структуры
        return str(data)
    except Exception as e:
        logger.exception("Ошибка парсинга ответа AI:")
        return f"Непредвиденный формат ответа AI: {e}"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я AI-бот. Отправь любое сообщение — я отвечу.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start — приветствие\n/help — эта подсказка\nПросто напиши сообщение и ждите ответ AI.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = asyncio.get_event_loop().time()
    last = USER_LAST_CALL.get(user_id, 0.0)
    if now - last < MIN_INTERVAL:
        await update.message.reply_text("Пожалуйста, подожди немного перед следующим сообщением.")
        return
    USER_LAST_CALL[user_id] = now

    text = update.message.text or ""
    if not text.strip():
        await update.message.reply_text("Пустое сообщение.")
        return

    # Показываем статус «печатает»
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Вызов AI
    reply = await call_ai_api(prompt=text)

    # Отправляем ответ (разделяем, если очень длинный)
    MAX_LEN = 4000
    if len(reply) <= MAX_LEN:
        await update.message.reply_text(reply)
    else:
        # Разбиваем на части по MAX_LEN
        for i in range(0, len(reply), MAX_LEN):
            await update.message.reply_text(reply[i:i+MAX_LEN])


def main():
    if not TELEGRAM_TOKEN or not AI_API_KEY:
        logger.error("TELEGRAM_TOKEN или AI_API_KEY не установлены.")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

    logger.info("Запускаем бота (long-polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
