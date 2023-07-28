CREATE TABLE votes (
    message_id integer NOT NULL,
    user_id integer NOT NULL,
    vote varchar(1),
    PRIMARY KEY (message_id, user_id)
);