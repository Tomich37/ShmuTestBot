from .database import Database
from .moderation import Moderation
import os
import configparser
import telebot
from telebot import types
import pdb
from telegram import MessageEntity

class Distribution:
    def __init__(self, bot, save_directory, i):
        self.database = Database(bot)
        self.moderation = Moderation(bot, save_directory)
        self.bot = bot
        self.save_directory = save_directory
        self.file_paths = []
        self.media_group = []    
        self.i = i  
        self.text = None  

    # Извлечение текста из БД
    def get_distribution_text(self):
        self.distribution_id = self.database.get_latest_distribution_id()
        text = self.database.send_distribution_text(self.distribution_id)
        return text
    
    def clear_file_paths(self):
        self.file_paths = []
    
    def clear_media_group(self):
        self.media_group = []

    def clear_i(self):
        self.i = 0

    # Обработчик текстовой рассылки
    def create_distribution_text(self, message):
        user_id = message.from_user.id
        text = message.text
        user_role = self.database.get_user_role(user_id)
        text_entities = message.entities or []  # Получение форматирования текста во входном сообщении
        entities = [types.MessageEntity(type=entity.type, offset=entity.offset, length=entity.length) for entity in text_entities]

        # Отправка рассылки
        distribution_id = self.database.save_distribution_text(text)
        if distribution_id is not None:
            if user_role == 'user':
                self.bot.send_message(user_id, "У вас недостаточно прав.")
            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
                select_groups_button = types.KeyboardButton(text="Назначить группы")
                cancel_download_distribution_button = types.KeyboardButton(text="Отменить рассылку")
                markup.add(select_groups_button)
                markup.add(cancel_download_distribution_button)
                
                # Выделение отрывков, заключенных в знаки *
                text_parts = text.split('*')
                for i in range(1, len(text_parts), 2):
                    text_parts[i] = f"<b>{text_parts[i]}</b>"
                text = ''.join(text_parts)
                
                self.bot.send_message(user_id, text=f"Сообщение для рассылки:\n\n{text}", parse_mode='HTML', entities=entities, reply_markup=markup)
        else:
            self.bot.send_message(user_id, "Не удалось создать рассылку.")

        # Очистка команды ожидания после завершения рассылки
        self.database.clear_pending_command(user_id)


    # Обработчик рассылки с фото
    def process_distribution_photo(self, message):
        user_id = message.from_user.id
        user_role = self.database.get_user_role(user_id)
        distribution_id = None  # Инициализация переменной distribution_id
        file_path = None  # Инициализация переменной file_path

        if self.i == 0:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
            finall_photo_button = types.KeyboardButton(text="Завершить загрузку фото")
            cancel_download_distribution_button = types.KeyboardButton(text="Отменить рассылку")
            markup.add(finall_photo_button)
            markup.add(cancel_download_distribution_button)
            self.bot.send_message(user_id, "Медиа загружены", reply_markup=markup)
            self.i += 1             

        # Очистка списка media_group
        self.media_group = []

        if message.caption is not None:
            self.text = message.caption
            photo_id = message.photo[-1].file_id
            self.i += 1 

            # Получение информации о фотографии
            file_info = self.bot.get_file(photo_id)
            file_name = file_info.file_path.split('/')[-1]  # Извлекаем имя файла из пути
            downloaded_file = self.bot.download_file(file_info.file_path)
            file_path = os.path.join(self.save_directory, file_name)

            with open(file_path, 'wb') as file:
                file.write(downloaded_file)

            distribution_id = self.database.save_distribution_text(self.text)

        else:            
            photo_id = message.photo[-1].file_id
            self.i += 1 

            # Получение информации о фотографии
            file_info = self.bot.get_file(photo_id)
            file_name = file_info.file_path.split('/')[-1]  # Извлекаем имя файла из пути
            downloaded_file = self.bot.download_file(file_info.file_path)
            file_path = os.path.join(self.save_directory, file_name)

            with open(file_path, 'wb') as file:
                file.write(downloaded_file)

        self.file_paths.append(file_path)

        for file_path in self.file_paths:
                    with open(file_path, 'rb') as file:
                        file_data = file.read()
                        media = types.InputMediaPhoto(file_data)
                        self.media_group.append(media)

    # Отправка рассылки
    def final_distribution_photo(self, message):
        user_id = message.from_user.id
        user_role = self.database.get_user_role(user_id)
        distribution_id = self.database.get_latest_distribution_id()
        if distribution_id is not None:
            if user_role == 'user':
                self.bot.send_message(user_id, "У вас недостаточно прав.")
            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
                select_groups_button = types.KeyboardButton(text="Добавить группы")
                cancel_download_distribution_button = types.KeyboardButton(text="Отменить рассылку")
                markup.add(select_groups_button)
                markup.add(cancel_download_distribution_button)

                self.media_group = []

                for i, file_path in enumerate(self.file_paths):
                    with open(file_path, 'rb') as file:
                        file_data = file.read()
                        media = types.InputMediaPhoto(file_data)
                        
                        if i == 0:
                            # Добавление подписи только для первого элемента
                            caption_parts = self.text.split('*')
                            for j in range(1, len(caption_parts), 2):
                                caption_parts[j] = f"<b>{caption_parts[j]}</b>"
                            media.caption = ''.join(caption_parts)
                        
                        self.media_group.append(media)

                # Отправка медиагруппы с текстом и фотографиями
                for media in self.media_group:
                    media.parse_mode = 'HTML'  # Применение HTML-разметки к подписям
                self.bot.send_media_group(user_id, self.media_group)
                self.database.clear_pending_command(user_id)
                self.text = None
                self.bot.send_message(user_id, "Рассылка подготовлена к отправке", reply_markup=markup)
                return self.media_group
        else:
            self.bot.send_message(user_id, "Не удалось создать рассылку.")
            
        # Очистка команды ожидания после завершения рассылки
        self.database.clear_pending_command(user_id)

    # Обработка рассылки если есть вложение типа document
    def create_distribution_with_file(self, message):
        user_id = message.from_user.id
        role = self.database.get_user_role(user_id)
        if role != 'user':
            distribution_id = self.database.get_latest_distribution_id()           

            if message.document:
                file = message.document
                file_name = file.file_name
                file_id = file.file_id
                file_info = self.bot.get_file(file_id)
                downloaded_file = self.bot.download_file(file_info.file_path)

                # Определение пути к файлу
                file_path = os.path.join(self.save_directory, file_name)

                with open(file_path, 'wb') as file:
                    file.write(downloaded_file)

                # Сохранение пути к файлу в БД
                self.database.save_distribution_file_path(distribution_id, file_path)

                self.file_paths.append(file_path)
            
            
            self.bot.send_document(user_id, open(file_path, 'rb'))
        else:
            self.database.clear_pending_command(user_id)
            self.bot.send_message(user_id, "У вас недостаточно прав")
    
    # Обработка нкопки отмены рассылки
    def cancel_distribution(self, message):
        user_id = message.from_user.id
        role = self.database.get_user_role(user_id)
        self.clear_file_paths()
        self.database.clear_pending_command(user_id)
        if role == 'moderator':
            markup = self.moderation.moder_markup()
            self.bot.send_message(user_id, "Рассылка отменена", reply_markup=markup)
        elif role == 'admin':
            markup = self.moderation.admin_markup()
            self.bot.send_message(user_id, "Рассылка отменена", reply_markup=markup)

    def handle_video_file(self, message):
        user_id = message.from_user.id
        role = self.database.get_user_role(user_id)
        self.database.clear_pending_command(user_id)
        if role != 'user':
            self.database.set_pending_command(user_id, '/svgg')
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
            select_groups_button = types.KeyboardButton(text="Группы видеорассылки")
            cancel_download_distribution_button = types.KeyboardButton(text="Отменить рассылку")
            markup.add(select_groups_button)
            markup.add(cancel_download_distribution_button)
    
            video_file = message.video
            if video_file is not None:
                file_name = video_file.file_name
                file_info = self.bot.get_file(video_file.file_id)
    
                # Определение пути к файлу
                file_path = os.path.join(self.save_directory, file_name)
                try:
                    with open(file_path, "wb") as f:
                        file_content = self.bot.download_file(file_info.file_path)
                        f.write(file_content)
        
                    distribution_id = self.database.save_distribution_text(message.caption)
                
                    with open(file_path, 'rb') as video:
                        sent_message = self.bot.send_video(message.chat.id, video, caption=message.caption)
                    
                    video_id = sent_message.video.file_id
                    message_id  = sent_message.message_id
                    self.database.save_message_id(message_id, video_id, distribution_id)
    
                    self.bot.send_message(message.chat.id, 'Видео загружено', reply_markup=markup)
                except telebot.apihelper.ApiTelegramException as e:
                    if "file is too big" in str(e):
                        self.bot.send_message(message.chat.id, "Ошибка: видеофайл слишком большой для отправки.")
                    else:
                        self.bot.send_message(message.chat.id, f"Произошла ошибка при отправке видео: {str(e)}")
            else:
                self.bot.send_message(user_id, "Пожалуйста, отправьте видеофайл.")
        else:
            self.bot.send_message(user_id, "У вас недостаточно прав")