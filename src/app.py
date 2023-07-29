import enum
import os
import threading
import logging

import flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)

import db

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID_NEW = os.getenv("TELEGRAM_CHANNEL_ID")
CHAT_ID_POPULAR = os.getenv("FORWARD_CHANNEL_ID")
COMMENTS_GROUP_ID = os.getenv("TELEGRAM_COMMENTS_GROUP_ID")

# Set up flask app
flask_app = flask.Flask(__name__)

# Set up logging to a file and console
LOG_FILE = os.getenv('LOG_FILE', default='bot.log')
logging.basicConfig(
    filename=LOG_FILE,
    format="%(asctime)s %(levelname)s | [%(name)s] %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.ERROR)

# Create a new console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(levelname)s | [%(name)s] %(message)s")
console_handler.setFormatter(formatter)

# Add the console handler to the root logger
logging.getLogger().addHandler(console_handler)

logger = logging.getLogger(__name__)


@flask_app.route('/healthz', methods=['GET'])
def healthcheck() -> tuple[str, int]:
    """Health check route for the Flask web application."""
    return 'Health check successful', 200


class ButtonValues(str, enum.Enum):
    POSITIVE_VOTE = "+"
    NEGATIVE_VOTE = "-"
    RATING = "="


def make_keyboard(rating: int = 0, tread_id: int = None) -> InlineKeyboardMarkup:
    keyboad = [
        [
            InlineKeyboardButton("👍", callback_data=ButtonValues.POSITIVE_VOTE),
            InlineKeyboardButton(f"{rating:+0d}", callback_data=ButtonValues.RATING),
            InlineKeyboardButton("👎", callback_data=ButtonValues.NEGATIVE_VOTE)
        ],
    ]
    if tread_id is not None:
        keyboad.append(
            [
                InlineKeyboardButton(
                    "Комментарии",
                    url=f"https://t.me/{COMMENTS_GROUP_ID}/{tread_id}/{tread_id}")
            ]
        )
    return InlineKeyboardMarkup(keyboad)


async def start(update: Update, _):
    """Handler for the /start command."""
    await update.message.reply_text(
        'Привет! Отправьте мне текстовое сообщение или фотографию, и я опубликую его в канале.'
    )


async def vote_handler(update: Update, _):
    query = update.callback_query
    updated = False

    if not query.data:
        return

    match query.data:
        case ButtonValues.POSITIVE_VOTE:
            updated = await db.set_user_vote(query.message.message_id, query.from_user.id, ButtonValues.POSITIVE_VOTE)
        case ButtonValues.NEGATIVE_VOTE:
            updated = await db.set_user_vote(query.message.message_id, query.from_user.id, ButtonValues.NEGATIVE_VOTE)
        case ButtonValues.RATING:
            rating = await db.get_rating(query.message.message_id)
            await query.answer(f"Плюсы: +{rating[0]}\nМинусы: -{rating[1]}")
            return

    logger.debug(
        f"Received vote \"{query.data}\" from user {query.from_user.username} on post {query.message.message_id}"
    )
    await query.answer()
    if updated:
        rating = await db.get_rating(query.message.message_id)
        keyboard = make_keyboard(rating[0] - rating[1])
        await query.edit_message_reply_markup(keyboard)

        if is_popular(rating):
            logger.info(f"Forwarding message {query.message.message_id} to Popular channel")
            await query.message.forward(CHAT_ID_POPULAR)


def is_popular(rating: tuple[int, int]) -> bool:
    """Checks if message is situatable for popular"""

    if rating[0] + rating[1] == 0:
        return False

    # positive votes more than 80% and this is at least 5 positive votes
    return (rating[0] - rating[1]) / (rating[0] + rating[1]) > 0.8 and rating[0] >= 5


async def media_handler(update: Update, context: CallbackContext) -> None:
    """Handler for media files (photos)."""
    user_id: int = update.message.from_user.id
    media_message = update.message
    caption: str | None = media_message.caption

    # Check the user's post count for today in the database
    user_post_count = await db.get_post_count_for_user(user_id)

    if user_post_count >= 5:
        await update.message.reply_text('Вы достигли лимита постов на сегодня (5 постов). Попробуйте завтра!')
        return

    user_name = update.message.from_user.first_name  # Get user's first name
    username = update.message.from_user.username  # Get user's username

    user_signature = (
        f"{user_name}: {caption}" if caption
        else f"@{username}: {caption}" if username
        else f"Аноним: {caption}"
    ) if caption else ""

    media_file = media_message.photo[-1]
    msg = await context.bot.send_photo(
        chat_id=CHAT_ID_NEW,
        photo=media_file.file_id,
        caption=user_signature,
        reply_markup=make_keyboard(),
    )

    await db.add_post(msg.message_id, user_id)
    logger.info(f"Created new post {msg.message_id} by user {username}")


async def message_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    # Check the user's post count for today in the database
    user_post_count = await db.get_post_count_for_user(update.message.from_user.id)

    if user_post_count >= 5:
        await update.message.reply_text('Вы достигли лимита постов на сегодня (5 постов). Попробуйте завтра!')
        return

    content = f"@{update.message.from_user.username}\n{update.message.text}"
    msg = await context.bot.send_message(CHAT_ID_NEW, content, reply_markup=make_keyboard())
    await db.add_post(msg.message_id, user_id)
    logger.info(f"Created new post {msg.message_id} by user {update.message.from_user.username}")


def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(~filters.COMMAND & filters.TEXT & filters.ChatType.PRIVATE, message_handler))
    application.add_handler(MessageHandler(~filters.COMMAND & filters.PHOTO & filters.ChatType.PRIVATE, media_handler))
    application.add_handler(CallbackQueryHandler(vote_handler))

    application.run_polling()


if __name__ == '__main__':
    flask_thread = threading.Thread(target=flask_app.run, kwargs={"host": "0.0.0.0", "port": 8080})
    flask_thread.start()
    main()
