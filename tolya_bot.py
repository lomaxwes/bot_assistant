import datetime
import os
import aiohttp
from sqlalchemy import create_engine, Column, Integer, VARCHAR, DateTime, inspect, Sequence
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, \
    CallbackContext
import json
from contextlib import contextmanager
import traceback


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
bot_token = os.getenv("TOKEN_BOT_GPT_MODEL")
file_path_errors = os.getenv("FILE_PATH_ERRORS")
file_path_users = os.getenv("FILE_PATH_USERS")
file_path_indefinite = os.getenv("FILE_PATH_INDEFINITE")


engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)
qa_id_seq = Sequence('qa_id_seq')


class QA(Base):
    __tablename__ = 'questions_answers'

    id = Column(Integer, qa_id_seq, primary_key=True)
    user_id = Column(Integer)
    user_name = Column(VARCHAR(200), nullable=True)
    question = Column(VARCHAR(2000))
    answer = Column(VARCHAR(2000), nullable=True)
    react = Column(Integer)
    comment = Column(VARCHAR(2000), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


inspector = inspect(engine)
if not inspector.has_table('questions_answers'):
    Base.metadata.create_all(engine)


try:
    with open(file_path_users, "r", encoding="utf-8") as file:
        users = json.load(file)
except FileNotFoundError:
    users = {}


try:
    with open(file_path_indefinite, "r", encoding="utf-8") as file:
        indefinite = json.load(file)
except FileNotFoundError:
    indefinite = {}


@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


async def get_answer_async(text):
    payload = {"text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post('http://127.0.0.1:8000/ask', json=payload) as resp:
            return await resp.json()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    first_name = update.message.from_user.first_name
    last_name = update.message.from_user.last_name

    if str(user_id) not in users:
        await update.message.reply_text(f"{first_name} {last_name or ''} вы не зарегистрированы. Ваш ID: {user_id}. Обратитесь в отдел IT для получения доступа!")
        if str(user_id) not in indefinite:
            indefinite[user_id] = f"{first_name} {last_name}"
            with open(file_path_indefinite, "w", encoding="utf-8") as file:
                json.dump(indefinite, file, ensure_ascii=False)
    else:
        await update.message.reply_text('Вы успешно зарегистрированы и имеете доступ. Задайте ваш вопрос ChatGPT')


# Удалено, тк содержит коммерческую информацию
async def process_model_output(raw_text):
    pass
    processed_text = ''
    return processed_text


def update_reaction(session, message_id, reaction):
    qa_record = session.query(QA).filter_by(id=message_id).first()
    if qa_record:
        qa_record.react = reaction
        session.commit()


async def button(update: Update, context: CallbackContext):
    query = update.callback_query


    reaction_str, qa_id_str = query.data.split(':')
    reaction = 1 if reaction_str == 'like' else 0

    await query.answer('Вы выбрали: {}'.format(reaction_str))

    if reaction_str == 'commit':
        context.user_data['awaiting_comment'] = qa_id_str
        await query.message.reply_text('Пожалуйста, отправьте комментарий к ответу:')
        return

    with session_scope() as session:
        qa_record = session.query(QA).filter_by(id=qa_id_str).first()
        if qa_record:
            qa_record.react = reaction
            session.commit()

            reaction_text = "like" if reaction == 1 else "dislike"
            button_text = f'Вы выбрали {reaction_text}'

            keyboard = [
                [
                    InlineKeyboardButton("👍", callback_data=f'like:{qa_id_str}'),
                    InlineKeyboardButton("👎", callback_data=f'dislike:{qa_id_str}'),
                ],
                [
                    InlineKeyboardButton("Комментарий", callback_data=f'commit:{qa_id_str}'),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.edit_text(f'Оценить ответ: {button_text}', reply_markup=reply_markup)


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = f"{update.message.from_user.first_name} {update.message.from_user.last_name or ''}"

    if str(user_id) not in users:
        await update.message.reply_text('У вас нет доступа. Обратитесь в отдел IT - офис 100.')
    elif update.message.text.startswith('/user_id'):
        await get_user_id(update, context)
    elif update.message.text.startswith('/first_name'):
        await get_user_first_name(update, context)
    elif update.message.text.startswith('/last_name'):
        await get_user_last_name(update, context)
    elif update.message.text.startswith('/username'):
        await get_username(update, context)
    else:
        if 'awaiting_comment' in context.user_data:
            qa_id = context.user_data['awaiting_comment']
            context.user_data.pop('awaiting_comment')

            with session_scope() as session:
                qa_record = session.query(QA).filter_by(id=qa_id).first()
                if qa_record:
                    qa_record.comment = update.message.text
                    session.commit()
                    await update.message.reply_text('Ваш комментарий сохранен.')
                else:
                    await update.message.reply_text('Ошибка: не удалось найти соответствующий вопрос/ответ в базе данных.')
        else:
            try:
                first_message = await update.message.reply_text('Ваш запрос обрабатывается, пожалуйста подождите...')
                res = await get_answer_async(update.message.text)
                if res['message'].count('\\\\') > 1:
                    processed_result = await process_model_output(res['message'])
                else:
                    processed_result = res['message']

                processed_result_truncated = processed_result[:2000]
                await context.bot.edit_message_text(text=processed_result, chat_id=update.message.chat_id,
                                                    message_id=first_message.message_id)

                with session_scope() as session:
                    new_qa = QA(user_id=user_id, user_name=user_name, question=update.message.text, answer=processed_result_truncated)
                    session.add(new_qa)
                    session.commit()

                    context.bot_data['last_qa_id'] = new_qa.id

                    keyboard = [
                        [
                            InlineKeyboardButton("👍", callback_data=f'like:{new_qa.id}'),
                            InlineKeyboardButton("👎", callback_data=f'dislike:{new_qa.id}'),
                        ],
                        [
                            InlineKeyboardButton("Комментарий", callback_data=f'commit:{new_qa.id}'),
                        ]
                    ]

                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text('Оценить ответ ', reply_markup=reply_markup)

            except Exception as e:
                current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(file_path_errors, "a", encoding="utf-8") as error_file:
                    error_file.write(f"Error {current_datetime}: {str(e)}\n")
                    error_file.write(f"Traceback: {traceback.format_exc()}\n")
                print(f"Ошибка при выполнении запроса в chatgpt: {e}")
                await update.message.reply_text('Произошла ошибка при обработке вашего запроса.')


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
    if last_name:
        await update.message.reply_text(f'Ваша фамилия в Telegram: {last_name}')
    else:
        await update.message.reply_text("У вас отсутствует фамилия пользователя.")


async def get_username(update, context) -> None:
    username = update.message.from_user.username
    if username:
        await update.message.reply_text(f'Ник пользователя в Telegram: {username}')
    else:
        await update.message.reply_text("У вас отсутствует ник пользователя.")


def main():
    application = Application.builder().token(bot_token).build()
    print('Бот запущен...')

    application.add_handler(CommandHandler("start", start, block=False))
    application.add_handler(CommandHandler("help", help_command, block=False))
    application.add_handler(CommandHandler("user_id", get_user_id, block=False))
    application.add_handler(CommandHandler("first_name", get_user_first_name, block=False))
    application.add_handler(CommandHandler("last_name", get_user_last_name, block=False))
    application.add_handler(CommandHandler("username", get_username, block=False))
    application.add_handler(MessageHandler(filters.TEXT, text, block=False))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()
    print('Бот остановлен')


if __name__ == "__main__":
    main()
