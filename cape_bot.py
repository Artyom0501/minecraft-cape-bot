import telebot
import requests
import schedule
import time
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from bs4 import BeautifulSoup

# === Настройки из переменных окружения ===
TOKEN = os.environ.get('TELEGRAM_TOKEN')
ALLOWED_USERS = os.environ.get('ALLOWED_USERS', '')
PORT = int(os.environ.get("PORT", 8000))

# Обрабатываем список разрешённых ID
allowed_users = [uid.strip() for uid in ALLOWED_USERS.split(',') if uid.strip().isdigit()]

bot = telebot.TeleBot(TOKEN)
known_capes = set()  # Храним уже известные ссылки

# === Проверка новых плащей на Minecraft.net ===
def check_new_capes():
    global known_capes
    print("🔍 Проверка сайта Minecraft.net...")

    try:
        url = 'https://www.minecraft.net/ru-ru'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        articles = soup.find_all('a', class_='card')
        new_found = False

        for article in articles:
            title = article.get_text(strip=True)
            href = article.get('href')
            link = 'https://www.minecraft.net' + href if href.startswith('/') else href

            if any(word in title.lower() for word in ['плащ', 'cape', 'скин', 'подарок']):
                if link not in known_capes:
                    known_capes.add(link)
                    new_found = True

                    for user_id in allowed_users:
                        bot.send_message(
                            user_id,
                            f"🧥 Обнаружена новая статья:\n*{title}*\n{link}",
                            parse_mode="Markdown"
                        )

        if not new_found:
            print("Новых плащей не найдено.")
    except Exception as e:
        print("❌ Ошибка при проверке:", e)

# === Расписание: проверка каждые 30 минут ===
schedule.every(30).minutes.do(check_new_capes)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

# === Проверка доступа пользователя ===
def is_allowed(user_id):
    return str(user_id) in allowed_users

# === Обработка команд бота ===
@bot.message_handler(commands=['start', 'плащ'])
def send_welcome(message):
    if not is_allowed(message.chat.id):
        bot.reply_to(message, "⛔️ У вас нет доступа к этому боту.")
        print(f"👤 Запрос от неразрешённого пользователя: {message.chat.id}")
        return

    bot.reply_to(message, "Привет! Бот будет присылать тебе новые плащи, как только они появятся!")

@bot.message_handler(commands=['ping'])
def ping_command(message):
    if not is_allowed(message.chat.id):
        return
    bot.send_message(message.chat.id, "🏓 Pong!")

# === Логгирование всех чатов (чтобы находить новых пользователей) ===
@bot.message_handler(func=lambda message: True)
def any_message(message):
    print(f"👤 Новый пользователь: {message.chat.id} написал: {message.text}")

# === Простой HTTP-сервер для Render ===
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), SimpleHandler)
    print(f"🌐 HTTP-сервер запущен на порту {PORT}")
    server.serve_forever()

# === Запуск ===
threading.Thread(target=run_server, daemon=True).start()
threading.Thread(target=run_schedule, daemon=True).start()

bot.polling()
