import logging
import os
import threading

import flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)

import db
from config import CHAT_ID_NEW, CHAT_ID_POPULAR, COMMENTS_GROUP_ID, TOKEN
from models import ButtonValues, PostKeyboard

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


async def start_command(update: Update, _):
    """Handler for the /start command."""
    await update.message.reply_text(
        'Привет! Отправьте мне текстовое сообщение или фотографию, и я опубликую его в канале.'
    )


async def my_posts_command(update: Update, _):
    """Handler for /my_posts command"""

    await update.message.reply_text("В разработке!")


async def edit_post_command(update: Update, _):
    """Handler from /edit command"""

    await update.message.reply_text("В разработке!")


async def stat_command(update: Update, _):
    """Handler from /stat command"""

    user_post_count = await db.get_post_count_for_user(update.message.from_user.id)
    text = ""
    match user_post_count:
        case 0:
            text = "За последние 24 часа от Вас не было постов. Самое время это исправить!"
        case 1:
            text = "Сегодня вы запостили одну публикацию. Доступно еще 4."
        case 2 | 3 | 4:
            text = f"Сегодня вы запостили {user_post_count} публикации. Доступно еще {5 - user_post_count}."
        case 5:
            text = "Сегодня вы сделали целых пять постов, отличная работа! Но пора отдохнуть :)"
    await update.message.reply_text(text)


async def rating_command(update: Update, context: CallbackContext):
    """Handler from /rating command"""

    rating = await db.get_user_rating(update.message.from_user.id)
    text = f"Ваш рейтинг: {rating}"
    await update.message.reply_text(text)


async def vote_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    updated = False

    if not query.data:
        return

    if str(query.message.chat_id) == CHAT_ID_POPULAR:
        post = await db.get_post_by_popular_id(query.message.message_id)
    else:
        post = await db.get_post(query.message.message_id)

    match query.data:
        case ButtonValues.POSITIVE_VOTE:
            updated = await db.set_user_vote(post["message_id"], query.from_user.id, ButtonValues.POSITIVE_VOTE)
        case ButtonValues.NEGATIVE_VOTE:
            updated = await db.set_user_vote(post["message_id"], query.from_user.id, ButtonValues.NEGATIVE_VOTE)
        case ButtonValues.RATING:
            rating = await db.get_rating(post["message_id"])
            user_vote = await db.get_user_vote(post["message_id"], query.from_user.id)
            text = f"Плюсы: +{rating[0]}\nМинусы: -{rating[1]}"
            if user_vote is not None:
                text += f"\nВаша оценка: {user_vote}"
            else:
                text += f"\nВы еще не оценили этот пост"
            await query.answer(text)
            return

    logger.debug(
        f"Received vote \"{query.data}\" from user {query.from_user.username} on post {post['message_id']}"
    )
    await query.answer()
    if not updated:
        return

    rating = await db.get_rating(post["message_id"])
    keyboard = PostKeyboard(
        rating=rating[0] - rating[1],
        thread_id=post["comment_thread_id"],
        comments=post["comments"]
    )
    await context.bot.edit_message_reply_markup(
        chat_id=CHAT_ID_NEW,
        message_id=int(post["message_id"]),
        reply_markup=keyboard.to_reply_markup()
    )

    if post.get("popular_id") is not None:
        await context.bot.edit_message_reply_markup(
            chat_id=CHAT_ID_POPULAR,
            message_id=int(post["popular_id"]),
            reply_markup=keyboard.to_reply_markup()
        )

    if post.get("popular_id") is None and is_popular(rating):
        msg = await query.message.copy(CHAT_ID_POPULAR, reply_markup=keyboard.to_reply_markup())
        await db.add_to_popular(post["message_id"], msg.message_id)
        logger.info(f"Post {post['message_id']} became popular")


