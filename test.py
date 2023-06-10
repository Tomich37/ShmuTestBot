import pandas as pd, telebot
from telebot import types

TOKEN = ''
file_path = 'June.xlsx'
data_frame = pd.read_excel(file_path)
block_size = 5
current_position = 0

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    events_button = types.KeyboardButton("События")
    markup.add(events_button)
    bot.send_message(message.chat.id, "Привет! Чтобы просмотреть мероприятия, нажми кнопку 'События'.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "События")
def handle_events_button(message):
    events(message)

# Показывает меню с кнопками
def show_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    next_button = types.InlineKeyboardButton("Следующие", callback_data='next')
    prev_button = types.InlineKeyboardButton("Предыдущие", callback_data='prev')
    markup.row(prev_button)
    markup.row(next_button)
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

# Обработчик команды /events
@bot.message_handler(commands=['events'])
def events(message):
    if current_position >= len(data_frame):
        bot.send_message(message.chat.id, "Больше нет мероприятий.")
    else:
        events_list = data_frame.iloc[current_position:current_position+block_size]
        response = "Мероприятия:\n\n"
        for index, event in events_list.iterrows():
            response += f"Дата: {event['Дата']}\n"
            response += f"Место проведения: {event['Место проведения']}\n"
            response += f"Мероприятие: {event['Мероприятие']}\n\n"
        bot.send_message(message.chat.id, response, reply_markup=get_pagination_buttons())

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
    if current_position >= len(data_frame):
        bot.answer_callback_query(callback_query_id=call.id, text="Больше нет мероприятий.")
    else:
        events_list = data_frame.iloc[current_position:current_position+block_size]
        response = "Мероприятия:\n\n"
        for index, event in events_list.iterrows():
            response += f"Дата: {event['Дата']}\n"
            response += f"Место проведения: {event['Место проведения']}\n"
            response += f"Мероприятие: {event['Мероприятие']}\n\n"
        bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=get_pagination_buttons())

# Обработчик команды /prev
def prev_events(call):
    global current_position
    current_position -= block_size
    if current_position < 0:
        current_position = 0
    events_list = data_frame.iloc[current_position:current_position+block_size]
    response = "Мероприятия:\n\n"
    for index, event in events_list.iterrows():
        response += f"Дата: {event['Дата']}\n"
        response += f"Место проведения: {event['Место проведения']}\n"
        response += f"Мероприятие: {event['Мероприятие']}\n\n"
    bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=get_pagination_buttons())

bot.infinity_polling()