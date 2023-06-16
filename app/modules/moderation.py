from .database import Database
import configparser
import telebot
from telebot import types

class Moderation:
    def __init__(self, bot):
        self.database = Database()
        self.bot = bot

    # Обработка кнопок модерации
    def check_moderation(self, user_id):
        role = self.database.get_user_role(user_id)   
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)     
        if role == "admin":
            add_moderator_button = types.KeyboardButton(text="Добавить модератора")
            delete_moderator_button = types.KeyboardButton(text="Снять с поста модератора")
            distribution_button= types.KeyboardButton(text="Создать рассылку")
            markup.add(add_moderator_button)
            markup.add(delete_moderator_button)
            markup.add(distribution_button)
            self.bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
        elif role == "moderator":
            distribution_button= types.KeyboardButton(text="Создать рассылку")
            markup.add(distribution_button)
            self.bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
        else:            
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)

        
        