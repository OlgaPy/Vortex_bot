import enum
from datetime import datetime
from typing import TypedDict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import COMMENTS_GROUP_TAG


class ButtonValues(enum.StrEnum):
    POSITIVE_VOTE = "+"
    NEGATIVE_VOTE = "-"
    RATING = "="


class Post(TypedDict):
    message_id: str
    user_id: str
    date: datetime
    comment_thread_id: str
    comment_count: int
    popular_id: str
    best_id: str
    media_group: str


class PostKeyboard:

    def __init__(
            self,
            *,
            rating: int = 0,
            comment_count: int = 0,
            thread_id: int | str = None
    ):
        self.rating = rating
        self.comment_count = comment_count
        self.thread_id = thread_id

    def to_reply_markup(self) -> InlineKeyboardMarkup:
        keyboad = [
            [
                InlineKeyboardButton("👍", callback_data=ButtonValues.POSITIVE_VOTE),
                InlineKeyboardButton(f"{self.rating:+0d}", callback_data=ButtonValues.RATING),
                InlineKeyboardButton("👎", callback_data=ButtonValues.NEGATIVE_VOTE)
            ],
        ]
        if self.thread_id is not None:
            url = f"https://t.me/{COMMENTS_GROUP_TAG.removeprefix('@')}/{self.thread_id}/{self.thread_id}"
            text = "Комментарии 💬" if self.comment_count == 0 else f"Комментарии ({self.comment_count}) 💬"
            keyboad.append([InlineKeyboardButton(text=text, url=url)])
        return InlineKeyboardMarkup(keyboad)
