ALTER TABLE posts RENAME COLUMN comments TO comment_count;
INSERT INTO migrations (version) VALUES (7);
