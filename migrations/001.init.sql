CREATE TABLE votes (
    message_id varchar(32) NOT NULL,
    user_id varchar(32) NOT NULL,
    vote varchar(1),
    PRIMARY KEY (message_id, user_id)
);

CREATE TABLE posts (
    message_id varchar(32) PRIMARY KEY,
    user_id varchar(32) NOT NULL,
    date timestamp NOT NULL
);

CREATE VIEW posts_count_for_last_day AS
    SELECT user_id, count(*) AS posts_count
    FROM posts
    WHERE date <= now() AND date > (now() - interval '1' DAY)
    GROUP BY user_id;