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

Чтобы сообщение попало в ленту основного проекта (t.me/new_kapibara) просто отправь его мне, а если у тебя объёмный текст с изображениями, то для его оформления удобно использовать встроенный в телеграм сервис телеграф https://telegra.ph

КАК ОПУБЛИКОВАТЬ ПОСТ

1. Отправьте сообщение боту и он перешлет его в телеграм-канал Капибара новое https://t.me/new_kapibara

2. К сообщению можно прикрепить изображение или видео

3. Добавьте к тексту сообщения теги, например, #мое #капибара и любые другие, которые соответствуют вашему посту. Используйте, пожалуйста, те же #теги которые были на пкб.

4. Некоторые возможности телеграм не поддерживаются на данный момент ботом: нельзя добавить стиль тексту жирный, подчеркнутый, зачеркнутый, курсив и так далее.

5. Если возможностей бота недостаточно, то можно воспользоваться сервисом телеграф https://telegra.ph
В нем можно добавлять картинки в середину текста, оформить заголовок и добавлять ссылки.

6. При публикации контента учитывайте правила постинга: t.me/new_old_pikabu/83517/196460. Материал, не соответствующий правилам, будет удален модераторами. Если есть сомнения, лучше предварительно уточнить у модераторов о возможности публикации.

7. После публикации ваш пост появится на https://t.me/new_kapibara

8. Если ваш пост откликнется в сердцах других пользователей, то он появится и на канале Капибара Популярное https://t.me/best_kapibara
"""
WELCOME_TEXT = os.getenv("WELCOME_TEXT", _default_welcome_text)
