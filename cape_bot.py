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

# Разбираем строку ALLOWED_USERS в список строковых ID
# (например: "12345678,87654321" → ["12345678", "87654321"])
allowed_users = [uid.strip() for uid in ALLOWED_USERS.split(',') if uid.strip().isdigit()]

bot = telebot.TeleBot(TOKEN)
known_capes = set()  # тут храним ссылки, которые уже «видели»

# === Функция парсинга и рассылки ===
def check_new_capes(triggered_by_command=False, trigger_user_id=None):
    global known_capes
    print("🔍 [LOG] Запущена проверка сайта Minecraft.net...")

    try:
        url = 'https://www.minecraft.net/ru-ru'
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('a', class_='card')
        print(f"🔍 [LOG] Найдено всего {len(articles)} карточек a.card на странице.")

        new_found = False
        found_articles = []  # будем хранить все подходящие (title, link)

        for article in articles:
            title = article.get_text(strip=True)
            href = article.get('href')
            link = 'https://www.minecraft.net' + href if href.startswith('/') else href

            # Ищем ключевые слова
            lower_title = title.lower()
            if 'плащ' in lower_title or 'cape' in lower_title or 'скин' in lower_title or 'подарок' in lower_title:
                found_articles.append((title, link))
                if link not in known_capes:
                    known_capes.add(link)
                    new_found = True
                    print(f"✅ [LOG] Новая статья: {title} → {link}")
                    # Рассылаем каждому из allowed_users
                    for user_id in allowed_users:
                        try:
                            bot.send_message(
                                int(user_id),
                                f"🧥 Обнаружена новая статья:\n*{title}*\n{link}",
                                parse_mode="Markdown"
                            )
                        except Exception as send_exc:
                            print(f"❌ [LOG] Не смогли отправить новость пользователю {user_id}: {send_exc}")

        # Если вызвано вручную (triggered_by_command=True), всегда отправляем список найденных, даже если старые
        if triggered_by_command and trigger_user_id:
            if found_articles:
                bot.send_message(trigger_user_id, f"🔍 Найдено {len(found_articles)} подходящих статей:")
                for title, link in found_articles:
                    bot.send_message(trigger_user_id, f"*{title}*\n{link}", parse_mode="Markdown")
            else:
                bot.send_message(trigger_user_id, "🔍 Статей с плащами, скинами или подарками не найдено.")
            print("🔍 [LOG] Ручная проверка завершена (результаты отправлены инициатору).")

        # Если это не ручная проверка, а расписание, и новых не найдено — шлем «нет новых» всем allowed_users
        elif not new_found:
            for user_id in allowed_users:
                try:
                    bot.send_message(int(user_id), "🔍 Проверка сайта Minecraft.net...\nНовых плащей не найдено.")
                except Exception as send_exc:
                    print(f"❌ [LOG] Не смогли отправить сообщение об отсутствии новостей пользователю {user_id}: {send_exc}")
            print("ℹ️ [LOG] Автопроверка завершена — новых статей не было.")

        else:
            print("✅ [LOG] Автопроверка: новые статьи уже разосланы.")
    except Exception as e:
        print("❌ [LOG] Ошибка при проверке:", e)
        # Если это вызов из /check — уведомить инициатора об ошибке
        if triggered_by_command and trigger_user_id:
            try:
                bot.send_message(trigger_user_id, f"❌ Ошибка при проверке сайта: {e}")
            except:
                pass

# === Запланированный запуск каждые 30 минут ===
schedule.every(30).minutes.do(check_new_capes)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

# === Проверка, разрешено ли пользователю выполнять команды ===
def is_allowed(user_id):
    return str(user_id) in allowed_users

# === Обработка команд бота ===
@bot.message_handler(commands=['start', 'плащ'])
def send_welcome(message):
    if not is_allowed(message.chat.id):
        bot.reply_to(message, "⛔️ У вас нет доступа к этому боту.")
        print(f"👤 [LOG] Доступ запрещён для пользователя {message.chat.id}")
        return
    bot.reply_to(message, "Привет! Бот будет присылать тебе новые плащи, как только они появятся!")

@bot.message_handler(commands=['ping'])
def ping_command(message):
    if not is_allowed(message.chat.id):
        return
    bot.send_message(message.chat.id, "🏓 Pong!")

@bot.message_handler(commands=['check'])
def manual_check(message):
    if not is_allowed(message.chat.id):
        bot.reply_to(message, "⛔️ У вас нет доступа к этой команде.")
        print(f"⛔️ [LOG] Попытка запуска /check от запрещённого {message.chat.id}")
        return

    bot.send_message(message.chat.id, "🔍 Выполняю ручную проверку сайта Minecraft.net...")
    # Запускаем проверку в отдельном потоке, чтобы не блокировать бота
    threading.Thread(
        target=check_new_capes,
        kwargs={"triggered_by_command": True, "trigger_user_id": message.chat.id},
        daemon=True
    ).start()

# === Логгирование всех входящих (для отладки новых пользователей) ===
@bot.message_handler(func=lambda message: True)
def any_message(message):
    print(f"👤 [LOG] Пользователь {message.chat.id} написал: {message.text}")

# === Простой HTTP-сервер для того, чтобы Render не «засыпал» ===
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), SimpleHandler)
    print(f"🌐 [LOG] HTTP-сервер запущен на порту {PORT}")
    server.serve_forever()

# === Стартуем HTTP-сервер и планировщик в потоках, затем включаем polling() ===
threading.Thread(target=run_server, daemon=True).start()
threading.Thread(target=run_schedule, daemon=True).start()

bot.polling()
