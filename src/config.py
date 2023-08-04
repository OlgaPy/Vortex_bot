import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID_NEW = os.getenv("TELEGRAM_CHANNEL_ID")
CHAT_ID_POPULAR = os.getenv("TELEGRAM_POPULAR_CHANNEL_ID")
COMMENTS_GROUP_ID = os.getenv("TELEGRAM_COMMENTS_GROUP_ID")
COMMENTS_GROUP_TAG = os.getenv("TELEGRAM_COMMENTS_GROUP_TAG")

MAX_USER_POST_COUNT_PER_DAY = int(os.getenv("MAX_USER_POST_COUNT_PER_DAY", 5))

POPULAR_POSITIVE_VOTES_PERCENTAGE = int(os.getenv("POPULAR_POSITIVE_VOTES_PERCENTAGE", 80))
POPULAR_POSITIVE_VOTES_MIN_COUNT = int(os.getenv("POPULAR_POSITIVE_VOTES_MIN_COUNT", 20))

_default_welcome_text = """
Добро пожаловать в бот канала Капибара Новое! 

Здесь каждый может поделиться своими творческими историями, фотографиями и другими удивительными моментами. Канал основного проекта t.me/new_old_pikabu 

Когда ваш пост откликнется у других пользователей он появится на канале Капибара Популярное https://t.me/best_kapibara
Добавлять посты через этого бота: @ContentAddBot

Используйте пожалуйста те же #теги которые были на пкб.
После публикации ваш пост появится на https://t.me/new_kapibara. В данный момент доступны для публикации фото, видео, тест и теги

Навигация по проекту: https://t.me/new_old_pikabu/83517/83518
"""
WELCOME_TEXT = os.getenv("WELCOME_TEXT", _default_welcome_text)