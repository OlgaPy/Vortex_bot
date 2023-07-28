import enum
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackContext, filters, CallbackQueryHandler

import db

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("BOT_CHAT_ID")


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
            await query.message.forward(CHAT_ID)


def is_popular(rating: tuple[int, int]) -> bool:
    """Checks if message is situatable for popular"""

    if rating[0] + rating[1] == 0:
        return False

    # positive votes more than 80% and this is at least 5 positive votes
    return (rating[0] - rating[1]) / (rating[0] + rating[1]) > 0.8 and rating[0] >= 5


async def message_handler(update: Update, context: CallbackContext):
    await context.bot.send_message(CHAT_ID, update.message.text, reply_markup=make_keyboard())


def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(MessageHandler(~filters.COMMAND & filters.TEXT, message_handler))
    application.add_handler(CallbackQueryHandler(vote_handler))

    application.run_polling()


if __name__ == '__main__':
    main()
