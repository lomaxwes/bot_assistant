import os
from dotenv import load_dotenv
from telegram import Update
from pprint import pprint
from telegram.ext import Application, CommandHandler, MessageHandler, filters

load_dotenv()

bot_token = os.getenv("TOKEN_BOT_FOR_ID_USER")


async def start(update, context) -> None:
    user_id = update.message.from_user.id
    first_name = update.message.from_user.first_name
    last_name = update.message.from_user.last_name
    start_text = f"Привет, {first_name} {last_name}!\nВаш ID {user_id}\n/help - все команды"
    await update.message.reply_text(start_text)


async def help_command(update, context) -> None:
    help_text = ("Доступные команды:\n/start - начать работу\n/help - справка\n/user_id - узнать ID\n/first_name - "
                 "ваше имя в Telegram\n/last_name - ваша фамилия в Telegram\n/username - ник в Telegram")
    await update.message.reply_text(help_text)


async def get_user_id(update, context) -> None:
    user_id = update.message.from_user.id
    await update.message.reply_text(f'Ваш ID в Telegram: {user_id}')


async def get_user_first_name(update, context) -> None:
    first_name = update.message.from_user.first_name
    await update.message.reply_text(f'Ваше имя в Telegram: {first_name}')


async def get_user_last_name(update, context) -> None:
    last_name = update.message.from_user.last_name
    await update.message.reply_text(f'Ваша фамилия в Telegram: {last_name}')


async def get_username(update, context) -> None:
    username = update.message.from_user.username
    if username:
        await update.message.reply_text(f'Ник пользователя в Telegram: {username}')
    else:
        await update.message.reply_text("У вас отсутствует ник пользователя.")


def main():
    application = Application.builder().token(bot_token).build()
    print('Бот запущен')

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("user_id", get_user_id))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("first_name", get_user_first_name))
    application.add_handler(CommandHandler("last_name", get_user_last_name))
    application.add_handler(CommandHandler("username", get_username))

    application.run_polling()
    print('Бот остановлен')


if __name__ == '__main__':
    main()
