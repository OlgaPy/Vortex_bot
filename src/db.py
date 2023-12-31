import os
from typing import Optional

import aiopg
from psycopg2.extras import DictCursor

from models import Post


def build_dsn():
    dbname = os.getenv('DB_NAME', default="main")
    user = os.getenv('DB_USER', default="postgres")
    password = os.getenv('DB_PASSWORD', default="")
    host = os.getenv('DB_HOST', default="localhost")
    port = os.getenv('DB_PORT', default="5432")
    return f"dbname={dbname} user={user} password={password} host={host} port={port}"


class ConnectionManager:
    _instance: Optional['ConnectionManager'] = None
    _connection: aiopg.Connection | None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @property
    def connected(self) -> bool:
        return self._connection is not None and not self._connection.closed

    async def connection(self) -> aiopg.Connection:
        return await self.__aenter__()

    async def __aenter__(self) -> aiopg.Connection:
        if not self.connected:
            self._connection = await aiopg.connect(build_dsn(), cursor_factory=DictCursor)

        return self._connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connected:
            await self._connection.close()


async def get_user_vote(message_id: int | str, user_id: int | str) -> str | None:
    stmt = """
    SELECT vote FROM votes WHERE (message_id, user_id) = (%(message_id)s, %(user_id)s);
    """
    params = {
        "message_id": str(message_id),
        "user_id": str(user_id)
    }
    conn = await ConnectionManager().connection()
    async with conn.cursor() as cur:
        await cur.execute(stmt, params)
        result = await cur.fetchone()

    return result[0] if result else None


async def set_user_vote(message_id: int | str, user_id: int | str, vote: str) -> bool:
    current_vote = await get_user_vote(message_id, user_id)
    if current_vote is None:
        stmt = """
        INSERT INTO votes (message_id, user_id, vote) VALUES (%(message_id)s, %(user_id)s, %(vote)s);
        """
    elif vote != current_vote:
        stmt = """
        DELETE FROM votes WHERE (message_id, user_id) = (%(message_id)s, %(user_id)s);
        """
    else:
        return False

    params = {
        "message_id": str(message_id),
        "user_id": str(user_id),
        "vote": vote
    }

    conn = await ConnectionManager().connection()
    async with conn.cursor() as cur:
        await cur.execute(stmt, params)

    return True


async def get_rating(message_id: int | str) -> tuple[int, int]:
    stmt = """
    SELECT vote, COUNT(vote) FROM votes WHERE message_id = %(message_id)s GROUP BY vote;
    """

    params = {
        "message_id": str(message_id),
    }

    conn = await ConnectionManager().connection()
    async with conn.cursor() as cur:
        await cur.execute(stmt, params)
        result = await cur.fetchall()
    
    result = dict(result)
    return result.get("+", 0), result.get("-", 0)


async def add_post(
        message_id: int | str,
        user_id: int | str,
        thread_id: int | str,
        media_group: str | None = None
):
    """Save post information"""

    stmt = """
    INSERT INTO posts (message_id, user_id, date, comment_thread_id, media_group) 
    VALUES (%(message_id)s, %(user_id)s, now(), %(thread_id)s, %(media_group)s);
    """

    params = {
        "message_id": str(message_id),
        "user_id": str(user_id),
        "thread_id": str(thread_id),
        "media_group": media_group
    }

    conn = await ConnectionManager().connection()
    async with conn.cursor() as cur:
        await cur.execute(stmt, params)


async def get_post(message_id: int | str) -> Post:
    """Fetch post"""

    stmt = """
    SELECT message_id, user_id, date, comment_thread_id, comment_count, popular_id, best_id, media_group
    FROM posts WHERE message_id = %(message_id)s;
    """

    params = {
        "message_id": str(message_id),
    }

    conn = await ConnectionManager().connection()
    async with conn.cursor() as cur:
        await cur.execute(stmt, params)
        result = await cur.fetchone()

    return Post(**result) if result else None


async def get_post_by_popular_id(popular_id: int | str) -> Post:
    """Fetch post by popular_id"""

    stmt = """
    SELECT message_id, user_id, date, comment_thread_id, comment_count, popular_id, best_id, media_group
    FROM posts WHERE popular_id = %(popular_id)s;
    """

    params = {
        "popular_id": str(popular_id),
    }

    conn = await ConnectionManager().connection()
    async with conn.cursor() as cur:
        await cur.execute(stmt, params)
        result = await cur.fetchone()

    return Post(**result) if result else None

async def get_post_by_best_id(best_id: int | str) -> Post:
    """Fetch post by best_id"""

    stmt = """
    SELECT message_id, user_id, date, comment_thread_id, comment_count, popular_id, best_id, media_group
    FROM posts WHERE best_id = %(best_id)s;
    """

    params = {
        "best_id": str(best_id),
    }

    conn = await ConnectionManager().connection()
    async with conn.cursor() as cur:
        await cur.execute(stmt, params)
        result = await cur.fetchone()

    return Post(**result) if result else None


async def get_post_by_media_group(media_group: str) -> Post:
    """Fetch post by group_id"""

    stmt = """
    SELECT message_id, user_id, date, comment_thread_id, comment_count, popular_id, best_id, media_group
    FROM posts WHERE media_group = %(media_group)s;
    """

    params = {
        "media_group": media_group,
    }

    conn = await ConnectionManager().connection()
    async with conn.cursor() as cur:
        await cur.execute(stmt, params)
        result = await cur.fetchone()

    return Post(**result) if result else None


async def increase_comments_counter(thread_id: int | str) -> Post:
    """Increases comments counter by 1"""

    stmt = """
    UPDATE posts SET comment_count = comment_count + 1 WHERE comment_thread_id = %(thread_id)s
    RETURNING message_id, user_id, date, comment_thread_id, comment_count, popular_id, best_id, media_group;
    """

    params = {
        "thread_id": str(thread_id),
    }

    conn = await ConnectionManager().connection()
    async with conn.cursor() as cur:
        await cur.execute(stmt, params)
        result = await cur.fetchone()

    return Post(**result) if result else None


async def get_post_count_for_user(user_id: int | str) -> int:
    """Fetch post count for last 24 hours"""

    stmt = "SELECT posts_count FROM posts_count_for_last_day WHERE user_id = %(user_id)s"

    params = {
        "user_id": str(user_id),
    }

    conn = await ConnectionManager().connection()
    async with conn.cursor() as cur:
        await cur.execute(stmt, params)
        result = await cur.fetchone()

    return result[0] if result else 0


async def add_to_popular(message_id: int | str, popular_id: int | str):
    stmt = """
    UPDATE posts SET popular_id = %(popular_id)s WHERE message_id = %(message_id)s;
    """

    params = {
        "message_id": str(message_id),
        "popular_id": str(popular_id),
    }

    conn = await ConnectionManager().connection()
    async with conn.cursor() as cur:
        await cur.execute(stmt, params)

async def add_to_best(message_id: int | str, best_id: int | str):
    stmt = """
    UPDATE posts SET best_id = %(best_id)s WHERE message_id = %(message_id)s;
    """

    params = {
        "message_id": str(message_id),
        "best_id": str(best_id),
    }

    conn = await ConnectionManager().connection()
    async with conn.cursor() as cur:
        await cur.execute(stmt, params)
