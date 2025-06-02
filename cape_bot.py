import telebot
import requests
import schedule
import time
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# === Настройки бота ===
TOKEN = '8093048403:AAHLQNTB_y9DDDORl5WtV8hqgl_cAh-5nnk'  # твой токен
CHAT_ID = '6399778317'  # твой chat_id
bot = telebot.TeleBot(TOKEN)

# Храним последний известный список плащей
known_capes = set()

# === ТВОЯ ФУНКЦИЯ ДЛЯ ПРОВЕРКИ ПЛАЩЕЙ ===
def check_new_capes():
    global known_capes
    try:
        response = requests.get('https://capes.dev/api/capes')
        data = response.json()

        new_found = False
        for cape in data:
            if cape['id'] not in known_capes:
                new_found = True
                known_capes.add(cape['id'])

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

# === РАСПИСАНИЕ ПРОВЕРОК ===
schedule.every(1).day.do(check_new_capes)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

# === ОБРАБОТЧИК КОМАНД БОТА ===
@bot.message_handler(commands=['start', 'плащ'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Бот будет присылать тебе новые плащи, как только они появятся!")

@bot.message_handler(commands=['cape'])
def send_cape(message):
    bot.send_message(message.chat.id, "🧥 *Vanilla Cape*\n\nЭтот плащ выдавался игрокам, у которых были и Java, и Bedrock версии Minecraft до 6 июня 2022 года.", parse_mode="Markdown")
    bot.send_photo(message.chat.id, 'https://static.wikia.nocookie.net/minecraft_gamepedia/images/7/77/Vanilla_Cape.png')

@bot.message_handler(commands=['test_cape'])
def test_cape(message):
    name = "Vanilla Cape"
    img = "https://ru.minecraft.wiki/images/Vanilla_cape.png?1d440"
    bot.send_message(message.chat.id, f"🧥 {name}")
    bot.send_photo(message.chat.id, img)

@bot.message_handler(commands=['ping'])
def ping_command(message):
    bot.send_message(message.chat.id, "🏓 Pong!")

# === ПРОСТОЙ HTTP-СЕРВЕР ДЛЯ Render ===
PORT = int(os.environ.get("PORT", 8000))

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), SimpleHandler)
    print(f"Starting HTTP server on port {PORT}")
    server.serve_forever()

# Запускаем веб-сервер в отдельном потоке
threading.Thread(target=run_server, daemon=True).start()

# Запускаем планировщик проверок в отдельном потоке
threading.Thread(target=run_schedule, daemon=True).start()

# Запускаем бота (блокирующая функция)
bot.polling()
