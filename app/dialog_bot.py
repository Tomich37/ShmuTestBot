import configparser
import telebot
import time
from .modules.database import Database
from telebot import types
from .modules.moderation import Moderation
from .modules.user_staff import User
from .modules.distribution import Distribution


class DialogBot:
    def __init__(self):
        # Чтение файла конфигурации
        config = configparser.ConfigParser()
        config.read('./config.ini')
        self.i = 0

        # Получение значения токена из файла конфигурации
        self.token = config.get('default', 'token')
        self.bot = telebot.TeleBot(self.token)
        self.save_directory = config.get('default', 'save_directory')

        # Создание экземпляра класса Database
        self.database = Database()
        self.user = User(self.bot, self.database, authorized_user=False)  # Pass authorized_user=False
        self.moderation = Moderation(self.bot, self.save_directory)
        self.distribution = Distribution(self.bot, self.save_directory, self.i)

        # Переменная для отслеживания авторизации user
        self.authorized_user = False

    @staticmethod
    def admin_markup():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        add_moderator_button = types.KeyboardButton(text="Модерация")
        markup.add(add_moderator_button)
        return markup

    @staticmethod
    def user_markup():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        distribution_button= types.KeyboardButton(text="События")
        markup.add(distribution_button)
        return markup

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

        @self.bot.message_handler(func=lambda message: message.text.lower() == 'добавить пользователей')
        def handle_add_users(message):
            user_id = message.from_user.id
            user_role = user_role = self.database.get_user_role(user_id)
            if self.database.user_exists_id(user_id):
                if user_role != 'user':
                    self.database.set_pending_command(user_id, '/add_users')  # Сохраняем команду в БД для последующего использования
                    self.bot.send_message(message.chat.id, "Загрузите exel файл")
                else:  
                    markup = self.user_markup()
                    self.bot.send_message(user_id, "Недостаточно прав", reply_markup=markup)
            else:
                __handle_start(message)

        @self.bot.message_handler(func=lambda message: message.text == "Меню")
        def handle_menu(message):
            user_id = message.from_user.id
            user_role = user_role = self.database.get_user_role(user_id)
            if self.database.user_exists_id(user_id):
                if user_role != 'user':
                    markup = self.admin_markup()
                    self.bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
                else:  
                    markup = self.user_markup()
                    self.bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
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

        # Кнопки подтверждения/отмены
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
            elif call.data.startswith('send_distribution_photo_'):
                distribution_id = self.database.get_latest_distribution_id()
                text = self.database.send_distribution_text(distribution_id)
                file_paths = self.database.get_distribution_file_paths(distribution_id)
                if file_paths:
                    file_path = file_paths[0]  # Получаем первый и единственный файл из списка
                    authorized_users = self.database.get_users()  # Получаем только авторизованных пользователей
                    for user in authorized_users:
                        user_id = user[0]
                        with open(file_path, 'rb') as photo:
                            print(user_id, photo, text)
                            try:
                                message = self.bot.send_photo(user_id, photo, caption=text)
                                time.sleep(0.5)
                            except telebot.apihelper.ApiTelegramException as e:
                                if e.result.status_code == 403:
                                    # Пользователь заблокировал бота
                                    self.database.update_user_authorized(user_id, 0)
                                    print(f"Пользователь с ID {user_id} заблокировал бота")
                                    continue  # Продолжаем рассылку следующему пользователю
                                else:
                                    print(f"Ошибка при отправке сообщения пользователю с ID {user_id}: {e}")
                                    continue  # Продолжаем рассылку следующему пользователю
                else:
                    print("Фотография не найдена.")
            elif call.data.startswith('send_distribution_'):
                distribution_id = self.database.get_latest_distribution_id()
                text = self.database.send_distribution_text(distribution_id)
                authorized_users = self.database.get_users()  # Получаем только авторизованных пользователей
                for user in authorized_users:
                    user_id = user[0]
                    try:
                        message = self.bot.send_message(user_id, text)
                        time.sleep(0.5)
                    except telebot.apihelper.ApiTelegramException as e:
                        if e.result.status_code == 403:
                            # Пользователь заблокировал бота
                            self.database.update_user_authorized(user_id, 0)
                            print(f"Пользователь с ID {user_id} заблокировал бота")
                            continue  # Продолжаем рассылку следующему пользователю
                        else:
                            print(f"Ошибка при отправке сообщения пользователю с ID {user_id}: {e}")
                            continue  # Продолжаем рассылку следующему пользователю                
            elif call.data == 'cancel_distribution':
                self.bot.send_message(call.message.chat.id, "Рассылка отменена", reply_markup=markup)                
                self.database.clear_pending_command(user_id)

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

        @self.bot.message_handler(func=lambda message: message.text.lower() == 'создать рассылку')
        def start_distribution(message):
            user_id = message.from_user.id
            text = "Документы:"
            distribution_id = self.database.save_distribution_text(text)
            self.database.set_pending_command(user_id, '/cd')  # Сохраняем команду в БД для последующего использования
            self.bot.send_message(message.chat.id, "Введите текст рассылки:")

        @self.bot.message_handler(func=lambda message: self.database.get_pending_command(message.from_user.id) == '/cd')
        def process_distribution_text(message):
            user_id = message.from_user.id
            if message.text == "Завершить загрузку":
                self.database.clear_pending_command(user_id)
                finish_distribution(message)
            elif message.text == "Отменить загрузку":
                self.database.clear_pending_command(user_id)
                cancel_distribution(message)
            else:
                if self.database.user_exists_id(user_id):
                    text = message.text
                    self.distribution.create_distribution_text(user_id, text)
                else:
                    __handle_start(message)


        @self.bot.message_handler(content_types=['photo'])
        def handle_photo(message):
            user_id = message.from_user.id
            if self.database.get_pending_command(user_id) == '/cd':
                self.distribution.process_distribution_photo(message)
        
        @self.bot.message_handler(content_types=['document'])
        def save_file(message):
            user_id = message.from_user.id
            if self.database.get_pending_command(user_id) == '/cd':               
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
                end_download_distribution_button = types.KeyboardButton(text="Завершить рассылку")
                cancel_download_distribution_button = types.KeyboardButton(text="Отменить рассылку")
                markup.add(end_download_distribution_button)
                markup.add(cancel_download_distribution_button)
                self.bot.send_message(message.chat.id, "Загружен файл:", reply_markup=markup) 
                self.distribution.create_distribution_with_file(message)  
            elif self.database.get_pending_command(user_id) == '/add_users':
                self.moderation.add_users(message)

        @self.bot.message_handler(func=lambda message: message.text.lower() == 'завершить загрузку')
        def finish_distribution(message):
            user_id = message.from_user.id            
            role = self.database.get_user_role(user_id) 
            if role != "user":      
                distribution_id = self.database.get_latest_distribution_id()   
                file_paths = self.database.get_distribution_file_paths(distribution_id)
                authorized_users = self.database.get_users()  # Получаем только авторизованных пользователей
                for user in authorized_users:
                    userd_id = user[0]
                    try:
                        self.bot.send_message(userd_id, "Документы:")
                        for file_path in file_paths:
                            with open(file_path, 'rb') as file:
                                self.bot.send_document(userd_id, file)
                        time.sleep(0.5)
                    except telebot.apihelper.ApiTelegramException as e:
                        if e.result.status_code == 403:
                            # Пользователь заблокировал бота
                            self.database.update_user_authorized(user_id, 0)
                            print(f"Пользователь с ID {user_id} заблокировал бота")
                            continue  # Продолжаем рассылку следующему пользователю
                        else:
                            print(f"Ошибка при отправке сообщения пользователю с ID {userd_id}: {e}")
                            continue  # Продолжаем рассылку следующему пользователю
                self.distribution.clear_file_paths()
                if role == 'admin':
                    markup = self.moderation.admin_markup()                
                    self.bot.send_message(message.chat.id, "Рассылка выполнена", reply_markup=markup)
                else:
                    markup = self.moderation.moder_markup()                
                    self.bot.send_message(message.chat.id, "Рассылка выполнена", reply_markup=markup)
            else:
                markup = self.moderation.user_markup()
                # Очистка команды ожидания после завершения рассылки
                self.database.clear_pending_command(user_id)
                self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)

        @self.bot.message_handler(func=lambda message: message.text.lower() == 'Отменить загрузку')
        def cancel_distribution(message):
            self.distribution.cancel_download_distribution(message)

        # Запуск бота
        self.bot.polling()