from .database import Database
import configparser
import telebot
from telebot import types

class Moderation:
    def __init__(self, bot):
        self.database = Database()
        self.bot = bot

    # Меню для разных ролей
    @staticmethod
    def admin_markup():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        add_moderator_button = types.KeyboardButton(text="Добавить модератора")
        delete_moderator_button = types.KeyboardButton(text="Снять с поста модератора")
        distribution_button= types.KeyboardButton(text="Создать рассылку")
        markup.add(add_moderator_button)
        markup.add(delete_moderator_button)
        markup.add(distribution_button)
        return markup

    @staticmethod
    def moder_markup():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        distribution_button= types.KeyboardButton(text="Создать рассылку")
        markup.add(distribution_button)
        return markup
    
    @staticmethod
    def user_markup():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        distribution_button= types.KeyboardButton(text="События")
        markup.add(distribution_button)
        return markup

    # Обработка кнопки "Модерация"
    def moderation_buttonn_klick(self, user_id):
        role = self.database.get_user_role(user_id)
        markup = None          
        if role == "admin":
            markup = self.admin_markup()
            self.bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
        elif role == "moderator":
            markup = self.moder_markup()
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)
        else:      
            markup = self.user_markup()     
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)

    # Обработка кнопки "Добавить модератора"
    def add_moderator_button(self, user_id):
        role = self.database.get_user_role(user_id)
        markup = None         
        if role != "admin":
            markup = self.user_markup()
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)
            if role == "moderator":                
                markup = self.moder_markup()
                self.bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
        else:
            markup = self.admin_markup()
            self.bot.send_message(user_id, text="Команда для назначения модератора: /add_mod \n\n Пример ее использования:\n /add_mod 79998887766", reply_markup=markup)
    
    # Обработка команды /add_mod
    def add_moderator(self, user_id, phone_number):
        role = self.database.get_user_role(user_id)
        markup = None
        if role == "admin":
            user_exists = self.database.user_exists_phone(phone_number)
            if user_exists:
                user_info = self.database.user_info(phone_number)
                # Формируем сообщение с информацией о пользователе
                user_message = f"Имя: {user_info[2]}\nФамилия: {user_info[3]}\nНомер телефона: {user_info[0]}\nID: {user_info[1]}\nРоль: {user_info[4]}"

                # Создаем клавиатуру с кнопками "Подтвердить" и "Отмена"
                keyboard = types.InlineKeyboardMarkup()
                confirm_add_mod_button = types.InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_add_mod_{phone_number}")
                cancel_add_mod_button = types.InlineKeyboardButton(text="Отмена", callback_data="cancel_add_mod")
                keyboard.add(confirm_add_mod_button, cancel_add_mod_button)

                # Отправляем сообщение с клавиатурой
                self.bot.send_message(user_id, user_message, reply_markup=keyboard)
            else:
                self.bot.send_message(user_id, "Пользователь не найден")           
        elif role == "moderator":
            markup = self.moder_markup()
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)
        else:
            markup = self.user_markup()            
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)    

    # Обработка кнопки "Удалить модератора"
    def remove_moderator_button(self, user_id):
        role = self.database.get_user_role(user_id)        
        if role != "admin":
            markup = self.user_markup() 
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)
            if role == "moderator":                
                markup = self.moder_markup()
                self.bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
        else:
            markup = self.admin_markup()
            self.bot.send_message(user_id, text="Команда для снятия модератора: /remove_mod \n\n Пример ее использования:\n /remove_mod 79998887766", reply_markup=markup)

    def remove_moderator(self, user_id, phone_number):
        role = self.database.get_user_role(user_id)
        markup = None
        if role == "admin":
            user_exists = self.database.user_exists_phone(phone_number)
            if user_exists:
                user_info = self.database.user_info(phone_number)
                # Формируем сообщение с информацией о пользователе
                user_message = f"Имя: {user_info[2]}\nФамилия: {user_info[3]}\nНомер телефона: {user_info[0]}\nID: {user_info[1]}\nРоль: {user_info[4]}"
                
                # Создаем клавиатуру с кнопками "Подтвердить" и "Отмена"
                keyboard = types.InlineKeyboardMarkup()
                confirm_remove_mod_button = types.InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_remove_mod_{phone_number}")
                cancel_remove_mod_button = types.InlineKeyboardButton(text="Отмена", callback_data="cancel_remove_mod")
                keyboard.add(confirm_remove_mod_button, cancel_remove_mod_button)

                # Отправляем сообщение с клавиатурой
                self.bot.send_message(user_id, user_message, reply_markup=keyboard)
            else:
                self.bot.send_message(user_id, "Пользователь не найден")           
        elif role == "moderator":
            markup = self.moder_markup()
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)
        else:
            markup = self.user_markup()            
            self.bot.send_message(user_id, "У вас недостаточно прав", reply_markup=markup)

    def create_distribution(self, user_id):
        # Логика создания рассылки
        pass

        
        