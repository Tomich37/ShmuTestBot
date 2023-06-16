import configparser
import telebot
from .modules.database import Database
from telebot import types
from .modules.moderation import Moderation
from .modules.user_staff import User

block_size = 5
current_position = 0

class DialogBot:
    def __init__(self):
        # Чтение файла конфигурации
        config = configparser.ConfigParser()
        config.read('./config.ini')

        # Получение значения токена из файла конфигурации
        self.token = config.get('default', 'token')
        self.bot = telebot.TeleBot(self.token)

        # Создание экземпляра класса Database
        self.database = Database()

        self.moderation = Moderation(self.bot)

        # Переменная для отслеживания авторизации user
        self.authorized_user = False
        
    def run(self):
        # Показывает меню с кнопками
        def __show_menu(chat_id):
            markup = types.InlineKeyboardMarkup()
            next_button = types.InlineKeyboardButton("Следующие", callback_data='next')
            prev_button = types.InlineKeyboardButton("Предыдущие", callback_data='prev')
            markup.row(prev_button)
            markup.row(next_button)
            self.bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

        # Обработчик команды /start
        @self.bot.message_handler(commands=['start'])
        def __handle_start(message):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            contact_button = types.KeyboardButton(text="Поделиться телефоном", request_contact=True)
            markup.add(contact_button)
            
            self.bot.send_message(message.chat.id, "Для авторизации прошу поделиться вашим номереом телефона", reply_markup=markup)
    
        # Обработчик получения контакта
        @self.bot.message_handler(content_types=['contact'])
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
                self.authorized_user = True
                # Переменная для получения проли пользователя
                user_role = self.database.get_user_role(user_id)
                print(user_role)
            else:
                # Добавляем нового пользователя
                self.database.add_user(user_id, phone_number, first_name, last_name, user_role = "user")
                self.authorized_user = True            

            # Удаляем кнопку "Поделиться телефоном" из клавиатуры
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)

            if user_role == "admin" or user_role == "moderator":
                moderation_button = types.KeyboardButton(text="Модерация")
                markup.add(moderation_button)
                self.bot.send_message(message.chat.id, "Теперь вы авторизованы и можете пользоваться другими командами бота.", reply_markup=markup)
            else:
                events_button = types.KeyboardButton(text="События")
                markup.add(events_button)
                self.bot.send_message(message.chat.id, "Теперь вы авторизованы и можете пользоваться другими командами бота.", reply_markup=markup)

        # Вызов функции check_moderation при получении сообщения "Модерация"
        @self.bot.message_handler(func=lambda message: message.text == "Модерация")
        def handle_moderation(message):
            user_id = message.from_user.id 
            self.moderation.check_moderation(user_id)

        # Вызов функции add_moderator при получении сообщения "Добавить модератора"
        @self.bot.message_handler(func=lambda message: message.text == "Добавить модератора")
        def add_moderator(message):
            user_id = message.from_user.id 
            self.moderation.add_moderator(user_id)
    
        # Вызов функции events при получении сообщения "События"
        @self.bot.message_handler(func=lambda message: message.text == "События")
        def __handle_events_button(message):
            __events(message)

        # Обработчик команды /events
        @self.bot.message_handler(commands=['events'])
        def __events(message):            
            
            if self.authorized_user == True: # Проверка на авторизацию
                # Получение информации из events.db
                events_list = self.database.get_events()

                if current_position >= len(events_list):
                    self.bot.send_message(message.chat.id, "Больше нет мероприятий.")
                else:
                    events_to_display = events_list[current_position:current_position+block_size]
                    response = "Мероприятия: \n\n"
                    for event in events_to_display:
                        response += f"Дата: {event[0]}\n"
                        response += f"Место проведения: {event[1]}\n"
                        response += f"Мероприятие: {event[2]}\n\n"
                    self.bot.send_message(message.chat.id, response, reply_markup=__get_pagination_buttons())
            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                contact_button = types.KeyboardButton(text="Поделиться телефоном", request_contact=True)
                markup.add(contact_button)
                self.bot.send_message(message.chat.id, "Вы не авторизировались, для продолжения предоставьте номер телефона", reply_markup=markup)

        # Получает кнопки пагинации
        def __get_pagination_buttons():
            markup = types.InlineKeyboardMarkup()
            next_button = types.InlineKeyboardButton("Следующие", callback_data='next')
            prev_button = types.InlineKeyboardButton("Предыдущие", callback_data='prev')
            markup.row(prev_button, next_button)
            return markup

        # Обработчик нажатия кнопок
        @self.bot.callback_query_handler(func=lambda call: True)
        def __handle_button_click(call):
            global message_id
            if call.data == 'next':
                __next_events(call)
            elif call.data == 'prev':
                __prev_events(call)

            admin_id = call.from_user.id
            message_id = call.message.message_id

            if call.data == "send_phone":
                self.bot.send_message(admin_id, "Пользователь назначен модератором")
                self.bot.delete_message(chat_id=call.message.chat.id, message_id=message_id)
            elif call.data == "cancel":
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
                distribution_button = types.KeyboardButton(text="Создать рассылку")
                markup.add(distribution_button)
                self.bot.send_message(admin_id, "Выберите действие:", reply_markup=markup)
                self.bot.delete_message(chat_id=call.message.chat.id, message_id=message_id)
                
        # Обработчик команды /prev
        def __prev_events(call):
            global current_position
            if current_position == 0:
                self.bot.answer_callback_query(callback_query_id=call.id, text="Это первая страница.")
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
                self.bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=__get_pagination_buttons(), disable_web_page_preview=True)
            except telebot.apihelper.ApiTelegramException as e:
                print(f"Failed to edit message: {e}")

        # Обработчик команды /next
        def __next_events(call):
            global current_position
            current_position += block_size

            events_list = self.database.get_events()
            if current_position >= len(events_list):
                current_position -= block_size
                self.bot.answer_callback_query(callback_query_id=call.id, text="Больше нет мероприятий.")
                return

            events_to_display = events_list[current_position:current_position+block_size]
            response = "Мероприятия:\n\n"
            for event in events_to_display:
                response += f"Дата: {event[0]}\n"
                response += f"Место проведения: {event[1]}\n"
                response += f"Мероприятие: {event[2]}\n\n"

            if current_position >= len(events_list):
                response += "\n\nЭто последняя страница."
            self.bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=__get_pagination_buttons())

        # Запуск бота
        self.bot.polling()

