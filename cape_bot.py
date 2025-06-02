import telebot
import requests
import schedule
import time
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# === Настройки из переменных окружения ===
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

bot = telebot.TeleBot(TOKEN)
known_capes = set()  # Храним уже известные ID плащей

# === Проверка новых плащей ===
def check_new_capes():
    global known_capes
    print("🔍 Проверка на новые плащи...")
    try:
        # Тестовый вывод
        bot.send_message(CHAT_ID, "✅ Проверка работает!")
    except Exception as e:
        print("Ошибка:", e)
        
    try:
        response = requests.get('https://laby.net/capes')
        data = response.json()

        new_found = False
        for cape in data:
            if cape['id'] not in known_capes:
                known_capes.add(cape['id'])
                new_found = True

                name = cape.get('name', 'Без названия')
                img = cape.get('image', '')

                bot.send_message(CHAT_ID, f"🧥 Обнаружен новый плащ: *{name}*", parse_mode="Markdown")
                if img.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    bot.send_photo(CHAT_ID, img)
                else:
                    bot.send_message(CHAT_ID, f"⚠️ Картинка не найдена или ссылка неправильная:\n{img}")

        if not new_found:
            print("Новых плащей нет.")
    except Exception as e:
        print("Ошибка при проверке новых плащей:", e)

# === Расписание: проверка каждую минуту ===
schedule.every(1).minutes.do(check_new_capes)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

# === Обработка команд бота ===
@bot.message_handler(commands=['start', 'плащ'])
def send_welcome(message):
    if str(message.chat.id) != CHAT_ID:
        return  # Игнорируем сообщения от чужих
    bot.reply_to(message, "Привет! Бот будет присылать тебе новые плащи, как только они появятся!")

@bot.message_handler(commands=['cape'])
def send_cape(message):
    if str(message.chat.id) != CHAT_ID:
        return
    bot.send_message(message.chat.id, "🧥 *Vanilla Cape*\n\nЭтот плащ выдавался игрокам, у которых были и Java, и Bedrock версии Minecraft до 6 июня 2022 года.", parse_mode="Markdown")
    bot.send_photo(message.chat.id, 'https://static.wikia.nocookie.net/minecraft_gamepedia/images/7/77/Vanilla_Cape.png')

@bot.message_handler(commands=['test_cape'])
def test_cape(message):
    if str(message.chat.id) != CHAT_ID:
        return
    name = "Vanilla Cape"
    img = "https://ru.minecraft.wiki/images/Vanilla_cape.png?1d440"
    bot.send_message(message.chat.id, f"🧥 {name}")
    bot.send_photo(message.chat.id, img)

@bot.message_handler(commands=['ping'])
def ping_command(message):
    if str(message.chat.id) != CHAT_ID:
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
    print(f"Запущен HTTP-сервер на порту {PORT}")
    server.serve_forever()

# === Запуск ===
threading.Thread(target=run_server, daemon=True).start()
threading.Thread(target=run_schedule, daemon=True).start()

bot.polling()
