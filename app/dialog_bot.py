import configparser
import telebot
from .database import Database
from telebot import types

block_size = 5
current_position = 0

class DialogBot:
    def __init__(self):
        # Чтение файла конфигурации
        config = configparser.ConfigParser()
        config.read('./config.ini')

        # Получение значения токена из файла конфигурации
        self.token = config.get('default', 'token')

        # Получение пути к файлу базы данных из файла конфигурации
        db_path_events = config.get('default', 'db_path_events')
        db_path_users = config.get('default', 'db_path_users')

        # Инициализация объекта базы данных с передачей пути к файлу базы данных
        self.database = Database(db_path_events, db_path_users)


    def run(self):
        bot = telebot.TeleBot(self.token)

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
        def handle_start(message):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            contact_button = types.KeyboardButton(text="Поделиться телефоном", request_contact=True)
            events_button = types.KeyboardButton(text="События")
            # users_button = types.KeyboardButton("Создать БД юзеров")
            markup.add(events_button)
            markup.add(contact_button)
            # markup.add(users_button)
            
            bot.send_message(message.chat.id, "Для авторизации прошу поделиться вашим номереом телефона", reply_markup=markup)
            # Передача user_id в database.py

        @bot.message_handler(func=lambda message: message.text == "События")
        def handle_events_button(message):
            events(message)

        # Обработчик получения контакта
        @bot.message_handler(content_types=['contact'])
        def handle_contact(message):
            user_id = message.from_user.id
            contact = message.contact
            phone_number = contact.phone_number
        
            # Отправляем подтверждение
            bot.send_message(message.chat.id, "Спасибо! Ваш номер телефона был получен.")
            self.database.set_user_data(user_id, phone_number)
            print(user_id, phone_number, contact)
        
        # Создание таблицы пользователей одной кнопкой, создано, больше не нужено
        # @bot.message_handler(func=lambda message: message.text == "Создать БД юзеров")
        # def handle_users_button(message):
        #     users(message)

        # @bot.message_handler(commands=['users'])
        # def users(message):
        #     self.database.create_users_table()
        #     print("Таблица создана")
        #     bot.send_message(message.chat.id, "Таблица создана")            

        # Обработчик команды /events
        @bot.message_handler(commands=['events'])
        def events(message):
            conn = self.database.get_database_connection_events()  # Создание нового соединения
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
                
        # Обработчик команды /prev
        def prev_events(call):
            global current_position
            if current_position == 0:
                bot.answer_callback_query(callback_query_id=call.id, text="Это первая страница.")
                return

            current_position -= block_size
            if current_position < 0:
                current_position = 0

            events_list = self.database.get_events()
            events_to_display = events_list[current_position:current_position+block_size]
            response = "Мероприятия:\n\n"
            for event in events_to_display:
                response += f"Дата: {event[0]}\n"
                response += f"Место проведения: {event[1]}\n"
                response += f"Мероприятие: {event[2]}\n\n"

            try:
                bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=get_pagination_buttons(), disable_web_page_preview=True)
            except telebot.apihelper.ApiTelegramException as e:
                print(f"Failed to edit message: {e}")

        # Обработчик команды /next
        def next_events(call):
            global current_position
            current_position += block_size

            events_list = self.database.get_events()
            if current_position >= len(events_list):
                current_position -= block_size
                bot.answer_callback_query(callback_query_id=call.id, text="Больше нет мероприятий.")
                return

            events_to_display = events_list[current_position:current_position+block_size]
            response = "Мероприятия:\n\n"
            for event in events_to_display:
                response += f"Дата: {event[0]}\n"
                response += f"Место проведения: {event[1]}\n"
                response += f"Мероприятие: {event[2]}\n\n"

            bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=get_pagination_buttons())

        # Запуск бота
        bot.polling()

