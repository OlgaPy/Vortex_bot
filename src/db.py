import aiopg


def build_dsn():
    dbname = "main"
    user = "postgres"
    password = "postgres"
    host = "db"
    port = 5432
    return f"dbname={dbname} user={user} password={password} host={host} port={port}"


async def get_user_vote(message_id: int | str, user_id: int | str) -> str | None:
    stmt = """
    SELECT vote FROM votes WHERE (message_id, user_id) = (%(message_id)s, %(user_id)s);
    """
    params = {
        "message_id": message_id,
        "user_id": user_id
    }
    async with aiopg.connect(build_dsn()) as conn:
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

    async with aiopg.connect(build_dsn()) as conn:
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

    async with aiopg.connect(build_dsn()) as conn:
        async with conn.cursor() as cur:
            await cur.execute(stmt, params)
            result = await cur.fetchone()

    return (result[0], result[1]) if result else None
