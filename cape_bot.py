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
def check_new_capes(triggered_by_command=False, trigger_user_id=None):
    global known_capes
    try:
        print("🔍 [DEBUG] Начало парсинга Minecraft.net")

        url = 'https://www.minecraft.net/ru-ru'
        response = requests.get(url)
        print(f"🔍 [DEBUG] Ответ от сайта: HTTP {response.status_code}")
        if response.status_code != 200:
            raise Exception(f"Ошибка ответа от сайта: {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('a', class_='card')
        print(f"🔍 [DEBUG] Найдено {len(articles)} карточек на странице")

        new_found = False
        found_articles = []

        for article in articles:
            title = article.get_text(strip=True)
            href = article.get('href')
            link = 'https://www.minecraft.net' + href if href and href.startswith('/') else href

            if not link:
                continue

            if any(word in title.lower() for word in ['плащ', 'cape', 'скин', 'подарок']):
                found_articles.append((title, link))
                if link not in known_capes:
                    known_capes.add(link)
                    new_found = True
                    print(f"🆕 [DEBUG] Новая подходящая статья: {title} ({link})")

                    for user_id in allowed_users:
                        bot.send_message(int(user_id), f"🧥 *{title}*\n{link}", parse_mode="Markdown")

        # Ответ пользователю вручную
        if triggered_by_command and trigger_user_id:
            if found_articles:
                bot.send_message(trigger_user_id, f"🔍 Найдено {len(found_articles)} подходящих статей:")
                for title, link in found_articles:
                    bot.send_message(trigger_user_id, f"*{title}*\n{link}", parse_mode="Markdown")
            else:
                bot.send_message(trigger_user_id, "🔍 Подходящих статей не найдено.")
            print(f"✅ [DEBUG] Ручная проверка завершена. Отправлено пользователю {trigger_user_id}")
        elif not new_found:
            print("ℹ️ [DEBUG] Автопроверка: новых статей нет.")

    except Exception as e:
        print(f"❌ [ERROR] Ошибка в check_new_capes: {e}")
        if triggered_by_command and trigger_user_id:
            bot.send_message(trigger_user_id, f"❌ Ошибка при проверке: {e}")

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
    if is_allowed(message.chat.id):
        bot.send_message(message.chat.id, "🏓 Pong!")

@bot.message_handler(commands=['check'])
def manual_check(message):
    if not is_allowed(message.chat.id):
        bot.reply_to(message, "⛔️ У вас нет доступа к этой команде.")
        return

    bot.send_message(message.chat.id, "🔍 Выполняю ручную проверку сайта Minecraft.net...")
    check_new_capes(triggered_by_command=True, trigger_user_id=message.chat.id)

# === Логгирование всех сообщений для поиска новых пользователей ===
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
