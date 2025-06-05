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
ALLOWED_USERS = os.environ.get('ALLOWED_USERS', '').split(',')

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

                    for user_id in ALLOWED_USERS:
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

# === Обработка команд бота ===
@bot.message_handler(commands=['start', 'плащ'])
def send_welcome(message):
    if str(message.chat.id) not in ALLOWED_USERS:
        return
    bot.reply_to(message, "Привет! Бот будет присылать тебе новые плащи, как только они появятся!")

@bot.message_handler(commands=['ping'])
def ping_command(message):
    if str(message.chat.id) not in ALLOWED_USERS:
        return
    bot.send_message(message.chat.id, "🏓 Pong!")

# === Простой HTTP-сервер для Render ===
PORT = int(os.environ.get("PORT", 8000))

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
