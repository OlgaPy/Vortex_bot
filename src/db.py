import aiopg
from typing import Optional


def build_dsn():
    dbname = "main"
    user = "postgres"
    password = "postgres"
    host = "localhost"
    port = 5430
    return f"dbname={dbname} user={user} password={password} host={host} port={port}"


class ConnectionManager:
    _instance: Optional['ConnectionManager'] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self._connection: aiopg.Connection | None = None

    async def __aenter__(self):
        if self._connection is None or self._connection.closed:
            self._connection = await aiopg.connect(build_dsn())
        return self._connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._connection is not None and not self._connection.closed:
            await self._connection.close()


async def get_user_vote(message_id: int | str, user_id: int | str) -> str | None:
    stmt = """
    SELECT vote FROM votes WHERE (message_id, user_id) = (%(message_id)s, %(user_id)s);
    """
    params = {
        "message_id": message_id,
        "user_id": user_id
    }
    async with ConnectionManager() as conn:
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
        "message_id": message_id,
        "user_id": user_id,
        "vote": vote
    }

    async with ConnectionManager() as conn:
        async with conn.cursor() as cur:
            await cur.execute(stmt, params)

    return True


async def get_rating(message_id: int | str) -> tuple[int, int]:
    stmt = """
    WITH 
        up_votes AS (
            SELECT count(*) AS votes FROM votes WHERE message_id = %(message_id)s AND vote = '+'
        ),
        down_votes AS (
            SELECT count(*) votes FROM votes WHERE message_id = %(message_id)s AND vote = '-'
        )
    SELECT u.votes AS "up_votes", d.votes AS "down_votes" 
    FROM up_votes AS u 
    CROSS JOIN down_votes AS d;
    """

    params = {
        "message_id": message_id,
    }

    async with ConnectionManager() as conn:
        async with conn.cursor() as cur:
            await cur.execute(stmt, params)
            result = await cur.fetchone()

    return (result[0], result[1]) if result else None
