CREATE INDEX votes_message_vote ON votes (message_id, vote);
INSERT INTO migrations (version) VALUES (5);
