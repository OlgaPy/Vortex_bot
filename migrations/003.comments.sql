ALTER TABLE posts ADD COLUMN comment_thread_id varchar(32);
ALTER TABLE posts ADD COLUMN comments integer DEFAULT 0;
ALTER TABLE posts ADD COLUMN popular_id varchar(32);
INSERT INTO migrations (version) VALUES (3);