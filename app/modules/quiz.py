from .database import Database
from telebot import types
import pandas as pd
import os, time, telebot

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
        start_button= types.KeyboardButton(text="Запустить опрос")
        create_button= types.KeyboardButton(text="Создать викторину")
        send_button= types.KeyboardButton(text="Выполнить викторину")
        upload_results_button= types.KeyboardButton(text="Выгрузить результаты")
        menu_button= types.KeyboardButton(text="Меню")
        markup.add(start_button)
        markup.add(create_button, send_button, upload_results_button)
        markup.add(menu_button)
        return markup
    
    def quiz_press_button(self, message):
        user_id = message.from_user.id
        role = self.database.get_user_role(user_id)
        try:
            if role != "user":
                self.database.set_pending_command(user_id, '/set_quiz')
                markup = self.quiz_markup()
                self.bot.send_message(user_id, 'Выберите действие', reply_markup = markup)
            else:
                self.database.clear_pending_command(user_id)
                self.bot.send_message(user_id, "У вас недостаточно прав")
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
            answers = self.database.get_quiz_answers(id_question)
            question_text = self.database.get_quiz_question(id_question)

            markup = types.InlineKeyboardMarkup()
            for ans_id, q_id, ans_text in answers:
                button = types.InlineKeyboardButton(ans_text, callback_data=f'quiz_test_question_{q_id}_answer_{ans_id}')
                markup.add(button)
                
            self.bot.send_message(chat_id=user_id, text=question_text, reply_markup=markup)

        except Exception as e:
            self.logger.exception(f"An error occurred in quiz/quiz_add_answer: {e}")
            self.bot.send_message(user_id, "Ошибка при обработке кнопки. Пожалуйста, повторите попытку позже")

    def quiz_choice(self, message):
        user_id = message.from_user.id
        try:
            self.database.set_pending_command(user_id, '/quiz_choice')
            questions = self.database.get_quiz_all_questions()

            # Разделяем вопросы на группы по 10 вопросов
            chunks = [questions[i:i+10] for i in range(0, len(questions), 10)]

            # Отправляем первую группу вопросов
            self.quiz_send_question_group(user_id, chunks, 0)
        except Exception as e:
            self.logger.exception(f"An error occurred in quiz/quiz_choice: {e}")
            self.bot.send_message(user_id, "Ошибка при обработке кнопки. Пожалуйста, повторите попытку позже")

    def quiz_send_question_group(self, user_id, chunks, group_index):
        markup = types.InlineKeyboardMarkup()

        # Добавляем кнопки навигации
        next_button = types.InlineKeyboardButton('Вперед >>', callback_data=f'quiz_next_group_{group_index}')
        cancle_button = types.InlineKeyboardButton('Отмена', callback_data='quiz_cancle_group')

        # Формируем текст сообщения с вопросами текущей группы
        message_text = "Введите ID интересующей Вас викторины (оно находится с правой стороны от |):\n\n"
        i = 1
        for question in chunks[group_index]:
            message_text += f'{i}. {question[1][:30]} | {question[0]}\n'
            i += 1

        # Проверяем, является ли текущая страница последней
        if group_index < len(chunks) - 1:
            next_button = types.InlineKeyboardButton('Вперед >>', callback_data=f'quiz_next_group_{group_index}')
            markup.add(next_button)
        markup.add(cancle_button)

        # Отправляем сообщение
        self.bot.send_message(user_id, message_text, reply_markup=markup)

    def quiz_upload_question_group(self, group_index, call):
        try:
            markup = types.InlineKeyboardMarkup(row_width=2)
            questions = self.database.get_quiz_all_questions()

            # Разделяем вопросы на группы по 10 вопросов
            chunks = [questions[i:i+10] for i in range(0, len(questions), 10)]

            # Кнопки
            next_button = types.InlineKeyboardButton('Вперед >>', callback_data=f'quiz_group_next_{group_index}')
            prev_button = types.InlineKeyboardButton('<< Назад', callback_data=f'quiz_group_prev_{group_index}')
            cancle_button = types.InlineKeyboardButton('Отмена', callback_data='quiz_group_cancle')

            # Добавляем кнопки навигации
            if group_index == len(chunks) - 1:
                markup.add(prev_button)
            elif group_index == 0:
                markup.add(next_button)
            else:
                markup.add(prev_button, next_button)        
            markup.add(cancle_button)

            # Формируем текст сообщения с вопросами текущей группы
            message_text = "Введите ID интересующей Вас викторины (оно находится с правой стороны от |):\n\n"
            i = 1
            for question in chunks[group_index]:
                message_text += f'{i}. {question[1][:30]} | {question[0]}\n'
                i += 1

            # Обновляем сообщение
            self.bot.edit_message_text(message_text, reply_markup=markup, chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception as e:
            self.logger.exception(f"An error occurred in quiz/quiz_upload_question_group: {e}")
            self.bot.send_message(call.from_user.id, "Ошибка при обработке кнопки. Пожалуйста, повторите попытку позже")

    def quiz_get_quiz_by_id(self, message):
        user_id = message.from_user.id
        try:
            try:
                id_question = int(message.text)
                question_text = self.database.get_quiz_question(id_question)
                if question_text is not None:
                    answers = self.database.get_quiz_answers(id_question)

                    cancle_button = types.InlineKeyboardButton('Отмена', callback_data='quiz_quiz_cancle')
                    send_button = types.InlineKeyboardButton('Разослать', callback_data=f'quiz_quiz_send_{id_question}')
                    delete_button = types.InlineKeyboardButton('Удалить', callback_data=f'quiz_quiz_delete_{id_question}')

                    markup = types.InlineKeyboardMarkup()
                    for ans_id, q_id, ans_text in answers:
                        button = types.InlineKeyboardButton(ans_text, callback_data=f'quiz_test_question_{q_id}_answer_{ans_id}')
                        markup.add(button)
                    
                    markup.add(send_button, delete_button)
                    markup.add(cancle_button)
                        
                    self.bot.send_message(chat_id=user_id, text=question_text, reply_markup=markup)
                else:
                    self.bot.send_message(user_id, "Викторины с таким ID не существует")
            except ValueError:
                self.bot.send_message(user_id, "Ожидается число")            
        except Exception as e:
            self.logger.exception(f"An error occurred in quiz/quiz_get_quiz_by_id: {e}")
            self.bot.send_message(user_id, "Ошибка при обработке кнопки. Пожалуйста, повторите попытку позже")

    def quiz_save_answer(self, call):
        try:
            user_id = call.from_user.id
            user_info = self.database.get_user_info(user_id)
            question_id, answer_id = self.quiz_extract_ids_from_callback(call.data)
            question_text = self.database.get_quiz_question(question_id)
            answer_text = self.database.quiz_get_answer_text_by_id(answer_id)
            
            self.database.quiz_save_answers(user_id, user_info[0], user_info[1], question_text[0], answer_text[0])
        except Exception as e:
            self.logger.exception(f"An error occurred in quiz/quiz_save_answer: {e}")
            self.bot.send_message(user_id, "Ошибка при обработке кнопки. Пожалуйста, повторите попытку позже")

    def quiz_extract_ids_from_callback(self, callback_data):
        parts = callback_data.split('_')
        question_id = int(parts[2])
        answer_id = int(parts[4])
        return question_id, answer_id
    
    def quiz_get_all_results(self, message):
        try:
            user_id = message.from_user.id
            results = self.database.quiz_get_all_results()
            
            if results:
                # Создаем DataFrame из результата запроса
                df = pd.DataFrame(results, columns=["ID ответа", "ID пользователя", "ФИО", "Номер телефона", "Вопрос", "Ответ"])

                # Сохраняем DataFrame в Excel-файл
                excel_path = "quiz_results.xlsx"
                df.to_excel(excel_path, index=False)

                # Отправляем Excel-файл пользователю
                with open(excel_path, "rb") as file:
                    self.bot.send_document(user_id, file)

                # Удаляем временный файл
                os.remove(excel_path)
            else:
                self.bot.send_message(user_id, "Нет результатов для экспорта.")
        except Exception as e:
            self.logger.exception(f"An error occurred in quiz/quiz_get_all_results: {e}")
            self.bot.send_message(user_id, "Ошибка при обработке кнопки. Пожалуйста, повторите попытку позже")

    def quiz_survey_press_button(self, message):
        role = self.database.get_user_role(message.from_user.id)
        all_users_id = self.database.get_users()
        markup = types.InlineKeyboardMarkup()
        ready_button = types.InlineKeyboardButton('Да, готов!', callback_data='quiz_survey_ready')
        markup.add(ready_button)
        text = 'Наше обучение уже закончилось, спасибо, что были с нами! Просим вас оценить работу нашего курса и ответить на пару вопросов! Готовы?'

        all_users_id = [user_id[0] for user_id in all_users_id]
        i = 1
        process_messge = self.bot.send_message(message.from_user.id, f"Процесс рассылки опроса: 0/{len(all_users_id)}", reply_markup=markup)
        for user_id in all_users_id:
            try:
                self.bot.edit_message_text(f"Процесс рассылки опроса: {i}/{len(all_users_id)}", chat_id=message.chat.id, message_id=process_messge.message_id)
                self.bot.send_message(user_id, text, reply_markup=markup)
                self.database.clear_pending_command(user_id)
                self.logger.info(f"User ID: {user_id}, успешная рассылка опроса") 
                i += 1
                time.sleep(0.5)
            except telebot.apihelper.ApiTelegramException as e:
                if e.result.status_code == 403:
                    # Пользователь заблокировал бота
                    self.database.update_user_authorized(user_id, 0)
                    self.logger.info(f"Пользователь с ID {user_id} заблокировал бота")
                    continue  # Продолжаем рассылку следующему пользователю
                else:
                    self.logger.exception(f"Ошибка при отправке сообщения пользователю с ID {user_id}: {e}")
                    continue  # Продолжаем рассылку следующему пользователю
        if role == 'admin':
            markup = self.quiz_markup()
            self.bot.send_message(user_id, "Рассылка выполнена", reply_markup=markup)
            self.logger.info(f"User ID: {user_id}, рассылка викторины завершена")

    def quiz_survey_first_question(self, call):
        user_id = call.from_user.id
        self.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        self.database.set_pending_command(user_id, '/quiz_survey_speaker')
        text = 'Назовите спикера, который наиболее всего вам понравился?'
        self.bot.send_message(user_id, text)

    def quiz_survey_speaker(self, message):
        user_id = message.from_user.id
        speaker = message.text
        self.database.survey_add_speaker(user_id, speaker)

        text = 'Используете ли вы материалы после обучения?'
        markup = types.InlineKeyboardMarkup()
        yes_button = types.InlineKeyboardButton('Да', callback_data='quiz_survey_materials_yes')
        no_button = types.InlineKeyboardButton('Нет', callback_data='quiz_survey_materials_no')
        markup.add(yes_button, no_button)

        self.bot.send_message(user_id, text, reply_markup=markup)

    def quiz_survey_birthday_request(self, call):
        user_id = call.from_user.id
        self.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        self.database.set_pending_command(user_id, '/quiz_survey_birthday')
        text = 'Укажите, пожалуйста, вашу дату рождения'
        self.bot.send_message(user_id, text)

    def quiz_survey_wish(self, message):
        print('text')
        user_id = message.from_user.id

        text = 'Хотите ли вы продолжить обучение?'
        markup = types.InlineKeyboardMarkup()
        yes_button = types.InlineKeyboardButton('Да', callback_data='quiz_survey_wish_yes')
        no_button = types.InlineKeyboardButton('Нет', callback_data='quiz_survey_wish_no')
        markup.add(yes_button, no_button)

        self.bot.send_message(user_id, text, reply_markup=markup)

    def quiz_survey_fio_request(self, call):
        user_id = call.from_user.id
        self.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        self.database.set_pending_command(user_id, '/quiz_survey_fio')
        text = 'Укажите ваше полное ФИО'
        self.bot.send_message(user_id, text)

    def quiz_survey_comments(self, message):
        user_id = message.from_user.id
        self.database.set_pending_command(user_id, '/quiz_survey_comments')
        text = 'Вы можете оставить развернутый комментарий о курсе, а мы обязательно сделаем продолжение обучения ещё лучше!'
        self.bot.send_message(user_id, text)

    def quiz_survey_final(self, message):
        user_id = message.from_user.id
        self.database.clear_pending_command(user_id)
        text = 'Спасибо вам за обратную связь! Если вы готовы продолжать, мы вернёмся к вам с новыми курсами и мероприятиями в ближайшем будущем!'
        self.bot.send_message(user_id, text)