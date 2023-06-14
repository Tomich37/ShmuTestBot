import sqlite3, configparser

class Database:
    def __init__(self, db_path_events, db_path_users):
        self.db_path_events = db_path_events
        self.db_path_users = db_path_users

    def get_database_connection_events(self):
        conn = sqlite3.connect(self.db_path_events)
        return conn

    def get_database_connection_users(self):
        conn = sqlite3.connect(self.db_path_users)
        return conn

    def create_events_table(self):
        cursor = self.connection_events.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS events (
                            eventid INTEGER PRIMARY KEY AUTOINCREMENT,
                            date TEXT,
                            place TEXT,
                            event TEXT
                        );''')
        self.connection_events.commit()

    def create_users_table(self):
        cursor = self.connection_users.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            userid INTEGER PRIMARY KEY,
                            nickname TEXT,
                            phone_number TEXT,
                            role TEXT,
                            region TEXT,
                            eventа TEXT
                        );''')
        self.connection_users.commit()        

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