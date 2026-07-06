# services/telegram-bot/main.py
import json
import os
import pika
import threading
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import httpx
from telegram.request import HTTPXRequest

# ===== ПРОКСИ =====
PROXY_HOST = "127.0.0.1"  # ← на VPS прокси слушает на localhost
PROXY_PORT = 1080
proxy_url = f"socks5://{PROXY_HOST}:{PROXY_PORT}"
transport = httpx.AsyncHTTPTransport(proxy=proxy_url)

# === Настройки ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not set")

CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")


# === Telegram Bot ===
def setup_bot():
    """Настройка Telegram бота с прокси"""
    # Создаем request с прокси
    request = HTTPXRequest(transport=transport)

    app = Application.builder().token(TELEGRAM_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("chatid", chatid_command))
    return app


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Привет! Я бот для уведомлений о заявках на ремонт.\n\n"
        "Я буду присылать уведомления о новых заявках и их удалениях.\n"
        "Используй /help для списка команд."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 Доступные команды:\n"
        "/start — приветствие\n"
        "/help — эта справка\n\n"
        "Уведомления приходят автоматически при создании или удалении заявок."
    )


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"🆔 Your chat ID: <code>{chat_id}</code>", parse_mode="Markdown"
    )


# === Отправка уведомлений ===
async def send_notification_created(data: dict):
    bot = Bot(token=TELEGRAM_TOKEN)
    message = (
        f"🆕 **Новая заявка на ремонт!**\n\n"
        f"📌 **ID:** {data.get('id')}\n"
        f"🔧 **Техника:** {data.get('vehicle_name')}\n"
        f"👤 **Клиент:** {data.get('client_name')}\n"
        f"📝 **Описание:** {data.get('description')}\n"
        f"👨‍💻 **Создал:** {data.get('created_by')}"
    )
    chat_id = CHAT_ID or data.get("chat_id")
    if chat_id:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        print(f"✅ Message sent to {chat_id}", flush=True)
    else:
        print(f"📨 Would send: {message}", flush=True)


async def send_notification_deleted(data: dict):
    bot = Bot(token=TELEGRAM_TOKEN)
    message = (
        f"🗑️ **Заявка удалена!**\n\n"
        f"📌 **ID:** {data.get('id')}\n"
        f"🔧 **Техника:** {data.get('vehicle_name')}\n"
        f"👨‍💻 **Удалил:** {data.get('deleted_by')}"
    )
    chat_id = CHAT_ID or data.get("chat_id")
    if chat_id:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        print(f"✅ Message sent to {chat_id}", flush=True)
    else:
        print(f"📨 Would send: {message}", flush=True)


# === RabbitMQ Consumer ===
def callback(ch, method, properties, body):
    try:
        message = json.loads(body.decode())
        event_type = message.get("event_type")
        data = message.get("data", {})

        print(f"📨 Received event: {event_type}", flush=True)

        if event_type == "repair_request.created":
            asyncio.run(send_notification_created(data))
        elif event_type == "repair_request.deleted":
            asyncio.run(send_notification_deleted(data))
        else:
            print(f"⚠️ Unknown event type: {event_type}", flush=True)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"❌ Error processing message: {e}", flush=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def consume():
    print("🐇 Starting RabbitMQ consumer...", flush=True)

    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue="repair_events", durable=True)
    channel.basic_consume(
        queue="repair_events", on_message_callback=callback, auto_ack=False
    )

    print("✅ Listening for events...", flush=True)
    channel.start_consuming()


# === Main ===
if __name__ == "__main__":
    consumer_thread = threading.Thread(target=consume, daemon=True)
    consumer_thread.start()

    print("✅ Starting Telegram bot...", flush=True)
    bot_app = setup_bot()
    bot_app.run_polling()
