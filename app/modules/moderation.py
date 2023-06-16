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

    def add_moderator(self, user_id):
        role = self.database.get_user_role(user_id)    
        
        if role != "admin":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)
            if role == "moderator":                
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
                distribution_button = types.KeyboardButton(text="Создать рассылку")
                markup.add(distribution_button)
                self.bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
        else:
            markup = types.InlineKeyboardMarkup(row_width=2)
            send_phone_button = types.InlineKeyboardButton(text="Отправить номер телефона", callback_data="send_phone")
            cancel_button = types.InlineKeyboardButton(text="Отмена", callback_data="cancel")
            markup.add(send_phone_button, cancel_button)
            self.bot.send_message(user_id, text="Введите номер телефона человека, которого вы хотите назначить модератором", reply_markup=markup)
            
    def handle_button_click(self, call, message_id):
        admin_id = call.from_user.id

        if call.data == "send_phone":
            self.bot.send_message(admin_id, "Пользователь назначен модератором")
            self.bot.delete_message(chat_id=call.message.chat.id, message_id=message_id)
        elif call.data == "cancel":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
            distribution_button = types.KeyboardButton(text="Создать рассылку")
            markup.add(distribution_button)
            self.bot.send_message(admin_id, "Выберите действие:", reply_markup=markup)
            self.bot.delete_message(chat_id=call.message.chat.id, message_id=message_id)

    def process_phone_number(self, message):
        phone_number = message.text
        user_exists = self.database.user_exists(phone_number)
        if user_exists:
            self.bot.send_message(message.chat.id, "Пользователь существует")
        else:
            self.bot.send_message(message.chat.id, "Пользователь не существует")

    def remove_moderator(self, user_id):
        # Логика снятия модератора с поста
        pass

    def create_distribution(self, user_id):
        # Логика создания рассылки
        pass

        
        