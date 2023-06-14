import sqlite3, configparser

class Database:
    def __init__(self, db_path_events, db_path_users):
        self.db_path_events = db_path_events
        self.db_path_users = db_path_users
        self.user_id = None
        
    def set_user_data(self, user_id, phone_number):
        self.user_id = user_id
        self.phone_number = phone_number

    def search_user(self):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT authorized FROM users WHERE user_id=?", (self.user_id,))
            result = cursor.fetchone()
        return result
    
    def get_database_connection_events(self):
        conn = sqlite3.connect(self.db_path_events)
        return conn

    def get_database_connection_users(self):
        conn = sqlite3.connect(self.db_path_users)
        return conn
    
    # Создание таблицы пользователей
    def create_users_table(self):
        with self.get_database_connection_users() as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            phone_number INTEGER UNIQUE,
                            userid INTEGER UNIQUE,
                            role TEXT,
                            region TEXT,
                            events TEXT,
                            authorized INTEGER
                        );''')
            conn.commit()       

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