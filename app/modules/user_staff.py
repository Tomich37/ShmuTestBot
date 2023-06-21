from .database import Database
import configparser
import telebot
from telebot import types


class User:
    def __init__(self, bot, database, authorized_user):
        self.bot = bot
        self.database = database
        self.current_position = 0
        self.block_size = 5  # Здесь можно указать желаемый размер блока мероприятий
        self.authorized_user = authorized_user  # Add authorized_user attribute and assign its value


    def events_handler(self, message):
        if self.authorized_user:  # Проверка на авторизацию
            # Получение информации из events.db
            events_list = self.database.get_events()

            if self.current_position >= len(events_list):
                self.bot.send_message(message.chat.id, "Больше нет мероприятий.")
            else:
                events_to_display = events_list[self.current_position : self.current_position + self.block_size]
                response = "Мероприятия: \n\n"
                for event in events_to_display:
                    response += f"Дата: {event[0]}\n"
                    response += f"Место проведения: {event[1]}\n"
                    response += f"Мероприятие: {event[2]}\n\n"
                self.bot.send_message(message.chat.id, response, reply_markup=self.get_pagination_buttons())
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            contact_button = types.KeyboardButton(text="Поделиться телефоном", request_contact=True)
            markup.add(contact_button)
            self.bot.send_message(
                message.chat.id,
                "Вы не авторизировались, для продолжения предоставьте номер телефона",
                reply_markup=markup,
            )

    def get_pagination_buttons(self):
        markup = types.InlineKeyboardMarkup()
        next_button = types.InlineKeyboardButton("Следующие", callback_data="next")
        prev_button = types.InlineKeyboardButton("Предыдущие", callback_data="prev")
        markup.row(prev_button, next_button)
        return markup

    def handle_button_click(self, call):
        if call.data == "next":
            self.next_events(call)
        elif call.data == "prev":
            self.prev_events(call)
        self.bot.answer_callback_query(callback_query_id=call.id)

    def prev_events(self, call):
        if self.current_position == 0:
            self.bot.answer_callback_query(callback_query_id=call.id, text="Это первая страница.")
            return

        self.current_position -= self.block_size
        if self.current_position < 0:
            self.current_position = 0

        events_list = self.database.get_events()
        events_to_display = events_list[self.current_position : self.current_position + self.block_size]
        response = "Мероприятия:\n\n"
        for event in events_to_display:
            response += f"Дата: {event[0]}\n"
            response += f"Место проведения: {event[1]}\n"
            response += f"Мероприятие: {event[2]}\n\n"

        try:
            self.bot.edit_message_text(
                response,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=self.get_pagination_buttons(),
                disable_web_page_preview=True,
            )
        except telebot.apihelper.ApiTelegramException as e:
            print(f"Failed to edit message: {e}")

    def next_events(self, call):
        self.current_position += self.block_size

        events_list = self.database.get_events()
        if self.current_position >= len(events_list):
            self.current_position -= self.block_size
            self.bot.answer_callback_query(callback_query_id=call.id, text="Больше нет мероприятий.")
            return

        events_to_display = events_list[self.current_position : self.current_position + self.block_size]
        response = "Мероприятия:\n\n"
        for event in events_to_display:
            response += f"Дата: {event[0]}\n"
            response += f"Место проведения: {event[1]}\n"
            response += f"Мероприятие: {event[2]}\n\n"

        if self.current_position >= len(events_list):
            response += "\n\nЭто последняя страница."
        self.bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=self.get_pagination_buttons(),
        )