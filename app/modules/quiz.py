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
            self.logger.exception(f"An error occurred in quiz/quiz_press_button: {e}")
            self.bot.send_message(user_id, "Ошибка при обработке кнопки. Пожалуйста, повторите попытку позже")

    def quiz_set_question(self, message):
        user_id = message.from_user.id
        try:
            self.database.set_pending_command(user_id, '/set_quiz_question')
            hide_markup = types.ReplyKeyboardRemove()
            self.bot.send_message(user_id, "Введите вопрос для викторины", reply_markup = hide_markup)
        except Exception as e:
            self.logger.exception(f"An error occurred in quiz/quiz_set_question: {e}")
            self.bot.send_message(user_id, "Ошибка при обработке кнопки. Пожалуйста, повторите попытку позже")

    def quiz_add_question(self, message):
        user_id = message.from_user.id
        try:
            question = message.text
            self.database.quiz_insert_question(question)
            self.database.set_pending_command(user_id, '/set_quiz_answer')
            question = self.database.get_last_quiz_question()
            question_id = question[0]
            question_text = question[1]

            self.database.set_quiz_question_id(user_id, question_id)

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
            complete_button= types.KeyboardButton(text="Завершить")
            cancel_button= types.KeyboardButton(text="Отмена")
            markup.add(complete_button, cancel_button)

            sent_message = self.bot.send_message(user_id, f'Введите ответы для викторины со следующим вопросом:\n\n{question_text}', reply_markup = markup)
            message_id = sent_message.message_id
            chat_id = sent_message.chat.id
            self.database.set_quiz_question_message_id(user_id, message_id, chat_id)
        except Exception as e:
            self.logger.exception(f"An error occurred in quiz/quiz_add_question: {e}")
            self.bot.send_message(user_id, "Ошибка при обработке кнопки. Пожалуйста, повторите попытку позже")

    def quiz_add_answer(self, message):
        user_id = message.from_user.id
        try:
            answer = message.text
            id_question = self.database.get_quiz_question_id(user_id)
            self.database.quiz_insert_answer(id_question, answer)
            answers = self.database.get_all_quiz_answers(id_question)
            question_text = self.database.get_quiz_question(id_question)

            markup = types.InlineKeyboardMarkup()
            for ans_id, q_id, ans_text in answers:
                button = types.InlineKeyboardButton(ans_text, callback_data=f'quiz_question_{q_id}_answer_{ans_id}')
                markup.add(button)
                
            self.bot.send_message(chat_id=user_id, text=question_text, reply_markup=markup)

        except Exception as e:
            self.logger.exception(f"An error occurred in quiz/quiz_add_answer: {e}")
            self.bot.send_message(user_id, "Ошибка при обработке кнопки. Пожалуйста, повторите попытку позже")