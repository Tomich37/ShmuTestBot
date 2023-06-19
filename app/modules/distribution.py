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
        self.bot.callback_query_handler(func=lambda call: True)(self.handle_button_click)

    # Обработка кнопки "Создать рассылку"
    def distribution_button_click(self, user_id):
        role = self.database.get_user_role(user_id)
        markup = None
        if role == "user":
            markup = self.moderation.user_markup()
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)
        else:
            markup = self.moderation.admin_markup()
            self.bot.send_message(user_id, text="Команда для создания рассылки: /cd \n\n Пример ее использования:\n /cd 'Ваш текст', можно прикреплять файлы", reply_markup=markup)

    def handle_button_click(self, call):
        user_id = call.from_user.id
        if call.data.startswith('send_distribution_'):
            # Get the distribution ID from callback_data
            distribution_id = call.data.split('_', 2)[2]

            # Get the distribution text from the database using the ID
            result = self.database.send_distribution_text(distribution_id)
            if result is not None:
                text = result
                # Get the list of all users from the database
                users = self.database.get_users()

                # Send the message to each user
                for user in users:
                    users_id = user[0]  # Assuming the user ID is stored in the first column of the table
                    self.bot.send_message(users_id, text)

                # Send a message to the user who created the distribution
                self.bot.send_message(user_id, "Рассылка успешно выполнена.")
            else:
                print(result, distribution_id, call.data)
                self.bot.send_message(user_id, "Рассылка не найдена.")
        elif call.data == 'cancel_distribution':
            self.bot.send_message(user_id, "Рассылка отменена.")