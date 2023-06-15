import configparser
import telebot
from .modules.database import Database
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

        # Создание экземпляра класса Database
        self.database = Database()

    def run(self):
        bot = telebot.TeleBot(self.token)

        # Показывает меню с кнопками
        def __show_menu(chat_id):
            markup = types.InlineKeyboardMarkup()
            next_button = types.InlineKeyboardButton("Следующие", callback_data='next')
            prev_button = types.InlineKeyboardButton("Предыдущие", callback_data='prev')
            markup.row(prev_button)
            markup.row(next_button)
            bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

        # Обработчик команды /start
        @bot.message_handler(commands=['start'])
        def __handle_start(message):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            contact_button = types.KeyboardButton(text="Поделиться телефоном", request_contact=True)
            markup.add(contact_button)
            
            bot.send_message(message.chat.id, "Для авторизации прошу поделиться вашим номереом телефона", reply_markup=markup)

        # Обработчик получения контакта
        @bot.message_handler(content_types=['contact'])
        def __handle_contact(message):
            contact = message.contact
            user_id = message.from_user.id
            first_name = message.from_user.first_name
            last_name = message.from_user.last_name
            phone_number = contact.phone_number

            # Отправляем в database значения user_id и phone_number
            self.database.set_user_data(user_id, phone_number)
            print(user_id, phone_number, first_name, last_name)

                # Проверяем, существует ли пользователь в базе данных
            if self.database.user_exists(phone_number):
                # Обновляем запись существующего пользователя
                self.database.update_user(user_id, phone_number, first_name, last_name)
            else:
                # Добавляем нового пользователя
                self.database.add_user(user_id, phone_number, first_name, last_name)

            # Удаляем кнопку "Поделиться телефоном" из клавиатуры
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
            events_button = types.KeyboardButton(text="События")
            markup.add(events_button)
            
            bot.send_message(message.chat.id, "Теперь вы авторизованы и можете пользоваться другими командами бота.", reply_markup=markup)

        # Вызов функции events при получении сообщения "События"
        @bot.message_handler(func=lambda message: message.text == "События")
        def __handle_events_button(message):
            __events(message)

        # Обработчик команды /events
        @bot.message_handler(commands=['events'])
        def __events(message):

            # Получение информации из events.db
            events_list = self.database.get_events()

            if current_position >= len(events_list):
                bot.send_message(message.chat.id, "Больше нет мероприятий.")
            else:
                events_to_display = events_list[current_position:current_position+block_size]
                response = "Мероприятия: \n\n"
                for event in events_to_display:
                    response += f"Дата: {event[0]}\n"
                    response += f"Место проведения: {event[1]}\n"
                    response += f"Мероприятие: {event[2]}\n\n"
                bot.send_message(message.chat.id, response, reply_markup=__get_pagination_buttons())

        # Получает кнопки пагинации
        def __get_pagination_buttons():
            markup = types.InlineKeyboardMarkup()
            next_button = types.InlineKeyboardButton("Следующие", callback_data='next')
            prev_button = types.InlineKeyboardButton("Предыдущие", callback_data='prev')
            markup.row(prev_button, next_button)
            return markup

        # Обработчик нажатия кнопок
        @bot.callback_query_handler(func=lambda call: True)
        def __handle_button_click(call):
            if call.data == 'next':
                __next_events(call)
            elif call.data == 'prev':
                __prev_events(call)
                
        # Обработчик команды /prev
        def __prev_events(call):
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
                bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=__get_pagination_buttons(), disable_web_page_preview=True)
            except telebot.apihelper.ApiTelegramException as e:
                print(f"Failed to edit message: {e}")

        # Обработчик команды /next
        def __next_events(call):
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

            bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=__get_pagination_buttons())

        # Запуск бота
        bot.polling()

