import telebot
import configparser
import sqlite3
from telebot import types
from threading import Thread
import signal
import sys

# Создание объекта парсера
config = configparser.ConfigParser()

# Читаем файл config.ini
config.read('config.ini')

# Получаем значения из файла
TOKEN = config.get('default', 'token')
file_path = config.get('default', 'file_path')
block_size = 5
current_position = 0

bot = telebot.TeleBot(TOKEN)

# Функция для получения соединения с базой данных
def get_database_connection():
    return sqlite3.connect('./bd/events.db')

# Функция для создания таблицы events
def create_events_table():
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS events (
                        eventid INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        place TEXT,
                        event TEXT
                    );''')
    conn.commit()
    conn.close()

# Функция для получения списка мероприятий из базы данных
def get_events():
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date, place, event FROM events")
    events_list = cursor.fetchall()
    conn.close()
    return events_list

# Показывает меню с кнопками
def show_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    next_button = types.InlineKeyboardButton("Следующие", callback_data='next')
    prev_button = types.InlineKeyboardButton("Предыдущие", callback_data='prev')
    markup.row(prev_button)
    markup.row(next_button)
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    events_button = types.KeyboardButton("События")
    markup.add(events_button)
    bot.send_message(message.chat.id, "Привет! Чтобы просмотреть мероприятия, нажми кнопку 'События'.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "События")
def handle_events_button(message):
    events(message)

# Обработчик команды /events
@bot.message_handler(commands=['events'])
def events(message):
    conn = get_database_connection()
    cursor = conn.cursor()

    sql_query = "SELECT date, place, event FROM events"
    cursor.execute(sql_query)
    events_list = cursor.fetchall()

    if current_position >= len(events_list):
        bot.send_message(message.chat.id, "Больше нет мероприятий.")
    else:
        events_to_display = events_list[current_position:current_position+block_size]
        response = "Мероприятия:\n\n"
        for event in events_to_display:
            response += f"Дата: {event[0]}\n"
            response += f"Место проведения: {event[1]}\n"
            response += f"Мероприятие: {event[2]}\n\n"
        bot.send_message(message.chat.id, response, reply_markup=get_pagination_buttons())
    
    conn.close()

# Получает кнопки пагинации
def get_pagination_buttons():
    markup = types.InlineKeyboardMarkup()
    next_button = types.InlineKeyboardButton("Следующие", callback_data='next')
    prev_button = types.InlineKeyboardButton("Предыдущие", callback_data='prev')
    markup.row(prev_button, next_button)
    return markup

# Обработчик нажатия кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_button_click(call):
    if call.data == 'next':
        next_events(call)
    elif call.data == 'prev':
        prev_events(call)

# Обработчик команды /next
def next_events(call):
    global current_position
    current_position += block_size
    events_list = get_events()

    if current_position >= len(events_list):
        bot.answer_callback_query(callback_query_id=call.id, text="Больше нет мероприятий.")
    else:
        events_to_display = events_list[current_position:current_position+block_size]
        response = "Мероприятия:\n\n"
        for event in events_to_display:
            response += f"Дата: {event[0]}\n"
            response += f"Место проведения: {event[1]}\n"
            response += f"Мероприятие: {event[2]}\n\n"
        bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=get_pagination_buttons())

# Обработчик команды /prev
def prev_events(call):
    global current_position
    current_position -= block_size
    if current_position < 0:
        current_position = 0
    events_list = get_events()

    events_to_display = events_list[current_position:current_position+block_size]
    response = "Мероприятия:\n\n"
    for event in events_to_display:
        response += f"Дата: {event[0]}\n"
        response += f"Место проведения: {event[1]}\n"
        response += f"Мероприятие: {event[2]}\n\n"
    bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=get_pagination_buttons())

# Функция для запуска бота
def start_bot():
    bot.polling()

# Обработчик прерывания выполнения программы (Ctrl+C)
def signal_handler(signal, frame):
    print("Программа остановлена")
    sys.exit(0)

# Создание таблицы и запуск бота в отдельном потоке
if __name__ == "__main__":
    create_events_table()

    # Установка обработчика прерывания выполнения программы (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    # Запуск бота в отдельном потоке
    bot_thread = Thread(target=start_bot)
    bot_thread.start()
