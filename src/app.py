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
from config import (
    CHAT_ID_NEW, 
    CHAT_ID_POPULAR, 
    COMMENTS_GROUP_ID, 
    TOKEN,
    MAX_USER_POST_COUNT_PER_DAY,
    POPULAR_POSITIVE_VOTES_PERCENTAGE,
    POPULAR_POSITIVE_VOTES_MIN_COUNT,
)
from helpers import plural_ru
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


async def start(update: Update, _):
    """Handler for the /start command."""
    await update.message.reply_text(
        'Привет! Отправьте мне текстовое сообщение, фотографию '
        'или видео, и я опубликую его в канале.'
    )


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

    positive_votes, negative_votes = rating
    if positive_votes + negative_votes == 0:
        return False
    
    positive_votes_percentage = positive_votes / (positive_votes + negative_votes) * 100

    # positive votes more than 80% and this is at least 20 positive votes
    return (
        positive_votes_percentage > POPULAR_POSITIVE_VOTES_PERCENTAGE 
        and positive_votes >= POPULAR_POSITIVE_VOTES_MIN_COUNT
    )


async def media_handler(update: Update, context: CallbackContext) -> None:
    """Handler for media files (photos)."""
    user_id: int = update.message.from_user.id
    media_message = update.message
    caption: str | None = media_message.caption

    # Check the user's post count for today in the database
    user_post_count = await db.get_post_count_for_user(user_id)

    if user_post_count >= MAX_USER_POST_COUNT_PER_DAY:
        plural_posts_msg = plural_ru(MAX_USER_POST_COUNT_PER_DAY, ["пост", "поста", "постов"])
        await update.message.reply_text(
            'Вы достигли лимита постов на сегодня '
            f'({MAX_USER_POST_COUNT_PER_DAY} {plural_posts_msg}). Попробуйте завтра!'
        )
        return

    media_group = media_message.media_group_id
    if media_group is not None:
        post = await db.get_post_by_media_group(media_group)
        if post is not None:
            if media_message.photo:
                await context.bot.send_photo(
                    photo=update.message.photo[-1],
                    chat_id=COMMENTS_GROUP_ID,
                    reply_to_message_id=int(post["comment_thread_id"]),
                )
            elif media_message.video:
                await context.bot.send_video(
                    video=media_message.video,
                    chat_id=COMMENTS_GROUP_ID,
                    reply_to_message_id=int(post["comment_thread_id"]),
                )
            else:
                logger.error(f"Unknown media type in message {media_message}")
            return

    user_name = update.message.from_user.first_name  # Get user's first name
    username = update.message.from_user.username  # Get user's username

    name = f"@{username}" if username else user_name
    user_signature = f"{name}\n{caption}\n" if caption else f"{name}"

    if media_message.photo:
        msg = await context.bot.send_photo(
            chat_id=CHAT_ID_NEW,
            photo=media_message.photo[-1],
            caption=user_signature,
            reply_markup=PostKeyboard().to_reply_markup(),
        )
    elif media_message.video:
        msg = await context.bot.send_video(
            chat_id=CHAT_ID_NEW,
            video=media_message.video,
            caption=user_signature,
            reply_markup=PostKeyboard().to_reply_markup(),
        )
    else:
        logger.error(f"Unknown media type in message {media_message}")
        return

    thread = await msg.copy(COMMENTS_GROUP_ID, disable_notification=True)
    await context.bot.pin_chat_message(COMMENTS_GROUP_ID, thread.message_id)
    keyboard = PostKeyboard(thread_id=thread.message_id)
    await msg.edit_reply_markup(keyboard.to_reply_markup())

    await db.add_post(msg.message_id, user_id, thread.message_id, media_group)
    logger.info(f"Created new post {msg.message_id} by user {username}")


async def message_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    # Check the user's post count for today in the database
    user_post_count = await db.get_post_count_for_user(update.message.from_user.id)

    if user_post_count >= MAX_USER_POST_COUNT_PER_DAY:
        plural_posts_msg = plural_ru(MAX_USER_POST_COUNT_PER_DAY, ["пост", "поста", "постов"])
        await update.message.reply_text(
            'Вы достигли лимита постов на сегодня '
            f'({MAX_USER_POST_COUNT_PER_DAY} {plural_posts_msg}). Попробуйте завтра!'
        )
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
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .connect_timeout(10)  # default 5s
        .read_timeout(30)  # default 5s
        .write_timeout(30)  # default 5s
        .get_updates_connect_timeout(60)  # default 5s
        .get_updates_pool_timeout(60)  # default 1s
        .get_updates_read_timeout(60)  # default 5s
        .get_updates_write_timeout(60)  # default 5s
        .pool_timeout(10)  # default 1s
        .build()
    )

    application.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(~filters.COMMAND & filters.TEXT & filters.ChatType.PRIVATE, message_handler))
    application.add_handler(
        MessageHandler(~filters.COMMAND & (filters.PHOTO | filters.VIDEO) & filters.ChatType.PRIVATE, media_handler))
    application.add_handler(CallbackQueryHandler(vote_handler))
    application.add_handler(MessageHandler(~filters.COMMAND & filters.Chat(int(COMMENTS_GROUP_ID)), comments_handler))

    application.run_polling(
        allowed_updates=[
            Update.MESSAGE, 
            Update.CALLBACK_QUERY,
        ]
    )


if __name__ == '__main__':
    flask_thread = threading.Thread(target=flask_app.run, kwargs={"host": "0.0.0.0", "port": 8080})
    flask_thread.start()
    main()
