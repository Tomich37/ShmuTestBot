import configparser
import telebot
import time
from .modules.database import Database
from telebot import types
from .modules.moderation import Moderation
from .modules.user_staff import User
from .modules.distribution import Distribution
import os


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
        self.database = Database(self.bot) 
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

    # @staticmethod
    # def user_markup():
    #     markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    #     distribution_button= types.KeyboardButton(text="События")
    #     markup.add(distribution_button)
    #     return markup

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
            contact = message.contact
            user_id = message.from_user.id
            self.phone_number = contact.phone_number
            phone_number = contact.phone_number

            # Отправляем в базу данных значения user_id и phone_number
            self.database.set_user_data(user_id, self.phone_number)

            print(user_id, self.phone_number)

            # Проверяем, существует ли пользователь в базе данных
            if self.database.user_exists_phone(phone_number):
                # Обновляем запись существующего пользователя
                self.database.update_user(user_id, phone_number)
                self.authorized_user = True
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
                print(user_role)
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

            # Обновляем атрибут authorized_user в экземпляре класса User
            self.user.authorized_user = self.authorized_user
        
        @self.bot.message_handler(func=lambda message: self.database.get_pending_command(message.from_user.id) == '/fio')
        def handle_fio(message):
            user_id = message.from_user.id
            result_fio = self.database.handle_fio(message, self.phone_number) 
            self.phone_number = None
            print(message.text)    
            if result_fio is None:
                self.bot.send_message(message.chat.id, "ФИО должно содержать два слова: Фамилия, имя\nПрошу повторить ввод")
            else:
                self.database.clear_pending_command(user_id)
                self.phone_number = None


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
                    self.bot.send_message(message.chat.id, "Загрузите exel файл. \n\nОбязательные столбцы:\nphone_number - телефон пользователя\n\nОпциональные столбцы:\nfirst_name - имя\nlast_name - фамилия\nregion - регион\nuser_group - группа пользователей (Базовая, продвинутая, блогеры)")
                else:
                    self.bot.send_message(user_id, "Недостаточно прав")
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
                                print(user_id, "фото доставлено")
                                time.sleep(3)
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
        # @self.bot.message_handler(func=lambda message: message.text == "События")
        # def __handle_events_button(message):
        #     user_id = message.from_user.id
        #     if self.database.user_exists_id(user_id):
        #         self.user.events_handler(message)
        #     else:
        #         __handle_start(message)

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
            self.distribution.clear_file_paths()
            self.distribution.clear_media_group()
            self.database.set_pending_command(user_id, '/cd')  # Сохраняем команду в БД для последующего использования
            self.bot.send_message(message.chat.id, "Введите текст рассылки, или приложите файлы \n\nНа данный момент поддерживаются:\n1.Текстовая рассылка\n2.До 9 фотографий с подписью\n3.Документы без подписи")

        @self.bot.message_handler(func=lambda message: self.database.get_pending_command(message.from_user.id) == '/cd')
        def process_distribution_text(message):
            user_id = message.from_user.id
            if message.text == "Завершить рассылку":
                self.database.clear_pending_command(user_id)
                finish_text_distribution(message)
            elif message.text == "Отменить рассылку":
                self.database.clear_pending_command(user_id)
                cancel_distribution(message)
            elif message.text == "Выбрать группы":
                self.database.clear_pending_command(user_id)
                select_groups_document_button(message)
            elif message.text == "Завершить загрузку фото":
                self.database.clear_pending_command(user_id)
                final_photo_distribution(message)
            else:
                if self.database.user_exists_id(user_id):
                    text = message.text
                    self.distribution.create_distribution_text(user_id, text)
                else:
                    __handle_start(message)
        
        #Текстовая рассылка
        @self.bot.message_handler(func=lambda message: message.text.lower() == 'выполнить рассылку')
        def finish_text_distribution(message):
            user_id = message.from_user.id            
            role = self.database.get_user_role(user_id)
            distribution_id = self.database.get_latest_distribution_id()
            if role != "user":      
                text = self.database.send_distribution_text(distribution_id)              
                hide_keyboard = types.ReplyKeyboardRemove()
                self.bot.send_message(user_id, "Производится рассылка, ожидайте уведомления о ее завершении", reply_markup=hide_keyboard)
                for userd_id in self.user_ids:
                    try:
                        self.bot.send_message(userd_id, text)
                        print(userd_id, "текст доставлен")
                        time.sleep(3)
                    except telebot.apihelper.ApiTelegramException as e:
                        if e.result.status_code == 403:
                            # Пользователь заблокировал бота
                            self.database.update_user_authorized(userd_id, 0)
                            print(f"Пользователь с ID {userd_id} заблокировал бота")
                            continue  # Продолжаем рассылку следующему пользователю
                        else:
                            print(f"Ошибка при отправке сообщения пользователю с ID {userd_id}: {e}")
                            continue  # Продолжаем рассылку следующему пользователю 
                if role == 'admin':
                    markup = self.moderation.admin_markup()                
                    self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                    print(user_id, 'тектовая рассылка завершена')
                else:
                    markup = self.moderation.moder_markup()                
                    self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                    print(user_id, 'тектовая рассылка завершена')
            else:
                self.database.clear_pending_command(user_id)
                self.bot.send_message(user_id, "У вас недостаточно прав")

        #Если загружено фото
        @self.bot.message_handler(content_types=['photo'])
        def handle_photo(message):
            user_id = message.from_user.id
            if self.database.get_pending_command(user_id) == '/cd':                
                self.distribution.process_distribution_photo(message)
                
        
        @self.bot.message_handler(func=lambda message: message.text.lower() == 'завершить загрузку фото')
        def final_photo_distribution(message):
           self.photo_group = self.distribution.final_distribution_photo(message)

        #Если загружен документ
        @self.bot.message_handler(content_types=['document'])
        def save_file(message):
            user_id = message.from_user.id
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

        #Обработка кнопки "завершить рассылку документов"
        @self.bot.message_handler(func=lambda message: message.text.lower() == 'завершить рассылку документов')
        def finish_document_distribution(message):
            user_id = message.from_user.id            
            role = self.database.get_user_role(user_id) 
            if role != "user":      
                distribution_id = self.database.get_latest_distribution_id()
                file_paths = self.database.get_distribution_file_paths(distribution_id)
                hide_keyboard = types.ReplyKeyboardRemove()
                self.bot.send_message(user_id, "Производится рассылка, ожидайте уведомления о ее завершении", reply_markup=hide_keyboard)
                for userd_id in self.user_ids:
                    try:
                        self.bot.send_message(userd_id, "Документы:")
                        for file_path in file_paths:
                            with open(file_path, 'rb') as file:
                                self.bot.send_document(userd_id, file)
                                print(userd_id, "документы доставлены")
                        time.sleep(3)
                    except telebot.apihelper.ApiTelegramException as e:
                        if e.result.status_code == 403:
                            # Пользователь заблокировал бота
                            self.database.update_user_authorized(userd_id, 0)
                            print(f"Пользователь с ID {userd_id} заблокировал бота")
                            continue  # Продолжаем рассылку следующему пользователю
                        else:
                            print(f"Ошибка при отправке сообщения пользователю с ID {userd_id}: {e}")
                            continue  # Продолжаем рассылку следующему пользователю
                self.distribution.clear_file_paths()
                if role == 'admin':
                    markup = self.moderation.admin_markup()                
                    self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                    print(user_id, 'рассылка документов завершена')
                else:
                    markup = self.moderation.moder_markup()                
                    self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                    print(user_id, 'рассылка документов завершена')
            else:
                self.database.clear_pending_command(user_id)
                self.bot.send_message(user_id, "У вас недостаточно прав")

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
            print("Создание рассылки документов")
            user_id = message.from_user.id
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
            print("Создание текстовой рассылки")
            user_id = message.from_user.id
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
            print("Создание рассылки с фото")
            user_id = message.from_user.id
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

        # Отправка фото
        @self.bot.message_handler(func=lambda message: message.text.lower() == 'завершить рассылку')
        def finish_photo_distribution(message):
            user_id = message.from_user.id            
            role = self.database.get_user_role(user_id)
            if role != "user":
                hide_keyboard = types.ReplyKeyboardRemove()
                self.bot.send_message(user_id, "Производится рассылка, ожидайте уведомления о ее завершении", reply_markup=hide_keyboard)
                for userd_id in self.user_ids:
                    try:
                        message = self.bot.send_media_group(userd_id, self.photo_group)
                        time.sleep(3)
                        print(userd_id, 'фото доставлено')
                    except telebot.apihelper.ApiTelegramException as e:
                        if e.result.status_code == 403:
                            # Пользователь заблокировал бота
                            self.database.update_user_authorized(userd_id, 0)
                            print(f"Пользователь с ID {userd_id} заблокировал бота")
                            continue  # Продолжаем рассылку следующему пользователю
                        else:
                            print(f"Ошибка при отправке сообщения пользователю с ID {userd_id}: {e}")
                            continue  # Продолжаем рассылку следующему пользователю       
                if role == 'admin':
                    markup = self.moderation.admin_markup()                
                    self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                    print(user_id, 'рассылка фото завершена')
                else:
                    markup = self.moderation.moder_markup()                
                    self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
                    print(user_id, 'рассылка фото завершена')
            else:
                self.database.clear_pending_command(user_id)
                self.bot.send_message(user_id, "У вас недостаточно прав")

        @self.bot.message_handler(func=lambda message: message.text == "Выгрузить пользователей")
        def handle_moderation(message):
            user_id = message.from_user.id
            if self.database.user_exists_id(user_id):
                print("Запрос пользователей")
                self.moderation.get_users_excel(message)
            else:
                __handle_start(message)

        #Если загружен документ
        @self.bot.message_handler(content_types=['video'])
        def handle_video_file(message):
            user_id = message.from_user.id
            if self.database.get_pending_command(user_id) == '/cd':
                try:
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
                    select_groups_button = types.KeyboardButton(text="Группы видеорассылки")
                    cancel_download_distribution_button = types.KeyboardButton(text="Отменить рассылку")
                    markup.add(select_groups_button)
                    markup.add(cancel_download_distribution_button)
                    self.bot.send_message(message.chat.id, "Загружен файл:", reply_markup=markup) 
                    self.distribution.handle_video_file(message)
                except telebot.apihelper.ApiTelegramException as e:
                    if "file is too big" in str(e):
                        self.bot.send_message(message.chat.id, "Ошибка: видеофайл слишком большой для отправки.")
                    else:
                        self.bot.send_message(message.chat.id, f"Произошла ошибка при отправке видео: {str(e)}")
        
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
                            print(userd_id, 'видео доставлено')
                        except telebot.apihelper.ApiTelegramException as e:
                            if e.result.status_code == 403:
                                # Пользователь заблокировал бота
                                self.database.update_user_authorized(userd_id, 0)
                                print(f"Пользователь с ID {userd_id} заблокировал бота")
                                continue  # Продолжаем рассылку следующему пользователю
                            else:
                                print(f"Ошибка при отправке сообщения пользователю с ID {userd_id}: {e}")
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
        
        #Получение пользователей определенных групп
        @self.bot.message_handler(func=lambda message: self.database.get_pending_command(message.from_user.id) == '/svg')
        def select_video_groups(message):
            print("Создание рассылки с видео")
            user_id = message.from_user.id
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

        # Запуск бота
        self.bot.polling()