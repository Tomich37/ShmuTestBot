from .database import Database
from telebot import types

class Quiz:
    def __init__(self, bot, logger):   
        self.database = Database(bot, self.menu_markup)     
        self.bot = bot
        self.logger = logger

    @staticmethod
    def menu_markup():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        menu_button= types.KeyboardButton(text="Меню")
        markup.add(menu_button)
        return markup
    
    @staticmethod
    def quiz_markup():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        create_button= types.KeyboardButton(text="Создать викторину")
        send_button= types.KeyboardButton(text="Выполнить викторину")
        upload_results_button= types.KeyboardButton(text="Выгрузить результаты")
        menu_button= types.KeyboardButton(text="Меню")
        markup.add(create_button, send_button, upload_results_button, menu_button)
        return markup
    
    def quiz_press_button(self, message):
        user_id = message.from_user.id
        try:
            self.database.set_pending_command(user_id, '/set_quiz')
            markup = self.quiz_markup()
            self.bot.send_message(user_id, 'Выберите действие', reply_markup = markup)
        except Exception as e:
                print(f"An error occurred in quiz/quiz_press_button: {e}")
                self.logger.exception(f"An error occurred in quiz/quiz_press_button: {e}")
                self.bot.send_message(user_id, "Ошибка при обработке кнопки. Пожалуйста, повторите попытку позже")
