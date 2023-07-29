import enum
import os

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

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID_NEW = os.getenv("BOT_CHAT_ID_NEW")
CHAT_ID_POPULAR = os.getenv("BOT_CHAT_ID_POPULAR")


class ButtonValues(enum.StrEnum):
    POSITIVE_VOTE = "+"
    NEGATIVE_VOTE = "-"
    RATING = "="


def make_keyboard(rating: int = 0) -> InlineKeyboardMarkup:
    keyboad = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍", callback_data=ButtonValues.POSITIVE_VOTE),
            InlineKeyboardButton(f"{rating:+0d}", callback_data=ButtonValues.RATING),
            InlineKeyboardButton("👎", callback_data=ButtonValues.NEGATIVE_VOTE)
        ]
    ])
    return keyboad


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

    await query.answer()
    if updated:
        rating = await db.get_rating(query.message.message_id)
        keyboard = make_keyboard(rating[0] - rating[1])
        await query.edit_message_reply_markup(keyboard)

        if is_popular(rating):
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


async def start(update: Update, context: CallbackContext):
    """Handler for the /start command."""
    await update.message.reply_text(
        'Привет! Отправьте мне текстовое сообщение или фотографию, и я опубликую его в канале.'
    )


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


def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(~filters.COMMAND & filters.TEXT & filters.ChatType.PRIVATE, message_handler))
    application.add_handler(MessageHandler(~filters.COMMAND & filters.PHOTO & filters.ChatType.PRIVATE, media_handler))
    application.add_handler(CallbackQueryHandler(vote_handler))

    application.run_polling()


if __name__ == '__main__':
    main()
