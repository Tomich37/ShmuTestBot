import configparser
import telebot
from .modules.database import Database
from telebot import types
from .modules.moderation import Moderation
from .modules.user_staff import User
from .modules.distribution import Distribution
import uuid


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
        self.user = User(self.bot, self.database, authorized_user=False)
        self.moderation = Moderation(self.bot)
        self.distribution = Distribution(self.bot)

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

            self.bot.send_message(message.chat.id, "Для авторизации прошу поделиться вашим номером телефона", reply_markup=markup)

        # Обработчик получения контакта
        @self.bot.message_handler(content_types=['contact'])
        def __handle_contact(message):
            contact = message.contact
            user_id = message.from_user.id
            first_name = message.from_user.first_name
            last_name = message.from_user.last_name
            phone_number = contact.phone_number

            # Отправляем в базу данных значения user_id и phone_number
            self.database.set_user_data(user_id, phone_number)

            print(user_id, phone_number, first_name, last_name)

            # Проверяем, существует ли пользователь в базе данных
            if self.database.user_exists_phone(phone_number):
                # Обновляем запись существующего пользователя
                self.database.update_user(user_id, phone_number, first_name, last_name)
                self.authorized_user = True
                # Переменная для получения роли пользователя
                user_role = self.database.get_user_role(user_id)
                print(user_role)
            else:
                # Добавляем нового пользователя
                self.database.add_user(user_id, phone_number, first_name, last_name, user_role="user")
                self.authorized_user = True
                user_role = None

            # Удаляем кнопку "Поделиться телефоном" из клавиатуры
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

            if user_role == "admin" or user_role == "moderator":
                moderation_button = types.KeyboardButton(text="Модерация")
                markup.add(moderation_button)
                self.bot.send_message(message.chat.id, "Теперь вы авторизованы и можете пользоваться другими командами бота.", reply_markup=markup)
            else:
                events_button = types.KeyboardButton(text="События")
                markup.add(events_button)
                self.bot.send_message(message.chat.id, "Теперь вы авторизованы и можете пользоваться другими командами бота.", reply_markup=markup)

            # Обновляем атрибут authorized_user в экземпляре класса User
            self.user.authorized_user = self.authorized_user


        # Вызов функции check_moderation при получении сообщения "Модерация"
        @self.bot.message_handler(func=lambda message: message.text == "Модерация")
        def handle_moderation(message):
            user_id = message.from_user.id
            if self.database.user_exists_id(user_id):
                self.moderation.moderation_buttonn_klick(user_id)
            else:
                __handle_start(message)

        # Вызов функции add_moderator при получении сообщения "Добавить модератора"
        @self.bot.message_handler(func=lambda message: message.text == "Добавить модератора")
        def add_moderator_button(message):
            user_id = message.from_user.id
            if self.database.user_exists_id(user_id):
                self.moderation.add_moderator_button(user_id)
            else:
                __handle_start(message)
        
        # Обработчик команды /add_mod
        @self.bot.message_handler(commands=['add_mod'])
        def add_mod(message):
            user_id = message.from_user.id
            if self.database.user_exists_id(user_id):
                phone_number = message.text[len('/add_mod') + 1:]
                self.moderation.add_moderator(user_id, phone_number)
            else:
                __handle_start(message)

        # Подтверждение добавления/удаления модератора
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_button_click(call):
            user_id = call.from_user.id
            markup = None
            if call.data.startswith('confirm_add_mod_'):
                phone_number = call.data.split('_')[3]
                self.database.add_moderator(phone_number)
                markup = self.moderation.admin_markup()
                self.bot.send_message(call.message.chat.id, "Модератор добавлен", reply_markup=markup)
            elif call.data == 'cancel_add_mod':
                self.bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
            elif call.data.startswith('confirm_remove_mod_'):
                phone_number = call.data.split('_')[3]
                print(phone_number)
                self.database.remove_moderator(phone_number)
                markup = self.moderation.admin_markup()
                self.bot.send_message(call.message.chat.id, "Модератор снят", reply_markup=markup)
            elif call.data == 'cancel_remove_mod':
                self.bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        
        # Вызов функции add_moderator при получении сообщения "Снять с поста модератора"
        @self.bot.message_handler(func=lambda message: message.text == "Снять с поста модератора")
        def remove_moderator_button(message):
            user_id = message.from_user.id
            self.moderation.remove_moderator_button(user_id)
        
        # Обработчик команды /remove_mod
        @self.bot.message_handler(commands=['remove_mod'])
        def remove_mod(message):
            user_id = message.from_user.id
            if self.database.user_exists_id(user_id):
                phone_number = message.text[len('/remove_mod') + 1:]
                self.moderation.remove_moderator(user_id, phone_number)
            else:
                __handle_start(message)

        # Вызов функции events при получении сообщения "События"
        @self.bot.message_handler(func=lambda message: message.text == "События")
        def __handle_events_button(message):
            user_id = message.from_user.id
            if self.database.user_exists_id(user_id):
                self.user.events_handler(message)
            else:
                __handle_start(message)

        # Обработчик команды /events
        @self.bot.message_handler(commands=['events'])
        def __handle_events_command(message):
            user_id = message.from_user.id
            if self.database.user_exists_id(user_id):
                self.user.events_handler(message)
            else:
                __handle_start(message)

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_button_click(call):
            message_id = call.message.message_id
            self.user.handle_button_click(call, message_id)

        # Вызов функции events при получении сообщения "Создать рассылку"
        @self.bot.message_handler(func=lambda message: message.text == "Создать рассылку")
        def handle_distribution_button(message):
            user_id = message.from_user.id
            if self.database.user_exists_id(user_id):
                self.distribution.distribution_button_click(user_id)
            else:
                self.__handle_start(message)

        # Обработчик команды /cd
        @self.bot.message_handler(commands=['cd'])
        def create_distribution(message):
            user_id = message.from_user.id
            if self.database.user_exists_id(user_id):
                # Get the text message from the user
                text = message.text.split(' ', 1)[1]

                # Save the distribution text in the database and get the ID
                distribution_id = self.database.save_distribution_text(text)

                if distribution_id is not None:
                    # Create a keyboard with "Send" and "Cancel" buttons
                    keyboard = types.InlineKeyboardMarkup()
                    send_button = types.InlineKeyboardButton(text="Отправить", callback_data=f"send_distribution_{distribution_id}")
                    cancel_button = types.InlineKeyboardButton(text="Отменить", callback_data="cancel_distribution")
                    keyboard.add(send_button, cancel_button)

                    # Send the message with the keyboard to the user
                    self.bot.send_message(user_id, f"Сообщение для рассылки:\n\n{text}", reply_markup=keyboard)
                else:
                    self.bot.send_message(user_id, "Не удалось создать рассылку.")
            else:
                self.__handle_start(message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('send_distribution_'))
        def send_distribution_callback(call):
            # Get the distribution ID from callback_data
            distribution_id = call.data.split('_', 2)[1]

            # Get the distribution text from the database using the ID
            result = self.database.send_distribution_text(distribution_id)

            if result is not None:
                text = result

                # Get the list of all users from the database
                users = self.database.get_users()

                # Send the message to each user
                for user in users:
                    user_id = user[0]  # Assuming the user ID is stored in the first column of the table
                    self.bot.send_message(user_id, text)

                # Send a message to the user who created the distribution
                self.bot.send_message(call.from_user.id, "Рассылка успешно выполнена.")
            else:
                self.bot.send_message(call.from_user.id, "Рассылка не найдена.")

        # Запуск бота
        self.bot.polling()