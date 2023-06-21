from .database import Database
from .moderation import Moderation
import os
import configparser
import telebot
from telebot import types

class Distribution:
    def __init__(self, bot, save_directory):
        self.database = Database()
        self.moderation = Moderation(bot)
        self.bot = bot
        self.save_directory = save_directory

    # Извлечение текста из БД
    def get_distribution_text(self):
        self.distribution_id = self.database.get_latest_distribution_id()
        text = self.database.send_distribution_text(self.distribution_id)
        return text

    # Обработчик текстовой рассылки
    def create_distribution_text(self, user_id, text):
        user_role = self.database.get_user_role(user_id)

        # Отправка рассылки
        distribution_id = self.database.save_distribution_text(text)
        if distribution_id is not None:
            if user_role == 'user':
                markup = self.moderation.user_markup()
                self.bot.send_message(user_id, "У вас недостаточно прав.", reply_markup=markup)
            else:
                # Создание кнопок "Отправить" и "отмена"              
                keyboard = types.InlineKeyboardMarkup()
                send_button = types.InlineKeyboardButton(text="Отправить", callback_data=f"send_distribution_{distribution_id}")
                cancel_button = types.InlineKeyboardButton(text="Отменить", callback_data="cancel_distribution")
                keyboard.add(send_button, cancel_button)

                self.bot.send_message(user_id, text=f"Сообщение для рассылки:\n\n{text}", reply_markup=keyboard)                
        else:
            self.bot.send_message(user_id, "Не удалось создать рассылку.")

        # Очистка команды ожидания после завершения рассылки
        self.database.clear_pending_command(user_id)        

    # Обработчик рассылки с фото
    def process_distribution_photo(self, message):
        user_id = message.from_user.id
        user_role = self.database.get_user_role(user_id)
        distribution_id = None  # Инициализация переменной distribution_id
        if message.caption is not None:
            text = message.caption
            photo_id = message.photo[-1].file_id

            # Получение информации о фотографии
            file_info = self.bot.get_file(photo_id)
            file_name = file_info.file_path.split('/')[-1]  # Извлекаем имя файла из пути
            downloaded_file = self.bot.download_file(file_info.file_path)
            file_path = os.path.join(self.save_directory, file_name)

            with open(file_path, 'wb') as file:
                file.write(downloaded_file)
            
            distribution_id = self.database.save_distribution_text(text)
        else:
            print('добавлено больше 1 фото')

        # Отправка рассылки
        if distribution_id is not None:
            if user_role == 'user':
                markup = self.moderation.user_markup()
                self.bot.send_message(user_id, "У вас недостаточно прав.", reply_markup=markup)
            else:
                # Создание кнопок "Отправить" и "отмена"              
                keyboard = types.InlineKeyboardMarkup()
                send_button = types.InlineKeyboardButton(text="Отправить", callback_data=f"send_distribution_photo_{distribution_id}")
                cancel_button = types.InlineKeyboardButton(text="Отменить", callback_data="cancel_distribution")
                keyboard.add(send_button, cancel_button)

                # Сохранение файла в базе данных
                self.database.save_distribution_file_path(distribution_id, file_path)

                # Отправка медиагруппы с текстом и фотографиями
                self.bot.send_photo(user_id, photo = open(file_path, 'rb'), caption=f"Сообщение для рассылки:\n\n{text}", reply_markup=keyboard)
        else:
            self.bot.send_message(user_id, "Не удалось создать рассылку.")
        # Очистка команды ожидания после завершения рассылки
        self.database.clear_pending_command(user_id)

    # Обработка рассылки если есть вложение типа document
    def create_distribution_with_file(self, message):
        user_id = message.from_user.id
        role = self.database.get_user_role(user_id)
        if role != 'user':
            text = message.caption

            # Сохранение текста в БД и получение id
            distribution_id = self.database.save_distribution_text(text)

            # Создание кнопок "Отправить" и "отмена"              
            keyboard = types.InlineKeyboardMarkup()
            send_button = types.InlineKeyboardButton(text="Отправить", callback_data=f"send_distribution_docs_{distribution_id}")
            cancel_button = types.InlineKeyboardButton(text="Отменить", callback_data="cancel_distribution")
            keyboard.add(send_button, cancel_button)

            if message.document:
                file = message.document
                file_name = file.file_name
                file_id = file.file_id
                file_info = self.bot.get_file(file_id)
                downloaded_file = self.bot.download_file(file_info.file_path)
                save_path = os.path.join(self.save_directory, file_name)
                file_extension = os.path.splitext(file_name)[1]

                # Определение пути к файлу
                file_path = os.path.join(self.save_directory, file_name)

                with open(save_path, 'wb') as file:
                    file.write(downloaded_file)

                # Сохранение пути к файлу в БД
                self.database.save_distribution_file_path(distribution_id, file_path)

                print(file_extension, text)
                self.bot.send_message(user_id, text)
                self.bot.send_document(message.chat.id, open(file_path, 'rb'))
                self.bot.send_message(user_id, "Сделать рассылку?", reply_markup=keyboard)

                # Очистка команды ожидания после завершения рассылки
                self.database.clear_pending_command(user_id)
        else:
            markup = self.moderation.user_markup()
            # Очистка команды ожидания после завершения рассылки
            self.database.clear_pending_command(user_id)
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)