def is_popular(rating: tuple[int, int]) -> bool:
    """Checks if message is situatable for popular"""

    if rating[0] + rating[1] == 0:
        return False

    # positive votes more than 80% and this is at least 20 positive votes
    return rating[0] / (rating[0] + rating[1]) > 0.8 and rating[0] >= 20


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

    name = f"@{username}" if username else user_name
    user_signature = f"{name}\n{caption}\n" if caption else f"{name}"

    media_file = media_message.photo[-1]
    msg = await context.bot.send_photo(
        chat_id=CHAT_ID_NEW,
        photo=media_file.file_id,
        caption=user_signature,
        reply_markup=PostKeyboard().to_reply_markup(),
    )

    thread = await msg.copy(COMMENTS_GROUP_ID, disable_notification=True)
    await context.bot.pin_chat_message(COMMENTS_GROUP_ID, thread.message_id)
    keyboard = PostKeyboard(thread_id=thread.message_id)
    await msg.edit_reply_markup(keyboard.to_reply_markup())

    await db.add_post(msg.message_id, user_id, thread.message_id)
    logger.info(f"Created new post {msg.message_id} by user {username}")


async def message_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    # Check the user's post count for today in the database
    user_post_count = await db.get_post_count_for_user(update.message.from_user.id)

    if user_post_count >= 5:
        await update.message.reply_text('Вы достигли лимита постов на сегодня (5 постов). Попробуйте завтра!')
        return

    keyboard = PostKeyboard()

    username = update.message.from_user.username
    user_name = update.message.from_user.first_name
    caption = update.message.caption
    name = f"@{username}" if username else user_name
    user_signature = f"{name}\n{caption}\n" if caption else f"{name}"
    content = f"{user_signature}\n{update.message.text}"
    msg = await context.bot.send_message(CHAT_ID_NEW, content, reply_markup=keyboard.to_reply_markup())

    thread = await msg.copy(COMMENTS_GROUP_ID, disable_notification=True)
    keyboard.thread_id = thread.message_id
    await context.bot.pin_chat_message(COMMENTS_GROUP_ID, thread.message_id)
    await msg.edit_reply_markup(keyboard.to_reply_markup())

    await db.add_post(msg.message_id, user_id, thread.message_id)
    logger.info(f"Created new post {msg.message_id} by user {update.message.from_user.username}")


async def comments_handler(update: Update, context: CallbackContext):
    """Handler for user comments"""

    thread_id = update.message.message_thread_id
    if not thread_id or update.message.pinned_message:
        return

    logger.info(f"User {update.message.from_user.username} left a comment in {thread_id} thread")

    post = await db.increase_comments_counter(thread_id)
    rating = await db.get_rating(post["message_id"])
    keyboard = PostKeyboard(
        rating=rating[0] - rating[1],
        thread_id=post["comment_thread_id"],
        comments=post["comments"]
    )

    await context.bot.edit_message_reply_markup(
        chat_id=CHAT_ID_NEW,
        message_id=int(post["message_id"]),
        reply_markup=keyboard.to_reply_markup()
    )

    if post.get("popular_id") is not None:
        await context.bot.edit_message_reply_markup(
            chat_id=CHAT_ID_POPULAR,
            message_id=int(post["popular_id"]),
            reply_markup=keyboard.to_reply_markup()
        )


def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # commands
    application.add_handler(CommandHandler("start", start_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("stat", stat_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("rating", rating_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("my_posts", my_posts_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("edit", edit_post_command, filters=filters.ChatType.PRIVATE))

    application.add_handler(MessageHandler(~filters.COMMAND & filters.TEXT & filters.ChatType.PRIVATE, message_handler))
    application.add_handler(MessageHandler(~filters.COMMAND & filters.PHOTO & filters.ChatType.PRIVATE, media_handler))
    application.add_handler(CallbackQueryHandler(vote_handler))
    application.add_handler(MessageHandler(~filters.COMMAND & filters.Chat(int(COMMENTS_GROUP_ID)), comments_handler))

    application.run_polling()


if __name__ == '__main__':
    flask_thread = threading.Thread(target=flask_app.run, kwargs={"host": "0.0.0.0", "port": 8080})
    flask_thread.start()
    main()
