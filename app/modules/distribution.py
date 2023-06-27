from .database import Database
from .moderation import Moderation
import os
import configparser
import telebot
from telebot import types
import pdb

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
    def create_distribution_text(self, user_id, text):
        user_role = self.database.get_user_role(user_id)       

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
                self.bot.send_message(user_id, text=f"Сообщение для рассылки:\n\n{text}", reply_markup=markup)            
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
        print(self.i)

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
                            media.caption = self.text  # Добавление подписи только для первого элемента
                        
                        self.media_group.append(media)

                # Отправка медиагруппы с текстом и фотографиями
                self.bot.send_media_group(user_id, self.media_group)
                self.database.clear_pending_command(user_id)
                self.text = None
                self.bot.send_message(user_id, "Рассылка подговтолена к отправке", reply_markup=markup)
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