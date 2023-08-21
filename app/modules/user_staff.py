from .database import Database
import configparser
import telebot
from telebot import types


class User:
    def __init__(self, bot, database):
        self.bot = bot
        self.database = database
    
    # Выдача материалов в зависимости от группы
    def get_materials(self, message):
        user_id = message.from_user.id
        user_group = self.database.get_user_group(user_id)
        if self.database.user_exists_id(user_id):
            if user_group in ['1', '2', 'буртный']:
                self.bot.send_message(message.chat.id, "Материалы доступны по ссылке:\nhttps://disk.yandex.ru/d/5pdekJ2JN_l4fw")
            elif user_group in ['3', '4']:
                self.bot.send_message(message.chat.id, "Материалы доступны по ссылке:\nhttps://disk.yandex.ru/d/a-pugligE5KB-g")
            elif user_group in ['5', '6']:
                self.bot.send_message(message.chat.id, "Материалы доступны по ссылке:\nhttps://disk.yandex.ru/d/XXmAn0JaFZKRVw")
            elif user_group in ['ТС']:
                self.bot.send_message(message.chat.id, "Материалы доступны по ссылке:\nhttps://disk.yandex.ru/d/5pdekJ2JN_l4fw\nhttps://disk.yandex.ru/d/a-pugligE5KB-g")
            else:
                self.bot.send_message(message.chat.id, "К сожалению Вас нет в списке. Ожидайте авторизации модераторами мероприятия.")
        else:
            self.bot.send_message(user_id, "К сожалению Вас нет в списке. Ожидайте авторизации модераторами мероприятия.")
    
    def get_review(self, message):
        user_id = message.from_user.id
        url_button = types.InlineKeyboardButton("Оставить отзыв", url = "https://forms.yandex.ru/u/64ba8061c417f32ee117af59/")

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(url_button)

        self.bot.send_message(user_id, "Нажмите на кнопку чтоб оставить отзыв", reply_markup = keyboard)