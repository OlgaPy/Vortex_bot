ALTER TABLE posts ADD COLUMN media_group varchar(32);
INSERT INTO migrations (version) VALUES (4);