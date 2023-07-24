import configparser
import telebot
import time
import logging
from logging.handlers import TimedRotatingFileHandler
from .modules.database import Database
from telebot import types
from .modules.moderation import Moderation
from .modules.user_staff import User
from .modules.distribution import Distribution
import os
import datetime

# Установка пути к директории с лог-файлами
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Определение текущей даты
current_date = time.strftime("%Y-%m-%d", time.localtime())

# Настройка формата записей лога
log_format = "%(asctime)s - %(levelname)s - %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

# Настройка файла для записи логов
log_file = os.path.join(logs_dir, f"app_{current_date}.log")

# Настройка уровня логирования
log_level = logging.INFO # Выбор нужного уровня логирования (INFO, WARNING, ERROR, CRITICAL)

# Создание и настройка объекта логирования
logger = logging.getLogger(__name__)
logger.setLevel(log_level)
handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1)
handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
logger.addHandler(handler)

class DialogBot:
    def __init__(self):
        # Чтение файла конфигурации
        config = configparser.ConfigParser()
        config.read('./config.ini')
        self.i = 0
        self.photo_group = None
        self.phone_number = None

        # Получение значения токена из файла конфигурации
        self.token = config.get('default', 'token')
        self.bot = telebot.TeleBot(self.token)
        self.save_directory = config.get('default', 'save_directory')

        # Создание экземпляра класса Database
        self.database = Database(self.bot, self.menu_markup) 
        self.user = User(self.bot, self.database)  # Pass authorized_user=False
        self.moderation = Moderation(self.bot, self.save_directory)
        self.distribution = Distribution(self.bot, self.save_directory, self.i)

    @staticmethod
    def admin_markup():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        add_moderator_button = types.KeyboardButton(text="Модерация")
        markup.add(add_moderator_button)
        return markup

    @staticmethod
    def user_markup():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        distribution_button= types.KeyboardButton(text="Материалы")
        review_button= types.KeyboardButton(text="Оставить отзыв")
        markup.add(distribution_button)
        markup.add(review_button)
        return markup

    def menu_markup(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        distribution_button= types.KeyboardButton(text="Меню")
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
            self.phone_number = None

            self.bot.send_message(message.chat.id, "Для авторизации прошу поделиться вашим номером телефона", reply_markup=markup)

        # Обработчик получения контакта
        @self.bot.message_handler(content_types=['contact'])
        def __handle_contact(message):
            try:
                contact = message.contact
                user_id = message.from_user.id
                self.phone_number = contact.phone_number
                phone_number = contact.phone_number
    
                # Отправляем в базу данных значения user_id и phone_number
                self.database.set_user_data(user_id, self.phone_number)
    
                logger.info(f"User ID {user_id}, Phone_number: {self.phone_number}, регистрация")
    
                # Проверяем, существует ли пользователь в базе данных
                if self.database.user_exists_phone(phone_number):
                    # Обновляем запись существующего пользователя
                    self.database.update_user(user_id, phone_number)
                    # Переменная для получения роли пользователя
                    user_role = self.database.get_user_role(user_id)
                    # Получение пути к текущему скрипту
                    current_dir = os.path.dirname(os.path.abspath(__file__))
    
                    # Построение полного пути к файлу фотографии
                    media_dir = os.path.join(current_dir, 'modules', 'media')
                    photo_path = os.path.join(media_dir, 'avatar.png')
                    # Значения нет в таблице, выполняем вставку
                    text = "Спасибо за регистрацию ❤️\n\nВ течение ближайших двух месяцев вы будете учиться работать в информационном пространстве в современных условиях с учетом специфики вашего региона.\n\nПервый вебинар состоится уже на этой неделе, не пропустите приглашение 🔥\n\nСкоро в боте появятся функции базы знаний, чтобы вы могли всегда найти самое важное ✅"
                    photo = open(photo_path, 'rb')
                    self.bot.send_photo(message.chat.id, photo, caption=text)
                    markup = self.menu_markup()                    
                    self.bot.send_message(message.chat.id, "Вам теперь доступен функционал бота", reply_markup=markup)
                    self.phone_number = None
                else:
                    self.bot.send_message(message.chat.id, "Прошу ввести данные в следующем порядке:\n1. Фамилия\n2. Имя\n\nНапример:\nИванов Иван\n\nЕсли введете данные в другом порядке, вы можете попасть не в ту группу.\n\nДля изменения введенных фамилии и имени введите команду /start")
                    self.database.set_pending_command(user_id, '/fio')
                    user_role = None
    
                # Удаляем кнопку "Поделиться телефоном" из клавиатуры
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    
                if user_role == "admin" or user_role == "moderator":
                    moderation_button = types.KeyboardButton(text="Модерация")
                    markup.add(moderation_button)
                    self.bot.send_message(message.chat.id, "Теперь вы авторизованы и можете пользоваться другими командами бота.", reply_markup=markup)
                    self.bot.clear_reply_handlers(message)
                elif user_role == "user":
                    self.bot.clear_reply_handlers(message)
                else:                    
                    self.bot.clear_reply_handlers(message)
                    
            except Exception as e:
                # Запись исключения в лог с указанием traceback
                logger.exception("Произошла ошибка")
        
        @self.bot.message_handler(func=lambda message: self.database.get_pending_command(message.from_user.id) == '/fio')
        def handle_fio(message):
            try:
                user_id = message.from_user.id
                result_fio = self.database.handle_fio(message, self.phone_number) 
                self.phone_number = None
                logging.debug(message.text)    
                if result_fio is None:
                    self.bot.send_message(message.chat.id, "ФИО должно содержать два слова: Фамилия, имя\nПрошу повторить ввод")
                else:
                    self.database.clear_pending_command(user_id)
                    self.phone_number = None
                logger.info(f"User ID: {user_id}, FIO: {message.text}")
            except Exception as e:
                self.database.clear_pending_command(user_id)
                logger.exception("An error occurred in handle_fio:")
                self.bot.send_message(message.chat.id, "Произошла ошибка при обработке ФИО. Пожалуйста, повторите попытку позже.")

        # Вызов функции check_moderation при получении сообщения "Модерация"
        @self.bot.message_handler(func=lambda message: message.text == "Модерация")
        def handle_moderation(message):
            try:
                user_id = message.from_user.id
                if self.database.user_exists_id(user_id):
                    self.moderation.moderation_buttonn_klick(user_id)
                else:
                    __handle_start(message)
            except Exception as e:
                logger.exception("An error occurred in handle_moderation:")
                self.bot.send_message(message.chat.id, "Произошла ошибка при обработке модерации. Пожалуйста, повторите попытку позже.")

        @self.bot.message_handler(func=lambda message: message.text.lower() == 'добавить пользователей')
        def handle_add_users(message):
            try:
                user_id = message.from_user.id
                user_role = user_role = self.database.get_user_role(user_id)
                if self.database.user_exists_id(user_id):
                    if user_role != 'user':
                        self.database.set_pending_command(user_id, '/add_users')  # Сохраняем команду в БД для последующего использования
                        self.bot.send_message(message.chat.id, "Загрузите exel файл. \n\nОбязательные столбцы:\nphone_number - телефон пользователя\n\nОпциональные столбцы:\nfirst_name - имя\nlast_name - фамилия\nregion - регион\nuser_group - группа пользователей (Базовая, продвинутая, блогеры)")
                    else:
                        self.bot.send_message(user_id, "Недостаточно прав")
                else:
                    __handle_start(message)
            except Exception as e:
                logger.exception("An error occurred in handle_add_users:")
                self.bot.send_message(message.chat.id, "Произошла ошибка при обработке добавления пользователей. Пожалуйста, повторите попытку позже.")

        @self.bot.message_handler(func=lambda message: message.text == "Меню")
        def handle_menu(message):
            try:
                user_id = message.from_user.id
                user_role = self.database.get_user_role(user_id)
                if self.database.user_exists_id(user_id):
                    if user_role != 'user':
                        markup = self.admin_markup()
                        self.bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
                    elif user_role == 'user':
                        markup = self.user_markup()
                        self.bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
                    else:
                        markup = self.moderation.moder_markup()
                        self.bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
                else:
                    __handle_start(message)
            except Exception as e:
                logger.exception("An error occurred in handle_menu:")
                self.bot.send_message(message.chat.id, "Произошла ошибка при обработке меню. Пожалуйста, повторите попытку позже.")

        # Вызов функции add_moderator при получении сообщения "Добавить модератора"
        @self.bot.message_handler(func=lambda message: message.text == "Добавить модератора")
        def add_moderator_button(message):
            try:
                user_id = message.from_user.id
                if self.database.user_exists_id(user_id):
                    self.moderation.add_moderator_button(user_id)
                else:
                    __handle_start(message)
            except Exception as e:
                logger.exception("An error occurred in add_moderator_button:")
                self.bot.send_message(message.chat.id, "Произошла ошибка при добавлении модератора. Пожалуйста, повторите попытку позже.")
        
        # Обработчик команды /add_mod
        @self.bot.message_handler(commands=['add_mod'])
        def add_mod(message):
            try:
                user_id = message.from_user.id
                if self.database.user_exists_id(user_id):
                    phone_number = message.text[len('/add_mod') + 1:]
                    self.moderation.add_moderator(user_id, phone_number)
                else:
                    __handle_start(message)
            except Exception as e:
                logger.exception("An error occurred in add_moderator_button:")
                self.bot.send_message(message.chat.id, "Произошла ошибка при добавлении модератора. Пожалуйста, повторите попытку позже.")

        # Кнопки подтверждения/отмены
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_button_click(call):
            user_id = call.from_user.id
            try:
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
                    self.database.remove_moderator(phone_number)
                    markup = self.moderation.admin_markup()
                    self.bot.send_message(call.message.chat.id, "Модератор снят", reply_markup=markup)
                elif call.data == 'cancel_remove_mod':
                    self.bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
            except Exception as e:
                logger.exception("An error occurred in handle_button_click:")
                self.bot.send_message(user_id, "Произошла ошибка при обработке нажатия кнопки. Пожалуйста, повторите попытку позже.")

        # Вызов функции add_moderator при получении сообщения "Снять с поста модератора"
        @self.bot.message_handler(func=lambda message: message.text == "Снять с поста модератора")
        def remove_moderator_button(message):
            user_id = message.from_user.id
            try:
                self.moderation.remove_moderator_button(user_id)
            except Exception as e:
                logger.exception("An error occurred in remove_moderator_button:")
                self.bot.send_message(user_id, "Произошла ошибка при обработке запроса. Пожалуйста, повторите попытку позже.")
        
        # Обработчик команды /remove_mod
        @self.bot.message_handler(commands=['remove_mod'])
        def remove_mod(message):
            user_id = message.from_user.id
            try:
                if self.database.user_exists_id(user_id):
                    phone_number = message.text[len('/remove_mod') + 1:]
                    self.moderation.remove_moderator(user_id, phone_number)
                else:
                    __handle_start(message)
            except Exception as e:
                logger.exception("An error occurred in remove_mod:")
                self.bot.send_message(user_id, "Произошла ошибка при обработке команды. Пожалуйста, повторите попытку позже.")

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_button_click(call):
            user_id = call.from_user.id
            try:
                message_id = call.message.message_id
                self.user.handle_button_click(call, message_id)
            except Exception as e:
                logger.exception("An error occurred in handle_button_click:")
                self.bot.send_message(call.from_user.id, "Произошла ошибка при обработке нажатия кнопки. Пожалуйста, повторите попытку позже.")


        @self.bot.message_handler(func=lambda message: message.text.lower() == 'создать рассылку')
        def start_distribution(message):
            user_id = message.from_user.id
            try:
                text = "Документы:"
                distribution_id = self.database.save_distribution_text(text)
                self.distribution.clear_file_paths()
                self.distribution.clear_media_group()
                self.database.set_pending_command(user_id, '/cd')  # Сохраняем команду в БД для последующего использования
                self.bot.send_message(message.chat.id, "Введите текст рассылки, или приложите файлы \n\nНа данный момент поддерживаются:\n1.Текстовая рассылка\n2.До 9 фотографий с подписью\n3.Документы без подписи")
                logger.info(f"User ID: {user_id}, создание рассылки")
            except Exception as e:
                logger.exception("An error occurred in start_distribution:")
                self.bot.send_message(user_id, "Произошла ошибка при начале создания рассылки. Пожалуйста, повторите попытку позже.")

        @self.bot.message_handler(func=lambda message: self.database.get_pending_command(message.from_user.id) == '/cd')
        def process_distribution_text(message):
            user_id = message.from_user.id
            try:
                if message.text == "Завершить рассылку":
                    self.database.clear_pending_command(user_id)
                    finish_text_distribution(message)
                elif message.text == "Отменить рассылку":
                    self.i = 0
                    self.distribution.clear_i()
                    self.database.clear_pending_command(user_id)
                    cancel_distribution(message)
                elif message.text == "Выбрать группы":
                    self.database.clear_pending_command(user_id)
                    select_groups_document_button(message)
                elif message.text == "Завершить загрузку фото":
                    self.distribution.clear_i()
                    final_photo_distribution(message)
                else:
                    if self.database.user_exists_id(user_id):
                        text = message.text
                        self.distribution.create_distribution_text(message)
                    else:
                        __handle_start(message)
            except Exception as e:
                self.database.clear_pending_command(user_id)
                logger.exception("An error occurred in process_distribution_text:")
                self.bot.send_message(user_id, "Произошла ошибка при обработке рассылки. Пожалуйста, повторите попытку позже.")
        
        #Текстовая рассылка
        @self.bot.message_handler(func=lambda message: message.text.lower() == 'выполнить рассылку')
        def finish_text_distribution(message):
            user_id = message.from_user.id
            try:           
                role = self.database.get_user_role(user_id)
                distribution_id = self.database.get_latest_distribution_id()
                if role != "user":
                    text = self.database.send_distribution_text(distribution_id)
                    text_entities = message.entities or []  # Получение форматирования текста во входном сообщении
                    entities = [types.MessageEntity(type=entity.type, offset=entity.offset, length=entity.length) for entity in text_entities]
                    hide_keyboard = types.ReplyKeyboardRemove()
                    self.bot.send_message(user_id, "Производится рассылка, ожидайте уведомления о ее завершении", reply_markup=hide_keyboard)
    
                    # Выделение отрывков, заключенных в знаки *
                    text_parts = text.split('*')
                    for i in range(1, len(text_parts), 2):
                        text_parts[i] = f"<b>{text_parts[i]}</b>"
                    text = ''.join(text_parts)
    
                    for userd_id in self.user_ids:
                        try:
                            markup = self.user_markup()
                            self.bot.send_message(userd_id, text, parse_mode='HTML', entities=entities, reply_markup=markup)
                            logger.info(f"User ID: {userd_id}, успешная доставка текста") 
                            time.sleep(3)
                        except telebot.apihelper.ApiTelegramException as e:
                            if e.result.status_code == 403:
                                # Пользователь заблокировал бота
                                self.database.update_user_authorized(userd_id, 0)
                                logger.info(f"Пользователь с ID {userd_id} заблокировал бота")
                                continue  # Продолжаем рассылку следующему пользователю
                            else:
                                logger.exception(f"Ошибка при отправке сообщения пользователю с ID {userd_id}: {e}")
                                continue  # Продолжаем рассылку следующему пользователю
                    if role == 'admin':
                        markup = self.moderation.admin_markup()                
                        self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                        logger.info(f"User ID: {user_id}, тектовая рассылка завершена") 
                    else:
                        markup = self.moderation.moder_markup()                
                        self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                        logger.info(f"User ID: {user_id}, тектовая рассылка завершена") 
                else:
                    self.database.clear_pending_command(user_id)
                    self.bot.send_message(user_id, "У вас недостаточно прав")
            except Exception as e:
                self.database.clear_pending_command(user_id)
                logger.exception("An error occurred in finish_text_distribution:")
                self.bot.send_message(user_id, "Произошла ошибка при обработке рассылки. Пожалуйста, повторите попытку позже.")
                

        #Если загружено фото
        @self.bot.message_handler(content_types=['photo'])
        def handle_photo(message):
            user_id = message.from_user.id
            try:
                if self.database.get_pending_command(user_id) == '/cd':                
                    self.distribution.process_distribution_photo(message)
                logger.info(f"User ID: {user_id}, получение фото в рассылке")  
            except Exception as e:
                logger.exception("An error occurred in handle_photo:")
                self.bot.send_message(user_id, "Произошла ошибка при загрузке фото. Пожалуйста, повторите попытку позже.")
                
        
        @self.bot.message_handler(func=lambda message: message.text.lower() == 'завершить загрузку фото')
        def final_photo_distribution(message):
            self.photo_group = self.distribution.final_distribution_photo(message)

        #Если загружен документ
        @self.bot.message_handler(content_types=['document'])
        def save_file(message):
            user_id = message.from_user.id
            try:
                if self.database.get_pending_command(user_id) == '/cd':
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
                    select_groups_button = types.KeyboardButton(text="Выбрать группы")
                    cancel_download_distribution_button = types.KeyboardButton(text="Отменить рассылку")
                    markup.add(select_groups_button)
                    markup.add(cancel_download_distribution_button)
                    self.bot.send_message(message.chat.id, "Загружен файл:", reply_markup=markup) 
                    self.distribution.create_distribution_with_file(message)  
                elif self.database.get_pending_command(user_id) == '/add_users':
                    self.moderation.add_users(message)
                logger.info(f"User ID: {user_id}, получение документа в рассылке") 
            except Exception as e:
                logger.exception("An error occurred in save_file:")
                self.bot.send_message(user_id, "Произошла ошибка при загрузке документа. Пожалуйста, повторите попытку позже.")

        #Обработка кнопки "завершить рассылку документов"
        @self.bot.message_handler(func=lambda message: message.text.lower() == 'завершить рассылку документов')
        def finish_document_distribution(message):
            user_id = message.from_user.id      
            try:
                logger.info(f"User ID: {user_id}, создание рассылки документов") 
                role = self.database.get_user_role(user_id) 
                if role != "user":      
                    distribution_id = self.database.get_latest_distribution_id()
                    file_paths = self.database.get_distribution_file_paths(distribution_id)
                    hide_keyboard = types.ReplyKeyboardRemove()
                    self.bot.send_message(user_id, "Производится рассылка, ожидайте уведомления о ее завершении", reply_markup=hide_keyboard)
                    for userd_id in self.user_ids:
                        markup = self.user_markup()
                        try:
                            self.bot.send_message(userd_id, "Документы:")
                            for file_path in file_paths:
                                with open(file_path, 'rb') as file:
                                    self.bot.send_document(userd_id, file)
                                    logger.info(f"User ID: {userd_id}, успешная доставка документов") 
                            time.sleep(3)
                        except telebot.apihelper.ApiTelegramException as e:
                            if e.result.status_code == 403:
                                # Пользователь заблокировал бота
                                self.database.update_user_authorized(userd_id, 0)
                                logger.info(f"Пользователь с ID {userd_id} заблокировал бота")
                                continue  # Продолжаем рассылку следующему пользователю
                            else:
                                logger.exception(f"Ошибка при отправке сообщения пользователю с ID {userd_id}: {e}")
                                continue  # Продолжаем рассылку следующему пользователю
                    self.distribution.clear_file_paths()
                    if role == 'admin':
                        markup = self.moderation.admin_markup()                
                        self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                        logger.info(f"User ID {user_id}: рассылка документов завершена")
                    else:
                        markup = self.moderation.moder_markup()                
                        self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                        logger.info(f"User ID {user_id}: рассылка документов завершена")
                else:
                    self.database.clear_pending_command(user_id)
                    self.bot.send_message(user_id, "У вас недостаточно прав")
            except Exception as e:
                self.database.clear_pending_command(user_id)
                logger.exception("An error occurred in finish_document_distribution:")
                self.bot.send_message(user_id, "Произошла ошибка при завершении рассылки. Пожалуйста, повторите попытку позже.")

        @self.bot.message_handler(func=lambda message: message.text.lower() == 'отменить рассылку')
        def cancel_distribution(message):
            self.distribution.cancel_distribution(message)

        @self.bot.message_handler(func=lambda message: message.text.lower() == 'выбрать группы')
        def select_groups_document_button(message):
            user_id = message.from_user.id
            self.database.set_pending_command(user_id, '/sdg')  # Сохраняем команду в БД для последующего использования
            region_values = self.database.get_unique_column_values("region")
            user_group_values = self.database.get_unique_column_values("user_group")
            region_values_str = "\n".join(str(value) for value in region_values if value is not None)
            user_group_values_str = "\n".join(str(value) for value in user_group_values if value is not None)
            message_text = f"Введите через запятую группы для рассылки, например:\nТестовая, базовая, Москва\n\nЧтобы отправить всем авторизованным в боте пользователям, введите 'все'\n\nДоступные группы:\nРегионы:\n{region_values_str}\n\nГруппы:\n{user_group_values_str}"
            self.bot.send_message(message.chat.id, message_text)
       
        #Получение пользователей определенных групп
        @self.bot.message_handler(func=lambda message: self.database.get_pending_command(message.from_user.id) == '/sdg')
        def select_document_groups(message):
            user_id = message.from_user.id
            try:
                logger.info(f"User ID: {user_id}, создание рассылки с документами") 
                # Получение введенных слов из сообщения и разделение их по запятой
                words = message.text.split(',')
                words = [word.strip().rstrip(',') for word in words]  # Удаление лишних пробелов
    
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
                finish_distribution_button = types.KeyboardButton(text="Завершить рассылку документов")
                cancel_download_distribution_button = types.KeyboardButton(text="Отменить рассылку")
                markup.add(finish_distribution_button)
                markup.add(cancel_download_distribution_button)    
    
                if "все" in words:
                    self.user_ids = [user[0] for user in self.database.get_users()]
                else:
                    # Получение идентификаторов пользователей, удовлетворяющих условиям поиска
                    self.user_ids = self.database.find_users_by_event_or_group(words)
                    self.user_ids = list(set(self.user_ids))
                    self.database.clear_pending_command(user_id)
    
                self.bot.send_message(message.chat.id, "Группы рассылки назначены", reply_markup=markup) 
            except Exception as e:
                self.database.clear_pending_command(user_id)
                logger.exception("An error occurred in select_document_groups:")
                self.bot.send_message(user_id, "Произошла ошибка при назначении групп. Пожалуйста, повторите попытку позже.")

        @self.bot.message_handler(func=lambda message: message.text.lower() == 'назначить группы')
        def select_groups_text_button(message):
            user_id = message.from_user.id
            self.database.set_pending_command(user_id, '/stg')  # Сохраняем команду в БД для последующего использования
            region_values = self.database.get_unique_column_values("region")
            user_group_values = self.database.get_unique_column_values("user_group")
            region_values_str = "\n".join(str(value) for value in region_values if value is not None)
            user_group_values_str = "\n".join(str(value) for value in user_group_values if value is not None)
            message_text = f"Введите через запятую группы для рассылки, например:\nТестовая, базовая, Москва\n\nЧтобы отправить всем авторизованным в боте пользователям, введите 'все'\n\nДоступные группы:\nРегионы:\n{region_values_str}\n\nГруппы:\n{user_group_values_str}"
            self.bot.send_message(message.chat.id, message_text)
       
        #Получение пользователей определенных групп
        @self.bot.message_handler(func=lambda message: self.database.get_pending_command(message.from_user.id) == '/stg')
        def select_text_groups(message):
            user_id = message.from_user.id
            try:
                logger.info(f"User ID: {user_id}, создание текстовой рассылки") 
                # Получение введенных слов из сообщения и разделение их по запятой
                words = message.text.split(',')
                words = [word.strip().rstrip(',') for word in words]  # Удаление лишних пробелов
    
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
                finish_distribution_button = types.KeyboardButton(text="Выполнить рассылку")
                cancel_download_distribution_button = types.KeyboardButton(text="Отменить рассылку")
                markup.add(finish_distribution_button)
                markup.add(cancel_download_distribution_button)
    
                if "все" in words:
                    self.user_ids = [user[0] for user in self.database.get_users()]
                else:
                    # Получение идентификаторов пользователей, удовлетворяющих условиям поиска
                    self.user_ids = self.database.find_users_by_event_or_group(words)
                    self.user_ids = list(set(self.user_ids))
                    self.database.clear_pending_command(user_id)
    
                self.bot.send_message(message.chat.id, "Группы рассылки назначены", reply_markup=markup) 
            except Exception as e:
                self.database.clear_pending_command(user_id)
                logger.exception("An error occurred in select_text_groups:")
                self.bot.send_message(user_id, "Произошла ошибка при назначении групп. Пожалуйста, повторите попытку позже.")

        @self.bot.message_handler(func=lambda message: message.text.lower() == 'добавить группы')
        def select_groups_photo_button(message):
            user_id = message.from_user.id            
            self.distribution.clear_i()
            self.database.set_pending_command(user_id, '/spg')  # Сохраняем команду в БД для последующего использования
            region_values = self.database.get_unique_column_values("region")
            user_group_values = self.database.get_unique_column_values("user_group")
            region_values_str = "\n".join(str(value) for value in region_values if value is not None)
            user_group_values_str = "\n".join(str(value) for value in user_group_values if value is not None)
            message_text = f"Введите через запятую группы для рассылки, например:\nТестовая, базовая, Москва\n\nЧтобы отправить всем авторизованным в боте пользователям, введите 'все'\n\nДоступные группы:\nРегионы:\n{region_values_str}\n\nГруппы:\n{user_group_values_str}"
            self.bot.send_message(message.chat.id, message_text)
       
        #Получение пользователей определенных групп
        @self.bot.message_handler(func=lambda message: self.database.get_pending_command(message.from_user.id) == '/spg')
        def select_photo_groups(message):
            user_id = message.from_user.id
            try:
                logger.info(f"User ID: {user_id}, создание рассылки с фото") 
                # Получение введенных слов из сообщения и разделение их по запятой
                words = message.text.split(',')
                words = [word.strip().rstrip(',') for word in words]  # Удаление лишних пробелов
    
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
                finish_distribution_button = types.KeyboardButton(text="Завершить рассылку")
                cancel_download_distribution_button = types.KeyboardButton(text="Отменить рассылку")
                markup.add(finish_distribution_button)
                markup.add(cancel_download_distribution_button)            
    
                if "все" in words:
                    self.user_ids = [user[0] for user in self.database.get_users()]
                else:
                    # Получение идентификаторов пользователей, удовлетворяющих условиям поиска
                    self.user_ids = self.database.find_users_by_event_or_group(words)
                    self.user_ids = list(set(self.user_ids))
                    self.database.clear_pending_command(user_id)
    
                self.bot.send_message(message.chat.id, "Группы рассылки назначены", reply_markup=markup) 
            except Exception as e:
                logger.exception("An error occurred in select_text_groups:")
                self.bot.send_message(user_id, "Произошла ошибка при назначении групп. Пожалуйста, повторите попытку позже.")

        # Отправка фото
        @self.bot.message_handler(func=lambda message: message.text.lower() == 'завершить рассылку')
        def finish_photo_distribution(message):
            user_id = message.from_user.id      
            try:
                logger.info(f"User ID: {user_id}, создание рассылки с фото")        
                role = self.database.get_user_role(user_id)
                if role != "user":
                    hide_keyboard = types.ReplyKeyboardRemove()
                    self.bot.send_message(user_id, "Производится рассылка, ожидайте уведомления о ее завершении", reply_markup=hide_keyboard)
                    for userd_id in self.user_ids:
                        markup = self.user_markup()
                        try:
                            message = self.bot.send_media_group(userd_id, self.photo_group)
                            time.sleep(3)
                            logger.info(f"User ID: {userd_id}, фото доставлено")   
                        except telebot.apihelper.ApiTelegramException as e:
                            if e.result.status_code == 403:
                                # Пользователь заблокировал бота
                                self.database.update_user_authorized(userd_id, 0)
                                logger.info(f"Пользователь с ID {userd_id} заблокировал бота")   
                                continue  # Продолжаем рассылку следующему пользователю
                            else:
                                logger.exception(f"Ошибка при отправке сообщения пользователю с ID {userd_id}: {e}")
                                continue  # Продолжаем рассылку следующему пользователю       
                    if role == 'admin':
                        markup = self.moderation.admin_markup()                
                        self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                        logger.info(f"User ID: {user_id}, рассылка фото завершена")
                    else:
                        markup = self.moderation.moder_markup()                
                        self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                        logger.info(f"User ID: {user_id}, рассылка фото завершена")
                else:
                    self.database.clear_pending_command(user_id)
                    self.bot.send_message(user_id, "У вас недостаточно прав")
            except Exception as e:
                self.database.clear_pending_command(user_id)
                logger.exception("An error occurred in finish_photo_distribution:")
                self.bot.send_message(user_id, "Произошла ошибка при завершении рассылки. Пожалуйста, повторите попытку позже.")

        # Обработка кнопки "Выгрузить пользователей"
        @self.bot.message_handler(func=lambda message: message.text == "Выгрузить пользователей")
        def handle_moderation(message):
            user_id = message.from_user.id
            if self.database.user_exists_id(user_id):
                logger.info(f"User ID: {user_id}, запрос пользователей")
                self.moderation.get_users_excel(message)
            else:
                __handle_start(message)

        #Если загружен документ
        @self.bot.message_handler(content_types=['video'])
        def handle_video_file(message):
            user_id = message.from_user.id
            if self.database.get_pending_command(user_id) == '/cd':
                try:
                    hide_keyboard = types.ReplyKeyboardRemove()
                    self.bot.send_message(message.chat.id, 'Ожидайте загрузки видео', reply_markup=hide_keyboard)
                    self.distribution.handle_video_file(message)
                except telebot.apihelper.ApiTelegramException as e:
                    if "file is too big" in str(e):
                        logger.info(f"User_ID {user_id}: Слишком большое видео")
                        self.bot.send_message(message.chat.id, "Ошибка: видеофайл слишком большой для отправки.")
                    else:
                        logger.exception("An error occurred in handle_video_file:")
                        self.bot.send_message(message.chat.id, "Произошла ошибка при отправке видео. Пожалуйста, повторите попытку позже.")
        
        #Обработка видео
        @self.bot.message_handler(func=lambda message: self.database.get_pending_command(message.from_user.id) == '/svgg')
        def select_video_groups(message):
            if message.text == "Группы видеорассылки":
                user_id = message.from_user.id
                region_values = self.database.get_unique_column_values("region")
                user_group_values = self.database.get_unique_column_values("user_group")
                region_values_str = "\n".join(str(value) for value in region_values if value is not None)
                user_group_values_str = "\n".join(str(value) for value in user_group_values if value is not None)
                self.database.set_pending_command(user_id, '/svg')   
                message_text = f"Введите через запятую группы для рассылки, например:\nТестовая, базовая, Москва\n\nЧтобы отправить всем авторизованным в боте пользователям, введите 'все'\n\nДоступные группы:\nРегионы:\n{region_values_str}\n\nГруппы:\n{user_group_values_str}"
                self.bot.send_message(message.chat.id, message_text)
                
            elif message.text == "Завершить видеорассылку":
                user_id = message.from_user.id           
                try:
                    logger.info(f"User ID: {user_id}, создание рассылки с видео")  
                    role = self.database.get_user_role(user_id)
                    if role != "user":
                        hide_keyboard = types.ReplyKeyboardRemove()
                        self.bot.send_message(user_id, "Производится рассылка, ожидайте уведомления о ее завершении", reply_markup=hide_keyboard)
                        distribution_id = self.database.get_latest_distribution_id()
                        video_id = self.database.get_distribution_file_paths(distribution_id)[0]
                        message_id = self.database.get_message_id_by_video_id(video_id)
                        for userd_id in self.user_ids:
                            try:
                                self.bot.forward_message(userd_id, message.chat.id, message_id)  # Пересылаем сообщение с видео
                                time.sleep(3)
                                logger.info(f"User ID: {userd_id}, видео доставлено")   
                            except telebot.apihelper.ApiTelegramException as e:
                                if e.result.status_code == 403:
                                    # Пользователь заблокировал бота
                                    self.database.update_user_authorized(userd_id, 0)
                                    logger.info(f"Пользователь с ID {userd_id} заблокировал бота")
                                    continue  # Продолжаем рассылку следующему пользователю
                                else:
                                    logger.exception(f"Ошибка при отправке сообщения пользователю с ID {userd_id}: {e}")
                                    continue  # Продолжаем рассылку следующему пользователю       
                        if role == 'admin':
                            markup = self.moderation.admin_markup()                
                            self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                        else:
                            markup = self.moderation.moder_markup()                
                            self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                    else:
                        self.database.clear_pending_command(user_id)
                        self.bot.send_message(user_id, "У вас недостаточно прав")
                    self.database.clear_pending_command(user_id)
                except Exception as e:
                    logger.exception("An error occurred in finish_photo_distribution:")
                    self.database.clear_pending_command(user_id)
                    self.bot.send_message(user_id, "Произошла ошибка при завершении рассылки. Пожалуйста, повторите попытку позже.")
        
        #Получение пользователей определенных групп
        @self.bot.message_handler(func=lambda message: self.database.get_pending_command(message.from_user.id) == '/svg')
        def select_video_groups(message):
            user_id = message.from_user.id
            try:
                logger.info(f"User ID: {user_id}, создание рассылки с фото") 
                # Получение введенных слов из сообщения и разделение их по запятой
                words = message.text.split(',')
                words = [word.strip().rstrip(',') for word in words]  # Удаление лишних пробелов

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
                finish_distribution_button = types.KeyboardButton(text="Завершить видеорассылку")
                cancel_download_distribution_button = types.KeyboardButton(text="Отменить рассылку")
                markup.add(finish_distribution_button)
                markup.add(cancel_download_distribution_button)            

                if "все" in words:
                    self.user_ids = [user[0] for user in self.database.get_users()]
                else:
                    # Получение идентификаторов пользователей, удовлетворяющих условиям поиска
                    self.user_ids = self.database.find_users_by_event_or_group(words)
                    self.user_ids = list(set(self.user_ids))
                
                self.database.set_pending_command(user_id, '/svgg')    
                self.bot.send_message(message.chat.id, "Группы рассылки назначены", reply_markup=markup) 
            except Exception as e:
                logger.exception("An error occurred in select_video_groups:")
                self.bot.send_message(user_id, "Произошла ошибка при назначении групп. Пожалуйста, повторите попытку позже.")
        
        # Обработка кнопки "Материалы"
        @self.bot.message_handler(func=lambda message: message.text == 'Материалы')
        def get_materials(message):
            user_id = message.from_user.id
            try:
                logger.info(f"User ID: {user_id}, получение материалов") 
                self.user.get_materials(message)
            except Exception as e:
                logger.exception("An error occurred in get_materials:")
                self.bot.send_message(user_id, "Ошибка при отправке материалов. Пожалуйста, повторите попытку позже")
        
        # Обработка кнопки "Оставить отзыв"
        @self.bot.message_handler(func=lambda message: message.text == 'Оставить отзыв')
        def get_review(message):
            user_id = message.from_user.id
            try:
                logger.info(f"User ID: {user_id}, получение отзыва") 
                self.user.get_review(message)
            except Exception as e:
                logger.exception("An error occurred in get_materials:")
                self.bot.send_message(user_id, "Ошибка при обработке кнопки. Пожалуйста, повторите попытку позже")

        # Запуск бота
        self.bot.polling()