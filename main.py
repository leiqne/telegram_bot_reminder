from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
import os
from dotenv import load_dotenv
from telegram.ext import *
from data_source import DataSource
import threading
import time
import asyncio
import datetime

load_dotenv()
TOKEN = os.getenv("TOKEN")
DATA=os.getenv("DATABASE_URL")

ENTER_MESSAGE, ENTER_TIME = range(2)
datasource = DataSource(DATA)

ADD_REMINDER_TEXT = "Add Reminder" 
INTERVAL= 30  

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello Honey!", reply_markup=add_reminder_button())

def add_reminder_button():
    keyboard = [[KeyboardButton(ADD_REMINDER_TEXT)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def add_reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please enter a message for the reminder: ")
    return ENTER_MESSAGE

async def enter_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["message_text"] = update.message.text
    await update.message.reply_text("Please enter a time when bot should remind format (dd/mm/yy hh:mm): ")
    return ENTER_TIME

async def enter_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = context.user_data["message_text"]
    time = datetime.datetime.strptime(update.message.text,"%d/%m/%Y %H:%M")
    message_data = datasource.create_reminder(update.message.chat_id, message_text, time)
    await update.message.reply_text("Your reminder:\n " + repr(message_data))
    return ConversationHandler.END



def start_check_reminders_task(app, loop):
    thread = threading.Thread(target=check_reminders, args=(app, loop))
    thread.daemon = True
    thread.start()

def check_reminders(app, loop):
    while True:
        for reminder_data in datasource.get_all_reminders():
            if reminder_data.should_be_fired():
                print(f"[{datetime.datetime.now()}] Envia mensaje → {reminder_data.message}")
                datasource.fire_reminder(reminder_data.reminder_id)

                asyncio.run_coroutine_threadsafe(
                    app.bot.send_message(reminder_data.chat_id, reminder_data.message),
                    loop
                )
        time.sleep(INTERVAL)


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(ADD_REMINDER_TEXT), add_reminder_handler)],
        states={
            ENTER_MESSAGE: [MessageHandler(filters.ALL, enter_message_handler)],
            ENTER_TIME: [MessageHandler(filters.ALL, enter_time_handler)],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    datasource.create_tables()
    loop = asyncio.get_event_loop()
    start_check_reminders_task(app, loop)

    app.run_polling()

