import sqlite3, configparser

class Database:
    def __init__(self, db_path_events, db_path_users):
        self.db_path_events = db_path_events
        self.db_path_users = db_path_users

    # Получение данных о пользователе из message_handler в dialog_bot    
    def set_user_data(self, user_id, phone_number):
        self.user_id = user_id
        self.phone_number = phone_number

    # Проверка на наличие пользователя в БД
    def user_exists(self, phone_number):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT authorized FROM users WHERE phone_number=?", (phone_number,))
            result = cursor.fetchone()
        return result is not None
    
    # Обновление записил пользователя в БД users
    def update_user(self, user_id, phone_number, first_name, last_name):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET user_id=?, authorized=?, first_name=?, last_name=? WHERE phone_number=?", (user_id, True, first_name, last_name, phone_number))
            conn.commit()

    #Добавление нового пользователя в БД users    
    def add_user(self, user_id, phone_number, first_name, last_name):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (user_id, phone_number, first_name, last_name, authorized) VALUES (?, ?, ?, ?, ?)", (user_id, phone_number, first_name, last_name, True))
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
            cursor.execute("SELECT date, place, event FROM events")
            events_list = cursor.fetchall()
        return events_list