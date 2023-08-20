DO
$$
BEGIN
 FOR i IN 1..30 LOOP
    INSERT INTO public.votes (
        message_id,
        user_id,
        vote
    )
    VALUES (
        16, --message_id here
        i,
        '+'
    );
 END LOOP;
END
$$
