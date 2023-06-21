import sqlite3, configparser

class Database:
    def __init__(self):
    
        # Чтение файла конфигурации
        config = configparser.ConfigParser()
        config.read('./config.ini')

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
    
    # Выдача информации по пользователю
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
    
    # Проверка роли пользователя
    def get_user_role(self, user_id):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE user_id=?", (user_id,))
            result = cursor.fetchone()
        return result[0] if result else None
    
    # Обновление записи пользователя в БД users
    def update_user(self, user_id, phone_number, first_name, last_name):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET user_id=?, authorized=?, first_name=?, last_name=? WHERE phone_number=?", (user_id, True, first_name, last_name, phone_number))
            conn.commit()

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
            cursor.execute("UPDATE users SET role='user' WHERE phone_number=?", (phone_number,))
            conn.commit()

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
    
    def update_user_authorized(self, user_id, authorized):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET authorized = ? WHERE user_id = ?", (authorized, user_id))
            conn.commit()

    def insert_user(self, phone_number, first_name, last_name, region, events):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (phone_number, first_name, last_name, region, events, authorized) VALUES (?, ?, ?, ?, ?, ?)",
                                (phone_number, first_name, last_name, region, events, 0))
            conn.commit()