from .database import Database
from .moderation import Moderation
import configparser
import telebot
from telebot import types

class Distribution:
    def __init__(self, bot):
        self.database = Database()
        self.moderation = Moderation(bot)
        self.bot = bot

    # Обработчик нажатия кнопки в рассылке
    def create_distribution(self, message):
        # Получение текста
        text = message.text.split(' ', 1)[1]
        user_id = message.from_user.id
        user_role = self.database.get_user_role(user_id)

        # Сохранение текста в БД и получение id
        distribution_id = self.database.save_distribution_text(text)
        if user_role == 'user':
            markup = self.moderation.user_markup()
            self.bot.send_message(user_id, "У вас недостаточно прав.", reply_markup=markup)
        else:
            if distribution_id is not None:
                # Создание кнопок "Отрпавить" и "отмена"
                keyboard = types.InlineKeyboardMarkup()
                send_button = types.InlineKeyboardButton(text="Отправить", callback_data=f"send_distribution_{distribution_id}")
                cancel_button = types.InlineKeyboardButton(text="Отменить", callback_data="cancel_distribution")
                keyboard.add(send_button, cancel_button)

                # Отправка сообщения для подтверждения отправки
                self.bot.send_message(user_id, f"Сообщение для рассылки:\n\n{text}", reply_markup=keyboard)
            else:
                self.bot.send_message(user_id, "Не удалось создать рассылку.")

    # Обработка кнопки "Создать рассылку"
    def distribution_button_click(self, user_id):
        role = self.database.get_user_role(user_id)
        markup = None
        if role == "user":
            markup = self.moderation.user_markup()
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)
        else:
            if role == "admin":
                markup = self.moderation.admin_markup()
                self.bot.send_message(user_id, text="Команда для создания рассылки: /cd \n\n Пример ее использования:\n /cd 'Ваш текст', можно прикреплять файлы", reply_markup=markup)
            else:
                markup = self.moderation.moder_markup()
                self.bot.send_message(user_id, text="Команда для создания рассылки: /cd \n\n Пример ее использования:\n /cd 'Ваш текст', можно прикреплять файлы", reply_markup=markup)
