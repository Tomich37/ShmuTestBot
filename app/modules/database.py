import sqlite3, configparser
import re
import os

class Database:
    def __init__(self, bot, menu_markup):
    
        # Чтение файла конфигурации
        config = configparser.ConfigParser()
        config.read('./config.ini')
        self.bot = bot
        self.menu_markup = menu_markup

        # Получение пути к файлу базы данных из файла конфигурации
        self.db_path_events = config.get('default', 'db_path_events')
        self.db_path_users = config.get('default', 'db_path_users')
    
    # Получение данных о пользователе из message_handler в dialog_bot    
    def set_user_data(self, user_id, phone_number):
        self.user_id = user_id
        self.phone_number = phone_number

    # Проверка на наличие пользователя в БД
    def user_exists_phone(self, phone_number):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT authorized FROM users WHERE phone_number=?", (phone_number,))
            result = cursor.fetchone()
        return result is not None
    
    def user_exists_id(self, user_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT authorized FROM users WHERE user_id=?", (user_id,))
            result = cursor.fetchone()
        return result is not None
    
    # Выдача информации по пользователю (для назначения/удаления админа), !!!переписать!!!
    def user_info(self, phone_number):
        if self.user_exists_phone(phone_number):
            with self.get_database_connection_users() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT phone_number, user_id, first_name, last_name, role FROM users WHERE phone_number=?", (phone_number,))
                result = cursor.fetchone()
            return result
        else:
            result = False
            return result
        
    # Выдача информации о пользователе по ФИО 
    def user_info_fio(self, fio):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT phone_number, user_id, fio, role, region, user_group FROM users WHERE fio LIKE ?", (fio + '%',))
            result = cursor.fetchone()
        return result
    
    # Выдача информации о пользователе по ФИО 
    def user_info_phone_number(self, phone_number):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT phone_number, user_id, fio, role, region, user_group FROM users WHERE phone_number LIKE ?", (phone_number,))
            result = cursor.fetchone()
        return result

    # Проверка роли пользователя
    def get_user_role(self, user_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE user_id=?", (user_id,))
            result = cursor.fetchone()
        return result[0] if result else None
    
    # Обновление записи пользователя в БД users
    def update_user(self, user_id, phone_number):
        phone_number = re.sub(r'\D', '', phone_number)
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE phone_number = ? AND user_id IS NULL", (phone_number,))
            result = cursor.fetchone()
            if result[0] > 0:
                cursor.execute("UPDATE users SET user_id=?, authorized=? WHERE phone_number=?", (user_id, True, phone_number))
                conn.commit()
            else:
                print("User ID not updated or phone number does not exist")


    #Добавление нового пользователя в БД users    
    def add_user(self, user_id, phone_number, first_name, last_name, user_role):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (user_id, phone_number, first_name, last_name, authorized, role) VALUES (?, ?, ?, ?, ?, ?)", (user_id, phone_number, first_name, last_name, True, user_role))
            conn.commit()
    
    # Назначение модера
    def add_moderator(self, phone_number):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role='moderator' WHERE phone_number=?", (phone_number,))
            conn.commit()
    
    # Снятие модера
    def remove_moderator(self, phone_number):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE phone_number=?", (phone_number,))
            result = cursor.fetchone()
            if result and result[0] == 'admin':
                # Пользователь имеет роль 'admin', нельзя изменить на 'user'
                return False
            else:
                cursor.execute("UPDATE users SET role='user' WHERE phone_number=?", (phone_number,))
                conn.commit()
                return True

    # Проверка на андмина        
    def check_admin_role(self, phone_number):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE phone_number=?", (phone_number,))
            result = cursor.fetchone()
            if result and result[0] == 'admin':
                return True
            else:
                return False

    def get_database_connection_users(self):
        conn = sqlite3.connect(self.db_path_users)
        return conn

    def get_database_connection_events(self):
        conn = sqlite3.connect(self.db_path_events)
        return conn    
    
    def get_events(self):
        with self.get_database_connection_events() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT date, place, event FROM events")
            events_list = cursor.fetchall()
        return events_list

    def get_users(self):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE authorized = 1")
            all_users = cursor.fetchall()
        return all_users

    def save_distribution_text(self, text):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO distribution (text) VALUES (?)", (text,))
            conn.commit()

            # Получение идентификатора рассылки
            distribution_id = cursor.lastrowid

        return distribution_id

    # Получение текста рассылки
    def send_distribution_text(self, distribution_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT text FROM distribution WHERE id=?", (distribution_id,))
            result = cursor.fetchone()
        if result:
            return result[0]
        return None

    # id последней рассылки
    def get_latest_distribution_id(self):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id) FROM distribution")
            result = cursor.fetchone()
        if result:
            return result[0]
        return None
    
    # удаление последней рассылки
    def delete_latest_distribution(self):
        latest_id = self.get_latest_distribution_id()
        if latest_id is not None:
            with self.get_database_connection_users() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM distribution WHERE id = ?", (latest_id,))
                conn.commit()
            return True
        return False

    # Сохранение пути файла для рассылки    
    def save_distribution_file_path(self, distribution_id, file_path):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO distibution_files (distribution_id, file_path) VALUES (?, ?)", (distribution_id, file_path))
            conn.commit()

    # Создание команды        
    def set_pending_command(self, user_id, command):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO user_pending_commands (user_id, command) VALUES (?, ?)", (user_id, command))
            conn.commit()

    # Взятие команды
    def get_pending_command(self, user_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT command FROM user_pending_commands WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
        if result:
            return result[0]
        return None

    # Очистка команды
    def clear_pending_command(self, user_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_pending_commands WHERE user_id = ?", (user_id,))
            conn.commit()

    # Изъятие пути
    def get_distribution_file_paths(self, distribution_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM distibution_files WHERE distribution_id = ?", (distribution_id,))
            results = cursor.fetchall()
        return [result[0] for result in results]
    
    # Изменение значения авторизации пользователя
    def update_user_authorized(self, user_id, authorized):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET authorized = ? WHERE user_id = ?", (authorized, user_id))
            conn.commit()

    # Добавление новых пользователей
    def insert_or_update_user(self, phone_number, fio, region, user_group, job):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO users (phone_number, fio, region, user_group, job, role) VALUES (?, ?, ?, ?, ?, ?)",
                        (phone_number, fio, region, user_group, job, "user"))
            conn.commit()
    
    # Поиск авторизированных пользователей по группам    
    def find_users_by_event_or_group(self, words):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            query = "SELECT user_id FROM users WHERE (LOWER(region) LIKE ? OR LOWER(user_group) LIKE ?) AND authorized = 1"
            users = []

            for word in words:
                word_lower = word.lower()
                params = ('%' + word_lower + '%', '%' + word_lower + '%')
                cursor.execute(query, params)
                result = cursor.fetchall()
                users.extend([user[0] for user in result])

            return users
        
    # Уникальные значения столбцов в users
    def get_unique_column_values(self, column_name):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            query = f"SELECT DISTINCT {column_name} FROM users"
            cursor.execute(query)
            result = cursor.fetchall()
            unique_values = [row[0] for row in result]
            return unique_values

    # Регистрация новых участников
    def handle_fio(self, message, phone_number):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            fio = message.text.lower().strip()
            user_id = message.from_user.id
            role = "user"

            # Удаление символов кроме букв из начала и конца строки
            fio = re.sub(r'[^\w\s]+', '', fio)

            # Проверка, что значение состоит из трех слов
            words = fio.split()
            if len(words) != 2:
                # Значение не соответствует требуемому формату
                return None

            # Проверка, что значение уже есть в таблице
            cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(fio) = ?", (fio,))
            result = cursor.fetchone()
            if result[0] > 0:
                # Проверка, что значение номера телефона отсутствует в таблице
                cursor.execute("SELECT COUNT(*) FROM users WHERE phone_number = ?", (phone_number,))
                result = cursor.fetchone()
                if result[0] > 0:
                    print("Пользователь существует")
                else:
                    try:
                        cursor.execute("UPDATE users SET user_id = ?, authorized = 1, phone_number = ?, role = ? WHERE LOWER(fio) = ?", (user_id, phone_number, role, fio))
                        conn.commit()
                    except sqlite3.IntegrityError:
                        # Обработка ошибки
                        print("Ошибка обновления записи пользователя: нарушение ограничения уникальности phone_number")
                    # Получение пути к текущему скрипту
                    current_dir = os.path.dirname(os.path.abspath(__file__))

                    # Построение полного пути к файлу фотографии
                    photo_path = os.path.join(current_dir, 'media', 'avatar.png')
                    # Значения нет в таблице, выполняем вставку
                    text = "Спасибо за регистрацию ❤️\n\nСкоро вы узнаете, как работать в  современном информационном пространстве вашего региона.\n\nВ ближайшее время мы отправим вам приглашение на лекцию, а пока вы можете посмотреть записи прошлых вебинаров, нажав на кнопку «Материалы» в панели меню.\n\nДо встречи на новых трансляциях!"
                    photo = open(photo_path, 'rb')
                    self.bot.send_photo(message.chat.id, photo, caption=text)

                    markup = self.menu_markup()                    
                    self.bot.send_message(message.chat.id, "Вам теперь доступен функционал бота", reply_markup=markup)
            else:
                # Проверка, что значение номера телефона отсутствует в таблице
                cursor.execute("SELECT COUNT(*) FROM users WHERE phone_number = ?", (phone_number,))
                result = cursor.fetchone()
                if result[0] > 0:
                    print("Пользователь существует")
                else:
                    cursor.execute("INSERT INTO users (fio, user_id, authorized, phone_number, role) VALUES (?, ?, 0, ?, ?)", (fio, user_id, phone_number, role))
                    # Получение пути к текущему скрипту
                    current_dir = os.path.dirname(os.path.abspath(__file__))

                    # Построение полного пути к файлу фотографии
                    photo_path = os.path.join(current_dir, 'media', 'avatar.png')
                    # Значения нет в таблице, выполняем вставку
                    text = "Спасибо за регистрацию ❤️\n\nСкоро вы узнаете, как работать в  современном информационном пространстве вашего региона.\n\nВ ближайшее время мы отправим вам приглашение на лекцию, а пока вы можете посмотреть записи прошлых вебинаров, нажав на кнопку «Материалы» в панели меню.\n\nДо встречи на новых трансляциях!"
                    photo = open(photo_path, 'rb')
                    self.bot.send_photo(message.chat.id, photo, caption=text)
            conn.commit()
            return True
    
    # Получение данных участников для выгрузки в exel
    def get_users_excel(self):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT phone_number, fio, user_group, region FROM users WHERE authorized = 1 AND user_id IS NOT NULL")
            users = cursor.fetchall()
            return users

    # Сохранения id сообщения для перессылки видео
    def save_message_id(self, message_id, video_id, distribution_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            
            query = "INSERT INTO distibution_files (message_id, file_path, distribution_id) VALUES (?, ?, ?);"
            cursor.execute(query, (message_id, str(video_id), distribution_id))

    # Получение id изначального сообщения по пути видео
    def get_message_id_by_video_id(self, video_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            
            query = "SELECT message_id FROM distibution_files WHERE file_path = ?;"
            cursor.execute(query, (str(video_id),))
            
            result = cursor.fetchone()
            if result:
                return result[0]  # Return the first value from the result (message_id)
            else:
                return None  # If no record found, return None

    # Получение группы пользователя
    def get_user_group(self, user_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            
            query = "SELECT user_group FROM users WHERE user_id = ?;"
            cursor.execute(query, (user_id,))
            
            result = cursor.fetchone()
            if result:
                return result[0]  # Return the first value from the result (message_id)
            else:
                return None  # If no record found, return None
    
    # Временное сохранение номера телефона
    def temp_phone_number(self, user_id, phone_number):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO temp_storage (user_id, phone_number) VALUES (?, ?)", (user_id, phone_number))
            conn.commit()

    def clear_temp_phone_number(self, user_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM temp_storage WHERE user_id = ?", (user_id,))
            conn.commit()
    
    # Взятие телефона
    def get_temp_phone_number(self, user_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT phone_number FROM temp_storage WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
        if result:
            return result[0]
        return None

    # Редактирование фио
    def update_user_fio(self, fio, user_id):
        phone_number = self.get_temp_phone_number(user_id)
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET fio = ?, authorized = 1 WHERE phone_number = ?", (fio, phone_number))
            conn.commit()
        self.clear_pending_command(user_id)
        self.bot.send_message(user_id, "ФИО пользователя изменено")
    
    # Редактирование региона
    def update_user_region(self, region, user_id):
        phone_number = self.get_temp_phone_number(user_id)
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET region = ?, authorized = 1 WHERE phone_number = ?", (region, phone_number))
            conn.commit()
        self.clear_pending_command(user_id)
        self.bot.send_message(user_id, "Регион пользователя изменен")

    # Редактирование группы
    def update_user_group(self, user_group, user_id):
        phone_number = self.get_temp_phone_number(user_id)
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET user_group = ?, authorized = 1 WHERE phone_number = ?", (user_group, phone_number))
            conn.commit()
        self.clear_pending_command(user_id)
        self.bot.send_message(user_id, "Группа пользователя изменена")

     #Добавление нового вопроса для викторины    
    def quiz_insert_question(self, question):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO quiz_questions (question) VALUES (?)", (question,))
            conn.commit()
    
    # Взятие вопроса викторины и ее id
    def get_last_quiz_question(self):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, question FROM quiz_questions WHERE id = (SELECT MAX(id) FROM quiz_questions)")
            result = cursor.fetchone()
        return result
    
    # Взятие вопроса викторины и ее id
    def get_quiz_question(self, question_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT question FROM quiz_questions WHERE id = {question_id}")
            result = cursor.fetchone()
        return result
    
    # Сохранение id вопроса для викторины      
    def set_quiz_question_id(self, user_id, question_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO user_question_id (user_id, question_id) VALUES (?, ?)", (user_id, question_id))
            conn.commit()

    # Взятие id вопроса для викторины    
    def get_quiz_question_id(self, user_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT question_id FROM user_question_id WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
        if result:
            return result[0]
        return None
    
    #Добавление ответа викторины от модератора
    def quiz_insert_answer(self, id_question, answer):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO quiz_mod_answers (id_question, answer) VALUES (?, ?)", (id_question, answer,))
            conn.commit()

    def get_all_quiz_answers(self, id_question):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM quiz_mod_answers WHERE id_question = {id_question}")
            result = cursor.fetchall()
        return result
    
    # Сохранение id вопроса сообщения для викторины      
    def set_quiz_question_message_id(self, user_id, message_id, chat_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO question_message_id (user_id, message_id, chat_id) VALUES (?, ?, ?)", (user_id, message_id, chat_id))
            conn.commit()

    # Взятие id сообщения и чата где выведен вопрос    
    def get_quiz_question_message_id(self, user_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT message_id FROM question_message_id WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
        return result
    
    # Удаление викторины
    def quiz_delete(self, id_question):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM quiz_mod_answers WHERE id_question = ?", (id_question,))
            cursor.execute("DELETE FROM quiz_questions WHERE id = ?", (id_question,))
            conn.commit()